---
name: dl-first-principles
description: >
  Use when designing or improving a deep-learning model, head, loss, training
  recipe, or research direction against a metric target: "how do I beat SOTA on
  X", "design a head/loss for Y", "my mAP/recall/AUROC is stuck", "should I add
  this module / a transformer / a bigger backbone", "training plateaued", "why
  did this ablation not move anything". Also use when interpreting a probe,
  oracle, ablation, control, or benchmark number before acting on it; when a
  gate, submission, or evaluation result disagrees with expectation; and when
  the same class of intervention has failed more than once or a closed branch is
  being reopened.
---

# DL First Principles

Derive the smallest intervention from an evidenced bottleneck. Two things make
that fail in practice, and both come before the reasoning:

**A number you have not controlled is not evidence.** **A gap you cannot resolve
is not a result.**

So the order is: recover what is closed → kill what is unidentifiable or
unmeasurable → establish the number is real → locate the limiting link against
the strongest shortcut → run one falsifiable test → close the branch.

## 1. Recover the decision state

Start from the user's goal and the project's runbook, results, code, and prior
decisions. Use memory to locate evidence; verify consequential facts against
artifacts. Keep protocols and revisions separate. If history is unavailable, mark
it unknown rather than assuming a fresh start.

```text
Target: metric current -> required; dataset/split/unit of evaluation
Guardrails: protected metrics, operating point, latency, data and compute budget
Scope: analysis, bounded probe, training, or integration; existing authorization
State: last valid result; failed hypotheses; next unresolved question
```

Before proposing anything, match its **mechanism, inputs, supervision,
representation, and evaluation protocol** against prior attempts. A new paper,
module name, loss weight, or run ID does not make a failed mechanism new. Reopen
a closed branch only with a concrete changed premise and a predicted observable
effect. Do not generalize a failure across protocols without checking
comparability.

## 2. Preflight: three desk checks that close branches for free

Minutes of work here routinely close weeks of GPU work. Run all three before
authorizing compute.

**Identifiability — can the labels name the thing without naming the class?**
Build the support table: for the attribute/behavior you want to learn, list which
classes, sites, or sources sit on each side. If one side holds a single class, a
perfect predictor of that attribute is a class detector, and no architecture,
loss, or regularizer fixes it. Check supra-class groupings too (nationality,
source domain, capture site, sensor) — removing class identity leaves those
intact. Renaming a class label as an instance attribute adds no instance
evidence.

**Power — how many independent units carry the metric, and what is the noise
floor?** Count *independent* units (distinct scenes, sites, identities, source
images), not boxes or crops. Measure the run-to-run floor once from two
identically-configured runs and reuse it for the project. If the planned effect
is smaller than the floor, or the target stratum is a few dozen boxes from a
handful of scenes, the experiment cannot answer the question at any budget —
change the axis, pool, or replicate before spending.

**Prior art — what is this already called?** Search papers and OSS for the named
method, whether code or weights exist, and what it reported, then state the
specific adaptation. Do this at proposal time. It does not replace a ready
experiment: once a decision is concrete and authorized, run it instead of
surveying again.

Each check has a real STOP outcome. When one fires, say what it closes and what
evidence would reopen it.

## 3. Establish that the number is real

Separate **measurement/code failure** from **a valid negative learning result**.
Dataloaders, label parsing, caching, score transforms, guards, and evaluators are
in scope when they determine what was actually tested. Trace:

```text
config/checkpoint -> data and targets -> forward/loss -> actual score
                 -> filtering/decision/output -> evaluator
```

Required before reading any results table:

- **Null controls must degrade.** Confirm the shuffled / permuted / random /
  label-only arm scores *worse* than the real one. A control that matches the
  treatment to many digits means the channel is dead, not that the effect is
  robust.
- **Controls must enact their counterfactual.** A control sharing a code branch
  with the treatment *is* the treatment. A null built with a different encoder,
  width, or calibration differs in geometry as well as in the intended factor.
  Inspect tensor values and their consumption on a few samples.
- **One evaluator, one config, one ground truth, fingerprinted.** Freeze and hash
  config/evaluator/GT identity at capture and assert it is unchanged across every
  arm. Never edit a file a running job re-reads.
- **One number per quantity.** If report, CSV, and gate read different keys they
  will eventually state opposite conclusions; reconcile against the authoritative
  evaluator before choosing a direction.
- **The changed component is active and consumed.** Perturb it and confirm the
  metric responds. Silent no-ops are common: a guard that disables augmentation,
  a head trained but ignored at inference, a flag dropped to route around a
  crash, a transform whose build failure was swallowed by a log line.
- **Exit 0 is not success.** Frameworks train through NaN and evaluate corpses.

Label material claims **measured**, **code-inspected**, **literature-supported**,
or **hypothesis**, and distinguish historical artifacts from a fresh run.
Literature motivates a mechanism; it does not establish that this dataset or
implementation supplies its prerequisites.

Match evidence to the question: a smoke subset can diagnose wiring; a gate needs
complete identity-matched outputs, the correct evaluator, and full provenance.
Do not impose a full capture protocol on a small analytic question.

## 4. Locate the limiting link

Decompose only the live difficulties. Use the axes as a checklist, not an essay
prompt:

| Axis | Diagnostic question |
| --- | --- |
| Input signal | Is the task-relevant information observable at native scale? |
| Representation / geometry | Does the active representation preserve that information and the required structure or invariance? |
| Supervision / identifiability | Can the labels distinguish the desired rule from identity, background, scale, or another shortcut? |
| Optimization | Do hard examples receive useful gradients, assignments, and adequate fitting? |
| Data / generalization | Does the split test the intended novel classes, scenes, sources, or conditions? |
| Decision / evaluation | Do the scores, rejection, output budget, and metric reward the intended behavior? |
| Compute | Can the useful intervention meet the real runtime and training budget? |

**Rank the leading hypothesis against the strongest shortcut, not against
chance.** The null for any separation claim is the cheapest thing that could
produce it: context outside the box, the predicted class itself, scene/site,
source domain, object size, or sensor. Measure that shortcut's score and read
your number against it — headroom over the shortcut, not over 0.5. Held-out-class
protocols do not protect you: they will score a supra-class shortcut as a pass,
so check that a held-out positive which *breaks* the shortcut still lands on the
right side.

Several links can be limiting at once. A large oracle gain does not prove its
component is the unique root cause, nor that the gain is learnable.

Read [validity and power](references/validity-and-power.md) for the control
catalog, noise-floor procedure, and operating-point rules. Read
[diagnostic probes](references/diagnostic-probes.md) when interpreting an oracle,
concept/attribute evidence, unseen-class generalization, or detector metrics.

## 5. Commit to one falsifiable intervention

Write a short chain with an observable at each uncertain link, and mark each link
**measured** or **assumed**:

```text
change -> intermediate effect -> target failure reduced -> required metric moves
```

Prefer the cheapest sufficient action: a parser fix, a data or supervision
change, calibration, a loss, a head, or a backbone — chosen by where the
information is missing, not by a fixed "loss before backbone" ordering. If an
oracle already covers the missed objects, adding proposals needs new
justification; if the labels admit a shortcut, more regularization has not
supplied the missing evidence.

Before running, specify:

- **Comparison:** baseline and intervention on a fixed protocol, matched samples,
  and a control that distinguishes the leading alternative. Change one causal
  factor, or state why a coupled change is necessary.
- **Independence:** a second view, model, or feature is evidence only if it
  *can* disagree. A view the model was trained to be invariant to, or a frozen
  embedding of the same crop the detector already scored, carries correlated
  errors and will corroborate false positives as readily as true ones.
- **Decision rule:** minimum useful effect stated as a multiple of the measured
  noise floor, plus protected-metric limits. Do not invent universal thresholds
  or weaken an existing gate after seeing results.
- **Operating point:** evaluate on the deployed decision path at the deployed
  threshold. A statistic pooled down to the score floor, or computed on a path
  the shipped inference does not take, can point the opposite way.
- **Liveness metric and abort condition:** name a signal the intervention cannot
  flatter. A bounded auxiliary loss falls beautifully on a dead model — watch the
  total loss and the task metric instead.
- **Budget and outcomes:** bounded time/compute; what supports the next stage;
  what rejects the hypothesis; what makes the test invalid or inconclusive. Keep
  final test data out of selection.

Once the decision is concrete and the action is authorized, execute it. Do not
replace a ready experiment with another survey, redesign, or permission question.
If the task is analysis-only, deliver the contract without launching it.

## 6. Interpret, update, and close

| Outcome | Next action |
| --- | --- |
| INVALID: wiring, schema, numerics, alignment, or evaluator broke the test | Preserve the error; repair the demonstrated boundary and rerun the affected minimum. Make no learning claim from it. |
| NEGATIVE: valid test misses the declared effect or guardrail | Record which hypothesis failed under which conditions; close that intervention. Reopen only on a changed premise. |
| INCONCLUSIVE: valid test lacks precision, coverage, or discrimination | Name the missing observation. Follow up only if it can change the decision within budget. |
| SUPPORTS NEXT STAGE: valid test meets its predeclared rule | Advance only as far as the evidence and authorization reach; carry guardrails forward. |
| TARGET MET: full requested evaluation and constraints pass | Report the achieved result, evidence, uncertainty, and scope. |

**Quarantine what is superseded.** When a defect invalidates earlier numbers,
move the artifacts to a `do_not_cite` path and state explicitly which previously
reported figures they replace. Numbers left in circulation get re-cited and
restart the loop.

A successful oracle supports a learnability probe, not a deployment claim. A
failed finite probe rejects its tested setup, not every possible learner. A proxy
gain must survive the actual decision path before it counts toward the target.
Proxy metrics can disagree with the target in *direction*, not just magnitude —
anchor to a measured target-side quantity when one exists.

Record what changed in the diagnosis, including when your own prediction was
wrong. If the same error recurs after a repair, revisit the producer/consumer
contract before another rerun. If equivalent interventions keep failing, revisit
the falsified causal link rather than adding another module or renaming the run.
Preplanned replications are legitimate; retries without new evidence are not.

Count progress as a validated fix, new discriminating evidence, or a completed
authorized experiment. A restated plan or repeated status check is not progress.
For multi-turn work, update the project runbook with the compact
[decision record](references/decision-record.md); for a one-off analysis keep it
inline. Do not create a competing log or update global memory unasked.

## Red flags — stop and re-check

| Thought | What it actually means |
| --- | --- |
| "The tool crashed, I'll drop that flag and continue" | The crash was reporting that the input could not be read. Routing around it changes what is being tested. |
| "The control matches the treatment exactly — reassuring" | The control is aliased to the treatment, or the channel is inert. Nothing was measured. |
| "New paper / new module name, so the old negative doesn't apply" | Match mechanism, inputs, supervision, representation, protocol. Only a changed premise reopens a branch. |
| "The loss is falling, so it's learning" | Bounded auxiliary losses fall on dead models. Check the task metric. |
| "Exit code 0, so the run succeeded" | Check a liveness metric and the evaluator's identity. |
| "The delta is small but consistent" | One seed has no consistency. Compare to the measured noise floor. |
| "Let me guess the cause and try a fix" | Instrument first; two guesses cost more than one measurement. |
| "AUROC 0.88, well above chance" | Chance is not the null. Measure the shortcut baseline. |
| "It passed held-out-class validation" | That protocol scores supra-class shortcuts as passes. |
| "Val says it improved, ship it" | Verify at the deployed threshold on the deployed path. |

## Compact output

Lead with the decision and evidence; use only the detail the task needs.

```text
STATE:      prior verdicts that constrain this; what is genuinely new
PREFLIGHT:  identifiability | power (n independent units, noise floor) | prior art
VALIDITY:   controls degrade? | provenance identity | changed component active
GOAL:       metric current -> required; unit of evaluation; guardrails
LIMITING LINK: + strongest shortcut and its measured score
CHAIN:      change -> effect -> failure reduced -> metric moves  (measured/assumed per link)
EXPERIMENT: comparison + control | decision rule (>= k x floor) | operating point
            | liveness metric + abort | budget
VERDICT:    INVALID / NEGATIVE / INCONCLUSIVE / SUPPORTS NEXT STAGE / TARGET MET
            + belief update + what this closes + reopening condition
```

The block above is for the record. In the reply, **open with two to four plain
sentences in the user's language** before any table or field label: what question
was tested, the answer, and what it changes for the next step. Name metrics in
words on first use ("区分能力 AUROC", "recall at 5% false alarms"), and give one
concrete example when a number would otherwise be abstract. Users who must ask
"用白话解释" afterwards have been given the record instead of the answer.

Before claiming success, verify the requested unit of evaluation, operating
point, hard subsets, data separation, and runtime constraints. Report both the
formal gate and the practical failure burden: a passing aggregate can still leave
the user's problem unsolved.
