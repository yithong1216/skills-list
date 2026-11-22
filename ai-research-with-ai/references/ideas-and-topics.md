# Ideas and Topics

How to go from "I don't know what to research" to one runnable question.

## Mindset to pass on to the user

- **Nobody knows the best thing to research** — not beginner PhD students, often
  not professors. Everyone is confused at the start. The fix is to start walking:
  "if you're lost in a forest, you don't stand still deciding — you walk and see
  what you hit."
- **Topic selection is continuous.** You don't pick a topic and then research it;
  you re-pick every 15 minutes as you learn what to cut and what to chase.
- **It's a marathon.** Motivation should be curiosity about *why* things work
  (why does Muon beat Adam? how do LLMs learn?), not a job in a year. Watch for
  *shiny-object syndrome* — jumping to a new idea when the current one gets boring.
- **Ideas being "already done" is fine.** A done idea gives you a baseline, and
  every solved problem opens ten more.
- Don't aim to beat Google/DeepSeek with one paper. Aim to understand something
  deeply; papers are stepping stones toward skill.

## Step 1 — Choose a field (human decision)

Ask which broad area: LLM pre-training, optimizers, post-training/RL, agents/long-
horizon, safety/interpretability, architectures beyond transformers (linear
attention, SSMs, JEPA, recursive/latent reasoning), memory modules, world/video
models, robotics, inference (speculative decoding, kernels). The AI can describe
each, but the human chooses. If the user's goal is a job at a frontier lab,
point them to what labs currently care about (long-horizon agents, RL
environments/evals, autonomous research, inference efficiency) — but stress
they must work out *how they personally can help*, not copy everyone else.

## Step 2 — Generate candidate questions with AI

Ask the AI for ideas grounded in *recent* papers in the chosen field, constrained
by the user's compute. Then filter hard. Good starter questions are usually
**understanding** questions ("what does multi-token prediction do inside the
weights?", "how wide must an attention head be to find one word in long
context?", "is shape generated before colour in an image model?") rather than
"invent a better X".

Filter each candidate on:

| Check | Keep if… |
|---|---|
| Already well known? | Not a textbook fact (e.g. "why does LR decay drop loss" — too known). Ask the AI to literature-check. |
| Compute | A first experiment runs in seconds on available hardware. Prefer math-grounded / scale-free questions when compute is small. |
| Depth | "Why?" can be asked at least 3 times before you hit the frontier of what anyone understands. |
| Not just a sweep | Not a plain hyperparameter sweep. |
| Interest | The user is actually curious about it. |

Even a "bad" question works if you keep asking *why* until you hit the limit of
what papers explain — that limit is where research starts.

## Step 3 — Score like a reviewer

Have the AI score ideas on ICML-style criteria — **soundness** (does it make
sense), **originality**, **significance**, and **clarity** — then ask *why* it gave
each score. AI is good at critique; it sometimes misses that something is already
published, so do a separate literature check.

## Known biases of AI-generated ideas

From a study of ~11,000 papers comparing human vs. LLM ideas: LLMs **bridge or
synthesize two existing papers** ~50–60% of the time vs. ~5–12% for humans.
Humans more often:
- find a **missing explanation** or a **contradiction** between papers,
- uncover a **hidden risk / failure mode**,
- **relax a strict assumption**,
- **build a new tool/artifact or benchmark**,
- do an **empirical mapping** of a space.

So when asking for ideas, explicitly request these opportunity types too, and
tell the AI not to propose mere combinations or hyperparameter tweaks. Combining
ideas is still valuable (AI finds combos people are too slow to try) — just not
the only mode.

## Gap-finding from one paper (Harvard "AI research experience" method)

1. Read **wide** first (skim many papers for the gist, build a map), then **deep**
   on the one you care about. ~20–40 papers is typical before a conference paper.
2. Read a paper as: problem → existing solutions → their shortcomings → this
   paper's contribution. Expect ~10% understanding on pass one; aim for ~70%.
   Use AI to explain sentences, but write your own notes by hand — that's where
   learning happens.
3. Generate ideas by finding gaps in the paper's **question, hypothesis, or
   experimental setup**: apply the method elsewhere, swap the data source, swap a
   component (CNN→transformer), test an untested regime.
4. Your first idea is rarely your best — iterate, check novelty and feasibility,
   and consider emailing the authors.

## Low-compute research angles

When the user has ~$0–$100: compete on insight, not compute.
- Mechanistic "understand X" studies on tiny models.
- Scale-free rules grounded in math (e.g. "≤26 experts per selected expert before
  the most common token overloads one").
- Theory/proofs (e.g. prove a new block generalizes the residual connection).
- Correct, clean implementations + designed-but-unrun scaling experiments for
  people with more compute (see `paper-writing.md`, "zero-compute paper").

## Be honest about the plan

- **Novelty gates the build.** Do the prior-work search on day 1, before
  implementing — especially for well-trodden areas (optimizer comparisons,
  hyperparameter transfer across width/depth, loss balancing). Name the closest
  known lines of work or the search terms; if you can't verify, say "check
  this", don't imply it's open.
- **Say what the budget buys** in rough terms and mark it as an estimate; say
  what kind of claim it can't support.
- **Venue realism.** A solo first paper on tiny models is a long shot at a main
  track; name the fallbacks (workshop, TMLR, arXiv + public write-up) without
  discouraging the attempt.
- If the user has an advisor or labmates, a 10-minute "is this known?" question
  to them beats a day of searching.

## Output for this phase

End with: the chosen question in one sentence, why it's runnable now, the first
experiment pinned down so it can be run as written (model size, named dataset,
step count, the arms, the metric) with a target runtime to verify by timing one
run — "time it first" replaces a *promised* runtime, not the spec. Then one
committed prediction that is consistent with the hypothesis and could actually
be wrong (not true by construction), what result would surprise us, and a rough
timeline to the deadline.
