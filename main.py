"""Pipeline entry point: runs every stage end to end.

The seven stages are imported (never spawned via `os.system`), so the process
remains in a single Python interpreter and errors propagate as exceptions
rather than silent exit codes.

    1. Co-occurrence matrix   -> cooccorrenze.run
    2. Co-occurrence ranking  -> cooccorrenzeclassifier.run
    3. Semantic mapping       -> findcouples.run
    4. TBox enrichment        -> addentities.enrich_tbox_rdflib
    5. ABox injection         -> kbonto.run_validated_injection
    6. Reasoning + cleaning   -> this module (`run_reasoning_and_export`)
    7. Validation & report    -> structural_validator + competecy_questions
                                 + kb_comparison, then report writer
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import owlready2
import rdflib
from owlready2 import (
    DatatypeProperty,
    ObjectProperty,
    default_world,
    get_ontology,
    sync_reasoner_pellet,
)
from rdflib import OWL, RDF, RDFS
from tqdm import tqdm

import addentities
import cooccorrenze
import cooccorrenzeclassifier
import findcouples
import kb_comparison
import kbonto
from competecy_questions import run_competency_queries
from config import (
    BASELINE_TBOX_TTL,
    CQ_RESULTS,
    JAVA_MEMORY_MB,
    KB_COMPARISON,
    LOG_VALIDATION,
    PROJECT_ROOT,
    UCO_FINAL_COMP_XML,
    UCO_FINAL_TTL,
    UCO_FINAL_XML,
    UCO_INFERRED_TTL,
)
from namespace_utils import normalize
from structural_validator import run_structural_check


def install_requirements() -> None:
    req_path = PROJECT_ROOT / "requirements.txt"
    if not req_path.exists():
        return
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_path)]
        )
    except subprocess.CalledProcessError as exc:
        print(f"Warning: pip install returned {exc.returncode}")


_JAVA_ROOTS_WINDOWS = (
    r"C:\Program Files\Java",
    r"C:\Program Files\Microsoft",
    r"C:\Program Files\Eclipse Adoptium",
    r"C:\Program Files\Eclipse Foundation",
    r"C:\Program Files\Zulu",
    r"C:\Program Files (x86)\Java",
    r"C:\Program Files (x86)\Common Files\Oracle\Java\java8path",
    r"C:\Program Files\Common Files\Oracle\Java\javapath",
)
_VERSION_RE = re.compile(r'version "(\d+)(?:\.(\d+))?')


def _java_major(exe: str) -> int:
    """Return the major version reported by `<exe> -version`, or -1 on failure.

    Handles both modern (`"25.0.1"`) and legacy (`"1.8.0_321"`) version strings.
    """
    try:
        output = subprocess.check_output(
            [exe, "-version"], stderr=subprocess.STDOUT, timeout=5,
        ).decode(errors="replace")
    except (subprocess.SubprocessError, OSError):
        return -1
    match = _VERSION_RE.search(output)
    if not match:
        return -1
    major = int(match.group(1))
    if major == 1 and match.group(2):
        major = int(match.group(2))  # 1.8 -> 8
    return major


def _find_windows_java() -> str:
    """Pick the newest java.exe under common Windows JDK install roots.

    Falls back to plain `"java"` (resolved against PATH) when nothing
    discoverable matches; the reasoner step will then surface a clear
    Java/Pellet error rather than a silent miss.
    """
    candidates: list[str] = []
    for root in _JAVA_ROOTS_WINDOWS:
        if not os.path.isdir(root):
            continue
        # Some roots ARE a JDK home (java8path/javapath); others CONTAIN
        # multiple JDK homes side-by-side.
        direct = os.path.join(root, "java.exe")
        if os.path.isfile(direct):
            candidates.append(direct)
            continue
        for entry in os.listdir(root):
            exe = os.path.join(root, entry, "bin", "java.exe")
            if os.path.isfile(exe):
                candidates.append(exe)
    if not candidates:
        return "java"
    candidates.sort(key=_java_major, reverse=True)
    return candidates[0]


def setup_java() -> None:
    if sys.platform == "darwin":
        try:
            java_home = subprocess.check_output(
                ["/usr/libexec/java_home"]
            ).decode().strip()
            owlready2.JAVA_EXE = os.path.join(java_home, "bin", "java")
        except (subprocess.CalledProcessError, FileNotFoundError):
            owlready2.JAVA_EXE = "java"
    else:
        owlready2.JAVA_EXE = _find_windows_java()
    owlready2.reasoning.JAVA_MEMORY = JAVA_MEMORY_MB


def _dedup_dataprop_marks(onto) -> None:
    """Remove `ObjectProperty` declaration from entities also marked as datatype."""
    for prop in tqdm(list(onto.properties()), desc="Cleaning properties"):
        try:
            if (ObjectProperty in prop.is_a) and (DatatypeProperty in prop.is_a):
                prop.is_a.remove(ObjectProperty)
        except ValueError:
            continue


def _filter_owlready_noise(graph: rdflib.Graph) -> rdflib.Graph:
    """Drop triples owlready2 occasionally emits with malformed IRIs."""
    cleaned = rdflib.Graph()
    for prefix, ns in graph.namespaces():
        cleaned.bind(prefix, ns)
    for s, p, o in tqdm(graph, desc="Filtering triples"):
        triple_strs = (str(s), str(p), str(o))
        if any("DATAPROPVAL" in t for t in triple_strs):
            continue
        if any(c in triple_strs[0] or c in triple_strs[1] for c in (" ", "{", "}")):
            continue
        cleaned.add((s, p, o))
    return cleaned


def run_reasoning_and_export(xml_in: Path, ttl_out: Path) -> str:
    onto = get_ontology(str(xml_in.resolve())).load()
    try:
        with onto:
            sync_reasoner_pellet(
                infer_property_values=True,
                infer_data_property_values=True,
                debug=0,
            )
        status = "Consistent"
    except owlready2.OwlReadyInconsistentOntologyError as exc:
        status = f"Inconsistent: {exc}"
    except Exception as exc:  # pellet wraps Java errors in a broad Exception
        status = f"Error: {exc}"

    _dedup_dataprop_marks(onto)

    graph = rdflib.Graph()
    for triple in default_world.as_rdflib_graph():
        graph.add(triple)
    graph = _filter_owlready_noise(graph)
    graph = normalize(graph)
    graph.serialize(destination=str(ttl_out), format="turtle")
    return status


def _run_enrichment_stages() -> None:
    cooccorrenze.run()
    cooccorrenzeclassifier.run()
    findcouples.run()
    addentities.enrich_tbox_rdflib()
    kbonto.run_validated_injection()


def _load_graph(path: Path) -> rdflib.Graph:
    fmt = "xml" if path.suffix.lower() in (".xml", ".owl") else "turtle"
    g = rdflib.Graph()
    g.parse(str(path), format=fmt)
    return g


def _publish_final_artefacts(comp_xml: Path) -> None:
    """Publish the post-reasoning graph as UCO_FINAL.{ttl,xml} with canonical IRIs."""
    g = normalize(_load_graph(comp_xml))
    g.serialize(destination=str(UCO_FINAL_TTL), format="turtle")
    g.serialize(destination=str(UCO_FINAL_XML), format="xml")


def _compute_metrics(graph: rdflib.Graph) -> dict:
    classes = list(graph.subjects(RDF.type, OWL.Class))
    individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
    properties = list(graph.subjects(RDF.type, OWL.ObjectProperty)) + list(
        graph.subjects(RDF.type, OWL.DatatypeProperty)
    )
    hierarchical_depth = 0
    for cls in tqdm(classes, desc="Computing depth"):
        depth = len(list(graph.transitive_objects(cls, RDFS.subClassOf)))
        hierarchical_depth = max(hierarchical_depth, depth)
    return {
        "classes": len(classes),
        "individuals": len(individuals),
        "properties": len(properties),
        "depth": hierarchical_depth,
    }


def _write_report(
    report_path: Path,
    *,
    inference_status: str,
    duration: float,
    triples_raw: int,
    triples_inf: int,
    metrics: dict,
    cq_results,
    structural_issues: list[str],
) -> None:
    gain = triples_inf - triples_raw
    gain_pct = round((gain / triples_raw) * 100, 2) if triples_raw else 0
    density = round(triples_inf / metrics["individuals"], 2) if metrics["individuals"] else 0
    connectivity = (
        round(metrics["individuals"] / metrics["classes"], 2) if metrics["classes"] else 0
    )
    richness = (
        round(metrics["properties"] / metrics["classes"], 2) if metrics["classes"] else 0
    )
    informative = [r for r in cq_results if r.status == "informative"]
    empty = [r for r in cq_results if r.status == "executed-empty"]
    errors = [r for r in cq_results if r.status == "error"]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("REPORT TECNICO DI VALIDAZIONE E METRICHE\n\n")
        f.write(f"Timestamp esecuzione: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Esito coerenza logica: {inference_status}\n")
        f.write(f"Durata totale pipeline: {round(duration, 2)}s\n\n")
        f.write("VALUTAZIONE CRESCITA INFERENZIALE\n")
        f.write(f"Volume triple base: {triples_raw}\n")
        f.write(f"Volume triple inferite: {triples_inf}\n")
        f.write(f"Nuova conoscenza prodotta: {gain} affermazioni\n")
        f.write(f"Coefficiente di espansione: {gain_pct}%\n\n")
        f.write("DESCRITTORI STRUTTURALI E COMPLESSITA\n")
        f.write(f"Classi totali: {metrics['classes']}\n")
        f.write(f"Individui totali: {metrics['individuals']}\n")
        f.write(f"Proprieta totali: {metrics['properties']}\n")
        f.write(f"Rapporto istanze per classe: {connectivity}\n")
        f.write(f"Indice di ricchezza semantica: {richness}\n")
        f.write(f"Grado di densita relazionale: {density}\n")
        f.write(f"Profondita gerarchica massima: {metrics['depth']}\n\n")
        f.write("EFFICACIA INFORMATIVA (COMPETENCY QUESTIONS)\n")
        f.write(f"CQ informative: {len(informative)}/{len(cq_results)}\n")
        f.write(f"CQ eseguite ma vuote: {len(empty)}\n")
        f.write(f"CQ in errore: {len(errors)}\n\n")
        f.write("PITFALLS E ANOMALIE RILEVATE\n")
        if not structural_issues:
            f.write("Nessuna criticita strutturale.\n")
        else:
            for issue in structural_issues:
                f.write(f"{issue}\n")


def main() -> None:
    install_requirements()
    setup_java()
    start = time.time()

    _run_enrichment_stages()

    if not UCO_FINAL_COMP_XML.exists():
        raise FileNotFoundError(UCO_FINAL_COMP_XML)

    triples_raw = len(_load_graph(UCO_FINAL_COMP_XML))
    inference_status = run_reasoning_and_export(UCO_FINAL_COMP_XML, UCO_INFERRED_TTL)
    _publish_final_artefacts(UCO_FINAL_COMP_XML)

    structural_issues = run_structural_check(UCO_FINAL_COMP_XML)
    cq_results = run_competency_queries(UCO_INFERRED_TTL, CQ_RESULTS)

    inferred_graph = _load_graph(UCO_INFERRED_TTL)
    metrics = _compute_metrics(inferred_graph)

    kb_comparison.write_report(
        BASELINE_TBOX_TTL, UCO_INFERRED_TTL, KB_COMPARISON,
    )

    _write_report(
        LOG_VALIDATION,
        inference_status=inference_status,
        duration=time.time() - start,
        triples_raw=triples_raw,
        triples_inf=len(inferred_graph),
        metrics=metrics,
        cq_results=cq_results,
        structural_issues=structural_issues,
    )


if __name__ == "__main__":
    main()
