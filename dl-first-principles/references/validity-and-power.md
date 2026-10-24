# Validity and power

Read the section that matches the current decision. Choose checks that could
change the decision and fit the budget; do not run the whole catalog.

## Null controls: what "the channel is dead" looks like

A results table is readable only after the null arms have been shown to degrade.

| Symptom | Diagnosis | Check |
| --- | --- | --- |
| Shuffled/random control equals the real arm to many decimals | The channel is not consumed at all — an empty schema, an unpopulated target field, a bypassed branch | Print the tensor the channel feeds and confirm non-degenerate values reach the loss/score |
| Control equals the baseline exactly | The control is aliased to the baseline in code (shared `if` branch, same lambda set) | Read the branch that selects the variant; two names on one branch are one variant |
| Control scores *better* than the real arm | The control differs in something other than the intended factor (encoder width, tower, calibration, normalization) | Rebuild the null with the same encoder/geometry, changing only semantics |
| A "no-op" setting does not reproduce the baseline bit-for-bit | The patch is not inert when off; every downstream number is confounded | Require exact reproduction at the off setting before trusting any on setting |

Order the controls and check the ordering is textbook:
`oracle > predicted > label-only > shuffled > random`. An inversion anywhere is a
defect report, not a finding.

## Provenance identity across arms

Every arm must be scored by the same evaluator against the same ground truth.

- Resolve the config **once**, dump the fully-resolved copy into the run
  directory, and have every downstream stage read the frozen copy. Never edit a
  config a running job re-reads — a mid-run edit contaminates from that variant
  onward and the only tell may be extra per-class lines in the log.
- Hash and assert per arm: evaluator fingerprint (including class count), ground
  truth fingerprint (image ids + boxes + labels), config sha, checkpoint id.
- Fail loudly on mismatch instead of continuing.
- If two implementations of the same metric exist (a local one and the official
  evaluator), they will disagree. Pick one canonical key that the report, the
  CSV, and the gate all read, and surface the divergence rather than hiding it.

An audit flag such as `oracle_ready = true` usually checks that names exist, not
that the entries carry defined targets. Read the per-class defined counts before
trusting any oracle ceiling.

## Silent no-ops: the changed component was never active

Common shapes:

- A guard disables the transform you asked for and logs one line
  (`... has been disabled`). Grep run logs for disable/skip messages, and assert
  the built pipeline contains what was requested — refuse to start otherwise.
- A framework swallows a build failure for a mistyped transform or module name
  and proceeds with nothing.
- A trained head is not consumed at inference; the shipped path and the
  evaluation path differ.
- A branch is bypassed because its input is masked, its reliability weights are
  zero, or its parameters are frozen.
- An augmentation is mathematically inert on this data (desaturating an image
  that is already grayscale; a rotation the model was trained to be invariant
  to).

Test: perturb the component's input or output and confirm the metric moves. If a
change of any size produces an identical number, it is not active.

**Exit 0 is not success.** Frameworks train through NaN and then evaluate the
dead model to completion. Watch the task metric and total loss, arm a watchdog on
the terminal condition, and scope any kill pattern to the specific run directory
so it cannot take a healthy concurrent run with it.

## The abort criterion must not be flatterable

Pick a liveness signal the intervention cannot make look good.

- A bounded auxiliary loss (focal, contrastive, cosine) keeps falling smoothly on
  a model whose main branch has already diverged. It is computed on a corpse.
- Watch the main task loss and the end metric instead, and require a non-zero
  value, not merely a finite one.
- When gradients are suspected, capture per-parameter-group norms *before*
  clipping; a hook that runs after the optimizer step sees nothing. The group
  that explodes is often not the group you changed.
- Measure before guessing. Two cheap instrumented minutes beat two speculative
  reruns.

## Power: independent units and the noise floor

**Count independent units, not samples.** Boxes from one scene, crops from one
source image, and images of one identity or site are not independent. Group
cross-validation and cluster bootstrap by that unit; a random image split inside
a shared acquisition leaks.

**Measure the floor once.** Run two identically-configured runs (or two seeds)
and record the absolute difference on every axis you report. That table is the
scale against which every later delta is judged, and it is usually much larger
than the deltas interventions produce. A per-class axis with good support often
has a far tighter floor than the headline aggregate — prefer it when it answers
the question.

**Refuse underpowered claims.** A stratum of a few dozen boxes, or a handful of
scenes, carries binomial noise that swamps most real effects. If a metric is
computed on a very small denominator, say so next to the number every time it is
reported. Do not claim a result on such an axis from a single run.

**Development data stops being test data.** Repeated recipe selection on a set
makes it development data whatever it is named. Freeze the chosen recipe before
an independent final evaluation, and keep oracle access, calibration, and
selection out of the sealed split.

## Shortcut baselines: what the null actually is

For any separation, discrimination, or attribute claim, measure the cheapest
alternative explanation and report headroom over *it*.

Shortcut candidates, in rough order of how often they fire:

1. **Context outside the object** — take the surrounding ring/patch alone and
   score the same task. It can approach whole-object performance, which means the
   real headroom for object evidence is the gap over the ring, not over chance.
2. **The prediction itself** — if an attribute head is fed the same feature the
   classifier used, its output can be a restatement of the predicted class. Test
   by grouping instances of *one* physical type by which class the model called
   them: if the attribute flips sign with the prediction on physically identical
   objects, it is reading the label, not the image.
3. **Supra-class grouping** — source domain, nationality, sensor, capture site,
   acquisition date. These survive class-level debiasing and defeat held-out-class
   protocols. Compute the cosine between your learned direction and each candidate
   grouping direction.
4. **Size, aspect, and scale** — match on them and check the effect survives.
5. **Scene identity** — if no scene contains two of the classes being compared,
   the same-scene control is unrunnable and the claim must be scoped accordingly.

**Held-out-class validation is not protection.** It will score a supra-class
shortcut as a comfortable pass. The discriminating test is a held-out positive
that *breaks* the shortcut: if the one positive from the other group projects to
the wrong side, the direction is the shortcut. Positives must cross type *and*
the suspected grouping.

## Operating point and the deployed decision path

- Compute every comparison at the threshold that will actually be used. A
  statistic pooled down to the score floor can show separation that lives
  entirely below the operating point, and point the wrong way.
- Follow the shipped path end to end: proposals → regression → score transform →
  rejection/arbitration → NMS/output budget → evaluator. A crop-level or
  GT-box-level number removes upstream error and is optimistic; the deployable
  number is measured on the inputs the system actually sees.
- Say how duplicates are handled. Per-GT best-candidate and all-matched-candidate
  aggregations can reverse the ranking between representations.
- Report the retention/cost side next to the gain, at a matched operating point
  or as a curve. A metric that falls because fewer outputs were emitted is a
  budget artifact, not better discrimination — normalize by outputs per image to
  see it.
- A proxy split can disagree with the target in direction, not just magnitude.
  When any target-side measurement exists, anchor to the literal setting that
  produced it rather than re-deriving from the proxy. Where a stable proxy→target
  ratio has been measured across several matched points, it may be used; a fit
  across two points or across different models may not.
