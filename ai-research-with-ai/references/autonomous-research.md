# Autonomous Research (agents running experiments without you)

Use when the user wants agents to run research for hours/days, overnight, or
across several GPUs.

## What autonomy is (and isn't) good for today

- **Good:** implementing ideas in code, running and debugging experiments,
  large numbers of micro-optimizations (kernels, architecture tweaks — Karpathy-
  style autoresearch found ~10% speedups on an already-tuned LLM), literature
  collection (faster and broader than a human), searching a *well-defined* space.
- **Weak:** choosing what to research (ideas are the hardest part), inventing
  genuinely new paradigms, staying diverse — left alone it tends to tweak learning
  rates forever.
- Expect most experiments to fail. That's true of human PhD research too; the
  point of automation is that failure becomes cheap.

So: autonomy *after* a human has set direction and the environment is debugged.
In the beginning you must babysit — read what the agent does and correct it.

## The pipeline (four loops)

```
Idea generator ──► Idea reviewer ──(approve)──► Plan writer ──► Plan reviewer
      ▲               │ request changes (max 3 rounds, then auto-reject)  │
      └───────────────┘                                                   ▼
                                     GPU queue ◄── Code reviewer ◄── Code implementer
```

- Each stage is a separate agent (or, to start simple, one agent reading each
  prompt in turn). Reviewers can **approve, reject, or request changes**; after 3
  rounds without approval, auto-reject so the loop can't stall.
- The idea reviewer enforces taste: novelty, not a plain hyperparameter sweep, not
  something already known, feasible in the compute budget.
- The GPU queue is a file (YAML/JSON/JSONL) that a runner agent drains. Rule:
  **the GPU must never be idle** — keep the queue non-empty.
- **Write the prompts by hand**, starting from one or two sentences each, and grow
  them as you see failure cases. Copy-pasted prompts you don't understand won't
  make you a better researcher; each lab is really "a set of markdown rules", and
  you learn by writing them.
- Start with fewer stages if it's overwhelming; add stages as needed. For one
  GPU on a first night, a good minimum is: **one researcher agent + a dumb
  deterministic runner script + a pre-run review** (ideally by a different
  model). Every extra LLM role is another thing that can stall at 3 a.m.
  Fewer *roles* does not mean fewer *safeguards* — even the minimal design keeps
  all of these:
  - the pre-run review is **mandatory** and bounded (max 3 rounds, then
    auto-reject) — it is what stops buggy or duplicate ideas burning GPU time;
  - a designed **screen → confirm → full** ladder with explicit budgets and a
    promotion rule (see below), not just "consider screening";
  - a **retry cap** on fix-and-resubmit (e.g. 2 attempts, then mark failed and
    move on) so one broken idea can't eat the night;
  - the ops basics: push results/code off the box regularly (rented instances
    get reclaimed), log rotation / disk check, kill zombie GPU processes, and a
    restart loop for the agent when its context fills or the CLI dies.
- A request to "design the setup" is asking for operational detail: spell out
  the files, the queue entry format, the runner's steps, and the stage budgets.
  Keep it lean by cutting commentary, not by cutting mechanisms.
- When the user asks for "the prompts/files", give copy-pasteable first versions
  they can then edit by hand — not just a description of what to write.

## Orchestrator / worker / guardian structure

(Pattern popularised by a DeepSeek researcher's open autoresearch skill.)

- **Orchestrator** (strong model) creates tasks with a goal, milestone and success
  criteria, and spawns a **fresh worker per task** — clean context windows work
  better than one long polluted context. Workers return results, not their
  thinking.
- **Guardians** check periodically (e.g. hourly) whether workers have stalled,
  looped, or crashed, and nudge/restart them. Guardians can watch each other in a
  ring.
- Three failure modes to design against:
  1. **Cognitive loop** — repeating the same idea/text (e.g. only tuning LR).
  2. **Stalling** — declaring "task done, here's a summary" instead of continuing.
  3. **Runtime fragility** — the terminal/app/connection dies.
- Behavioural constraints for long runs: don't ask the human questions, don't ask
  "should I submit?" — act; keep append-only state/log files per task
  (status, findings, decisions); auto-diagnose errors, fix, resubmit.
- Optionally use **different LLM families** to critique each other's plans
  (models tend to favour their own output), and cap critique length so it doesn't
  bloat.

## Enforce with mechanism, not with prompts

Anything that must hold overnight should be enforced by the runner or the OS,
because agents drift from instructions:

- **Protect the metric.** Eval code and validation data read-only to the agent
  (separate user / file permissions / pinned copy the runner uses). Agents under
  pressure to improve a number will edit the eval. Re-evaluate the final best
  yourself, ideally on a held-out second validation split.
- **The runner owns the GPU.** The agent writes queue entries; a plain script
  runs them with a hard timeout and process-group kill, records structured
  status (ok / oom / nan / timeout / crash), and is idempotent on restart. One
  writer per shared file.
- **Budgets live in runner config**, not in agent-editable fields — otherwise
  the agent shortens training to get "fast wins".
- **Noise floor and promotion.** Reproduce the baseline 2–3× first; a win must
  beat the seed spread by a margin; top candidates are automatically re-run
  with multiple seeds before being accepted. One change per experiment.
- **Screen → confirm → full.** Always design this ladder: e.g. smoke test
  (seconds, catches crashes) → screen (~5–10% of the full budget, kills clearly
  bad arms) → confirm (longer, 2+ seeds, for survivors) → full length (few).
  Before trusting it, verify on a handful of known configs that screen ranking
  predicts full-run ranking, and make screens long enough that compile/warm-up
  doesn't dominate.
- **Sandbox and caps.** Throwaway container/user with no secrets; API spend cap
  and turn cap; alert (or stop) if no result row appears for N minutes; shut
  the instance down when done.
- **Proxy hardware.** If the target is different hardware (e.g. 8×H100 vs. one
  4090), throughput/kernel findings may not transfer; plan to re-check the top
  candidates on the target.
- **Read the challenge rules first.** Confirm the actual scoring rule and
  constraints from the repo README before designing anything; don't trust
  recalled rules.
- Avoid arbitrary quotas ("a third must be architectural") — use a rotation of
  idea buckets and a cap on consecutive hyperparameter-only experiments.
- **First night supervised.** Run a short (1–3 h) unattended loop while you can
  still check it before trusting a full night.

## Memory and documentation

- **One repository per research thread.** The agent documents every setup,
  failure, error and success there — that repo *is* the knowledge base and lets a
  later agent (or a cheaper model) resume.
- Keep a summary index of all past experiments so new ideas don't repeat old
  ones; without it the agent will rerun yesterday's experiments.
- When the agent makes a mistake, have it diagnose the mistake and **add a rule**
  to its rules file so it doesn't recur. Rules accumulate into the lab's method.
- For verifiable domains (math, biology), tell it to find *verifiable* ways to
  check its own results (tools, simulations, proofs).

## Practical infrastructure

- **Model split:** a strong, expensive model plans/orchestrates/debugs; cheap fast
  models implement and run in parallel. Use parallel workers in separate git
  worktrees so they don't stomp on each other.
- **GPUs:** rent rather than fight free tiers (time is worth more than a few
  dollars). On marketplace GPUs (e.g. Vast.ai): set container disk ≥60 GB, sort by
  deep-learning-performance per $/hr, watch for hidden bandwidth pricing, rent a
  few instances and destroy the ones that fail to start. Consumer cards
  (3090/4090/5090) are plenty for small-model research.
- Let the coding agent help with SSH keys, installs, and connection; you rarely
  need to do it by hand.
- Run agents inside **tmux** (and ideally on an always-on VPS that SSHes into the
  GPUs) so a dropped connection doesn't kill the session or training. Tell the
  agent explicitly: training must survive IDE/laptop disconnects.
- Give the agent a **time budget** ("you have 40 minutes", "24 hours") so it
  plans elimination rounds vs. longer runs accordingly, and ask it to predict how
  long its plan takes and check those predictions.
- Watch token/usage limits; use cheaper models for routine steps.

## Human's job while it runs

- Periodically ask the agent (or a side chat) "what's going on, in one sentence?"
- Kill obviously bad branches, push it off pure hyperparameter tweaking toward
  architectural/mechanistic questions.
- Your judgment and attention are now the bottleneck: agents amplify both good
  and bad habits (scope creep, rabbit holes). Know what you're doing, why, and when
  to stop. Expect decision fatigue after a few hours.
- Verify results yourself before claiming them. Agent output is not ground truth.
