# DBLP QuAD 2.0 (DBLP Question Answering Dataset)
A repository for DBLP QuAD 2.0

The train, dev,and test sets are found in data folder.

#### Example:
```json
{
"id": "94fb678b-dd7e-4b29-a052-86ed04b477cf",
        "question": "Which researchers who have not coauthored with Dana S. Nau share many common coauthors with him?",
        "sparql": "PREFIX dblp: <https://dblp.org/rdf/schema#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT ?name ?affiliation (COUNT(DISTINCT ?coauthor) AS ?count) (?cocoauthor as ?dblp) (SAMPLE(?orcids) as ?orcid) WHERE {   VALUES ?author { <https://dblp.org/pid/n/DanaSNau> }   ?publ dblp:authoredBy ?author .   ?publ dblp:authoredBy ?coauthor .   FILTER ( ?author != ?coauthor ) .   ?copubl dblp:authoredBy ?coauthor .   ?copubl dblp:authoredBy ?cocoauthor .   FILTER ( ?author != ?cocoauthor ) .   MINUS { ?cocopubl dblp:authoredBy ?author . ?cocopubl dblp:authoredBy ?cocoauthor }   ?cocoauthor rdfs:label ?name .   OPTIONAL { ?cocoauthor dblp:primaryAffiliation ?affiliation . }   OPTIONAL { ?cocoauthor dblp:orcid ?orcids . } } GROUP BY ?name ?affiliation ?cocoauthor ORDER BY DESC(?count) LIMIT 10",
        "answer": {
            "head": {
                "vars": [
                    "name",
                    "affiliation",
                    "count",
                    "dblp",
                    "orcid"
                ]
            },
            "results": {
                "bindings": [...]
            }
            }
  }

```
