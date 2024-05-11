# llm-auction

## Getting started

### How to install:
Our package is compatible with Python 3.9 - 3.11.

- Start with creating a virtual environment and install the required packages
```
python -m venv myvenv
source myvenv/bin/activate
pip install edsl
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

### Rule option menu: 
    - seal_clock= 'seal' or 'clock' 
    - ascend_descend='ascend' or 'descend' if seal_clock= 'clock' 
    - price_order='first' or 'second' or 'third' if seal_clock= 'seal'
    - private_value='private' or 'common'
    - open_blind='open' or 'blind' if seal_clock= 'clock' 
        - i.e. bidder don't see the drop out in the clock

### TODO:
Advanced setting:
- If we want to design new auctions, for example, a dynamical game. In the first round, the players play SP. Then in the next round, play FP….
Fuse Rule module and Order module.
