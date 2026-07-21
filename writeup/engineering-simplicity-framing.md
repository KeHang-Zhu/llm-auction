# Framing Memo: From Studying Simplicity to Engineering It

## 1. The central framing

这篇论文不应被定义为：

- 一篇研究 LLM 如何在 auction 中出价的论文；
- 一篇比较若干 auction prompts 的论文；
- 或一篇新增若干 simplicity hypotheses 并逐个检验的论文。

更强、也更 generalizable 的定位是：

> **Mechanism design has developed a science of simplicity, but not yet an engineering practice for producing it. This paper develops a theory-guided workflow for engineering behavioral simplicity. Auctions are the testbed in which the workflow is constructed and validated, not the boundary of the contribution.**

核心研究问题可以写成：

> **How can a designer systematically engineer mechanisms that bounded participants can use correctly?**

LLM panel 在这里不是最终研究对象，而是使 engineering workflow 成为可能的 screening instrument：

> **Can theory-guided LLM experimentation search a combinatorial design space, identify robust simplicity-preserving designs, and prioritize the human experiments worth running?**

最重要的一句话是：

> **We turn simplicity from a property to be characterized or tested after the fact into a design objective that can be systematically searched, measured, and improved.**

## 2. Scientific study versus engineering

Engineering 不是 science 的反面。Engineering 使用 scientific knowledge，但它的起点、研究单位和交付物不同。

| | Scientific study of simplicity | Engineering simplicity |
| --- | --- | --- |
| Starting question | Does mechanism or treatment \(X\) affect correct play, and why? | Which feasible configuration best produces correct play under the designer’s constraints? |
| Starting point | A phenomenon or hypothesis | A performance objective and a design problem |
| Unit of analysis | One mechanism comparison or treatment contrast | A structured design space containing multiple components and interactions |
| Typical design | One or several isolated hypotheses | A design grammar and the full set of meaningful combinations |
| Role of theory | Generate and explain hypotheses | Define design dimensions, constraints, predicted interactions, and inadmissible cells |
| Role of experiments | Estimate whether an effect exists | Measure candidate designs, eliminate failures, rank alternatives, and update the map |
| Treatment of nulls and backfires | Evidence for or against a hypothesis | Information about inactive components, constraints, and anti-levers |
| Deliverable | A causal or descriptive fact | A reusable design procedure, performance map, and selected candidate designs |
| Evaluation standard | Identification and external validity | Performance, robustness, cost, constraint preservation, and portability |

Previous work has largely supplied the **science of simplicity**:

- One paper compares a sealed-bid mechanism with an ascending implementation.
- Another tests one description or menu representation.
- Another studies contingent reasoning, forward planning, or beliefs.
- Each produces a valuable local comparative static.

What is missing is the engineering synthesis:

- translate those theories into controllable design dimensions;
- enumerate meaningful combinations;
- test main effects and interactions;
- screen for performance across heterogeneous reasoners;
- select designs subject to implementation cost and institutional constraints;
- convert untested cells into prioritized human experiments.

This distinction should be explicit in the Introduction. Otherwise, a referee can reasonably say that the paper is only a larger collection of scientific treatment tests.

## 3. Why simplicity is engineerable

A property is engineerable when five conditions hold:

1. **A target performance can be defined.**
   - The mechanism specifies the behavior that implements its intended incentive or welfare properties.
   - Behavioral simplicity can therefore be measured by the distance between prescribed and realized play.

2. **The designer controls inputs that can move performance.**
   - The designer can change the implementation, description, timing, information display, and decision support.
   - These choices can change behavior even when the economic outcome rule is held fixed.

3. **Theory supplies a design grammar.**
   - Simplicity theory decomposes cognitive burden into contingent reasoning, forward planning, and belief formation.
   - These constructs determine which levers are meaningful, which combinations should be substitutes or complements, and which cells should be inert or harmful.

4. **Candidate configurations can be measured and compared.**
   - An experimental instrument can estimate which configurations reduce behavioral deviation.
   - LLM panels make it feasible to search a much larger combinatorial space than human experiments alone.

5. **The selected design can be validated and updated.**
   - Existing human results anchor observed cells.
   - LLM-only cells become prospective human predictions.
   - Human evidence updates the design map, creating an iterative design loop.

The logical answer to “Why can simplicity be engineered?” is therefore:

> **Because simplicity is not determined only by the allocation rule. It is an observable performance property of the mechanism-interface-reasoner system, and designers control several components of that system. Once theory organizes those components and experiments measure their interactions, simplicity becomes a design variable.**

## 4. A general engineering problem

The paper can formalize the general object before mentioning auctions.

- Let \(g\) be the social choice or outcome rule the designer wants to preserve.
- Let \(a^*(\theta)\) be the behavior prescribed by the mechanism for participant type \(\theta\).
- Let \(x=(i,d,r)\in\mathcal X\) denote an interface design:
  - \(i\): implementation or extensive form;
  - \(d\): description and information presentation;
  - \(r\): reasoning or decision support.
- Let \(D_P(x)\) be behavioral deviation under participant population \(P\).
- Let \(C(x)\) be the monetary, operational, communication, or latency cost of the design.

The engineering problem is:

\[
x^* \in \arg\min_{x\in\mathcal X}
\left\{D_P(x)+\lambda C(x)\right\}
\quad
\text{subject to preserving }g\text{ and the institution's design constraints.}
\]

A conventional scientific experiment estimates one contrast:

\[
\tau_{x,x'}=D_P(x)-D_P(x').
\]

Engineering requires the collection of these contrasts and interactions to answer a decision:

> Which configuration should the designer deploy?

The LLM panel does not need to estimate human \(D_P(x)\) in levels. Its role is to provide a robust ordinal screen over \(x\), so that scarce human experiments can be allocated to the most promising or theoretically informative cells.

## 5. The general engineering workflow

The paper’s main methodological contribution should be a reusable six-stage workflow:

1. **Specify the institutional objective.**
   - Fix the outcome rule and the prescribed behavior.
   - Define the behavioral error that threatens the mechanism’s objective.

2. **Compile theory into a design grammar.**
   - Identify the cognitive demands created by the mechanism.
   - Translate them into controllable implementation, description, and support levers.

3. **Construct the feasible combinatorial design space.**
   - Enumerate all theoretically meaningful cells.
   - Mark impossible or incoherent combinations as N/A.
   - State predicted main effects and interactions before observing results.

4. **Screen the design space.**
   - Run the cells on a prespecified panel of bounded artificial reasoners.
   - Retain only effects that are robust across model families and equivalent implementations of the lever.

5. **Anchor and select.**
   - Use existing human experiments to validate known cells.
   - Rank candidate designs by expected behavioral improvement, implementation cost, and robustness.

6. **Validate and update.**
   - Convert unobserved cells into falsifiable human predictions.
   - Use new human or field evidence to update the map.

This is the difference between a static “periodic table” and engineering:

- A periodic table organizes known and missing elements.
- An engineering system additionally specifies an objective, constraints, a search rule, a selection criterion, and an update loop.

## 6. The role of auctions

Auctions should be described as a **model system**, **test bench**, or **wind tunnel** for the general method.

They are useful because they provide:

- a sharp normative benchmark;
- an observable behavioral error;
- multiple implementations of closely related economic rules;
- theoretically characterized cognitive burdens;
- rich human experimental evidence for ordinal validation;
- continuous outcomes that make treatment effects easy to compare.

The key positioning sentence should be:

> **We use auctions as a testbed because they combine unusually sharp behavioral benchmarks with unusually rich human evidence. The engineering framework itself is not auction-specific.**

Or, more vividly:

> **The auction is the wind tunnel, not the airplane: it supplies a controlled environment in which to build and validate a general workflow for engineering simplicity.**

The paper should state the conditions under which the workflow travels beyond auctions:

- the institution has a well-defined target behavior or strategy;
- the same objective can be presented through multiple implementations or interfaces;
- deviations from prescribed play are measurable;
- theory provides a decomposition of the relevant cognitive demands;
- at least some human or field evidence is available to anchor the screen.

Candidate domains include:

- school choice and matching;
- public-benefit enrollment;
- tax filing and compliance interfaces;
- voting and collective-choice procedures;
- procurement and allocation platforms;
- consent, privacy, and contract interfaces.

The deferred-acceptance result can remain external robustness rather than part of the auction ranking. Its role is narrower but important:

> It is an existence proof that the same engineering dimension—exposing a safety invariant rather than merely restating mechanics—can be instantiated outside auctions.

## 7. Recommended paper architecture

### 1. Introduction: From the Science of Simplicity to Its Engineering

- Begin with the general implementation problem: formally desirable mechanisms fail when participants cannot recognize how to use them.
- Explain what existing science has established.
- Identify the missing engineering capability.
- Define engineering as systematic design under an objective and constraints.
- Introduce the theory-to-design-to-screening workflow.
- Only then introduce auctions as the testbed.

### 2. A General Framework for Engineering Simplicity

- Define the mechanism, target behavior, deviation, interface design, and cost.
- Present the three-part design grammar:
  - implementation;
  - description;
  - reasoning support.
- Define the engineering objective.
- Present the six-stage screening and validation workflow.

### 3. The Auction Testbed and Instrument Validation

- Explain why auctions provide a useful test bench.
- Introduce SPSB, ascending clocks, human benchmarks, and the LLM panel.
- Validate only the ordinal signal needed by the engineering workflow.

### 4. Engineering the Auction Interface

- Instantiate the general design grammar in auctions.
- Populate the full meaningful combinatorial map.
- Report main effects and interactions.
- Rank candidate configurations using performance, robustness, and cost.

### 5. Diagnosing the Design Space

- Use traces to describe which stated strategies accompany different mechanisms and levers.
- Treat realized behavior as the performance metric.
- Identify inactive components and anti-levers.

### 6. Portability, Human Predictions, and Design Implications

- Use deferred acceptance as an external-domain portability check.
- State the conditions under which the method generalizes.
- List prospective human experiments generated by the map.
- Explain how future evidence updates the engineering workflow.

## 8. What should change in the current v3

The current draft already contains most of the raw material, but the hierarchy should change.

### Abstract

- Do not begin with the second-price auction.
- Begin with the absence of an engineering method for behavioral simplicity.
- Define the workflow before introducing the testbed.
- Present auction findings as validation and demonstration of the method.
- End with a general claim about designing participant-facing mechanisms.

### Introduction

- Keep the first two current paragraphs, but sharpen the science-versus-engineering distinction.
- Move the paragraph about LLMs becoming real bidders to the Discussion.
  - In its current position, it makes the paper sound like a paper about markets for LLM agents.
- Move “This paper needs one such mechanism…” later.
- Introduce the general engineering workflow before the SPSB example.
- Reframe the contribution from “a validated auction-screening instrument” to “a general theory-guided simplicity-engineering workflow, validated in auctions.”

### Theory section

- Expand the current general Section 2.1 into a genuine engineering framework.
- Define the objective \(D_P(x)+\lambda C(x)\).
- Distinguish:
  - a theoretical design grammar;
  - an experimental screen;
  - a deployment or human-validation decision.
- Move “The Auction Scenario” into the testbed section.

### Design map

- Keep the auction map, but make it the **instantiation** of a general map.
- Add an earlier figure showing the general engineering cycle.
- The current auction map should no longer be Figure 1.

### Results

- Organize results as outputs of the engineering workflow:
  - validation of the screen;
  - search over candidate designs;
  - robust selection;
  - anti-levers and failed configurations;
  - predictions selected for human testing.
- Report cost because engineering is constraint-aware, but do not define engineering merely as cheaper experimentation.

### Discussion

- Replace “guidance for fielding strategy-proof mechanisms to LLM participants” with broader guidance for participant-facing mechanism design.
- Present design for LLM participants as one application, not the paper’s identity.
- Use deferred acceptance to demonstrate portability without mixing it into the auction ranking.

## 9. Recommended new Figure 1

The first figure should communicate the general contribution before any auction appears:

    Institutional objective and prescribed behavior
                           ↓
    Theory decomposes cognitive burden
                           ↓
    Design grammar
    (implementation × description × reasoning support)
                           ↓
    Full feasible combinatorial design space
                           ↓
    LLM-panel screening + cross-family robustness filter
                           ↓
    Human anchors ──► robust candidate designs
                           ↓
    Prioritized human/field experiments
                           ↓
    Evidence updates the design map

The existing auction design map then becomes the testbed-specific Figure 2.

## 10. Possible titles

- **Engineering Simplicity: A Theory-Guided Method for Behavioral Mechanism Design**
- **From Studying Simplicity to Engineering It**
- **Engineering Behavioral Simplicity in Mechanisms**
- **Engineering Simplicity: Theory-Guided Design Screening with LLM Agents**

The current title, **Engineering Simplicity**, is strong. A subtitle should clarify that the contribution is a general design method rather than an auction application.

## 11. Proposed abstract

> Mechanism design has developed a science of simplicity: theory characterizes when optimal behavior should be easy to recognize, and experiments test particular mechanisms or explanations one at a time. What is missing is an engineering practice—a systematic way to translate theory into controllable design dimensions, search their meaningful combinations, and select robust implementations under cost and institutional constraints. We develop such a workflow. The method fixes the mechanism’s economic objective, organizes designer choices along implementation, description, and reasoning-support dimensions, uses a panel of large language model agents to screen the resulting design space, and reserves human experiments for validation and for the most informative untested cells. We build and validate the workflow in auctions, a testbed with sharp strategy benchmarks, multiple implementations of the same economic rule, and a rich human experimental record. The LLM panel recovers human cross-mechanism rankings and treatment directions across model families even though it does not reproduce human bids in levels. The resulting design map identifies robust substitutes, complements, and anti-levers: an ascending implementation performs best; exposing the invariant that makes truthful play safe recovers much of that benefit; scaffolding relevant payoff contingencies helps; and prompting unnecessary beliefs backfires. Existing human results anchor observed cells, while unobserved cells become falsifiable predictions. An external matching application illustrates how the same design dimension travels beyond auctions. The contribution is not an auction model of LLM behavior, but a general method for turning behavioral simplicity into a measurable and engineerable design objective.

## 12. The contribution in three sentences

> Existing research studies simplicity locally, one mechanism or intervention at a time. We develop an engineering workflow that translates simplicity theory into a combinatorial design space, screens that space with a robust LLM panel, and uses human evidence to validate and update the resulting map. Auctions provide the test bench; the contribution is a reusable method for engineering behavioral simplicity in participant-facing mechanisms.
