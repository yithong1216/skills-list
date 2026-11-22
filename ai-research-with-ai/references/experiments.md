# Experiments

How to design, run, and interpret experiments when an AI agent does most of the
execution.

## 1. Environment and baselines first

The most common failure: the AI invents a module, compares against an
under-tuned baseline on a toy task, and declares victory. Prevent it:

1. Build the environment: model code, **real** data (download; don't let the agent
   silently generate synthetic data when real data is available), evaluation.
2. Implement baselines from the actual papers (have the agent read them), and
   **tune them as hard as the new method**.
3. **Make comparisons fair** — match parameters or compute. If the new module adds
   parameters (e.g. a big n-gram memory table), give the baseline equivalent
   capacity or report matched-compute numbers.
4. Run ~5-second smoke tests of every arm. These aren't research — they catch
   crashes, bugs, hacks, and leakage.
5. Ask the agent to **act as an ICML reviewer of the setup** and list issues;
   fix; repeat until it finds none. Specifically ask "which bugs are *likely* here?"
   before asking it to look.
6. Red flags to chase immediately: two different methods with *identical* loss
   curves; a new method winning by a huge margin early; measuring only training
   loss when the claim is about a capability (add a task-level eval).

7. **Measure the noise floor**: run the baseline 2–3× with different seeds. A
   difference smaller than ~2× the seed-to-seed spread is not a result. Use
   paired seeds across arms for small effects.

Only after this do you let the AI search/invent inside the environment.

## 2. Tiny, fast experiments

- Default budget: **~5–10 seconds per experiment** for understanding work (a few
  million parameters, a few hundred steps, laptop or free Colab/Kaggle GPU is
  fine). If a question can't be probed in seconds, find a nearby question that can.
- If the agent's runs creep to minutes, ask how long each takes and push it back down.
- **Time one run before planning a grid.** Don't promise "10 s per run" — measure
  it on the user's machine, then count the runs (arms × LRs × seeds) honestly.
- **Check the short regime can show the effect.** Ask "would this phenomenon be
  visible in N steps?" Regularization, weight-decay and collapse effects often
  need long horizons or an overfitting regime; a tiny run then yields a foregone
  null. Options: a smaller dataset so overfitting arrives fast, more steps on a
  smaller model, or a proxy measurement — and state the caveat.
- **When the claim is "X differs from Y", include Y.** To test whether weight
  decay under Muon is cargo-culted from AdamW you need the AdamW arm too.
- **Tune fairly per arm.** If the hypothesis varies one knob (weight decay),
  re-tune the interacting knob (LR) for each value, or you measure the confound.
- **Screening must predict the full run.** Before trusting short screens, check
  on a handful of known configs that screen ranking matches full-run ranking;
  if runs are so short that compile/warm-up dominates, lengthen them.
- Approximate big-run conditions with small runs: list factors that differ at scale
  (depth, width, vocab size, context length, LR schedule like cosine decay, data
  mix) and vary **one factor per experiment** to see which ones change the conclusion.
- For speedrun/benchmark-style work (e.g. "train this LLM fastest"): run
  **elimination rounds** at ~5–10% of full training, kill clearly bad arms, keep
  the ones near or above baseline, then lengthen. Expect early winners to fade —
  tuned baselines are hard to beat late in training.
- Mini scaling laws: 3 small sizes (e.g. 5M/8M/12M params) × a few context lengths
  tell you whether an effect grows or shrinks with scale.

## 3. The understanding loop

For each experiment:

```
Hypothesis (1 sentence) → Prediction + why → Run → Result (1 sentence + small table)
→ Did it match? If not, why? → Single next step
```

Use the workhorse prompts on every AI claim: **"Why this?"**, **"How do you
know?"**, **"Explain simpler."** When the AI contradicts something it said
earlier, stop and resolve it — that tension is often the discovery. Example from
the source: an AI proposed "teach the model to ignore memory hints when
reasoning"; asking *why* surfaced that hints help fact recall but hurt reasoning,
and that training only with hints makes the model forget facts when hints are
off — a far more interesting finding than the original proposal.

## 3b. Is the finding real? (before building on it)

When something interesting shows up, do these *before* any intervention
experiments — they are cheap and they decide what everything else means:

1. **Reproduce** with a second seed.
2. **Control**: does it also happen in the comparison condition (other
   optimizer, baseline module)? If yes, the story changes.
3. **Right quantity?** Is the measurement the meaningful one (e.g. rank of the
   Q·K product or per-head blocks vs. rank of Q and K separately)? Is the
   threshold arbitrary?
4. **Trajectory**: measure over training, not just at the end.
5. **Cheap confounds**: a 3-point check of the usual suspects (learning rate,
   weight decay, init). Don't dismiss these with an argument — run them.
6. **Known already?** Quick literature search on the phenomenon's name.

When pruning a long list of AI-proposed follow-ups: state the one question,
keep controls and confound checks first, then the one or two interventions that
discriminate between explanations, and defer anything that changes the subject
(new dataset, new architecture, engineering work).

## 4. Searching for general rules

A productive mode with AI: pick a narrow, specific setup, then have the agent run
hundreds of short experiments looking for **one simple rule that always holds**.

- Keep re-asking: "Is there a single general rule here? State it in one sentence."
- When a candidate rule appears, tell the agent: test it across as many varied
  settings as possible; if the formula fails, extend it, make it approximate, or
  fall back to a qualitative rule — but keep it as general as the data allows.
- Once a direction is fixed, the agent can work autonomously for hours (it's good
  at searching a well-defined space, bad at choosing the space).
- Example from the source: started from "two agents moving in a world model —
  one network or two?", narrowed to "the slower object learns worse", and long
  autonomous search generalised it to "**when you add two losses, the one with the
  smaller magnitude learns slowly**, predictably by the loss ratio" — a rule
  checkable before training.

## 5. Keeping the agent on track

- Restate the plan scope ("only value and output projections, nothing else") and
  stop it when it wanders into unrelated experiments.
- Use mid-run steering: interrupt to correct (e.g. "don't generate synthetic data,
  the README says how to download real data").
- You don't need to read every line of every experiment — track the mental model,
  not the details. Have the agent explain each step in one sentence.
- Run several independent research threads in parallel with separate agents
  rather than one agent doing everything.

## 6. Recording results

- Append every result, including failures, to a findings log (one line each:
  setting → result → interpretation).
- A negative result is a result ("stochastic routing noise didn't help at 1.6 min
  of training") — but label how weak the evidence is.
- Commit/tag the code version each experiment ran on so it stays reproducible as
  the main code evolves.
- Before scaling anything, write down which effects survived all factor sweeps.
- Report the range honestly: "held across 2M–10M params, 4 widths" — not
  "scale-free". If possible spend the scarce budget on one or two larger
  confirmation runs of the surviving finding.
