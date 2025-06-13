# Learning from Synthetic Laboratory: Language Models as Auction Participants
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## Table of Contents
1. [Overview](#overview)
2. [How to use](#getting-started)


## Overview
This is the code for: https://openreview.net/forum?id=XZ71GHf8aB.
<p align="center">
  <img src="overview.png" alt="Your Image" width="650" >
</p>

If you make use of this code in any formal way, we would appreciate a citation:

```
@article{zhuevidence,
  title={Evidence from the Synthetic Laboratory: Language Models as Auction Participants},
  author={Zhu, Kehang and Shah, Anand V and Jiang, Yanchen and Horton, John Joseph and Parkes, David C}
}
```


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
We will use EDSL to implement the LLM experiments. 

### Rule option menu: 
    - seal_clock= 'seal' or 'clock' 
    - ascend_descend='ascend' or 'descend' if seal_clock= 'clock' 
    - price_order='first' or 'second' or 'third' if seal_clock= 'seal'
    - private_value='private' or 'common'
    - open_blind='open' or 'blind' if seal_clock= 'clock' 
        - i.e. bidder don't see the drop out in the clock

## 🔧 Dependencies
The main third-party package requirement are `openai` and `edsl`.

## 💡 Contributing, Feature Asks, and Bugs
Interested collaborating in LLM as auction participants? Found a nasty bug that you would like us to squash? Please send us an email at kehangzhu@gmail.com.
