# Decision log

Each product decision, the options that were considered, and the reasoning. Decisions marked **Owner call** were made by the product owner (Chandni). **Build call** marks implementation details that follow from them.

| # | Decision | Options considered | Chosen | Why | Type |
|---|---|---|---|---|---|
| D1 | Document domain | Employment rules · business setup · residency/visas · data protection | **Employment rules: UAE Labour Law + ADGM ER 2024** | Official Arabic and English texts exist for the Labour Law, which makes the Arabic test meaningful. Mainland vs free zone is a real, confusing split. Questions are everyday and high-stakes. | Owner call |
| D2 | Target user | HR/people ops · employees and new hires · government service channel | **Employees and new hires** | The largest group with this need. They ask in dialect and plain language, so it's a harder and more realistic test of Arabic quality. | Owner call |
| D3 | Model lineup | Small sovereign + frontier · large sovereign + frontier · both tiers | **Jais 2 8B Chat, Falcon-H1-Arabic 7B Instruct, Claude** | Tests the realistic "self-host a small sovereign model vs pay for a frontier API" choice. Runs on Colab at low cost. | Owner call |
| D4 | Accuracy scoring | Auto + LLM judge + human spot-check · judge only · human only | **Auto key-fact + LLM judge + human spot-check (~15)** | Scales to 120 answers while proving how far the judge can be trusted | Owner call |
| D5 | Citation quality | Right article + supports claim · right article only · any citation | **Right article AND supports the claim** | Catches the most dangerous failure: the right article cited for a claim it doesn't make | Owner call |
| D6 | Arabic fluency | Judge + native reviewer · judge + auto checks · auto only | **Judge (1–5) + native reviewer on ~10 answers** | Supports a credible Arabic quality claim, not just "replied in Arabic" | Owner call |
| D7 | Test set | 40 (50/50 EN/AR) · 25 · 60+ | **40: 20 EN / 20 AR, ~6 dialect, ~6 comparisons, ~5 unanswerable** | Covers every failure mode while staying small enough to verify by hand | Owner call |
| D8 | Retrieval | Same for all · tuned per model | **Same passages for every model** | Controlled experiment: differences come from the model | Owner call |
| D9 | Baseline and judge | Claude/GPT combinations | **Claude answers, GPT judges** | Avoids a model grading its own family | Owner call |
| D10 | How the winner is picked | Accuracy-first · Arabic-first · cost-first · trade-offs only | **Accuracy and safe refusals first** (40/25/20/15) | Wrong legal information is the worst failure for this user | Owner call |
| D11 | Publishing | Private then public · public now · don't push | **Private now, public once results are in** | No half-finished public claims | Owner call |
| D12 | Chunking unit | Fixed-size tokens · Article/Section | **One chunk per Article/Section** (long ones split, keeping the label) | Makes citation checks automatic and exact | Build call |
| D13 | Retriever | BM25 · embeddings · hybrid | **Hybrid: BM25 + multilingual embeddings (bge-m3) when available** | Arabic questions must find English ADGM sections, and BM25 alone can't match across languages | Build call |
| D14 | Gold answer status | Trust drafted answers · verify | **Every gold answer starts `draft`; promoted only after the fact-in-article check + human read** | Keeps confirmed facts separate from drafted ones | Build call |

| D15 | Unknown jurisdiction (user doesn't say mainland or ADGM) | Show both, model explains · let search decide · assume mainland | **Always retrieve mainland AND ADGM passages; the model says which rule applies where** | Many employees don't know which regime covers them, so silently answering with the wrong one is the riskiest failure | Owner call |
| D16 | Answer style | Short + plain + next step · short + citations only · detailed with conditions | **2–4 plain-language sentences, citations, then one "what to do next" step** | Built for employees, not lawyers: actionable and readable | Owner call |
| D17 | Claude baseline tier | Haiku · Sonnet · Opus · Haiku + Sonnet | **Sonnet (mid-tier)** | The realistic production choice, and a fair cost-quality comparison | Owner call |
| D18 | Running the open models | Colab Pro full precision · free Colab 4-bit · free first, upgrade if needed | **Colab Pro, full precision (bf16)** | Models are judged as released, so compression can't be blamed for weak results | Owner call |

## Open questions (to decide)

- Q2: Do we add a large-model tier (Jais 2 70B / Falcon-H1-Arabic 34B) in v2?
- Q3: Who is the native Arabic reviewer?
