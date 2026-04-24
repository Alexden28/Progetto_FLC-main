"""Namespace normalisation helpers.

`owlready2` reconstructs IRIs using `<base>#<fragment>` regardless of the
separator present in the source file. When the baseline UCO TBox uses
`http://ffrdc.ebiquity.umbc.edu/ns/ontology/<name>` (slash), the round-trip
through owlready2 produces `http://ffrdc.ebiquity.umbc.edu/ns/ontology/#<name>`
(slash + hash), which breaks every SPARQL query written against the
canonical slash namespace.

This module rewrites every IRI in a graph to the canonical form defined in
`config.UCO_NS_IRI`, covering both the `/#` and the `#` variants.
"""
from rdflib import Graph, URIRef

from config import UCO_NS_IRI, UCO_PREFIX

_LEGACY_PREFIXES = (
    "http://ffrdc.ebiquity.umbc.edu/ns/ontology/#",
    "http://ffrdc.ebiquity.umbc.edu/ns/ontology#",
)


def _canonical(term):
    if not isinstance(term, URIRef):
        return term
    value = str(term)
    for legacy in _LEGACY_PREFIXES:
        if value.startswith(legacy):
            return URIRef(UCO_NS_IRI + value[len(legacy):])
    return term


def normalize(graph: Graph) -> Graph:
    """Return a new graph with every UCO IRI rewritten to the canonical form."""
    normalized = Graph()
    for prefix, ns in graph.namespaces():
        if str(ns) in _LEGACY_PREFIXES:
            continue
        normalized.bind(prefix, ns)
    normalized.bind(UCO_PREFIX, UCO_NS_IRI, override=True, replace=True)

    for s, p, o in graph:
        normalized.add((_canonical(s), _canonical(p), _canonical(o)))
    return normalized
