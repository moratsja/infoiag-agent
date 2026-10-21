# INFOIAG agent

Ontology-guided summarization agent for the INFOIAG 2026 project. It summarises DivSumm tweets, maps claims onto `ontology/ontologyStefan.rdf`, and checks two kinds of claim with Owlready2's reasoner.

The checked summary is rewritten at most `MAX_REVISIONS` times (default 1). Each rewrite is extracted, mapped, and checked again.

## Pipeline

`summarize` writes the summary from the tweets and the user prompt. The model does not see the group labels (`White`, `Hisp`, `AA`). Those labels stay on the tweet. They are not used by the agent.

`extract_claims` turns the summary into claims. If there are none, the run stops. That is not a verified summary.

`ontology_mapping` asks the model to attach each claim to classes, object properties, and individuals from the vocabulary. Unknown names are dropped. A mapping is kept only when it is exactly one of these shapes:

- class membership: an individual and a class, such as `christmas` type `Event`
- object property: two individuals and a property, such as `america recognizesPublicHoliday christmas`

A subject or object may be a class or a general group. If the mapping is not one of those shapes, the claim is not verifiable. The model does not invent ontology terms and does not write SPARQL.

`select_query` calls Owlready2 `sync_reasoner()` on a temporary copy of the ontology, once per claim. The original RDF file is not modified.

`evaluate` stores one status per claim. A rewrite issue is created only for `CONTRADICTED`.

`rewrite` fixes contradicted claims. Not-verifiable claims stay unless the posts themselves do not support them. The check then runs again.

## Claim statuses

`sync_reasoner()` is Owlready2's HermiT reasoner. SPARQL only reads stored triples. An empty SPARQL result is not proof that a claim is false. The query `q1` uses `FILTER NOT EXISTS`, which is closed-world, and that query is not used as the claim verdict.

Missing knowledge is unknown, not false.

- `SUPPORTED`: the reasoner entails the claim. For a class, the negation is added and HermiT reports an inconsistency. `christmas` is a `PublicHolidayEvent`, and that class is a subclass of `Event`, so `christmas` type `Event` is supported.
- `CONTRADICTED`: the ontology was consistent, and adding the claim makes it inconsistent.
- `NOT_VERIFIABLE`: neither the claim nor its negation follows. “Americans love Christmas” stays here. The file says America recognizes Christmas as a public holiday. That is not a feeling.

`passed` is true only when every claim is `SUPPORTED`. A summary of only not-verifiable claims does not pass, and a not-verifiable claim does not by itself start a rewrite. A contradicted claim can start one rewrite. If a contradiction is still there after the rewrite limit, `passed` stays false.

The same two checks apply to any topic whose names are in the vocabulary. `christmas` type `Event` is supported because `PublicHolidayEvent` is a subclass of `Event`. `evaPerson` type `Person` is supported because `evaPerson` is an `AdultPerson`. “Christmas is a sporting competition” is `NOT_VERIFIABLE`: `PublicHolidayEvent` and `SportingCompetitionEvent` are not disjoint. The file does say `LeagueCompetition` is disjoint with `TournamentCompetition`, but neither class has an individual, so that axiom cannot contradict a current claim. The checker does not add an axiom or an individual to force one.

## What this does not do

The intermediate report says the model selects a description-logic query, and that HermiT checks queries such as “a person who is an American citizen and does not take part in Christmas”. This code does not do that. It checks class membership and object properties with Owlready2's reasoner. It does not decide arbitrary natural-language entailment.

Equal Coverage, ROUGE, DeepEval, and token cost are not implemented. Group labels are stored and not scored.

Intermediate Report 2 still says the model selects a description-logic query and that HermiT checks that query. The report should say instead: Owlready2's reasoner checks class membership and object properties. The two event classes are not disjoint. Evaluation metrics from that report are not part of this run.

## Setup

Owlready2 runs HermiT with the `java` command. If `java` is not on `PATH`, the checker uses `java.exe` under `C:\Program Files\Eclipse Adoptium` when that folder exists.

```bash
cd infoiag-agent
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install .
```

`.env` holds only `OPENAI_API_KEY`.

```bash
python main.py --data data/raw/divsumm/input_docs/Christmas.txt --prompt prompt_christmas
python main.py --data data/raw/divsumm/input_docs/Christmas.txt --prompt prompt_christmas --baseline
pytest
```

The ontology tests call the real file. The rewrite-loop test mocks the LLM, so it does not need an API key.

On this Windows machine, application control blocks the `xxhash` DLL that LangGraph imports. A plain `pytest` then fails while collecting the graph tests. The ontology tests in `tests/test_reasoner.py` do not import LangGraph and can still run. Allowing that DLL, or running where it is not blocked, is required for the graph tests.

[DivSumm](https://github.com/PortNLP/DivSumm) is in `data/raw/divsumm/`. Cite Olabisi, Hudson, Jetter, and Agrawal, COLING 2022, if you use the data.
