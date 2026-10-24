# Compact experiment decision record

Use inside the existing project runbook when work spans experiments or turns.
Reference existing artifacts instead of copying large logs. Populate only fields
needed for the decision; do not require a new database or tooling framework.

```text
Contract/version: target, guardrails, protocol, scope, budget
Hypothesis: causal link being tested; strongest alternative; strongest shortcut
Prior attempts: comparable run IDs, validity, results, rejected explanations
New premise: what differs and why that should change an observable
Preflight: identifiability verdict; independent units + noise floor; prior art
Experiment: one comparison; controls; sample/split and evaluator identities
Provenance: code/config/checkpoint/data identifiers needed to reproduce it
Predeclared rule: useful effect vs noise floor, guardrails, operating point,
                  liveness metric + abort, budget, inconclusive handling
Result: artifact path; metrics/counts/uncertainty; relevant exact error if invalid
Verdict: INVALID / NEGATIVE / INCONCLUSIVE / SUPPORTS NEXT STAGE / TARGET MET
Belief update: supported link, rejected link, remaining uncertainty
Superseded: earlier reported figures this replaces; quarantine path for invalid ones
Next action: bounded action; reopening condition for any closed branch
```

For a resumed task, read the latest record and verify any run/artifact state that
could have changed. Do not infer a completed experiment from a launch command or
a plan. Retain negative results when the mechanism is renamed.

When a defect invalidates earlier numbers, move those artifacts to a
`do_not_cite` directory and name, in the record, every previously reported figure
they replace. Invalid numbers left in place get re-cited and restart the branch.
