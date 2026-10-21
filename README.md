# INFOIAG agent

Ontology-guided summarization agent for the INFOIAG 2026 project. It summarises DivSumm tweets, maps claims onto `ontology/ontologyStefan.rdf`, and checks two kinds of claim with HermiT.

The checked summary is rewritten at most `MAX_REVISIONS` times (default 1). Each rewrite is extracted, mapped, and checked again.

## Pipeline

`summarize` writes the summary from the tweets and the user prompt. The model does not see the group labels (`White`, `Hisp`, `AA`). Those labels stay on the tweet for a later fairness check.

`extract_claims` turns the summary into claims. If there are none, the run stops. That is not a verified summary.

`ontology_mapping` asks the model to attach each claim to classes, object properties, and individuals from the vocabulary. Unknown names are dropped. A mapping is kept only when it is exactly one of these shapes:

- class membership: an individual and a class, such as `christmas` type `Event`
- object property: two individuals and a property, such as `america recognizesPublicHoliday christmas`

A subject or object may be a class or a general group. If the mapping is not one of those shapes, the claim is not verifiable. The model does not invent ontology terms and does not write SPARQL.

`select_query` runs HermiT on a temporary copy of the ontology, once per claim. The original RDF file is not modified.

`evaluate` stores one status per claim. A rewrite issue is created only for `CONTRADICTED`.

`rewrite` fixes those contradicted claims, keeps supported claims, and leaves not-verifiable claims unless the posts themselves do not support them. Then the check runs again.

## Claim statuses

HermiT is an OWL reasoner. SPARQL only reads stored triples. An empty SPARQL result is not proof that a claim is false. The query `q1` uses `FILTER NOT EXISTS`, which is closed-world database semantics, and that query is not used as an OWL negation.

The checker uses the open-world assumption. Missing knowledge is unknown, not false.

- `SUPPORTED`: the ontology entails the claim. For a class, this is tested by adding the negation and seeing that HermiT reports an inconsistency. `christmas` is asserted as a `PublicHolidayEvent`. `PublicHolidayEvent` is a subclass of `Event`, so `christmas` type `Event` is supported even though `Event` is not the direct asserted type.
- `CONTRADICTED`: the ontology was consistent, and adding the claim makes it inconsistent.
- `NOT_VERIFIABLE`: neither the claim nor its negation follows. “Americans love Christmas” stays here. The file says America recognizes Christmas as a public holiday. That is not a feeling.

`passed` is true only when every claim is `SUPPORTED`. A summary of only not-verifiable claims does not pass, and it is not rewritten. If a contradiction is still present after the rewrite limit, `passed` stays false.

`PublicHolidayEvent` and `SportingCompetitionEvent` are not disjoint in the RDF file. The only `owl:disjointWith` there is `LeagueCompetition` / `TournamentCompetition`. The checker adds a disjointness axiom for those two event classes on the temporary copy only. That is a proof-of-concept modelling assumption. With it, “Christmas is a sporting competition” is `CONTRADICTED`. Without it, that claim is `NOT_VERIFIABLE`. A different class, such as `Country`, is not treated as a contradiction just because Christmas has another type.

## What this does not do

The intermediate report says the model selects a description-logic query, and that HermiT checks queries such as “a person who is an American citizen and does not take part in Christmas”. This code does not do that. It checks class membership and object-property assertions only. It does not decide arbitrary natural-language entailment.

Equal Coverage, ROUGE, DeepEval, and token cost are not implemented. Group labels are stored for that later check.

## Setup

HermiT needs Java. This project was run with Eclipse Temurin 17. `java` should be on `PATH`. On Windows, if it is not, the checker also looks under `C:\Program Files\Eclipse Adoptium`.

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

The ontology tests call the real file and the real reasoner. The rewrite-loop test mocks the LLM, so it does not need an API key.

On this Windows machine, application control blocks the `xxhash` DLL that LangGraph imports. A plain `pytest` then fails while collecting the graph tests. The HermiT tests in `tests/test_reasoner.py` do not import LangGraph and can still run. Allowing that DLL, or running where it is not blocked, is required for the graph tests.

[DivSumm](https://github.com/PortNLP/DivSumm) is in `data/raw/divsumm/`. Cite Olabisi, Hudson, Jetter, and Agrawal, COLING 2022, if you use the data.
