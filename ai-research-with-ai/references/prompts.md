# Prompt Templates

Starting points, not magic. The source's advice: adapt these by hand and grow
them as you see the agent fail. Replace `<…>`.

## Ideas

**Generate ideas grounded in recent work**
```
I'm doing research on <field> for <venue/deadline or goal>. My compute is <laptop / 1x RTX 4090 / $X>.
Search recent papers (last ~12 months, incl. top conferences) and propose 8 research questions.
Rules: each must be testable with a first experiment that runs in seconds on my hardware;
no plain hyperparameter sweeps; nothing that is already textbook knowledge.
Include at least two of each: missing explanation / contradiction between papers,
hidden failure mode, relaxed assumption, new tool or benchmark — not only "combine paper A + B".
Give each as one sentence, plus: why it's open, and the first 5-second experiment.
```

**Score like a reviewer**
```
Act as an ICML reviewer. Score each idea 1-10 on soundness, originality, significance, feasibility.
Flag any that are likely already published (name the paper). Then tell me the single one you'd pick and why, in one sentence.
```

**Ask me first**
```
Before doing anything, ask me 3 questions (with suggested answers) that will help decide what to research. Don't start training yet.
```

## Experiments

**Environment before invention**
```
Set up the research environment for <question>: download real data (don't generate synthetic data), implement <baseline(s)> from the paper(s), and an eval that measures <capability>, not just training loss.
Make comparisons fair (match params/compute). Run 5-second smoke tests of every arm.
Then act as an ICML reviewer of this setup: list likely bugs, unfair comparisons, and leakage, fix them, and repeat until you find no issues. Report in one sentence.
```

**Tiny experiment with prediction**
```
Design the smallest experiment (≤10 seconds) that tests: <hypothesis>.
Before running, predict the result and explain why in one sentence. Then run it,
report the result as a small table + one sentence, say whether the prediction held, and recommend the single next step.
```

**Approximate large scale with small runs**
```
We want to know whether <finding> holds in large-scale training, using only ~5-second experiments.
List the factors that differ at scale (depth, width, vocab size, context length, LR schedule, data mix, …),
then vary one factor per experiment. Report which factors change the conclusion.
```

**Search for a general rule (can run autonomously)**
```
I'm leaving for <N hours>. Keep working. Goal: find one simple rule that always holds for <narrow setup>,
using many 2–10 second experiments across as many varied settings as you can.
If a formula fails, extend it, make it approximate, or fall back to a qualitative rule — but keep it as general as possible.
Avoid anything needing long training. Log every experiment to FINDINGS.md. When I'm back, give me the rule in one sentence and the evidence table.
```

**Bug hunt when something looks off**
```
<Observation, e.g. "the loss curves for both attention types are identical">. That worries me.
First list which bugs are most likely to cause this, then check each in the code and experiments. Report what you found in one sentence.
```

## Conversation control (use constantly)

- `Explain simpler. One sentence.`
- `Why this? How do you know — did we measure it or is it a guess?`
- `Earlier you said <X>, now you say <Y>. Which is it and why?`
- `What is the one thing we are trying to find out here?`
- `Just tell me the first thing you want to do. One sentence.` → `Do it, and recommend the next single thing.`
- `What is the exact next step you recommend, and why?`

## Autonomous loop prompts (start this short, grow by hand)

- **Idea miner:** `You generate AI research ideas for <project>. Search the internet and the repo's past experiments index; propose novel ideas; no hyperparameter sweeps; nothing already tried.`
- **Idea reviewer:** `You review ideas for novelty, taste, and feasibility in <budget>. Reject sweeps and known results. Output: approve / reject / request changes, with one-sentence reason.`
- **Plan writer / reviewer:** `Write a detailed experiment plan for this approved idea (arms, controls, metric, runtime).` / `Review the plan for unfair comparisons, missing controls, overstated claims. Max 3 rounds.`
- **Implementer / code reviewer:** `Implement the approved plan; smoke-test it.` / `Review the diff for bugs and leakage before it goes to the GPU queue.`
- **Runner:** `Drain queue.jsonl onto the GPU(s). The GPU must never be idle. Log results to the thread's repo.`

## Writing

```
Write a short paper draft (ICML style) from FINDINGS.md with figures for each key result. It's fine if rough.
```
```
Act as an ICML reviewer of this draft. List the top weaknesses that would cause rejection, ordered by severity. Then fix them and re-review.
```
```
Rewrite this abstract in plain words a first-year student understands. Keep every claim supported by our results; soften anything that isn't.
```
