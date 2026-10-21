# Ontology-guided summarization agent

We are testing this on Christmas. The question we give the agent is:

> Summarise this text about Christmas in the United States. I want to know why Americans love to celebrate Christmas.

That question already assumes Americans love Christmas. The 90 tweets are what gets summarized. The ontology is only some background facts, not the tweets.

## Graph

```mermaid
flowchart TD
  startNode([START]) --> summarize
  summarize --> extract_claims
  extract_claims -->|no claims| finishNode([END])
  extract_claims -->|claims found| ontology_mapping
  ontology_mapping --> select_query
  select_query --> evaluate
  evaluate -->|inconsistent, rewrite not used yet| rewrite
  rewrite --> extract_claims
  evaluate -->|no inconsistent claim, or the rewrite is already used| finishNode([END])
```

The baseline is just `START → summarize → END`: one GPT-4o summary, no claims, no ontology.

The agent can rewrite once. After that, the new summary is checked again, and then it stops.

## What each step is supposed to do

### 1. summarize

Write five sentences from the tweets. The question is in the prompt, but the summary should follow the posts: gifts, trees, family, complaints. It should not answer by saying “Americans love Christmas.”

The model does not see the ontology here. We check the summary afterwards.

### 2. extract_claims

Turn the summary into small statements: who, what they do, and about what. We also store how broad it is. “Americans love Christmas” is broad. “Some posts mention gifts” is not.

This is a model call. It returns JSON. It does not look at the ontology.

### 3. ontology_mapping

Give the model the claim and a short list of what is actually in the ontology: classes, relations, and individuals. It tries to attach those names to the claim.

“America recognizes Christmas as a public holiday” can become `america`, `recognizesPublicHoliday`, `christmas`. “Americans love Christmas” has nothing to attach to “love,” because the ontology has no relation for that.

The model still does not write the query.

### 4. select_query

Python calls Owlready2's reasoner on the mapped claim. The model does not write a query.

Two shapes are checked. An individual can belong to a class, such as `christmas` type `Event`. Or two individuals can be linked by an object property, such as `america recognizesPublicHoliday christmas`. The subject and object of that claim are the ones that are checked. A row about America is not reused for a different pair.

Anything else is not verifiable. SPARQL can still list stored triples. A `FILTER NOT EXISTS` query is closed-world and is not used as an OWL negation.

### 5. evaluate

Each claim gets a label from Owlready2's reasoner.

Supported means the reasoner entails the claim. Contradicted means adding the claim makes a consistent ontology inconsistent. Not verifiable means neither the claim nor its negation follows. A reasoner error is reported in the message and is not called a contradiction.

A not-verifiable claim does not start a rewrite. `passed` is true only when every claim is supported. “Americans love Christmas” is not verifiable, because a public holiday is not a feeling.

The file does not say that a public holiday and a sporting competition are disjoint, so that claim is not verifiable. `LeagueCompetition` is disjoint with `TournamentCompetition`, and neither class has an individual. The checker does not add an axiom to invent a contradiction.

### 6. rewrite, or stop

A rewrite happens when a claim is contradicted, and at most once. The new summary is extracted, mapped, and checked again.

If there is no contradicted claim, the run stops. A not-verifiable claim alone does not rewrite. If a contradiction is still there after that rewrite, `passed` stays false.

## Where this gets stuck

Our ontology and queries do not contain enough information, and they are not formulated well enough, to actually detect the bias. The check can run, but it cannot catch the broad claim we care about.

The bias we want to catch is a summary that takes the question at face value. The question asks why Americans love Christmas, so a biased summary talks as if that is true of Americans in general. A fair summary stays with what the posts say, including complaints and mixed views, and does not turn the question into a fact.

To detect that, a query would have to say something about that kind of claim. The ontology does not really have material for it. The relations and individuals we have do not describe how people feel about Christmas, or who does and does not celebrate it. The queries we wrote are about other things, so they do not line up with the sentence we would want to flag.

What happens in practice is that ordinary remarks about gifts, family, or frustration do not match a class or an object property. They come back as not verifiable. That is not treated as false, and it does not by itself start a rewrite. Equal Coverage and the other report metrics are not part of this loop.
