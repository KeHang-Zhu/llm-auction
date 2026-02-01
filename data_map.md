# Data Map for LLM Auction Experiments

Last updated: 2026-01-31

## Directory Structure Overview

### 1. `robustness_logs/V10/` - Multi-model baseline auctions (NO rule explanation)
Models: GPT-5-mini, Gemini, Claude Sonnet, Llama

| Auction Type | GPT-5-mini | Gemini | Claude Sonnet | Llama |
|--------------|------------|--------|---------------|-------|
| FPSB IPV | ✓ | ✓ | ✓ | ✓ |
| SPSB IPV | ✓ | ✓ | ✓ | ✓ |
| Third-Price IPV | ✓ | ✓ | ✓ | ✓ |
| SPSB APV | ✓ | ✓ | ✓ | ✓ |
| Common Value First | ✓ | ✓ | ✓ | ✓ |
| Common Value Second | ✓ | ✓ | ✓ | ✓ |

### 2. `robustness_logs_with_explanation/V10/` - Multi-model baseline (WITH rule explanation)
Models: GPT-5-mini, Gemini, Claude Sonnet, Llama

| Auction Type | GPT-5-mini | Gemini | Claude Sonnet | Llama |
|--------------|------------|--------|---------------|-------|
| FPSB IPV | ✓ | ✓ | ✓ | ✓ |
| SPSB IPV | ✓ | ✓ | ✓ | ✓ |
| Third-Price IPV | ✓ | ✓ | ✓ | ✓ |
| SPSB APV | ✓ | ✓ | ✓ | ✓ |
| All-Pay IPV | ✓ | ✓ | ✓ | ✓ |
| Common Value First | ✓ | ✓ | ✓ | ✓ |
| Common Value Second | ✓ | ✓ | ✓ | ✓ |

### 3. `experiment_logs_with_explanation/V10/` - GPT-5-mini interventions + baselines
Model: GPT-5-mini (default)

**Baseline Auctions:**
- fpsb_ipv, spsb_ipv, third_price_ipv
- spsb_apv, ascending_clock_apv, ascending_clock_apv_closed
- common_value_first, common_value_second
- all_pay_ipv

**Interventions (SPSB only):**
- intervention_dominant_strategy
- intervention_menu
- intervention_nash_deviation
- intervention_proxy_breitmoser
- intervention_risk_averse
- intervention_risk_neutrality
- intervention_risk_seeking
- intervention_wrong_strategy

### 4. `experiment_logs_gpt_4o/V10/` - GPT-4o interventions
Model: GPT-4o

**Interventions (SPSB only):**
- intervention_dominant_strategy
- intervention_menu
- intervention_nash_deviation
- intervention_proxy_breitmoser
- intervention_risk_averse
- intervention_risk_neutrality
- intervention_risk_seeking
- intervention_wrong_strategy

### 5. `experiment_logs_gpt_4o/V12/` - GPT-4o FULL intervention axes (MAIN DATA)
Model: GPT-4o

**Axis 1: Contingent Thinking** (FPSB, SPSB, TPSB)
- axis1_contingent_baseline[_first/_third]
- axis1_contingent_dominated[_first/_third]
- axis1_contingent_enumerate[_first/_third]
- axis1_contingent_worstcase[_first/_third]

**Axis 2: Forward Reasoning** (FPSB, SPSB, TPSB)
- axis2_forward_baseline[_first/_third]
- axis2_forward_backward_induct[_first/_third]
- axis2_forward_onestep[_first/_third]
- axis2_forward_tree[_first/_third]

**Axis 3: Higher-Order Beliefs** (FPSB, SPSB, TPSB)
- axis3_beliefs_baseline[_first/_third]
- axis3_beliefs_common_knowledge[_first/_third]
- axis3_beliefs_firstorder[_first/_third]
- axis3_beliefs_secondorder[_first/_third]

**Prospect Theory / Loss Aversion** (FPSB, SPSB, TPSB)
- loss_aversion_baseline[_first/_third]
- loss_aversion_endowment[_first/_third]
- loss_aversion_gain_frame[_first/_third]
- loss_aversion_loss_frame[_first/_third]
- loss_aversion_mixed_frame[_first/_third]
- loss_aversion_WTA_WTP[_first/_third]

**Other Interventions** (FPSB, SPSB, TPSB)
- intervention_menu[_first/_third]
- intervention_nash_deviation[_first/_third]
- intervention_proxy_breitmoser[_first/_third]
- intervention_risk_averse[_first/_third]
- intervention_risk_neutral[_first/_third]
- intervention_risk_seeking[_first/_third]
- intervention_NE_strat_reveal[_first/_third]
- intervention_wrong_strat_reveal[_first/_third]

### 6. `experiment_logs_claude/V10/` - Claude interventions (LIMITED)
Model: Claude Sonnet

- intervention_claude
- intervention_dominant_strategy
- intervention_proxy_breitmoser
- intervention_risk_seeking

---

## Data Availability Summary for Engineering Simplicity Paper

### HAVE:

**1) Many models playing SPSB (baseline failure)**
- ✓ GPT-5-mini, Gemini, Claude Sonnet, Llama: `robustness_logs/V10/spsb_ipv_*`
- ✓ GPT-4o: `experiment_logs_gpt_4o/V12/axis1_contingent_baseline` (SPSB)
- **STATUS: COMPLETE** (5 models)

**2) Many models playing Ascending Clock**
- ✓ GPT-5-mini: `experiment_logs_with_explanation/V10/ascending_clock_apv`
- ✗ Gemini, Claude, Llama, GPT-4o: NO ASCENDING CLOCK DATA
- **STATUS: INCOMPLETE** (only 1 model)

**3) Interventions across axes**
- ✓ GPT-4o: Full axis1, axis2, axis3, loss_aversion in V12
- ✗ Other models: NO intervention axis data
- **STATUS: INCOMPLETE** (only GPT-4o has full intervention data)

**4) Mixtures / steering vectors**
- ✗ No data yet
- **STATUS: NOT STARTED**

### NEED TO GENERATE:

1. **Ascending Clock for Gemini, Claude, Llama, GPT-4o**
   - Critical for OSP replication across models

2. **Intervention axes for other models** (optional but strengthens paper)
   - At minimum: Claude Sonnet or GPT-5-mini running axis1/axis2/axis3

3. **Mixtures / steering vector experiments**
   - Design needed

---

## File Naming Conventions

- `*_first` = First-Price auction variant
- `*_third` = Third-Price auction variant
- No suffix = Second-Price (SPSB)
- `_gpt5mini`, `_gemini`, `_claude_sonnet`, `_llama` = model suffixes in robustness logs
