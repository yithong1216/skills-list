"""Offline notification regressions; set AUTODL_SKILL_ROOT to test another copy."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import smtplib
import tempfile
import threading
import time
import unittest
from unittest import mock


ROOT = Path(os.environ.get("AUTODL_SKILL_ROOT", Path(__file__).resolve().parents[1]))


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


watch = load_helper("watch_progress_notify")
mail = load_helper("send_email_notify")


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "train.log"
        self.progress = self.root / "progress.txt"
        self.status = self.root / "exit_code.txt"
        self.state = self.root / "notify_state.json"
        self.args = argparse.Namespace(
            project="offline", run_id="run-a", run_root=str(self.root),
            log_file=str(self.log), progress_file=str(self.progress),
            exit_code_file=str(self.status), state_file=str(self.state),
            thresholds="50", env_file="", dry_run=False, tail_lines=0,
            terminal_attempts=3, retry_interval=0, interval=0, once=False,
        )
        self.receipts = []
        self.transport_code = 0
        self.transport_delay = 0
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {}, clear=True).start()
        mock.patch.object(watch.subprocess, "run", side_effect=self.transport).start()

    def transport(self, command, **kwargs):
        # This is the only external boundary replaced; state and parsing are real.
        time.sleep(self.transport_delay)
        self.receipts.append((command[command.index("--run-id") + 1],
                              command[command.index("--event") + 1]))
        return subprocess.CompletedProcess(command, self.transport_code)

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return watch.check_once(self.args)

    def sent(self, run_id="run-a"):
        if not self.state.exists():
            return []
        data = json.loads(self.state.read_text(encoding="utf-8"))
        if "runs" in data:
            return data["runs"].get(json.dumps(["offline", run_id]), {}).get("sent", [])
        return data.get("sent", [])

    def test_nested_progress_and_accuracy_are_not_overall_progress(self):
        self.assertIsNone(watch.parse_progress_from_text(
            "Epoch 2/20\nvalidation 100%\naccuracy: 99.8%\nStep 90/100\n"))

    def test_explicit_log_marker_uses_latest_value_not_maximum(self):
        self.assertEqual(watch.parse_progress_from_text(
            "AUTODL_PROGRESS=80%\nAUTODL_PROGRESS=20%\naccuracy 99%"), 20)

    def test_dedicated_progress_file_accepts_bare_percentage(self):
        self.progress.write_text("37.5\n", encoding="utf-8")
        self.assertEqual(watch.parse_progress(str(self.progress), "validation 100%"), 37.5)

    def test_recovered_error_without_exit_marker_is_not_terminal(self):
        self.assertEqual(watch.detect_failure(
            "ERROR temporary fetch failure\nretry succeeded\ntraining continues", str(self.status)),
            (False, ""))

    def test_malformed_exit_marker_is_not_a_failed_experiment(self):
        self.status.write_text("pending", encoding="utf-8")
        self.assertEqual(watch.detect_failure("", str(self.status)), (False, ""))

    def test_failed_delivery_remains_retryable(self):
        self.progress.write_text("75%", encoding="utf-8")
        self.transport_code = 1
        self.check()
        self.assertEqual(self.sent(), [])
        self.transport_code = 0
        self.check()
        self.assertEqual(self.sent(), ["progress_50"])
        self.assertEqual(self.receipts, [("run-a", "progress_50")] * 2)

    def test_dry_run_does_not_create_or_modify_state(self):
        self.progress.write_text("75%", encoding="utf-8")
        self.args.dry_run = True
        self.check()
        self.assertFalse(self.state.exists())

    def test_dry_run_preserves_existing_production_state_bytes(self):
        original = b'{"sent": ["keep this legacy state untouched"]}'
        self.state.write_bytes(original)
        self.progress.write_text("75%", encoding="utf-8")
        self.args.dry_run = True
        self.check()
        self.assertEqual(self.state.read_bytes(), original)

    def test_state_deduplication_is_scoped_to_project_and_run(self):
        self.progress.write_text("75%", encoding="utf-8")
        self.check()
        self.args.run_id = "run-b"
        self.check()
        self.args.run_id = "run-a"
        self.check()
        self.assertEqual(self.receipts, [("run-a", "progress_50"), ("run-b", "progress_50")])

    def test_failed_terminal_status_never_sends_late_progress(self):
        self.progress.write_text("100%", encoding="utf-8")
        self.status.write_text("2", encoding="utf-8")
        self.check()
        self.check()
        self.assertEqual(self.receipts, [("run-a", "failed")])

    def test_success_sends_only_one_terminal_notification(self):
        self.progress.write_text("100%", encoding="utf-8")
        self.status.write_text("0", encoding="utf-8")
        self.check()
        self.check()
        self.assertEqual(self.receipts, [("run-a", "success")])

    def test_concurrent_checks_do_not_duplicate_notifications(self):
        self.progress.write_text("75%", encoding="utf-8")
        self.transport_delay = 0.1
        gate = threading.Barrier(2)
        errors = []

        def worker():
            try:
                gate.wait(timeout=5)
                watch.check_once(self.args)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(self.receipts, [("run-a", "progress_50")])

    def test_corrupt_state_fails_closed_without_sending(self):
        self.state.write_text('{"sent": [', encoding="utf-8")
        self.progress.write_text("75%", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(self.receipts, [])

    def test_failed_state_replacement_preserves_last_committed_state(self):
        self.state.write_text('{"sent": ["old"]}', encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                watch.save_state(self.state, {"sent": ["new"]})
        self.assertEqual(json.loads(self.state.read_text(encoding="utf-8")), {"sent": ["old"]})

    def test_email_log_tail_is_off_by_default(self):
        self.log.write_text("PRIVATE_CUSTOM_SENTINEL", encoding="utf-8")
        output = io.StringIO()
        with mock.patch("sys.argv", ["send_email_notify.py", "--project", "offline",
                                     "--run-id", "run-a", "--event", "failed", "--dry-run",
                                     "--log-file", str(self.log)]), contextlib.redirect_stdout(output):
            mail.main()
        self.assertNotIn("PRIVATE_CUSTOM_SENTINEL", output.getvalue())

    def test_zero_tail_lines_never_exports_entire_log(self):
        self.log.write_text("PRIVATE_CUSTOM_SENTINEL", encoding="utf-8")
        self.assertEqual(mail.read_tail(str(self.log), 0), "")

    def test_terminal_delivery_failures_stop_after_bounded_attempts(self):
        self.status.write_text("2", encoding="utf-8")
        self.transport_code = 1
        sleeps = []

        def no_wait(seconds):
            sleeps.append(seconds)
            if len(sleeps) > 6:
                raise RuntimeError("watcher did not terminate")

        self.transport_delay = 0
        # Transport does not sleep here because the real loop's sleep is replaced.
        def fail_transport(command, **kwargs):
            self.receipts.append(("run-a", command[command.index("--event") + 1]))
            return subprocess.CompletedProcess(command, 1)

        with mock.patch("sys.argv", ["watch_progress_notify.py", "--project", "offline",
                                     "--run-id", "run-a", "--state-file", str(self.state),
                                     "--exit-code-file", str(self.status)]), \
                mock.patch.object(watch.time, "sleep", side_effect=no_wait), \
                mock.patch.object(watch.subprocess, "run", side_effect=fail_transport), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                result = watch.main()
            except RuntimeError:
                result = "did not terminate"
        self.assertEqual(result, 1)
        self.assertEqual(self.receipts, [("run-a", "failed")] * 3)
        self.assertEqual(self.sent(), [])

    def test_partial_smtp_refusal_is_not_reported_as_success(self):
        connection = mock.MagicMock()
        connection.__enter__.return_value = connection
        connection.send_message.return_value = {"refused@example.invalid": (550, b"refused")}
        with mock.patch.object(mail.smtplib, "SMTP", return_value=connection):
            with self.assertRaises(smtplib.SMTPRecipientsRefused):
                mail.send_message(mail.EmailMessage(), {
                    "SMTP_HOST": "smtp.invalid", "SMTP_PORT": "587", "SMTP_USER": "fake",
                    "SMTP_PASSWORD": "fake", "SMTP_TLS": "false",
                })

    def test_legacy_unscoped_state_is_rejected_without_delivery(self):
        self.state.write_text('{"sent": ["progress_50"]}', encoding="utf-8")
        self.progress.write_text("75%", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(self.receipts, [])

    def test_state_identity_mismatch_is_rejected_without_delivery(self):
        data = {"schema_version": 2, "runs": {json.dumps(["offline", "run-a"]): {
            "project": "other-project", "run_id": "run-a", "sent": [],
        }}}
        self.state.write_text(json.dumps(data), encoding="utf-8")
        self.progress.write_text("75%", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(self.receipts, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
