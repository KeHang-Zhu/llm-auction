# llm-auction

## Coding design EDSL
We will use John’s fantastic repo of EDSL to implement the LLM experiments. 

### Basic design: 
Rule option
- Rule module: generate prompts for the bidders/ Auctioneer (If exist)
- Order module: deciding the bidding order depending on the rule
- Stop module: deciding the ending condition

Sealed v.s. Open
- Information sharing module
Ascending v.s. Descending
- Auctioneer’s module: with a fixed raise amount
1st price v.s. 2nd price v.s. 3rd price
- Winning decision module: declare winner and clearing price
Common value/ private value/ Independent value
- Value determination module: determine the value distribution

Advanced setting:
- If we want to design new auctions, for example, a dynamical game. In the first round, the players play SP. Then in the next round, play FP….
Fuse Rule module and Order module.

Example code snippet:
```
Agent = agent(...)
A = Auction(agent_list, model_list, rule, … )
A.run(n=100, Temp =0.4)
```
