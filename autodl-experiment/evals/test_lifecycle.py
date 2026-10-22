"""Offline lifecycle regression tests; use AUTODL_SKILL_ROOT to test a snapshot.

Runs real Bash scripts with local fake SMTP/GPU/conda dependencies. No SSH,
network, real email, package installation, or broad process termination.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(os.environ.get("AUTODL_SKILL_ROOT", Path(__file__).resolve().parents[1]))
BASH = os.environ.get("BASH_BIN") or shutil.which("bash")
if os.name == "nt":
    BASH = os.environ.get("BASH_BIN", r"C:\Program Files\Git\bin\bash.exe")


def posix(path: Path) -> str:
    value = path.resolve().as_posix()
    return "/" + value[0].lower() + value[2:] if os.name == "nt" else value


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path.cwd() / "work" / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="autodl-lifecycle-", dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.run = self.base / "run"
        self.calls = self.base / "calls.txt"
        self.env = os.environ.copy()
        for name in ("NOTIFY_ENABLED", "PYTHON_BIN", "CONDA_ENV", "CONDA_SH", "TMUX", "STY", "SESSION_KIND", "SESSION_NAME", "HF_HOME", "HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
            self.env.pop(name, None)
        self.env.update(PATH=str(self.bin) + os.pathsep + self.env["PATH"],
                        TEST_CALLS=posix(self.calls), PYTHONUNBUFFERED="1")
        # Git Bash prepends its own utilities to imported Windows PATH. Restore
        # fixture priority inside each noninteractive shell for reliable doubles.
        self.env["BASH_ENV"] = posix(write(self.base / "test-env.sh", f'export PATH="{posix(self.bin)}:/usr/bin:/bin:$PATH"\n'))
        self.fake_python = write(self.bin / "python", """#!/usr/bin/env bash
name="${1##*/}"
printf '%s' "$name" >> "$TEST_CALLS"
printf '|%s' "${@:2}" >> "$TEST_CALLS"
printf '\\n' >> "$TEST_CALLS"
if [[ "$name" == watch_progress_notify.py ]]; then
  exit_file=''
  while (( $# )); do
    if [[ "$1" == --exit-code-file ]]; then exit_file="$2"; shift; fi
    shift
  done
  if [[ -n "$exit_file" ]]; then
    for ((i=0; i<100; i++)); do
      if [[ -s "$exit_file" ]]; then
        printf 'observed_exit=%s\\n' "$(cat "$exit_file")" >> "$TEST_CALLS"
        exit 0
      fi
      sleep .03
    done
    printf 'watcher-timeout\\n' >> "$TEST_CALLS"
    exit 8
  fi
fi
exit 0
""")
        for name in ("tmux", "screen"):
            write(self.bin / name, "#!/usr/bin/env bash\nexit 1\n")
        write(self.bin / "nvidia-smi", "#!/usr/bin/env bash\nprintf 'Fake GPU, 0 MiB, 24576 MiB, 0 %%\\n'\n")

    def shell(self, script: Path, *args: str, env=None):
        return subprocess.run([BASH, posix(script), *map(str, args)], env=env or self.env,
                              cwd=self.base, capture_output=True, text=True, timeout=15)

    def wrapped(self, payload="echo current-run; exit 0", *, notify=None):
        script = write(self.base / "payload.sh", "#!/usr/bin/env bash\n" + payload + "\n")
        env = self.env.copy()
        if notify is not None:
            env["NOTIFY_ENABLED"] = str(notify)
        return self.shell(ROOT / "scripts/wrap_existing_run.sh", posix(script), "run",
                          "fixture", "run-1", posix(self.base / "notify.env"), "50,100", env=env)

    def test_reused_run_is_rejected_without_overwriting_prior_evidence(self):
        write(self.run / "logs/main.log", "old-run-evidence\n")
        write(self.run / "exit_code.txt", "0\n")
        write(self.run / "notify_state.json", '{"sent":["success"]}\n')
        result = self.wrapped()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.run / "logs/main.log").read_text(), "old-run-evidence\n")
        self.assertEqual((self.run / "exit_code.txt").read_text(), "0\n")
        self.assertFalse(self.calls.exists(), "Reuse must be rejected before notifying")

    def test_notifications_are_off_by_default(self):
        result = self.wrapped()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists(), "No sender/watcher may run without explicit opt-in")

    def test_exit_seven_is_preserved(self):
        result = self.wrapped("echo payload-failed; exit 7", notify=0)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual((self.run / "exit_code.txt").read_text().strip(), "7")

    def test_exit_zero_is_preserved(self):
        result = self.wrapped("echo payload-ok; exit 0", notify=0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.run / "exit_code.txt").read_text().strip(), "0")

    def test_one_watcher_observes_terminal_exit_marker(self):
        result = self.wrapped("sleep .1; exit 7", notify=1)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        calls = self.calls.read_text().splitlines()
        watchers = [line for line in calls if line.startswith("watch_progress_notify.py|")]
        self.assertEqual(len(watchers), 1, calls)
        self.assertIn("--exit-code-file|", watchers[0])
        self.assertNotIn("--once", watchers[0])
        self.assertIn("observed_exit=7", calls)

    def test_marker_write_failure_stops_owned_watcher_without_claiming_success(self):
        write(self.bin / "mv", "#!/usr/bin/env bash\nexit 9\n")
        result = self.wrapped(notify=1)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.run / "exit_code.txt").exists())
        self.assertIn("status=unknown", result.stderr)
        self.assertNotIn("watcher-timeout", self.calls.read_text())

    def test_prerun_configs_are_allowed_in_fresh_run(self):
        write(self.run / "configs/config.yaml", "fixture: true\n")
        result = self.wrapped()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.run / "configs/config.yaml").read_text(), "fixture: true\n")

    def test_run_identity_is_recorded(self):
        result = self.wrapped()
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = self.run / "run_metadata.txt"
        self.assertTrue(metadata.exists(), "No process/run identity persisted")
        fields = dict(line.split("=", 1) for line in metadata.read_text().splitlines())
        self.assertEqual(fields["run_id"], "run-1")
        self.assertTrue(fields["wrapper_pid"].isdigit())
        self.assertTrue(fields["worker_pid"].isdigit())

    def test_claim_rejects_interrupted_run_without_other_evidence(self):
        (self.run / ".run_claim").mkdir(parents=True)
        result = self.wrapped()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.run / "logs/main.log").exists())

    def test_wrapper_uses_selected_notification_interpreter(self):
        selected = write(self.bin / "selected-python", f'#!/usr/bin/env bash\nprintf "selected\\n" >> "$TEST_CALLS"\nexec bash "{posix(self.fake_python)}" "$@"\n')
        self.env["PYTHON_BIN"] = posix(selected)
        result = self.wrapped(notify=1)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls.read_text().splitlines().count("selected"), 2)

    def test_tmux_session_identity_is_detected(self):
        write(self.bin / "tmux", '#!/usr/bin/env bash\n[[ "$1" == display-message ]] || exit 1\nprintf "fixture-session\\n"\n')
        self.env["TMUX"] = "fixture-socket,1,0"
        result = self.wrapped()
        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = self.run / "run_metadata.txt"
        self.assertTrue(metadata.exists())
        fields = dict(line.split("=", 1) for line in metadata.read_text().splitlines())
        self.assertEqual(fields["session_kind"], "tmux")
        self.assertEqual(fields["session_name"], "fixture-session")

    def render_template(self, command: str):
        source = (ROOT / "assets/run.sh.template").read_text(encoding="utf-8")
        replacements = {"<PROJECT_NAME>": "fixture", "<RUN_ID>": "run-1",
                        "<CONDA_ENV>": "fixture-env", "<THRESHOLDS>": "50,100",
                        "<SKILL_SCRIPT_DIR>": posix(ROOT / "scripts"), "<LAUNCH_COMMAND>": command,
                        "/root/autodl-tmp/${PROJECT_NAME}": posix(self.base),
                        "/etc/network_turbo": posix(self.base / "absent-network-turbo")}
        for old, new in replacements.items():
            source = source.replace(old, new)
        # Git Bash sandbox denies mkdir -p traversal of absolute profile paths.
        source = source.replace(f'RUN_ROOT="{posix(self.base)}/runs/${{RUN_ID}}"',
                                'RUN_ROOT="runs/${RUN_ID}"')
        self.run = self.base / "runs/run-1"
        self.env["RUN_ROOT"] = "runs/run-1"
        self.env["PROJECT_DIR"] = posix(self.base)
        self.env["CONDA_SH"] = posix(write(self.base / "conda.sh", "conda() { return 9; }\n"))
        return write(self.base / "rendered-run.sh", source)

    def test_template_setup_failure_has_terminal_marker(self):
        script = self.render_template("echo should-not-run")
        result = self.shell(script)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.run / "exit_code.txt").exists(), "Setup failure was not recorded")
        self.assertEqual((self.run / "exit_code.txt").read_text().strip(), "9")
        self.assertNotIn("should-not-run", (self.run / "logs/main.log").read_text())

    def test_template_successful_setup_propagates_payload_failure(self):
        script = self.render_template("echo payload-started; exit 7")
        write(self.base / "conda.sh", "conda() { return 0; }\n")
        result = self.shell(script)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual((self.run / "exit_code.txt").read_text().strip(), "7")
        self.assertIn("payload-started", (self.run / "logs/main.log").read_text())

    def test_template_explicit_python_skips_conda_and_preserves_cache(self):
        script = self.render_template('printf "cache=%s legacy=%s\\n" "${HF_HUB_CACHE:-unset}" "${HUGGINGFACE_HUB_CACHE:-unset}"; "$PYTHON_BIN" -V')
        self.env["PYTHON_BIN"] = posix(Path(sys.executable))
        self.env["HF_HUB_CACHE"] = "/already/populated/cache"
        result = self.shell(script)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        log = (self.run / "logs/main.log").read_text()
        self.assertIn("cache=/already/populated/cache legacy=unset", log)

    def test_template_does_not_invent_a_new_cache_root(self):
        script = self.render_template('printf "home=%s cache=%s\\n" "${HF_HOME:-unset}" "${HF_HUB_CACHE:-unset}"')
        write(self.base / "conda.sh", "conda() { return 0; }\n")
        result = self.shell(script)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("home=unset cache=unset", (self.run / "logs/main.log").read_text())

    def test_interrupted_wrapper_does_not_claim_nested_child_terminated(self):
        child_done = self.base / "child-done.txt"
        payload = write(self.base / "nested.sh", f'#!/usr/bin/env bash\n(sleep 1; echo done > "{posix(child_done)}") &\nwait\n')
        proc = subprocess.Popen([BASH, posix(ROOT / "scripts/wrap_existing_run.sh"), posix(payload),
                                 "run", "fixture", "run-1"], env=self.env, cwd=self.base,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 5
        metadata = self.run / "run_metadata.txt"
        while time.monotonic() < deadline:
            if metadata.exists() and "worker_pid=" in metadata.read_text():
                break
            time.sleep(.02)
        fields = dict(line.split("=", 1) for line in metadata.read_text().splitlines())
        signal = write(self.base / "signal.sh", '#!/usr/bin/env bash\nkill -TERM "$1"\n')
        sent = self.shell(signal, fields["wrapper_pid"])
        self.assertEqual(sent.returncode, 0, sent.stderr)
        output, errors = proc.communicate(timeout=5)
        while not child_done.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(child_done.exists(), "Fixture child must finish before cleanup")
        self.assertEqual(proc.returncode, 143, output + errors)
        self.assertFalse((self.run / "exit_code.txt").exists(), "Nested child was not accounted for; terminal status would be false")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertIn("status=unknown", result.stdout)

    def terminal_metadata(self):
        write(self.run / "run_metadata.txt", "metadata_version=1\nrun_id=run-1\nproject=fixture\nwrapper_pid=999999999\n")

    def test_monitor_reports_unknown_when_no_process_or_terminal_proof(self):
        write(self.run / "logs/main.log", "100% old-looking-log\n")
        write(self.run / "run_metadata.txt", "run_id=run-1\nwrapper_pid=999999999\nwrapper_start_ticks=1\nworker_pid=999999998\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertIn("status=unknown", result.stdout.lower())

    def test_monitor_uses_recorded_exit_not_log_success(self):
        self.terminal_metadata()
        write(self.run / "logs/main.log", "100% success\n")
        write(self.run / "exit_code.txt", "7\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertIn("status=failed", result.stdout.lower())
        self.assertIn("exit_code=7", result.stdout)

    def test_monitor_zero_exit_is_process_success_despite_error_log(self):
        self.terminal_metadata()
        write(self.run / "logs/main.log", "ERROR from a recovered retry\n")
        write(self.run / "exit_code.txt", "0\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertEqual(result.returncode, 0)
        self.assertIn("status=succeeded", result.stdout)

    def test_monitor_invalid_marker_is_unknown(self):
        self.terminal_metadata()
        write(self.run / "exit_code.txt", "success\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unknown", result.stdout)

    def test_monitor_standalone_exit_zero_without_identity_is_unknown(self):
        write(self.run / "exit_code.txt", "0\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unknown", result.stdout)
        self.assertIn("observed_exit_code=0", result.stdout)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc identity is unavailable in Git Bash")
    def test_monitor_verifies_live_linux_process_identity(self):
        pid = os.getpid()
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        write(self.run / "run_metadata.txt", f"metadata_version=1\nrun_id=run-1\nproject=fixture\nwrapper_pid={pid}\nwrapper_start_ticks={fields[19]}\nboot_id={boot}\n")
        result = self.shell(ROOT / "scripts/monitor_run.sh", posix(self.run))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("status=running", result.stdout)

    def preflight_env(self, *, cuda_available=True, operation_error=False):
        env = self.env.copy()
        env["PYTHON_BIN"] = posix(Path(sys.executable))
        package_dir = self.base / "packages"
        write(package_dir / "torch.py", f"""__version__ = 'test-torch'
class version:
    cuda = 'test-cuda'
class cuda:
    @staticmethod
    def is_available(): return {cuda_available!r}
    @staticmethod
    def device_count(): return 1
    @staticmethod
    def get_device_name(index): return 'Fake GPU'
    @staticmethod
    def synchronize(): pass
class Tensor:
    def sum(self): return self
    def item(self): return 1
def ones(*args, **kwargs):
    if {operation_error!r}: raise RuntimeError('CUDA operation failed')
    return Tensor()
""")
        env["PYTHONPATH"] = str(package_dir)
        env["HTTPS_PROXY"] = "http://secret-user:secret-password@proxy.invalid:8080"
        return env

    def test_preflight_hides_proxy_credentials(self):
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=self.preflight_env())
        self.assertNotIn("secret-password", result.stdout + result.stderr)
        self.assertNotIn("secret-user", result.stdout + result.stderr)

    def test_preflight_identifies_exact_python_and_cuda_health(self):
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=self.preflight_env())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(sys.executable, result.stdout)
        self.assertIn("readiness=ready", result.stdout.lower())
        self.assertIn("cuda_smoke=ok", result.stdout.lower())

    def test_preflight_inventory_does_not_hide_unavailable_cuda(self):
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=self.preflight_env(cuda_available=False))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("readiness=unready", result.stdout.lower())

    def test_preflight_cuda_operation_must_work(self):
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=self.preflight_env(operation_error=True))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("readiness=unready", result.stdout.lower())

    def test_preflight_conda_activation_failure_does_not_fall_back(self):
        env = self.env.copy()
        env["CONDA_SH"] = posix(write(self.base / "conda.sh", "conda() { return 9; }\n"))
        env["CONDA_ENV"] = "fixture-env"
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readiness=unready", result.stdout)
        self.assertFalse(self.calls.exists(), "Activation failure must not run fallback python")

    def test_preflight_requested_conda_script_missing_does_not_fall_back(self):
        self.env["CONDA_SH"] = posix(self.base / "missing-conda.sh")
        result = self.shell(ROOT / "scripts/preflight_autodl.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists(), "Missing requested conda setup must not select fallback python")

    def test_preflight_driver_failure_is_unready(self):
        write(self.bin / "nvidia-smi", "#!/usr/bin/env bash\nexit 9\n")
        result = self.shell(ROOT / "scripts/preflight_autodl.sh", env=self.preflight_env())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readiness=unready", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
