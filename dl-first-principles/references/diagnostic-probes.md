# Interpreting high-risk probes

Read the relevant section, not every possible control. Choose controls that can
change the current decision and fit the experiment budget.

## Input, representation, supervision, and learnability

Separate the questions:

1. Can native pixels or permitted metadata support the requested target?
2. Does the frozen representation preserve the target-relevant evidence?
3. Does available supervision identify the desired rule rather than a shortcut?
4. Does the actual optimization learn a transferable rule?
5. Can the deployed decision rule turn it into useful output?

A supervised identity classifier, a concept decoder, and an unseen-identity
rejector answer different questions. Excellent identity AUROC does not establish
engine counting, semantic localization, or open-set rejection. Poor linear-probe
accuracy may reflect readout limitations, insufficient samples, or optimization;
it is not proof that information is absent. Even success with a richer readout
must be scoped to its targets, training labels, and evaluation split.

If information loss is the leading hypothesis, compare native/local pixels,
an earlier spatial representation, and the active pooled representation using
the same target and grouped split. Upsampling existing pixels does not add native
resolution. Measure actual target visibility before claiming a hard information
limit. If the design needs metric dimensions, establish GSD or scale metadata;
pixel size in a resized crop is not physical size.

## Oracles and controls

Specify what the oracle supplies, where it intervenes, and what stays fixed.
Keep oracle access separate from training, model selection, and final testing.
Use development proxy classes for oracle-guided design; sealed final unknown
labels must not become training or calibration inputs.

An oracle is an upper bound only for the stated intervention and assumptions.
A failed learned "oracle" may be a weak probe. An oracle cannot reveal the
benefit of an inactive branch, broken target parser, or a downstream decision
that ignores its output. Check those before treating failure as semantic evidence.

Controls must enact their intended counterfactual. Inspect tensor values and
their consumption for a few samples. If label-only equals the baseline because
the implementation aliases them, the semantic-increment test has not happened.
An exactly constant branch may reflect zero reliability weights or masking.
Repair that boundary, then compare corrected controls on identical samples and
calibration. Keep the unchanged gate; report whether the repair changes the verdict.

## Semantic attributes and shortcut learning

Inspect identity-by-attribute support, missing/absent/unknown semantics, and
confounders before designing a new semantic head. If all but one identity share
an attribute, image-level labels permit an identity lookup solution. Renaming
class labels as instance attributes does not add instance-level evidence.

Use the relevant controls: held-out identities/sites, background-only inputs,
label permutation, actual part annotations, or semantically targeted occlusion.
Rotation consistency, compact attention, query diversity, foreground masks, and
pairwise identity separation do not alone identify named parts. Report target
factors and difficult class pairs, not just a mean improved by unrelated factors.

Teacher feasibility is a prerequisite to pseudo-label training. Verify on a small
representative set that a proposed teacher supplies target-domain part evidence,
and compare true prompts with unrelated prompts and whole-object leakage. A
downstream mask refiner cannot establish engine semantics when its upstream box
is just the whole aircraft. A dataset advertised as "attributes" or "masks" must
be checked for the actual granularity, visibility, coverage, and access needed.

Example: a count predictor scores highly on a random image split, but count is
almost a lookup of aircraft identity and held-out-identity counting fails. First
test independent count/part evidence with appropriate identity support. If that
evidence is absent, changing a loss weight leaves the central ambiguity intact.
This closes that proposed repair, not all future counting methods.

## Open-set and detection metrics

- Distinguish unknown-vs-background objectness from known-vs-unknown rejection
  among real foreground objects. Improving one does not demonstrate the other.
- Separate known fitting, calibration, development selection, anomaly exposure,
  and truly unseen evaluation identities. Random image splits within exposed
  identities test a different task. Use identity/source grouping appropriate to
  the claim; do not silently migrate between 5-, 10-, and 20-known-class protocols.
- Pairwise separation from a convenient known class is insufficient when deployed
  rejection uses the nearest or highest-scoring member of **all** known classes.
  Test against the actual strongest competing known class and hard confusion pairs.
- Follow proposal recall -> regression -> score transform -> rejection/arbitration
  -> NMS/output budget -> evaluator. A crop-level oracle removes upstream errors
  and cannot by itself validate a full detector or whole-scene latency.
- Report known retention alongside unknown rejection, and count false positives
  per image/object where useful. Compare at the same operating point or show a
  curve. Threshold selection on calibration is separate from diagnostic FPR@95TPR
  computed from a test ROC; report the realized test retention at the frozen
  threshold rather than presenting its nominal 95% as measured.
- Establish the evaluator's unit: detections, matched objects, unique GT objects,
  images, or classes; macro vs micro weighting; IoU and box budget. Lower A-OSE
  after emitting fewer boxes does not alone demonstrate better rejection, and a
  mean FDR gate can hide an unusable ship false-alarm rate.
- Report sample counts, independent identities/scenes, and uncertainty when close
  to a gate. Two more successes among 23 images of one identity are development
  evidence, not broad unknown-class generalization. Repeated recipe selection on
  that set makes it development data even if originally named "test". Freeze
  the chosen recipe before an independent final evaluation.
