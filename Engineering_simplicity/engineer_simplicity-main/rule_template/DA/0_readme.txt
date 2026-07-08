# DA (Deferred Acceptance) Prompt Templates

This folder contains prompt templates for LLM experiments on Deferred Acceptance matching.

## Theoretical Background

### Key Papers
1. **Li (2017)**: OSP mechanisms - sequential local queries make dominance "obvious"
2. **Ashlagi-Gonczarowski (2018)**: DA is OSP-implementable only under acyclic priorities
3. **Gonczarowski-Heffetz-Thomas (2024)**: Menu framing for DA (descriptions, not OSP implementation)
4. **Pycia & Troyan (2023)**: k-step foresight and simplicity standards

### The Key Comparison
| Interface | Analogy | True OSP? | Expected Truthfulness |
|-----------|---------|-----------|----------------------|
| Submit full RoL (direct) | Sealed-bid 2P | NO | ~50-60% |
| Sequential local queries (iterative) | Ascending clock | See below | ~90%+ |

### IMPORTANT: Iterative vs True OSP (2026-02-09)

The current "OSP" mode is more accurately described as **"Iterative Revelation"**:

| Mode | What We Test | OSP Property? |
|------|--------------|---------------|
| **Direct** | Submit full ranking at once | NO |
| **Iterative** (`da_osp_choice.txt`) | Sequential "pick your favorite" | **NOT TRUE OSP** - doesn't show clinchable set |
| **True OSP** (`da_osp_yesno_guaranteed.txt`) | Yes/No with guaranteed fallback | **YES** - shows what you get NOW vs continue |

**Why the distinction matters**: True OSP per Li (2017) requires showing the agent what they can "clinch" RIGHT NOW. The iterative choice interface helps (it's simpler than submitting a full ranking), but doesn't provide the "worst-case vs best-case at each divergence point" guarantee that defines obviousness.

**For true OSP testing**: Use `da_osp_yesno_guaranteed.txt` which shows:
- What happens if YES: immediate match to candidate
- What happens if NO: continue with fallback set (candidate still available)

See `/docs/OSP_DA_FIX.md` for full specification of true OSP implementation.

---

## Prompt Files

### Direct Revelation (submit full Rank Order List)
- `da_direct_null.txt` - Minimal info baseline
- `da_direct_traditional.txt` - Standard DA mechanics explained
- `da_direct_menu_mechanics.txt` - Menu-DA framing (Yannai's two-step description)
- `da_direct_menu_property.txt` - Menu-SP framing (KEY intervention: "ranking can't change obtainable set")
- `da_direct_textbook_sp.txt` - Textbook strategyproofness statement

### Iterative Interface (sequential local questions)
- `da_osp_choice.txt` - "What is your top choice among remaining?" (iterative, not true OSP)
- `da_osp_yesno.txt` - "Is X your top choice?" (simple yes/no, not true OSP)
- `da_osp_yesno_guaranteed.txt` - **TRUE OSP** with clinchable set and fallback guarantee

### Axis 1: Contingent Reasoning
Interventions that prompt reasoning about what happens given others' actions.
- `axis1_da_enumerate.txt` - Prompt to enumerate others' possible rankings
- `axis1_da_dominated.txt` - Identify dominated rankings
- `axis1_da_worstcase.txt` - Focus on worst-case obtainable set
- `axis1_da_onestep.txt` - Frame as simple one-step decision (mechanism comprehension)
- `axis1_da_tree.txt` - Present DA as decision tree (mechanism comprehension)
- `axis1_da_backward_induct.txt` - Prompt backward induction through DA rounds

### Axis 2: Forward Planning (k-step foresight)
Interventions that vary how many rounds ahead the agent is prompted to plan.
Based on Pycia & Troyan (2023) simplicity standards.

**Approach A: k-step Simulation Scaffolding**
- `axis2_da_0step.txt` - Baseline: just submit ranking, no simulation guidance (k=0)
- `axis2_da_1step.txt` - Think about first rejection (k=1)
- `axis2_da_2step.txt` - Think through first two rejections (k=2)
- `axis2_da_fullsim.txt` - Mentally simulate entire algorithm (k=∞)

**Approach B: Monotonicity/Safety Framing**
- `axis2_da_monotonic_options.txt` - "Your options never shrink"
- `axis2_da_monotonic_safety.txt` - "Rejections only redirect, never eliminate"
- `axis2_da_monotonic_outcome.txt` - "Obtainable set determines outcome"

### Axis 3: Higher-Order Beliefs
- `axis3_da_firstorder.txt` - Ask what others will rank
- `axis3_da_secondorder.txt` - Ask what others think YOU will rank
- `axis3_da_common_knowledge.txt` - Emphasize common knowledge of rationality

### Loss Aversion (Prospect Theory)
Tests whether LLMs exhibit loss aversion (overweighting losses vs gains).
- `loss_aversion_gain_frame.txt` - Frame outcomes as gains from zero
- `loss_aversion_loss_frame.txt` - Frame outcomes as losses from expectation
- `loss_aversion_mixed_frame.txt` - Mixed framing (explicit gains and losses)
- `loss_aversion_endowment.txt` - Given explicit starting endowment
- `loss_aversion_WTA_WTP.txt` - Prompts WTA vs WTP comparison

### Risk Preferences
Tests whether LLMs respond to risk preference framing.
- `intervention_risk_averse.txt` - Risk averse persona
- `intervention_risk_neutral.txt` - Risk neutral persona
- `intervention_risk_seeking.txt` - Risk seeking persona

---

## Template Variables

All prompts use Jinja2-style variables:
- `{{student_id}}` - Student identifier (A, B, C, D)
- `{{vw}}, {{vx}}, {{vy}}, {{vz}}` - Values for schools w, x, y, z
- `{{pw}}, {{px}}, {{py}}, {{pz}}` - Priority ranks at each school (1 = highest)
- `{{available_set}}` - For OSP prompts: currently available schools
- `{{candidate}}` - For OSP yes/no: the school being asked about
- `{{global_ranking}}` - Hint about what other applicants prefer
- `{{max_value}}` - For loss aversion: maximum possible value (used as reference point)

---

## Output Formats

### Non-OSP (direct revelation)
```
Ranking: w > x > y > z
```

### OSP choice
```
Choice: w
```

### OSP yes/no
```
Answer: YES
```
or
```
Answer: NO
```

---

## Priority Generation (Acyclic)

For OSP-implementability, use Ergin-acyclic priorities.
Simple construction: fix top-2 students, bottom-2 students, permute within blocks.

Example (students A,B,C,D; top-2 = {A,B}):
```
w: A > B > C > D
x: B > A > C > D
y: A > B > D > C
z: B > A > D > C
```

---

## Code Requirements for OSP Interface

Your code implements the OSP mechanism state machine:
1. Maintain set of available schools per student
2. Query students one at a time with local questions
3. Update state based on responses
4. Terminate when all matched

The LLM only answers local questions; code handles DA logic.

---

## Changelog

### 2026-02-09: Iterative vs True OSP Clarification

**Rationale**: Based on the plan in "Comprehensive Intervention Analysis", we clarified the distinction between iterative revelation and true OSP:

- **Iterative** (`da_osp_choice.txt`): Sequential "pick your favorite" - simpler than direct, but NOT true OSP
- **True OSP** (`da_osp_yesno_guaranteed.txt`): Shows clinchable set and fallback guarantee per Li (2017)

**Key insight**: True OSP requires showing "School X would accept you RIGHT NOW if you chose it" - the agent must see the worst-case/best-case comparison at each divergence point. Simply asking iterative questions doesn't provide this obviousness guarantee.

**Documentation added**:
- Updated header to distinguish Iterative vs True OSP
- Added reference to `/docs/OSP_DA_FIX.md`
- Created `/docs/INTERVENTION_TAXONOMY.md` for comprehensive taxonomy

---

### 2026-02-04: Axis Reorganization

**Rationale**: Based on Shengwu Li's "Designing Simple Mechanisms" (2024) and Pycia & Troyan's "A Theory of Simplicity" (2023), we reorganized the intervention axes:

- **Axis 1 (Contingent Reasoning)**: Reasoning about what happens given others' actions
- **Axis 2 (Forward Planning)**: Planning across multiple decision points (k-step foresight)
- **Axis 3 (Belief Reasoning)**: Reasoning about others' beliefs

**Key insight**: Forward planning (k-step foresight) only applies to mechanisms where agents make multiple sequential decisions. Direct-revelation DA is a one-shot mechanism, so the old "forward planning" interventions there were actually testing mechanism comprehension/contingent reasoning. The new Axis 2 interventions scaffold thinking about the algorithm's rounds.

**Files renamed**:
| Old Name | New Name | Date |
|----------|----------|------|
| `axis2_da_onestep.txt` | `axis1_da_onestep.txt` | 2026-02-04 |
| `axis2_da_tree.txt` | `axis1_da_tree.txt` | 2026-02-04 |
| `axis2_da_backward_induct.txt` | `axis1_da_backward_induct.txt` | 2026-02-04 |

**New Axis 2 (Forward Planning) interventions**:
These test k-step foresight in the direct-revelation DA mechanism:
- `axis2_da_0step.txt` — baseline (k=0)
- `axis2_da_1step.txt` — one-step lookahead (k=1)
- `axis2_da_2step.txt` — two-step lookahead (k=2)
- `axis2_da_fullsim.txt` — full algorithm simulation (k=∞)
- `axis2_da_monotonic_options.txt` — "options never shrink" framing
- `axis2_da_monotonic_safety.txt` — "rejections only redirect" framing
- `axis2_da_monotonic_outcome.txt` — "obtainable set" framing

**New Loss Aversion and Risk Preference interventions** (added 2026-02-04):
- `loss_aversion_gain_frame.txt`
- `loss_aversion_loss_frame.txt`
- `loss_aversion_mixed_frame.txt`
- `loss_aversion_endowment.txt`
- `loss_aversion_WTA_WTP.txt`
- `intervention_risk_averse.txt`
- `intervention_risk_neutral.txt`
- `intervention_risk_seeking.txt`
