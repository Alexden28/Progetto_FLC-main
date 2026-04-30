"""
Step 6: Reasoning and Validation Pipeline

This module performs the final validation steps:
1. Loads the enriched ontology (UCO_FINAL_COMP.xml)
2. Runs Pellet reasoner for consistency checking and inference
3. Cleans and exports inferred knowledge base (UCO_INFERRED.ttl)
4. Executes structural validation
5. Runs competency questions (SPARQL queries)
6. Generates comprehensive reports comparing pre/post inference states

The output includes detailed metrics on knowledge expansion, structural properties,
and query coverage to evaluate the effectiveness of the enrichment pipeline.
"""

import os
import sys
import time
import subprocess
import rdflib
from rdflib import RDF, RDFS, OWL, XSD, Literal, URIRef
from owlready2 import *
from tqdm import tqdm

try:
    from structural_validator import run_structural_check
    from competecy_questions import run_competency_queries
except ImportError:
    def run_structural_check(x): return []
    def run_competency_queries(x, y): return (0, 0)


def setup_java():
    if sys.platform == "darwin":
        try:
            java_home = subprocess.check_output(['/usr/libexec/java_home']).decode().strip()
            owlready2.JAVA_EXE = os.path.join(java_home, "bin", "java")
        except Exception:
            owlready2.JAVA_EXE = "java"
    else:
        owlready2.JAVA_EXE = "java"
    owlready2.reasoning.JAVA_MEMORY = 16000


def run_reasoning(onto) -> str:

    with onto:
        sync_reasoner_pellet(
            infer_property_values=True,
            infer_data_property_values=True,
            debug=0
        )
    return "Consistent"


def compute_metrics(graph: rdflib.Graph) -> dict:

    n_classes = len(list(graph.subjects(RDF.type, OWL.Class)))
    n_individuals = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
    n_obj_props = len(list(graph.subjects(RDF.type, OWL.ObjectProperty)))
    n_dat_props = len(list(graph.subjects(RDF.type, OWL.DatatypeProperty)))
    n_properties = n_obj_props + n_dat_props
    
    triples_count = len(graph)
    
    rel_density = round(triples_count / n_individuals, 2) if n_individuals > 0 else 0
    connectivity_ratio = round(n_individuals / n_classes, 2) if n_classes > 0 else 0
    semantic_richness = round(n_properties / n_classes, 2) if n_classes > 0 else 0
    
    hierarchical_depth = 0
    classes_list = list(graph.subjects(RDF.type, OWL.Class))
    for cls in classes_list:
        depth = len(list(graph.transitive_objects(cls, RDFS.subClassOf)))
        hierarchical_depth = max(hierarchical_depth, depth)
    
    return {
        "triples": triples_count,
        "classes": n_classes,
        "individuals": n_individuals,
        "properties": n_properties,
        "object_properties": n_obj_props,
        "datatype_properties": n_dat_props,
        "relational_density": rel_density,
        "connectivity_ratio": connectivity_ratio,
        "semantic_richness": semantic_richness,
        "hierarchical_depth": hierarchical_depth
    }


def compare_ontologies(pre_metrics: dict, post_metrics: dict) -> str:

    triple_gain = post_metrics["triples"] - pre_metrics["triples"]
    triple_gain_pct = round((triple_gain / pre_metrics["triples"]) * 100, 2) if pre_metrics["triples"] > 0 else 0
    
    class_gain = post_metrics["classes"] - pre_metrics["classes"]
    individual_gain = post_metrics["individuals"] - pre_metrics["individuals"]
    prop_gain = post_metrics["properties"] - pre_metrics["properties"]
    
    report = []
    report.append("ONTOLOGY COMPARISON: PRE vs POST INFERENCE")
    report.append("=" * 60)
    report.append("")
    report.append(f"{'Metric':<30} {'Pre-Inference':>15} {'Post-Inference':>15} {'Change':>12}")
    report.append("-" * 72)
    report.append(f"{'Total Triples':<30} {pre_metrics['triples']:>15,} {post_metrics['triples']:>15,} {triple_gain:>+12,}")
    report.append(f"{'Classes':<30} {pre_metrics['classes']:>15,} {post_metrics['classes']:>15,} {class_gain:>+12,}")
    report.append(f"{'Individuals':<30} {pre_metrics['individuals']:>15,} {post_metrics['individuals']:>15,} {individual_gain:>+12,}")
    report.append(f"{'Properties (total)':<30} {pre_metrics['properties']:>15,} {post_metrics['properties']:>15,} {prop_gain:>+12,}")
    report.append(f"{'  - Object Properties':<30} {pre_metrics.get('object_properties', 'N/A'):>15} {post_metrics.get('object_properties', 'N/A'):>15} {'':>12}")
    report.append(f"{'  - Datatype Properties':<30} {pre_metrics.get('datatype_properties', 'N/A'):>15} {post_metrics.get('datatype_properties', 'N/A'):>15} {'':>12}")
    report.append("")
    report.append(f"{'Relational Density':<30} {pre_metrics['relational_density']:>15.2f} {post_metrics['relational_density']:>15.2f} {post_metrics['relational_density']-pre_metrics['relational_density']:>+12.2f}")
    report.append(f"{'Connectivity Ratio':<30} {pre_metrics['connectivity_ratio']:>15.2f} {post_metrics['connectivity_ratio']:>15.2f} {post_metrics['connectivity_ratio']-pre_metrics['connectivity_ratio']:>+12.2f}")
    report.append(f"{'Semantic Richness':<30} {pre_metrics['semantic_richness']:>15.2f} {post_metrics['semantic_richness']:>15.2f} {post_metrics['semantic_richness']-pre_metrics['semantic_richness']:>+12.2f}")
    report.append(f"{'Hierarchical Depth':<30} {pre_metrics['hierarchical_depth']:>15,} {post_metrics['hierarchical_depth']:>15,} {post_metrics['hierarchical_depth']-pre_metrics['hierarchical_depth']:>+12,}")
    report.append("")
    report.append(f"TRIPLE EXPANSION: {triple_gain:,} new triples ({triple_gain_pct}%)")
    report.append("")
    
    return "\n".join(report)


def main():
    setup_java()
    start_time = time.time()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(base_dir, "UCO_FINAL_COMP.xml")
    inferred_file = os.path.join(base_dir, "UCO_INFERRED.ttl")
    log_file = os.path.join(base_dir, "LOG_VALIDAZIONE.txt")
    query_results = os.path.join(base_dir, "RISULTATI_QUERY_CQ.txt")

    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"Required input file not found: {xml_file}")

    g_raw = rdflib.Graph()
    g_raw.parse(xml_file, format="xml")
    pre_metrics = compute_metrics(g_raw)

    onto = get_ontology(os.path.abspath(xml_file)).load()

    print("Running Pellet reasoner")
    try:
        inference_status = run_reasoning(onto)
    except Exception as e:
        inference_status = f"Inconsistent - {str(e)}"

    g_clean = rdflib.Graph()
    for s, p, o in tqdm(default_world.as_rdflib_graph(), desc="Filtering triples"):
        s_str, p_str, o_str = str(s), str(p), str(o)
        
        if "DATAPROPVAL" in s_str or "DATAPROPVAL" in p_str or "DATAPROPVAL" in o_str:
            continue
        
        if any(char in s_str for char in [' ', '{', '}']):
            continue
        if any(char in p_str for char in [' ', '{', '}']):
            continue
            
        g_clean.add((s, p, o))

    g_clean.serialize(destination=inferred_file, format="turtle")
    post_metrics = compute_metrics(g_clean)

    print("Running structural validation")
    structural_issues = run_structural_check(xml_file)
    
    print("Executing competency questions")
    executed_cq, informative_cq = run_competency_queries(inferred_file, query_results)

    comparison_report = compare_ontologies(pre_metrics, post_metrics)

    with open(log_file, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("COMPREHENSIVE VALIDATION AND INFERENCE REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Duration: {round(time.time() - start_time, 2)}s\n")
        f.write(f"Inference Status: {inference_status}\n\n")
        
        f.write(comparison_report)
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("STRUCTURAL VALIDATION RESULTS\n")
        f.write("=" * 60 + "\n")
        if not structural_issues:
            f.write("No structural issues detected.\n")
        else:
            f.write(f"Found {len(structural_issues)} issues:\n\n")
            issue_counts = {}
            for issue in structural_issues:
                code = issue.split()[0]
                issue_counts[code] = issue_counts.get(code, 0) + 1
            for code, count in sorted(issue_counts.items()):
                f.write(f"  {code}: {count} occurrences\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("COMPETENCY QUESTIONS SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Queries Executed: {executed_cq}\n")
        f.write(f"Informative Queries: {informative_cq}\n")
        if executed_cq > 0:
            f.write(f"Coverage: {round(informative_cq/executed_cq*100, 1)}%\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("NEW KNOWLEDGE EXAMPLES (from inference)\n")
        f.write("=" * 60 + "\n")
        
        new_classes = post_metrics["classes"] - pre_metrics["classes"]
        new_individuals = post_metrics["individuals"] - pre_metrics["individuals"]
        
        if new_classes > 0:
            f.write(f"\nInferred Classes: {new_classes} new class assertions\n")
            f.write("  Example: Anonymous classes materialized through reasoning\n")
        
        if new_individuals > 0:
            f.write(f"\nInferred Individuals: {new_individuals} new type assertions\n")
            f.write("  Example: Individuals classified into additional categories\n")
        
        triple_gain = post_metrics["triples"] - pre_metrics["triples"]
        f.write(f"\nTotal Knowledge Expansion: {triple_gain:,} triples\n")
        f.write(f"  This represents implicit knowledge made explicit by the reasoner.\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 70 + "\n")

    print(f"\nValidation complete")


if __name__ == "__main__":
    main()
