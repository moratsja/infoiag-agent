# infoiag-agent

Summarise DivSumm tweets and check the claims against the ontology.

## Setup

```bash
cd infoiag-agent
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install .
```

Put `OPENAI_API_KEY` in `.env`.

The reasoner needs Java. If `java` is not on PATH, the code looks for `java.exe` under `C:\Program Files\Eclipse Adoptium`.

## Run

```bash
python main.py --data data/raw/divsumm/input_docs/Christmas.txt --prompt prompt_christmas
python main.py --data data/raw/divsumm/input_docs/Christmas.txt --prompt prompt_christmas --baseline
python main.py --data data/raw/divsumm/input_docs/Netflix.txt --prompt prompt_netflix
```

`--save` writes the run to `data/processed/`.
