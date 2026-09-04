# Research evidence — how to spot AI writing (2026-09)

Evidence companion to `../SKILL.md`. The skill carries the actionable rules; this file carries the numbers, study names, and citations behind them so the skill can stay short.

- **Compiled:** 2026-09-03
- **Source:** NotebookLM deep web research, 83 sources. Notebook "Research: How to Spot AI Writing (2026-09)". Raw output: `~/.claude/projects/system-improvement/outputs/notebooklm-research/2026-09-03-spot-ai-writing/`
- **Covers:** q1 lexical tells · q2 structural tells · q3 model fingerprints · q4 editing techniques and false positives · q5 deep-report synthesis.

> **PERISHABLE.** Model-specific findings decay fast. Labs suppress named tells in post-training (GPT-4.1 → GPT-5.4 em dash collapse is the clearest case) and writers scrub memed vocabulary once it is memed. Anything naming a model version or a per-model rate should be treated as stale after roughly one quarter — re-run the research quarterly. Structural and rhetorical findings age far more slowly than lexical ones.

---

## Q1 — Lexical tells

*Overused words, phrases, openers and closers beyond the known Wikipedia list; model-specific "Claudisms" and "Geminisms"; what the PubMed excess-vocabulary studies measure.*

### Punctuation and typography

**Em dash.** E. M. Freeburg, *"The Last Fingerprint: How Markdown Training Shapes LLM Prose"* (arXiv:2603.27006, March 2026). Thesis: the em dash is "markdown leaking into prose" — the smallest prose-legal unit of structural organization, an analogue of the markdown divider `---`. Two-condition suppression experiment, ~240,000 generated words against a 57,232-word human baseline. Em dashes per 1,000 words:

| Model | Unconstrained | Suppressed |
|---|---|---|
| GPT-4.1 (OpenAI) | 10.62 | 9.10 |
| Claude Opus 4.6 (Anthropic) | 9.09 | 0.19 |
| Claude Sonnet 4 (Anthropic) | 8.29 | 1.31 |
| Claude Haiku 3.5 (Anthropic) | 7.51 | 0.18 |
| DeepSeek V3 | 6.95 | 5.41 |
| GPT-4o Mini (OpenAI) | 4.16 | 4.23 |
| GPT-4o (OpenAI) | 4.12 | 2.68 |
| Gemini 2.5 Pro (Google) | 3.53 | 0.00 |
| GPT-5.4 (OpenAI) | 1.43 | 0.29 |
| Gemini 2.5 Flash (Google) | 1.28 | 1.48 |
| Llama 3.1 8B / 3.3 70B Instruct (Meta) | 0.00 | 0.00 |
| **Human baseline** | **3.23** | — |

Human essays ranged **0.33 to 17.12** — the spread is why an em-dash count alone proves nothing. Corpus confirmation: Czuma (2026), 69,632 *medRxiv* Discussion sections, papers containing at least one em dash rose from **4.23%** before 2022-11-30 to **11.58%** after.

**Curly vs straight quotes** (Wikipedia volunteer editors, on default typesetting behaviour): ChatGPT and DeepSeek emit curly quotes and apostrophes natively; Gemini and Claude emit straight ones.

**Present participial clauses** ("...reducing manual tasks, increasing productivity"). Reinhart et al., *PNAS*, February 2025 — 8,290 human texts with matched LLM outputs. GPT-4o uses them at **5.3x** the human rate. Wikipedia's cleanup guide calls them "tailing clauses" tacked on to inject false significance.

**Nominalisations** ("utilization", "conceptualization"). Same PNAS study: GPT-4o at **2.1x** the human rate, producing a heavy passive corporate register.

**Mechanical boldface.** Wikipedia and GitHub cleanup guides: bolding key concepts across whole paragraphs in a "key takeaways" shape, inherited from READMEs, fan wikis, pitch decks.

### Claudisms

Tracked on Hacker News and ExplainX.ai. Primary: **"load-bearing"** — a 614-comment HN thread ("How to stop Claude from saying load-bearing"), applied to trivial code or ideas carrying no structural weight. Also **"substrate"** (biochemistry term for abstract infrastructure); **"honest take" / "honest assessment" / "honest caveat"** (reflective filler when faking humility); **"synthesize"** ("I can synthesize that for you"); **"reconciling", "fold", "crux", "invariant", "gate", "canonical"** (over-represented enough that engineers keep ban lists in `CLAUDE.md`); **"belt-and-suspenders"**; **"beat"** and **"register"** (structural timing / social tone, noted by public speakers drafting scripts); **"blast radius", "cutover", "bake", "earned its keep"**. **"wire" / "wiring" / "wired"**: a commit-log analysis inside one engineering org found "wired" going from virtually non-existent to **10% of commit descriptions** as Claude usage rose. **"seam" / "seamslop"** — named by Matt Pocock, documented on ExplainX.ai, after Claude Opus used "seam" relentlessly as connective tissue while explaining Buddhism.

### Geminism

**"analytical"** — Gemini 3 Pro latches onto the word if the user types it even once, then repeats it across the rest of the conversation.

### B2B "high drama" metaphors

From Olivia Cal's 2026 B2B blacklist, Plus AI's style audit, r/ChatGPT compiled lists, Grammarly's high-frequency AI words, HumanizeThisAI blind tests: **"beacon"** ("a beacon of hope"), **"symphony"** ("a symphony of features"), **"roadmap"**, **"journey"**, **"unwavering"**, **"Swiss-Army knife"**, **"seamlessly integrated"**, **"at the forefront"**, **"game-changer"**, **"unveil" / "unleash" / "unmask"** (brochure verbs replacing show, introduce, explain), **"robust" / "facilitate" / "leverage"** (readers flagged these as jargon that flattens prose), **"X in a trench-coat"**.

### Openers

**"With the advent of..."**, **"In today's digital age..."**, **"In the ever-evolving landscape of [industry]..."** — SynkrLAB's overused ChatGPT lead-ins, Florida Realtors' writing tells, Olivia Cal's transition checklist. Statistically safe next-token placeholders. Also **"Imagine a world"**, **"Demystify"**, **"As a college student"**, and **"I rise to speak"** — noticed by parliamentary reporters when UK MPs' AI-drafted speeches all defaulted to it.

### Transitions and padding

**"Furthermore", "Moreover", "Additionally", "Consequently", "Hence", "Thus"** — SynkrLAB's academic/corporate connectors grid, Grammarly, HumanizeThisAI. **"This means that...", "As a result...", "One key benefit is...", "Another important factor is...", "This highlights the importance of..."** — Winston AI's 2026 catalog of symmetric paragraph bridges. **"However, one must consider"** — r/ChatGPT false-contrast signpost. **"It's worth noting that...", "In terms of...", "To elaborate...", "In light of..."** — SynkrLAB clarifying/framing phrases.

### Closers

**"Ultimately", "To wrap things up", "At the end of the day", "In essence"** — critiqued in "32 Signs of AI Writing" as "essay-format brain damage from training data"; real writers land the plane or trust the reader. **"Remember, [restated thesis]"** — the patronizing close. Growth-hacker fragments from Plus AI's audit: **"And honestly? That's rare"**, **"Here's the kicker"**, **"And here's the part most people miss"**, **"You're not imagining it"**, **"The best part? It's this"**, **"Shouting into the void"**, **"Curious what others think"**, **"No fluff"**.

### Creative and empathetic-prompt tells (r/ChatGPT logs)

**"You're not broken"** (appears in venting prompts with no insecurity implied); **"It's enough" / "you're enough" / "and for now, that's enough"**; **"Victorian [orphan / wife / child]"** in period framing; the grit cluster **"feral", "raccoon", "fumbling", "gremlin", "the weight pressing down on me"**.

### Academic excess-vocabulary spikes

Dmitry Kobak et al., *Science Advances*, July 2025 — 15.1 million PubMed abstracts, counterfactual excess-frequency ratio *r* for 2024: **"delves"** *r* = **28.0**; **"underscores"** *r* = **13.8**; **"showcasing"** *r* = **10.7**. Largest absolute volume gaps in the corpus: **"potential" δ = 0.052**, **"findings" δ = 0.041**.

Kentaro Matsui, *"Delving Into PubMed Records"*, *Perspectives on Medical Education*, December 2025 — 135 AI-influenced terms across 27.5 million PubMed records. Terms at modified Z-score ≥ 3.5 include **delve, underscores, primarily, meticulous, boast, commendable, intricate, realm**.

**Legacy-attribution phrases** (from "agent-toolkit", the "undue emphasis on legacy and importance" pattern): *stands/serves as*, *is a testament/reminder*, *plays a vital/significant/crucial/pivotal role*, *reflects broader*, *symbolizing its ongoing/enduring/lasting impact*, *key turning point*, *indelible mark*, *deeply rooted*, *profound heritage*, *steadfast dedication*.

---

## Q2 — Structural tells

*What gives AI away at the level of cadence, paragraph shape, meta narration, punctuation habits, formatting, parallelism and hedging — and what heuristic detects each.*

**1. Metronomic cadence / low burstiness.** Computational stylometry scores sentence-length uniformity on a **Consistency metric (0-100)**. "Average AI" clusters tightly at **52-55** across all model families. RLHF evaluators penalize both monotony and chaos, pushing models to group sentence lengths into **15-25 words**. **Type-Token Ratio (TTR)** clusters just as tightly at **44-49%** across every major model. RLHF-tuned models average **Expressiveness 76/100** and **Conciseness 42/100**.
*Heuristic:* read it out loud. Same tempo every sentence, standard SVO, no short punchy bursts = likely AI. GPTZero treats missing length/structure variation as a primary signal.

**2. Paragraph uniformity — "perfect rectangles."** Paragraphs run claim → example → restatement with near-equal sentence lengths, producing blocks that look identical from a distance.
*Heuristic:* look at the layout without reading. Identical block shapes and uniform line counts show missing human organizational randomness.

**3. Openers, closers, tidy summaries.** Summary-then-restate openings ("When it comes to understanding [topic], there are several key factors to consider..."). Conclusions restating the introduction almost verbatim with no new insight. Canned closers: *Ultimately, In conclusion, To wrap things up, Remember, [thesis]*.
*Heuristic — the "cut-the-ends" test:* delete the first and last paragraphs. In AI text the document loses zero informational value, because those paragraphs are throat-clearing.

**4. Meta process narration and abstract headings.** The model narrates gathering information — "after reviewing the available sources", "an examination of history shows", "upon closer analysis" — having no lived experience to state from. A human expert states the fact; the chatbot recounts reading it. Headings: humans write *Reception*, *Early Life*; LLMs write *Why the Reception Was Mixed*, *Key Contributions and Lasting Impact*.
*Heuristic:* flag any heading that gives away the section's conclusion, and any sentence narrating the document's own assembly.

**5. Punctuation and typesetting habits.** Colon-heavy list headers — the **Bold Header: Explanatory Sentence** shape, rarely used without the colon. Curly quotes (ChatGPT, DeepSeek) vs straight (Gemini, Claude).
*Heuristic:* inspect contractions. Mixed straight/curly apostrophes in one short text, or curly quotes inside code samples, mean unedited copy-paste.

**6. Em dash as structural joint.** Freeburg's two mechanisms: (a) *structural joint leakage* — models trained on markdown internalize `---`, `-` and YAML delimiters as architectural boundaries; told to write pure prose with no headers, bold or lists, the structural impulse escapes through the em dash, legal in both registers; (b) *decision-deferral* — the em dash is a "semantic airlock" letting an autoregressive model avoid committing to a period, comma, colon or parenthesis, piling on unearned clauses and triplets.
*Heuristic:* density and spacing, not presence. Several unspaced em dashes in one short paragraph doing three different grammatical jobs is the tell.

**7. Formatting overdose.** Mechanical bolding of keywords, inherited from READMEs, wikis and slides. On Wikipedia, AI frequently skips Level-2 headings (`==`) straight to Level 3 (`===`), breaking accessibility conventions. Listicle reflex: bullets where a flowing paragraph would build the argument better, dodging the work of writing transitions.

**8. Negative parallelism.** The contrast-reframe: *"It is not just about X, it's about Y"*, *"not because of X, but because of Y"*. Pew Research Center analysis of Common Crawl shows the web rate rising from **0.87 uses per 10k words in early 2023 to 2.72 in late 2025**.
*Heuristic:* decorative or repeated "not just X, but Y" that reframes without delivering insight is a hollow structural move.

**9. Hedge stacking, sycophancy, the "no-screw-up" tell.** RLHF's safe/helpful/harmless objective produces a defensive crouch — *"It is important to remember", "it could be argued that", "generally speaking", "to some extent"* stacked at the start, middle and end of one paragraph. Sycophancy pushes "rounder" people-pleasing word choices (pebble over rock) and therapeutic cliches. Then the absence tell: flawless grammar, zero voice, zero idiosyncrasy, zero mistakes. Humans write about friction and anecdotes ("I tried this once and got fired"); the total absence of human failure is itself a signal.

---

## Q3 — Model fingerprints and 2024 → 2026 drift

*How Claude, GPT-4o/5, Gemini, Llama and DeepSeek differ stylometrically, and how the tells moved.*

**Claude (Anthropic) — the careful literary architect.** Rated most human-like in blind tests for literary subtlety, voice adaptation and rhythm variation. Claude Opus produces the longest, most structurally complex sentences of any major model, with lengths swinging naturally from **5 to 40 words** — real burstiness. Low conciseness: it meanders. Tone thoughtful, measured, warm; hedging reads as a careful person rather than a risk-averse machine. Over-intensifies with *incredibly*, *wildly*. Straight quotes. Em dash **9.09/1k** unconstrained, dropping **98%** to **0.19** under suppression. Vocabulary: the Claudisms listed under Q1.

**OpenAI (GPT-4o, GPT-5) — the dense enthusiastic corporate editor.** Noun-heavy. Reinhart et al. (PNAS): present participial clauses at **5.3x** the human rate, nominalisations at **2.1x**, agentless passive at **half** the human rate. Reward tuning favours energetic positive language. Curly quotes. GPT-4.1 is the em dash outlier at **10.62/1k** — higher than Herman Melville in *Moby-Dick* — with high suppression resistance: **9.10** under a no-markdown instruction, still **3.86** under explicit em dash prohibition. Vocabulary: *camaraderie* and *tapestry* about **150x** the human rate in the same genre; heavy overrepresentation of *palpable, intricate, delve, underscore, showcase, meticulous, boast*; LinkedIn structures ("No fluff. Just shouting into the void here...") and openers like "Short answer: No—".

**Gemini (Google) — the structured bulleted pragmatist.** Heavy structural rigidity: nested bullets and numbered lists by default, every section on an introduction-body-summary template with mechanical transitions and bold headers. Dry, clinical, cautious; lowest expressiveness of the major models, reading like a sterile textbook. Straight quotes. Em dash **3.53/1k** unconstrained, suppressed completely to **0.00**. Prefers accessible terms over jargon ("blood sugar" not "glucose"). Echoes the user's vocabulary and repeats rule-of-three triplets about twice per page. *Stuttering bug:* Google Help and community threads from late 2025 document Gemini Pro's context memory collapsing after **10-20 turns**, after which it separates every word with ellipses and loops.

**Llama (Meta) — the non-dashing reserved observer.** Llama 3.1 8B and 3.3 70B produce exactly **0.00** em dashes per 1,000 words under every condition. The pre-RLHF base model had a latent markdown tendency of **0.49** em dashes/1k and **28** markdown features; Meta's RLHF drove it to absolute zero. Tone cautious and observant. Unique tell: **"unease"** at **60-100x** the human rate in the same genre. Also over-prefers *palpable* and *intricate*.

**DeepSeek — the high-dash challenger.** Structurally aligned with the OpenAI family. Curly quotes. Em dash **6.95/1k** unconstrained, **5.41** under a no-markdown rule, **1.57** even under explicit prohibition.

### Drift, 2024 → 2026

```
[2024: peak vocabulary tells] -> [2025: structural + punctuation tells] -> [2026: tuned out]
"delve" spikes 28x in papers     em dashes double on web; lists dominate    GPT-5.4 at 1.43/1k
```

1. **Vocabulary tells memed and declined.** *delve*, *tapestry* peaked in 2024 (Kobak: *r* = 28.0 for "delves", 13.8 "underscores", 10.7 "showcasing"). Once publicly mocked, writers filtered them and labs targeted them in post-training. Lexical tells age fastest.
2. **Em dash became the dominant structural tell** as vocabulary bans entered system prompts. Freeburg explains why: dual-register status — a formatting joint to the model's structural brain, legal punctuation to the prose processor — so it survives suppression that kills headers and bullets.
3. **OpenAI's generational shift.** GPT-4.1 at **10.62** unconstrained vs GPT-5.4 at **1.43** unconstrained and **0.29** suppressed, with zero markdown features leaking into prose.
4. **Web lag.** Pew Research Center, 490,000 English webpages from Common Crawl: em dashes **doubled** 2023→2026 (**5.79 → 11.19 per 10k words**); Oxford commas up **63%** (**34.04 → 55.51 per 10k words**); negative parallelism nearly **tripled**.
5. **Academic saturation.** Kyle Siler, *PNAS* 2026, 7.3 million papers: roughly **57%** of 2025 published articles show LLM-associated language fingerprints, up from **12% in 2023**.

---

## Q4 — Editing techniques, anti-patterns, false positives

*What editors change, what to do before drafting, what not to do, and who gets falsely accused.*

### Before drafting

- **Write messy first drafts.** An unpolished braindump sets an irregular grammatical baseline an LLM cannot replicate.
- **Outline lived experience, not abstract claims.** Map verifiable case studies, direct client quotes, real metrics ("when we cut [client]'s proposal turnaround from 12 days to 4") rather than gesturing at scenarios.
- **Prompt with aggressive constraints.** Never ask for "better" or "more professional" — that triggers the homogenized default. Supply a specific persona plus a sample of your own writing, and explicit rules: contractions, sentences under 30 words, active voice, banned jargon (*robust*, *pivotal*).
- **Set numeric stylometric targets.** Advanced workflows prompt against measured metrics — e.g. "target a conciseness rating of 68 versus the model default of 42".

### The pattern layer

Detectors evaluate probabilistic patterns and cadence across segments, not banned words.

1. **Sentence-length uniformity.** AI clusters at **15-25 words**. Fix with the **high-low technique**: a long explanatory sentence, then a short sharp one. Like this.
2. **Paragraph rectangles.** The recipe is claim → explain → generic example → restate. Vary paragraph depth; interrupt with asymmetric lists, bolded fragments, one-line paragraphs.
3. **Symmetrical openers and closers.** Delete the first and last paragraphs of an AI draft. Answer the reader's question inside the **first 200 words** with no elaborate setup.
4. **Punctuation and formatting.** Replace crutch em dashes with periods or commas, or split the clause; keep em dashes for genuine high-value interruptions. Break the **rule of three** — cut lists to two or expand to four, since triplets score as balanced in training data. Strip bolding from generic qualifiers; bold only concrete metrics, named sources, punchlines. Delete the **"not X, but Y"** negation pivot and state the point.

### The meaning layer

- **Take a stance.** RLHF makes models allergic to controversial positions; they hide behind fake balance ("While X has merits, Y also offers benefits..."). Pick a side.
- **Nix defensive hedging.** Cut *it is important to consider*, *generally speaking*, *to some extent*, *it could be argued*.
- **Name, date and link claims.** The "vague-specific mismatch" ("studies indicate that efficiency increases") is a core tell — AI has no retrieval layer at generation time. Name the institution, date the data, link it. If you cannot source it, delete it.
- **Inject failure.** LLMs have no regrets or screw-ups. "We tried this exact strategy in 2024 and the client fired us because..." is unfakeable.
- **Eradicate inanimate agency (the actor tell).** AI gives action verbs to objects and skips the human doer. *"The closure map published."* → *"The city planning office published the closure map."* *"The lanes closed."* → *"Road crews closed the lanes."*
- **Eliminate meta-narration.** Cut "Let's dive into these steps", "Below, we will analyze".

### Anti-patterns

- **No mechanical find-and-replace.** Swapping *additionally* → *also*, *delve* → *explore*, *moreover* → *besides* does nothing to sentence-rhythm predictability. Detectors read multi-word probability sequences; word swaps still flag.
- **Avoid thesaurus-swapping humanizer tools.** They lower statistical probability at the cost of grammatical-but-bizarre phrasing — "paramountly significant" instead of "important".
- **Apply the pub test.** Read the rewrite out loud. Would you say this to a colleague over a beer? If not, discard it and write it plainly.
- **Avoid over-fragmentation.** Chopping every sentence into fragments, or the staccato triplet ("No fluff. No filler. No bullshit."), mimics AI marketing-brochure style and destroys voice.

### The false-positive problem

Detectors are probability estimators, not forensic proof.

- **ESL writers.** Stanford study led by Weixin Liang, testing major detectors against TOEFL essays by non-native speakers: **61.22% average false-positive rate**. Non-native writers are trained toward grammatically perfect, structured, safe prose, leaning on textbook transitions (*moreover*, *furthermore*, *in addition*) and formal hedges. They take fewer casual grammatical risks, so their text sits in the same low-perplexity band detectors flag.
- **Academic and technical prose.** Requires precise standardized terminology ("convolutional neural network", anatomical vocabulary). Style guides encourage features overlapping LLM defaults: **nominalizations** (LLMs at **1.5-2x** casual human rate), **present participial clauses** (GPT-4o at **2-5x** human baseline), formal tricolon rule-of-three rhetoric.
- **Protocol against over-correction:** (1) never treat a detector score as a verdict — correlation, not confession; (2) verify sourcing over style — named, dated, verifiable citations for every major claim indicate human expertise, since AI cannot invent checkable real-world citations without a retrieval layer; (3) check for idiosyncratic errors — localized idiom mistakes and personal asides that RLHF would have smoothed away.

### Audit decision tree

```
[Explicit summary at the start or end of every section?]
   |- YES: delete the summary paragraph entirely. (10 sec)
   `- NO: proceed.
[Paragraphs are perfect rectangles of uniform sentence length?]
   |- YES: find the longest sentence, put a short punchy fragment right after it. (30 sec)
   `- NO: proceed.
[Points, adjectives, or bullets in groups of exactly three?]
   |- YES: cut one or expand to four to break the symmetry. (1 min)
   `- NO: proceed.
[Claims attached to "studies show" / "research indicates"?]
   |- YES: replace with named source + date + link, or delete the claim. (5-15 min)
   `- NO: proceed.
[Defensive hedges like "it's important to note"?]
   |- YES: strike the introductory phrase, state the claim directly. (15 sec)
   `- NO: proceed.
```

---

## Q5 — Deep report: methodology, taxonomy, detection reliability

*The synthesis across the notebook's landmark studies — sample sizes, the four-register taxonomy, the PubMed indicator set, and what the papers conclude about detection.*

### The four constituent studies

1. **Siler, 2026 (*PNAS*)** — macro diffusion. Full texts of **7.3 million** journal articles, 2020-2025, across Elsevier, Frontiers, MDPI, PLoS. Corpus of **228 focal words** spiking post-2022; tracked regional, institutional, publisher and disciplinary adoption.
2. **Kobak et al., 2025 (*Science Advances*)** — excess vocabulary, modelled like epidemiological excess mortality. Over **15 million PubMed abstracts**, 2010-2024. Pre-ChatGPT baseline (2021-2022) projected expected frequencies for **26,657 words** into 2024 to compute the counterfactual frequency gap (δ).
3. **Freeburg, 2026 (*arXiv*)** — structural-register hypothesis. Two-condition suppression experiment on **12 instruction-tuned models** across 5 providers (Anthropic, OpenAI, Meta, Google, DeepSeek), ~**240,000 words** of prose against a **57,232-word** human baseline. Traces markdown-formatted pretraining compressing into prose as em dashes.
4. **Juzek & Ward, 2025 (*arXiv*)** — learning-from-human-feedback as driver of lexical choice. Evaluated Meta's Llama models to isolate RLHF/DPO effects; by emulating the human-feedback evaluation procedure they showed feedback workers systematically over-reward texts containing specific stylistic keywords, cementing a "lexical alignment bias".

### Macro adoption

- **57%** of published academic articles showed LLM-influence signs by 2025, up from ~**12%** in 2023 (Siler, 7.3M sample).
- Kobak's **lower bound**: at least **13.5%** of 2024 PubMed abstracts were LLM-processed — a minimum of **200,000 papers per year**. In younger for-profit journals and non-native English regions the lower bound reaches **40%**.
- The post-2022 shift in written English exceeds the linguistic disruption of the COVID-19 pandemic.

### Word-frequency surges (Kobak et al.)

Frequency ratio *r* (observed vs expected) and absolute percentage-point gap δ: *delves* **r = 28.0** (largest stylistic spike in scientific history); *underscores* **r = 13.8**; *showcasing* **r = 10.7**; *potential* **δ = 0.052**; *findings* **δ = 0.041**; *crucial* **δ = 0.037**.

### The four-register taxonomy of LLM tells

1. **Lexical register.** Rare style words (*delve, intricate, realm, meticulously, showcasing, pivotally*) plus common surge connectors used as filler (*notably, particularly, across, additionally, within*).
2. **Structural register (markdown and punctuation leakage).** Dual-register punctuation — the em dash as the ultimate structural joint, slipping past formatting-suppression prompts because it is prose-legal. Hierarchical bulleting with bold headers when uninvited. Typographical typology: curly quotes native to OpenAI and DeepSeek, straight to Claude and Gemini.
3. **Grammatical register.** Present participial clauses at **5.3x** the human baseline in GPT-4o output; nominalisations at **2.1x**, producing a clinical passive B2B/academic tone.
4. **Rhetorical register.** Puffery and reassurance ("marking a pivotal moment", "stands as a testament to"). Collaborative leftovers that bypass human editing — JSON citation residue like `{"attribution":{"attributableIndex": "X-Y"}}`, or "I hope this helps!".

### The PubMed common-words indicator set

Kobak et al. showed **ten manually selected high-frequency style words** act as a rigorous LLM-usage indicator:

> **across, additionally, comprehensive, crucial, enhancing, exhibited, insights, notably, particularly, within**

Combined absolute frequency gap for the set in 2024 academic writing: **Δ_common = 11.0%**. The set is completely non-overlapping with the rare-word list (**291 words** at frequency threshold *p* < 0.02, **Δ_rare = 13.6%**), making it a mathematically independent confirmation that **11% to 13.6%** of scientific abstracts are LLM-assisted.

### Detection-reliability conclusions

- **Single-feature tells are not detectors.** Mark Twain used **10.13** em dashes per 1,000 words in *Huckleberry Finn* — effectively identical to GPT-4.1's 10.62. The folk em-dash heuristic fails on its own.
- **Short-text bias.** Perplexity/burstiness classifiers and lexical checks are highly unstable on short samples and produce high false-positive rates.
- **Sociological stratification.** Detectors disproportionately misflag non-native English speakers and formal academic/technical prose. Siler found the highest flag rates at lower-ranked institutions and in regions further from English-primary use, so aggressive automated policing penalizes equity-seeking scholars.
- **Linguistic co-evolution.** 2024's tells are decaying: writers scrub *delve* and *pivotal* while providers suppress punctuation profiles in newer generations. Detection is a moving target — which is why this file is dated and perishable.

### Flowery-language examples from the wild

Kobak et al. highlighted three real published 2023 sentences carrying the full stylistic footprint:

1. "By **meticulously delving** into the **intricate** web connecting [...] and [...], this **comprehensive** chapter takes a deep dive into their involvement as significant risk factors for [...]."
2. "A **comprehensive** grasp of the **intricate** interplay between [...] and [...] is **pivotal** for effective therapeutic strategies."
3. "Initially, we **delve** into the **intricacies** of [...], accentuating its indispensability in cellular physiology, the enzymatic labyrinth governing its flux, and the **pivotal** [...] mechanisms."

---

## Known conflicts in the source material

The NotebookLM outputs disagree with themselves on three Freeburg figures. q1, q2 and q3 cite one set; the q5 summary table cites another. Both are recorded rather than silently reconciled. Prefer the q1/q2/q3 set — it appears three times and matches the per-model detail table — and re-verify against the Freeburg paper before quoting.

| Model | q1 / q2 / q3 unconstrained | q5 table unconstrained |
|---|---|---|
| Claude Opus 4.6 | 9.09 | 8.46 |
| DeepSeek V3 | 6.95 | 8.66 |
| GPT-5.4 | 1.43 | 0.75 |

Suppressed values agree across all files (0.19, 5.41, 0.29 respectively).

Second discrepancy: q3 gives GPT-4o participial clauses at **5.3x** and nominalisations at **2.1x** (matching Reinhart et al. directly), while q4's false-positive section quotes softer ranges — participial clauses **2-5x**, nominalisations **1.5-2x**. The q4 ranges appear to describe LLMs generally rather than GPT-4o specifically.

---

## References

The NotebookLM export emitted its numbered `## References` lists empty — the inline `[n]` markers in the raw q-files have no resolved titles or URLs attached. Entries below are reconstructed from attribution stated inline in the research text. No URL has been invented; the single link present is derived mechanically from a stated arXiv identifier.

### Peer-reviewed and preprint studies

- Kobak, D. et al. — "Excess vocabulary" analysis of 15.1M PubMed abstracts. *Science Advances*, July 2025. [q1] [q3] [q5]
- Reinhart, A. et al. — Corpus study of 8,290 human texts and matched LLM outputs; participial clauses and nominalisations. *PNAS*, February 2025. [q1] [q3] [q5]
- Freeburg, E. M. — "The Last Fingerprint: How Markdown Training Shapes LLM Prose." *arXiv*:2603.27006, March 2026. https://arxiv.org/abs/2603.27006 [q1] [q2] [q3] [q5]
- Siler, K. — LLM language fingerprints across 7.3M journal articles, 2020-2025. *PNAS*, 2026. [q3] [q5]
- Matsui, K. — "Delving Into PubMed Records": 135 AI-influenced terms across 27.5M PubMed records. *Perspectives on Medical Education*, December 2025. [q1]
- Juzek, T. & Ward — Learning-from-human-feedback as driver of lexical alignment bias in Llama models. *arXiv*, 2025. [q5]
- Czuma — Temporal corpus analysis of 69,632 *medRxiv* Discussion sections; em dash prevalence pre/post 2022-11-30. 2026. [q1]
- Liang, W. et al. (Stanford) — Detector false-positive rates on TOEFL essays by non-native English speakers. [q4]

### Institutional research

- Pew Research Center — Common Crawl analysis of 490,000 English webpages; em dash, Oxford comma and negative-parallelism frequency shifts 2023-2026. [q2] [q3]

### Editorial guides, community catalogs, vendor lists

- Wikipedia — "Signs of AI writing" cleanup guide and volunteer-editor observations (tailing clauses, curly quotes, mechanical boldface, heading-level skipping). [q1] [q2]
- Hacker News — "How to stop Claude from saying load-bearing" (614 comments) plus related threads on *substrate*, *honest take*, *synthesize*, *fold*, *crux*, *invariant*, *gate*, *belt-and-suspenders*, *X in a trench-coat*. [q1] [q3]
- ExplainX.ai — Claudism tracker; "seamslop" (term attributed to Matt Pocock). [q1] [q3]
- Olivia Cal — 2026 B2B content blacklist of flowery metaphors and vague adjectives. [q1]
- Plus AI — writing style audit; ChatGPT-specific phrase list. [q1] [q3]
- SynkrLAB — overused ChatGPT lead-ins; academic/corporate connectors grid; clarifying and framing phrases checklist. [q1]
- Winston AI — 2026 catalog of overused transition sentences. [q1]
- Grammarly — high-frequency AI words and transitions. [q1]
- HumanizeThisAI — blind-test reader flags on corporate jargon. [q1]
- r/ChatGPT — community catalogs of cliche phrases, therapeutic defaults, Victorian tropes, the creative-grit adjective cluster. [q1]
- "32 Signs of AI Writing" (Jef's copywriting tips) — the "in conclusion close" and the patronizing "remember" close. [q1]
- Florida Realtors — AI writing tells for practitioners. [q1]
- agent-toolkit — "undue emphasis on legacy and importance" pattern. [q1]
- GitHub cleanup guides — over-emphasis and boldface patterns inherited from READMEs. [q1]
- GPTZero — publicly described reliance on sentence-length and structure variation as a primary statistical signal. [q2]
- Google Help and community threads, late 2025 — Gemini Pro context-collapse "ellipsis stuttering" bug after 10-20 turns. [q3]
- UK parliamentary reporting — "I rise to speak" as an AI-drafted speech default. [q1]
