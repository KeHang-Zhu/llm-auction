# V12 Intervention Experiments

This folder contains YAML configuration files for V12 behavioral intervention experiments, based on Shengwu Li's mechanism complexity theory and prospect theory.

## Experiment Structure

All 18 intervention experiments are organized into 4 categories:

### Axis 1: Contingent Reasoning (4 experiments)
Tests whether LLMs understand dominant strategies in SPSB.

- `axis1_contingent_baseline.yaml` - Baseline with no guidance
- `axis1_contingent_enumerate.yaml` - Prompt to enumerate others' possible bids
- `axis1_contingent_dominated.yaml` - Prompt to identify dominated strategies
- `axis1_contingent_worstcase.yaml` - Focus on worst-case analysis

**Prediction**: LLMs should bid = value regardless. If enumeration prompts cause bid-shading, it reveals confusion about dominance.

### Axis 2: Forward Planning (4 experiments)
Tests backward induction through sequential decision problems.

- `axis2_forward_baseline.yaml` - Two-stage auction (sealed → clock)
- `axis2_forward_backward_induct.yaml` - Explicit backward induction prompt
- `axis2_forward_onestep.yaml` - Frame as one-step decision
- `axis2_forward_tree.yaml` - Present explicit decision tree

**Prediction**: Simplified framings (onestep, tree) should improve bidding by reducing forward planning requirements.

### Axis 3: Higher-Order Beliefs (4 experiments)
Tests whether LLMs are swayed by belief prompts (they shouldn't be in SPSB).

- `axis3_beliefs_baseline.yaml` - Standard SPSB with rational opponents
- `axis3_beliefs_firstorder.yaml` - "What will others bid?"
- `axis3_beliefs_secondorder.yaml` - "What do others think YOU will bid?"
- `axis3_beliefs_common_knowledge.yaml` - Common knowledge of rationality

**Prediction**: Belief prompts should NOT affect bidding. Any effect reveals confusion about dominant strategies.

### Loss Aversion (6 experiments)
Tests for prospect theory effects (losses weighted ~2.25x gains).

- `loss_aversion_baseline.yaml` - Neutral framing
- `loss_aversion_gain_frame.yaml` - All outcomes as gains
- `loss_aversion_loss_frame.yaml` - Outcomes as losses from endowment
- `loss_aversion_mixed_frame.yaml` - Mixed gains and losses
- `loss_aversion_endowment.yaml` - Explicit starting endowment
- `loss_aversion_WTA_WTP.yaml` - WTA vs WTP comparison

**Prediction**: Bid should be frame-invariant. Human-like bias would show higher bids in loss frame.

## Running Experiments

### Single Experiment
```bash
python new/main.py --config configs/interventions/axis1_contingent_baseline.yaml
```

### All experiments in one axis
```bash
# Run all Axis 1 experiments
for config in configs/interventions/axis1_*.yaml; do
    python new/main.py --config "$config"
done

# Run all Axis 2 experiments
for config in configs/interventions/axis2_*.yaml; do
    python new/main.py --config "$config"
done

# Run all Axis 3 experiments
for config in configs/interventions/axis3_*.yaml; do
    python new/main.py --config "$config"
done

# Run all Loss Aversion experiments
for config in configs/interventions/loss_aversion_*.yaml; do
    python new/main.py --config "$config"
done
```

### All V12 experiments
```bash
for config in configs/interventions/*.yaml; do
    python new/main.py --config "$config"
done
```

### Parallel execution (if supported)
```bash
python new/main.py --config configs/interventions/axis1_contingent_baseline.yaml --parallel
```

## Configuration Parameters

All experiments share these parameters (matching V10 intervention experiments):

- **Experiment**: Version V12, experiment-specific name and description
- **Auction**: 3 agents, 1 round
- **Rule**: Sealed-bid, second-price, private values, open results
- **Value**: common_range [20, 49], private_range 49, increment 0.1, seed_base 1299
- **LLM**: gpt-4o, temperature 0.5
- **Prompt**: plan_reflection strategy, rule_template/V12/
- **Execution**: 100 repetitions, output to experiment_logs/V12/[experiment_name]

## Output Structure

Results are saved to:
```
experiment_logs/V12/
├── axis1_contingent_baseline/
├── axis1_contingent_enumerate/
├── axis1_contingent_dominated/
├── axis1_contingent_worstcase/
├── axis2_forward_baseline/
├── axis2_forward_backward_induct/
├── axis2_forward_onestep/
├── axis2_forward_tree/
├── axis3_beliefs_baseline/
├── axis3_beliefs_firstorder/
├── axis3_beliefs_secondorder/
├── axis3_beliefs_common_knowledge/
├── loss_aversion_baseline/
├── loss_aversion_gain_frame/
├── loss_aversion_loss_frame/
├── loss_aversion_mixed_frame/
├── loss_aversion_endowment/
└── loss_aversion_WTA_WTP/
```

Each experiment directory contains:
- Raw output JSONL files
- Experiment metadata
- Configuration snapshot
- Prompt file copies

## Analysis Metrics

Key metrics for analysis:

1. **Bid Shading**: (Value - Bid) / Value
2. **Rationality**: |Bid - Value| < threshold (e.g., 0.05)
3. **Treatment Effects**: Compare baseline to treatments within each axis
4. **Cross-axis Comparison**: Which axis has the largest effect?

## References

- Li, S. (2024). "Designing Simple Mechanisms." JEP 38(4): 175-192.
- Li, S. (2017). "Obviously Strategy-Proof Mechanisms." AER 107(11): 3257-87.
- Kahneman, D. & Tversky, A. (1979). "Prospect Theory." Econometrica 47(1): 263-91.
- Bini et al. (2024). "Behavioral Economics of AI: LLM Biases and Corrections."

## See Also

- [rule_template/V12/0_readme.txt](../../rule_template/V12/0_readme.txt) - Detailed intervention design
- [rule_template/V12/DESIGN_DOCUMENT.md](../../rule_template/V12/DESIGN_DOCUMENT.md) - Theoretical framework
