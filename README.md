# llm-auction

## Getting started

### How to install:
Our package is compatible with Python 3.9 - 3.11.

- Start with creating a virtual environment and install the required packages
```
python -m venv myvenv
source myvenv/bin/activate
pip install -r requirements.txt
```
- You need to have a .env file that contains your openai API key
```
touch .env
nano .env
```
In the text editor，replace the  ... with your actual OpenAI API key：
```
OPENAI_API_KEY = ...
```

## Coding design EDSL
We will use John’s fantastic repo of EDSL to implement the LLM experiments. 

### Basic design: 
Rule option
- Rule module: generate prompts for the bidders
- Order module: deciding the bidding order depending on the rule
- Stop module: deciding the ending condition

Sealed v.s. Open
- Information sharing module
Ascending v.s. Descending
- Auctioneer’s module: with a fixed raise amount
1st price v.s. 2nd price v.s. 3rd price
- Winning decision module: declare winner and clearing price
Common value/ private value
- Value determination module: determine the value distribution

Advanced setting:
- If we want to design new auctions, for example, a dynamical game. In the first round, the players play SP. Then in the next round, play FP….
Fuse Rule module and Order module.
