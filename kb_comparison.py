"""Qualitative comparison between the baseline TBox and the final KB.

Produces a human-readable report that highlights the actual contribution
of the pipeline: which classes are new, which individuals were injected,
how deep the hierarchy grew, which object/datatype properties now carry
data.

The comparison focuses on *what* was added, with concrete samples (class
names + labels, individual IRIs + associated comments), because the prof
explicitly asked for a side-by-side reading of the initial versus final
knowledge base.

Input : uco_1_5.ttl (baseline), UCO_INFERRED.ttl (final)
Output: KB_COMPARISON.txt
"""
from collections import defaultdict
from pathlib import Path
import time
from typing import Iterable

import rdflib
from rdflib import OWL, RDF, RDFS

from config import BASELINE_TBOX_TTL, KB_COMPARISON, UCO_INFERRED_TTL

_SAMPLE_SIZE = 15


def _parse_any(path: Path) -> rdflib.Graph:
    g = rdflib.Graph()
    fmt = "xml" if path.suffix.lower() in (".xml", ".owl") else "turtle"
    g.parse(str(path), format=fmt)
    return g


def _classes(graph: rdflib.Graph) -> set:
    return {s for s in graph.subjects(RDF.type, OWL.Class) if isinstance(s, rdflib.URIRef)}


def _individuals(graph: rdflib.Graph) -> set:
    return {s for s in graph.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, rdflib.URIRef)}


def _class_label(graph: rdflib.Graph, cls) -> str:
    label = next(iter(graph.objects(cls, RDFS.label)), None)
    return str(label) if label else ""


def _parent(graph: rdflib.Graph, cls) -> str:
    parent = next(iter(graph.objects(cls, RDFS.subClassOf)), None)
    return str(parent).split("/")[-1].split("#")[-1] if parent else "-"


def _individual_sample(graph: rdflib.Graph, ind):
    classes = [str(o).split("/")[-1].split("#")[-1] for o in graph.objects(ind, RDF.type)
               if str(o) not in (str(OWL.NamedIndividual),)]
    comment = next(iter(graph.objects(ind, RDFS.comment)), None)
    comment_str = str(comment)[:140].replace("\n", " ") if comment else ""
    return {
        "iri": str(ind).split("/")[-1].split("#")[-1],
        "classes": classes[:3],
        "comment": comment_str,
    }


def _property_usage(graph: rdflib.Graph):
    usage = defaultdict(int)
    for _, p, _ in graph:
        usage[str(p)] += 1
    return usage


def _format_class(graph: rdflib.Graph, cls) -> str:
    name = str(cls).split("/")[-1].split("#")[-1]
    label = _class_label(graph, cls)
    parent = _parent(graph, cls)
    label_part = f" (label: {label})" if label and label != name else ""
    return f"{name}{label_part}  -> parent: {parent}"


def _take(iterable: Iterable, n: int) -> list:
    return list(iterable)[:n]


def compare(
    baseline_path: Path = BASELINE_TBOX_TTL,
    final_path: Path = UCO_INFERRED_TTL,
) -> dict:
    baseline = _parse_any(Path(baseline_path))
    final = _parse_any(Path(final_path))

    base_classes = _classes(baseline)
    final_classes = _classes(final)
    base_individuals = _individuals(baseline)
    final_individuals = _individuals(final)

    new_classes = sorted(final_classes - base_classes, key=str)
    removed_classes = sorted(base_classes - final_classes, key=str)
    new_individuals = sorted(final_individuals - base_individuals, key=str)

    base_props = _property_usage(baseline)
    final_props = _property_usage(final)
    new_props = {p: c for p, c in final_props.items() if p not in base_props}

    return {
        "baseline_triples": len(baseline),
        "final_triples": len(final),
        "baseline_classes": len(base_classes),
        "final_classes": len(final_classes),
        "new_classes": new_classes,
        "removed_classes": removed_classes,
        "baseline_individuals": len(base_individuals),
        "final_individuals": len(final_individuals),
        "new_individuals": new_individuals,
        "sample_new_classes": [
            _format_class(final, c) for c in _take(new_classes, _SAMPLE_SIZE)
        ],
        "sample_new_individuals": [
            _individual_sample(final, i) for i in _take(new_individuals, _SAMPLE_SIZE)
        ],
        "new_properties": sorted(new_props.items(), key=lambda kv: -kv[1])[:_SAMPLE_SIZE],
        "baseline_path": str(baseline_path),
        "final_path": str(final_path),
    }


def write_report(
    baseline_path: Path = BASELINE_TBOX_TTL,
    final_path: Path = UCO_INFERRED_TTL,
    output_path: Path = KB_COMPARISON,
) -> dict:
    data = compare(baseline_path, final_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("CONFRONTO KNOWLEDGE BASE: INIZIALE vs FINALE\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Baseline : {data['baseline_path']}\n")
        f.write(f"Finale   : {data['final_path']}\n\n")

        f.write("METRICHE DI CRESCITA\n")
        f.write(f"Triple: {data['baseline_triples']} -> {data['final_triples']} "
                f"(+{data['final_triples'] - data['baseline_triples']})\n")
        f.write(f"Classi: {data['baseline_classes']} -> {data['final_classes']} "
                f"(+{len(data['new_classes'])} nuove, "
                f"-{len(data['removed_classes'])} rimosse)\n")
        f.write(f"Individui: {data['baseline_individuals']} -> "
                f"{data['final_individuals']} "
                f"(+{len(data['new_individuals'])} nuovi)\n\n")

        f.write(f"ESEMPI DI CLASSI AGGIUNTE (prime {_SAMPLE_SIZE})\n")
        if not data["sample_new_classes"]:
            f.write("Nessuna nuova classe individuata.\n")
        for entry in data["sample_new_classes"]:
            f.write(f"  - {entry}\n")
        f.write("\n")
        f.write("Significato: le nuove classi estendono la TBox UCO con concetti "
                "emersi dal dominio cyber-events (co-occorrenze + mapping semantico) "
                "e con le classi generate durante l'iniezione ABox per disambiguare "
                "vittime e attori.\n\n")

        f.write(f"ESEMPI DI INDIVIDUI AGGIUNTI (prime {_SAMPLE_SIZE})\n")
        if not data["sample_new_individuals"]:
            f.write("Nessun nuovo individuo individuato.\n")
        for ind in data["sample_new_individuals"]:
            classes = ", ".join(ind["classes"]) or "-"
            comment = f" | {ind['comment']}" if ind["comment"] else ""
            f.write(f"  - {ind['iri']} [classes: {classes}]{comment}\n")
        f.write("\n")
        f.write("Significato: ogni individuo corrisponde a un record del "
                "Cyber Events Database, classificato per similarita' semantica "
                "contro il pillar piu' vicino e arricchito con attributi "
                "derivati dalle colonne del dataset.\n\n")

        f.write(f"PROPRIETA' CON USO NUOVO (prime {_SAMPLE_SIZE} per frequenza)\n")
        if not data["new_properties"]:
            f.write("Nessuna proprieta' introdotta rispetto alla baseline.\n")
        for prop, count in data["new_properties"]:
            short = str(prop).split("/")[-1].split("#")[-1]
            f.write(f"  - {short}: {count} triple\n")
        f.write("\n")
        f.write("Significato: queste proprieta' erano dichiarate ma non utilizzate "
                "nella TBox di partenza; l'iniezione ABox le ha popolate rendendo "
                "la KB effettivamente interrogabile.\n")

    return data


if __name__ == "__main__":
    write_report()
