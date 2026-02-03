# DA (Deferred Acceptance) Prompt Templates

This folder contains prompt templates for LLM experiments on Deferred Acceptance matching.

## Theoretical Background

### Key Papers
1. **Li (2017)**: OSP mechanisms - sequential local queries make dominance "obvious"
2. **Ashlagi-Gonczarowski (2018)**: DA is OSP-implementable only under acyclic priorities
3. **Gonczarowski-Heffetz-Thomas (2024)**: Menu framing for DA (descriptions, not OSP implementation)

### The Key Comparison
| Interface | Analogy | OSP? | Expected Truthfulness |
|-----------|---------|------|----------------------|
| Submit full RoL (direct) | Sealed-bid 2P | NO | ~50-60% |
| Sequential local queries | Ascending clock | YES | ~90%+ |

---

## Prompt Files

### Non-OSP Direct Revelation (submit full Rank Order List)
- `da_direct_null.txt` - Minimal info baseline
- `da_direct_traditional.txt` - Standard DA mechanics explained
- `da_direct_menu_mechanics.txt` - Menu-DA framing (Yannai's two-step description)
- `da_direct_menu_property.txt` - Menu-SP framing (KEY intervention: "ranking can't change obtainable set")
- `da_direct_textbook_sp.txt` - Textbook strategyproofness statement

### OSP Sequential Interface (code asks local questions)
- `da_osp_choice.txt` - "What is your top choice among remaining?"
- `da_osp_yesno.txt` - "Is X your top choice among remaining? YES/NO"

### Axis 1: Contingent Reasoning
- `axis1_da_enumerate.txt` - Prompt to enumerate others' possible rankings
- `axis1_da_dominated.txt` - Identify dominated rankings
- `axis1_da_worstcase.txt` - Focus on worst-case obtainable set

### Axis 2: Forward Planning
- `axis2_da_backward_induct.txt` - Prompt backward induction through DA rounds
- `axis2_da_onestep.txt` - Frame as simple one-step decision
- `axis2_da_tree.txt` - Present DA as decision tree

### Axis 3: Higher-Order Beliefs
- `axis3_da_firstorder.txt` - Ask what others will rank
- `axis3_da_secondorder.txt` - Ask what others think YOU will rank
- `axis3_da_common_knowledge.txt` - Emphasize common knowledge of rationality

---

## Template Variables

All prompts use Jinja2-style variables:
- `{{student_id}}` - Student identifier (A, B, C, D)
- `{{vw}}, {{vx}}, {{vy}}, {{vz}}` - Values for schools w, x, y, z
- `{{pw}}, {{px}}, {{py}}, {{pz}}` - Priority ranks at each school (1 = highest)
- `{{available_set}}` - For OSP prompts: currently available schools
- `{{candidate}}` - For OSP yes/no: the school being asked about

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
