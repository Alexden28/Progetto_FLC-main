"""Shortcut entry point: skip the data-preparation stages.

Assumes `UCO_FINAL_COMP.xml` already exists (produced by a previous full
run via `main.py`) and only re-runs reasoning, validation and report
generation. Useful when iterating on the reasoner configuration, the
structural checks, or the competency questions without re-building the
ABox.
"""
import time

import rdflib
from rdflib import OWL, RDF, RDFS
from tqdm import tqdm

import kb_comparison
from competecy_questions import run_competency_queries
from config import (
    BASELINE_TBOX_TTL,
    CQ_RESULTS,
    KB_COMPARISON,
    LOG_VALIDATION,
    UCO_FINAL_COMP_XML,
    UCO_INFERRED_TTL,
)
from main import (
    _compute_metrics,
    _load_graph,
    _publish_final_artefacts,
    run_reasoning_and_export,
    setup_java,
)
from structural_validator import run_structural_check


def main() -> None:
    setup_java()
    start = time.time()

    if not UCO_FINAL_COMP_XML.exists():
        raise FileNotFoundError(UCO_FINAL_COMP_XML)

    triples_raw = len(_load_graph(UCO_FINAL_COMP_XML))
    inference_status = run_reasoning_and_export(UCO_FINAL_COMP_XML, UCO_INFERRED_TTL)
    _publish_final_artefacts(UCO_FINAL_COMP_XML)

    structural_issues = run_structural_check(UCO_FINAL_COMP_XML)
    run_competency_queries(UCO_INFERRED_TTL, CQ_RESULTS)

    inferred_graph = _load_graph(UCO_INFERRED_TTL)
    metrics = _compute_metrics(inferred_graph)
    triples_inf = len(inferred_graph)

    kb_comparison.write_report(BASELINE_TBOX_TTL, UCO_INFERRED_TTL, KB_COMPARISON)

    gain = triples_inf - triples_raw
    gain_pct = round((gain / triples_raw) * 100, 2) if triples_raw else 0

    with open(LOG_VALIDATION, "w", encoding="utf-8") as f:
        f.write("REPORT TECNICO (modalita' tag: solo inferenza e validazione)\n\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Esito: {inference_status}\n")
        f.write(f"Durata: {round(time.time() - start, 2)}s\n\n")
        f.write(f"Triple base: {triples_raw}\n")
        f.write(f"Triple inferite (pulite): {triples_inf}\n")
        f.write(f"Expansion: {gain_pct}%\n\n")
        f.write(f"Classi: {metrics['classes']}\n")
        f.write(f"Individui: {metrics['individuals']}\n")
        f.write(f"Proprieta: {metrics['properties']}\n")
        f.write(f"Depth: {metrics['depth']}\n\n")
        if structural_issues:
            f.write(f"Criticita strutturali: {len(structural_issues)}\n")
        else:
            f.write("Nessuna criticita strutturale.\n")


if __name__ == "__main__":
    main()
