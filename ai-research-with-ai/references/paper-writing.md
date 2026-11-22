# Paper Writing

From results to an ICML/NeurIPS/ICLR-style paper (or a solid public write-up).

## Principles

- **You can't let AI write the whole paper** — it goes off the rails. Use it to
  draft, critique, format and find holes; the human judges and keeps it on track,
  and must understand every claim in it.
- **Start a draft immediately.** Ask the agent to write a short paper with figures
  as soon as there are a few results. It will be "AI slop" — that's the point: it
  shows what you actually have and what's missing. Then iterate.
- **Write every day, even badly; ask for feedback before you feel ready.** Small
  daily write-ups (cohesive, well explained, sound, possibly new) are how papers
  accumulate.
- A paper takes months. One paper won't change your career; it's a stepping stone.

## What reviewers check (score your draft on these)

1. **Soundness** — does it make sense; are baselines fair and tuned; is the eval
   measuring the claimed capability?
2. **Originality** — not already done (run a real literature check).
3. **Significance** — does anyone care; does it plausibly matter at scale?
4. **Clarity** — cohesive, comprehensive, well explained.

Prefer a **simple, memorable finding** (one rule, one formula) over a pile of
tables — humans remember simple things. But claim only the range you tested:
"across 2M–10M-parameter models on one dataset", not "scale-free" or "general".
An abstract should be one clean version for the evidence in hand — no
bracketed either/or sentences.

## Using AI as the reviewer

- "Act as an ICML reviewer. List the weaknesses that would get this rejected."
  Then ask it to fix them and re-review until it runs out of serious issues.
- Common reviewer hits for AI-assisted work: unfair baseline, models too small
  (reviewers may expect ≥100M params for LLM claims), unclear novelty, only toy
  tasks, overstated claims. Tone claims down to what the evidence supports.
- Route weaknesses to the right fix: weak citation coverage → more literature
  review; claims too strong → restructure/soften; missing experiments → run them.
- **Find the single most likely rejection reason and design an experiment for
  it** — don't just list it under limitations. Typical decisive objections:
  "isn't this just <simpler known quantity>?" (e.g. is a loss-ratio rule really
  a gradient-norm-ratio effect, and does it depend on the optimizer's
  normalization?), "does it survive an intervention?" (change the quantity and
  see if the effect follows — correlation across settings isn't enough), and
  "how does it compare to the standard methods for this problem?" Cheap
  intervention and control experiments beat more sweeps of the same kind.
- **Held-out, not in-sample.** If the paper's claim is a predictive rule ("within
  10%"), show it predicting settings that weren't used to fit it.
- **Compare against the field's standard methods** when the finding touches a
  problem that has them — as baselines or at least as an explicit discussion of
  why they don't apply.
- Name the **headline figure** (the one plot that carries the claim) and build
  the paper around it.
- **Prior work is a search, not a citation list.** Before drafting, check
  whether the finding (or its explanation) is already published in the adjacent
  literature — e.g. a rule about combining losses must be checked against the
  multi-task loss-balancing literature (GradNorm, uncertainty weighting, PCGrad).
- **Venue realism.** Say plainly where the paper stands for a main track and
  name fallbacks (workshop, TMLR, arXiv + write-up) and the cheapest additions
  that would move it up (a second dataset, one larger confirmation run) — and
  say how the user could actually get them on their budget, flagged as an
  estimate.

## Structure

**Introduction** (Harvard template): broad context (why the general problem
matters) → what specifically is hard → what others did → why that falls short →
"In this work we propose X" → brief roadmap of method and key results.

**The rest:** method (with clean math; let the AI help derive and check proofs,
then verify the steps yourself), experimental setup (fairness, compute matching),
results, ablations, scaling trend from small sizes, limitations (state honestly:
small models, synthetic facts, etc.), related work.

Figures: ask the agent to draw diagrams in LaTeX/TikZ or matplotlib, screenshot
the render, feed it back, and have it fix layout. Make titles descriptive — the
title should say what actually happens.

## Zero/low-compute paper recipe

If the user can't afford large runs, a credible paper can still:
1. **Define the idea and theory clearly** (math, intuition).
2. **Ship a correct implementation** others can run without debugging.
3. **Do a real literature review** placing the idea among related work.
4. **Design scalable experiments** (scaling sweeps over size, context length,
   hyperparameters, architectures) that labs with compute can run.
5. Bonus: run preliminary small-scale experiments and mini scaling laws.

Publish code + paper; you get the credit and others build on it. Frame it as
"here is the rule at small scale and the exact experiments that would test it
at large scale" — the designed experiments are an invitation, not evidence.

## Voice and polish

- AI drafts are jargon-heavy and hard to read — rewrite in plain words, especially
  the abstract. Ask "explain this paragraph to a beginner in 3 sentences" and use
  that.
- For anything posted publicly (X, LinkedIn, blog), screenshot result tables but
  **rewrite the prose yourself** — people don't want to read AI-generated text.
- Tools: an agentic IDE (Claude Code, Codex, Cursor, Antigravity) with file access
  works well for LaTeX papers; AI LaTeX editors (e.g. OpenAI Prism) are fine for
  drafting but you still must understand everything.

## Iteration and submission

- Rejection is normal: improve and resubmit to the next venue.
- Post progress publicly while writing (observations, graphs, failed experiments —
  you don't need a breakthrough each post). Fear of idea theft mostly slows science
  down; public work also brings collaborators, feedback and sometimes compute.
