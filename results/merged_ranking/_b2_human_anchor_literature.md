# Literature check (2026-07-08): the B2 "no human anchor" claim must be qualified

Verified via web (details + URLs in the session transcript; magnitudes for the paywalled two
should be pulled from PDFs before citing numbers):

1. **Gonczarowski, Heffetz, Ishai & Thomas (EC 2024; arXiv:2409.18166)** — beyond the menu-vs-
   traditional contrast the paper already cites, their **Menu-SP treatment** is a genuine
   invariant-exposing description ("Some set of Obtainable Prizes will be calculated using the
   submitted rankings of all the participants except for you. You will receive your highest-ranked
   Obtainable Prize."). Results: SP-understanding 71% (highest; Textbook-SP 62%, mechanics ~56–58%,
   null 54%); straightforward play 59% vs 53% (Textbook-SP) vs 48–50% (null/menu-mechanics) —
   directionally consistent, modest behavioral effect. **This is a human test of an
   invariant-exposing description in DA. Sign agrees with our B2 result; magnitude is muted.**
2. **Katuščák & Kittsteiner, "Strategy-Proofness Made Simpler" (Management Science, 2024)** — TTC;
   description explaining that feasibility depends only on others' reports (type-c invariant).
   **Increases truth-telling**; effect interacts with numeracy. Second human anchor, sign agrees.
3. **Guillén & Hakimov (EER 2018)** — TTC field experiment: describing the strategy-proofness
   *property* helps; **describing the mechanism's mechanics BACKFIRES** (significant negative).
   This is a human anchor for our new DA menu-mechanics backfire cell (4.2%→6.9%) — sign agrees.
4. **Masuda, Mikami, Sakai, Serizawa, Wakayama (Exp. Econ. 2022)** — Vickrey; direct ADVICE
   ("You can maximize your earnings by bidding your valuations as they are"), hedged. Truthful
   bidding 20%→47% (net ≈24pp). Type (b) advice, NOT an invariant description — cite to draw the
   (a) announcement / (b) advice / (c) invariant-exposure taxonomy, which Gonczarowski et al.
   themselves use.
5. Danz–Vesterlund–Wilson (JEP 2024) pure-incentives test: DA incentives are intuitive once
   isolated from the algorithm — consistent with our localization (the barrier is seeing safety
   through the mechanism, not the incentive comparison itself).

## Required paper edits (integration pass)

- §7 (sec:humans) prediction paragraph: reposition. What remains genuinely unanchored:
  (i) the **auction** Payoff Safety one-liner (Masuda is advice, not invariant text; no human test
  of "your bid determines whether you win, not what you pay" as a bare invariant statement);
  (ii) the **magnitude** claim — LLM populations show large behavioral gains from invariant text
  where the human evidence (GHIT 2024) shows understanding >> behavior. Frame our prediction as:
  the behavioral gain in humans should concentrate in invariant-carrying text (consistent with
  GHIT Menu-SP and K&K), should appear in auctions where no test exists, and the mechanics-only
  restatement should backfire (already confirmed in humans by Guillén–Hakimov — cite as anchor).
- tab:ranking human-anchor column: "Menu, invariance property (DA)" → consistent-in-sign with GHIT
  2024 Menu-SP (understanding strongly, behavior modestly); "Menu, mechanics only (DA)" →
  **anchored, agrees** (Guillén–Hakimov 2018 mechanics backfire). "Safety description (auction)"
  stays a lab prediction, now sharpened to the auction domain + magnitude.
- §6.4 "sharpened story" paragraph: add one sentence noting the human record independently supports
  the invariance-content split (GHIT Menu-SP vs Menu-DA; Guillén–Hakimov property vs mechanics).
- Bib: add masuda2022net (Exp Econ 25:902–941), guillen2018effectiveness (EER 101:505–511),
  katuscak2024simpler (Mgmt Sci, online Dec 2024), danz2024evaluating (JEP 38(4):131–154) —
  check auction_v2.bib for existing keys first (gonczarowski2024describing already present).
- 02_related.tex descriptions-literature paragraph: one-sentence update covering K&K + the
  advice-vs-description taxonomy.
