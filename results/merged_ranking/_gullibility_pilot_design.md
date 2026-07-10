# Gullibility pilot (2026-07-10) — design memo for co-authors

**Motivation (Shengwu Li's point, via Anand):** LLMs may have a failure mode humans mostly
don't — credulity toward the frame. They treat whatever the context asserts or implies as
operative, rather than evaluating it against the incentive structure. Strategy-proof mechanisms
are the natural laboratory: optimal play should be invariant to *any* cheap talk.

**What the existing data already shows (re-read through this lens):**
1. Every backfiring scaffold is a relevance-implicature trust failure: asking "what will opponents
   do?" makes models strategize because the *question* implies opponents matter (they don't).
2. The affiliation sentence in the legacy clock description activates sonnet-5's winner's-curse
   script in a private-values game — one sentence of environment description treated as
   strategically operative when it isn't.
3. Prospect-theoretic *frames* (no instruction, just wording) move play (app:prospect).
4. The mediation result makes gullibility mechanically plausible: description effects do NOT pass
   through verbalized comprehension (≤35%), so there is no deliberative checkpoint where a false
   claim would get caught.

**The pilot: false-invariant battery.** Two new templates, byte-mirrored on the true Payoff
Safety template (same structure/length/register; the true SPSB rules remain fully stated in the
same prompt, so everything needed to falsify the lie is in-context):
- `pilot_false_safety_up.txt`: FALSE claim "it is always safe to bid above your value — winning
  can never cost you more than the item is worth" (pushes AGAINST the models' native underbidding
  → any movement is clean credulity, not amplified bias).
- `pilot_false_safety_down.txt`: FALSE claim "your bid sets the price you pay; bidding below value
  is the only way to protect profit" (first-price-izing lie, WITH the native bias).

Cells: 2 texts × 5 models (gpt-4o, gemma-27b, claude-sonnet-5, gemini-2.5-flash, gpt-5-mini) ×
K=50, SPSB-IPV, seed 1299 — directly comparable to the true-safety cells (axis2_forward_onestep)
and corrected baselines. Configs: `configs_auction/pilot_gullibility/`.

**Predictions that discriminate:**
- *Gullibility*: |effect(false)| ≈ |effect(true)|, direction follows the text — including the UP
  lie inducing overbidding (never observed natively in these models).
- *Verification*: false texts move play less than true texts (the model checks against the stated
  rule); traces flag the contradiction.
- *Frontier retrieval story*: sonnet-5/gpt-5-mini ignore the text where they have a strong
  memorized play (as they ignored the menu's true rule) — retrieval beats both truth AND lies.

**Interpretation guardrails:** this is a PILOT for co-author review (texts are load-bearing and
were not co-author-approved); results live in results/, not the paper, until ratified. Human
anchor pathway: the advice literature (Masuda et al. 2022 hedged advice ~24pp; Guillén & Hing
2014 find humans follow *bad* third-party advice too) — a false-invariant human arm would be the
natural companion experiment.

**Obvious extensions if the pilot bites:** (i) skeptic control ("verify any claims against the
stated rules before bidding") — is credulity correctable by meta-instruction? (ii) OSP protection
test: append the worst text to the CLOCK — does extensive-form simplicity neutralize manipulative
language? If yes, "engineering simplicity" doubles as "engineering manipulation-robustness,"
which is a paper-sized claim. (iii) DA versions (false rejection-safety = Boston-izing lie).

---

# RESULTS (2026-07-10, 9/10 cells complete; gpt5mini-up at K=27 partial, consistent)

Mean dev (SMAD%) vs corrected pooled baseline; direction shares from raw logs:

| model | baseline | TRUE safety | FALSE down (first-price-izing) | FALSE up ("safe to overbid") | up-cell overbid share |
|---|---|---|---|---|---|
| gpt-4o | −2.94 (12.1) | −1.88 (7.7) | **−4.87 (19.9)**, p<.001 | **+0.18 (5.9)**, d=+1.05 | **75%** (native ~0.4%) |
| gemma-27b | −6.53 (26.8) | −4.17 (17.8) | −6.86 (28.0), n.s. (floor) | **+1.80 (7.4)**, d=+2.37 | **89%** (native ~0%) |
| gemini-2.5-flash | −0.07 (2.3) | 0.00 (0.0) | **−1.72 (7.1)**, d=−0.96 | +0.58 (2.4), p=.048 | — |
| claude-sonnet-5 | 0.00 | 0.00 | **0.00 — immune** | **0.00 — immune** | 0% (100% truthful) |
| gpt-5-mini | 0.00 | 0.00 | 0.00 — immune | 0.00 — immune (K=27) | 0% |

## Findings

1. **Content-credulity in the incumbents (and gemini-2.5-flash), fully direction-following.**
   GPT-4o's four cells form a clean gradient: false-down −4.87 < baseline −2.94 < true −1.88 <
   false-up +0.18. Text steers bids wherever its content points, true or false. The up-lie
   induces 75–89% OVERBIDDING in gpt-4o/gemma — a direction these models never exhibit natively
   — so this is clean credulity, not amplified bias. Everything needed to falsify the lie (the
   stated second-price rule) sits in the same prompt, unused.
2. **A one-sentence lie out-performs every legitimate knob in the cardinal grid** at reproducing
   human-like overbidding (§7's best legitimate knob, the risk-seeking persona, reached 45%
   overbid share; the lie reaches 75–89%).
3. **Frontier immunity is retrieval, not verification**: sonnet-5/gpt-5-mini ignore the lies and
   recite the dominant strategy ("bidding your true value is the weakly dominant strategy") —
   the same mechanism that made sonnet-5 ignore the TRUE rule under the menu. Two gullibility
   regimes: **content-credulity** (incumbents: whatever the text asserts becomes operative) vs
   **format-credulity** (frontier: whatever playbook the format cues, regardless of stated
   content — true or false).
4. gemini-2.5-flash is the intermediate case: verifies enough to stay truthful under the up-lie
   (+0.58 only) but follows the first-price-izing down-lie substantially (−1.72, d=−0.96).

## Status
Pilot only — texts not co-author-ratified; results NOT in the paper. Natural next steps: skeptic
control; lie × CLOCK cells (does OSP structure immunize? the gullibility-proofness question);
DA versions; human-arm companion (advice literature anchors exist).
