import json

from src.nodes.ontology_mapping import ontology_mapping
from src.nodes.select_query import select_query

test_claim = {
    "subject": "America",
    "predicate": "recognizes",
    "object": "Christmas as a public holiday",
    "scope": "specific",
    "claim_type": "factual",
    "relevant_entities": ["America", "Christmas"],
    "text": "America recognizes Christmas as a public holiday.",
}


def main():
    mapped = ontology_mapping({"claims": [test_claim]})
    print("MAPPED CLAIM:")
    print(json.dumps(mapped["mapped_claims"], ensure_ascii=False, indent=2))
    selected = select_query({"claims": [test_claim], "mapped_claims": mapped["mapped_claims"]})
    print("QUERY RESULTS:")
    print(json.dumps(selected["query_results"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
