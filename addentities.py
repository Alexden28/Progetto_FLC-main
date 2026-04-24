"""Step 4/6 of the enrichment pipeline.

Adds the manually curated concepts from `ontologyadd.xlsx` to the baseline UCO
TBox as new `owl:Class` axioms, each subclass of the UCO class suggested by
the previous step (falling back to `owl:Thing` when the suggested parent
cannot be resolved). All new IRIs are minted under the canonical UCO
namespace defined in `config.py`, so downstream SPARQL queries do not need
to UNION over multiple prefixes.

Input : uco_1_5.ttl, ontologyadd.xlsx
Output: uco_1_5_enriched.ttl
"""
import pandas as pd
from rdflib import Graph, Literal, OWL, RDF, RDFS

from config import (
    BASELINE_TBOX_TTL,
    ENRICHED_TBOX_TTL,
    ONTOLOGY_ADD_XLSX,
    UCO,
    UCO_PREFIX,
)


def _build_class_map(g: Graph) -> dict:
    """Short-name (lowercase) -> class URI, for parent lookups."""
    class_map: dict = {}
    for s in g.subjects(RDF.type, OWL.Class):
        short_name = str(s).split("#")[-1].split("/")[-1].lower()
        class_map[short_name] = s
    return class_map


def _resolve_parent(class_map: dict, parent_label: str):
    parent_uri = class_map.get(parent_label)
    if parent_uri is not None:
        return parent_uri
    for name, uri in class_map.items():
        if parent_label in name:
            return uri
    return OWL.Thing


def enrich_tbox_rdflib() -> int:
    """Enrich the baseline TBox with rows from ontologyadd.xlsx.

    Returns the number of classes actually added.
    """
    g = Graph()
    g.parse(str(BASELINE_TBOX_TTL), format="turtle")
    g.bind(UCO_PREFIX, UCO)

    df = pd.read_excel(ONTOLOGY_ADD_XLSX)
    class_map = _build_class_map(g)

    added = 0
    for _, row in df.iterrows():
        concept = str(row["Concept"]).strip()
        parent_label = str(row["UCO_Parent_Class"]).strip().lower()

        class_name = concept.title().replace(" ", "")
        new_class_uri = UCO[class_name]
        parent_uri = _resolve_parent(class_map, parent_label)

        g.add((new_class_uri, RDF.type, OWL.Class))
        g.add((new_class_uri, RDFS.subClassOf, parent_uri))
        g.add((new_class_uri, RDFS.label, Literal(concept)))

        class_map[class_name.lower()] = new_class_uri
        added += 1

    g.serialize(destination=str(ENRICHED_TBOX_TTL), format="turtle")
    return added


if __name__ == "__main__":
    enrich_tbox_rdflib()
