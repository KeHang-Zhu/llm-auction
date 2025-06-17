# Learning from Synthetic Laboratory: Language Models as Auction Participants

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Auction Parameters](#auction-parameters)
4. [Reproducing Our Results](#reproducing-our-results)

---

## Overview

This repository accompanies our paper → [https://openreview.net/forum?id=XZ71GHf8aB](https://openreview.net/forum?id=XZ71GHf8aB).

<p align="center">
  <img src="overview.png" alt="Project overview diagram" width="650">
</p>

If you build on this work, please cite us:

```bibtex
@article{zhuevidence,
  title  = {Evidence from the Synthetic Laboratory: Language Models as Auction Participants},
  author = {Zhu, Kehang and Shah, Anand V and Jiang, Yanchen and Horton, John Joseph and Parkes, David C}
}
```

---

## Getting Started

Our code supports **Python 3.9 – 3.11**.

```bash
# 1  Create and activate a virtual‑env
python -m venv venv
source venv/bin/activate

# 2  Install dependencies
pip install edsl

# 3  Configure your OpenAI key
cat > .env <<'EOF'
OPENAI_API_KEY=YOUR_KEY_HERE
EOF
```

---

## Auction Parameters

All experiments are launched via one of the three driver scripts below. Use the flags shown to configure auction mechanics.

| Auction type           | Driver script          | Required flags                                                                                           | Optional flags                                                                               |
| ---------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Sealed‑bid**         | `main.py`              | `--seal_clock seal`                                                                                      | `--price_order {first,second,third,allpay}`<br>`--private_value {private,affiliated,common}` |
| **Clock**              | `main.py`              | `--seal_clock clock`<br>`--ascend_descend descend`                                                       | `--open_blind {open,blind}`<br>`--private_value {private,affiliated,common}`                 |
| **Ebay proxy**         | `main_ebay.py`         | `--seal_clock ebay` *(fixed)*<br>`--price_order second` *(fixed)*<br>`--private_value private` *(fixed)* | `--turns 10`<br>`--closing {true,false}`<br>`--reserve_price 60`                             |
| **Intervention study** | `main_intervention.py` | *(inherits flags from sealed‑bid)*                                                                       |                                                                                              |

### Quick examples

Run a second‑price sealed‑bid auction:

```bash
python main.py 
```

Run a second‑price sealed‑bid auction with intervention:

```bash
python main_intervention.py 
```

Run the Ebay‑style proxy auction:

```bash
python main_ebay.py
```
You can vary all the hyperparameters in these main functions.
---

## Reproducing Our Results

We use **[EDSL](https://docs.expectedparrot.com/en/latest/)**, whose universal remote cache stores every completed LLM call. Re‑running our code with the *same prompt* and *same random seed* therefore incurs **no additional API cost**—results are retrieved automatically.

### 1  Seeds and model settings

| Value regime        | Seeds used      |
| ------------------- | --------------- |
| Private             | **1299 – 1309** |
| Affiliated & Common | **1399 – 1409** |

All experiments use **GPT‑4**, `temperature = 0.5`.

### 2  Cached runs (default)

```python
results = survey.by(model).run(
    remote_inference_description="cache reuse", 
    remote_inference_visibility="public"         
)
```

The snippet above will *first look in the cache*; if a match is found, the result is loaded instantly.

### 3  Forcing a fresh run (optional)

To ignore the cache—for instance, when testing a new prompt—add `fresh=True`:

```python
results = survey.by(model).run(
    remote_inference_description="fresh run",
    remote_inference_visibility="public",
    fresh=True
)
```

### 4  Verifying cache hits

EDSL prints the **Job UUID** and whether it was served from cache. You can also inspect the universal cache via the web UI linked in the EDSL docs.

---

Happy experimenting! If anything is unclear, please open an issue 🙌



## 🔧 Dependencies
The main third-party package requirement are `openai` and `edsl`.

## 💡 Contributing, Feature Asks, and Bugs
Interested collaborating in LLM as auction participants? Found a nasty bug that you would like us to squash? Please send us an email at kehangzhu@gmail.com.
