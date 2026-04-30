"""
Competency Questions Module

Executes SPARQL queries against the inferred knowledge base to validate 
that the ontology can answer domain-specific questions. Queries are organized 
by type: Descriptive, Analytical, Structural, and Comparative.

The module distinguishes between executed queries and informative queries 
(those returning meaningful results), providing detailed feedback on coverage.
It now includes 35 queries, with a specific focus on comparative analysis 
between explicit and inferred knowledge and operational effectiveness.
"""

import rdflib
import time
from typing import Dict, Tuple


def get_queries() -> Dict[str, Tuple[str, str]]:
    """
    Return dictionary of 35 competency questions organized by type.
    
    Returns:
        Dict mapping query ID to (description, SPARQL query) tuples
    """
    prefixes = """
        PREFIX hash: <http://ffrdc.ebiquity.umbc.edu/ns/ontology#>
        PREFIX slash: <http://ffrdc.ebiquity.umbc.edu/ns/ontology/>
        PREFIX rdfs: <http://www.w3.org/1999/02/22-rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    """

    queries = {
        "CQ01_Descriptive": ("Extraction of Incidents-Dates-Actors", """
            SELECT ?incidente ?data ?tipoAttore WHERE {
              { ?incidente slash:hasEventDate ?data } UNION { ?incidente hash:hasEventDate ?data }
              OPTIONAL {
                { ?incidente slash:hasActorType ?tipoAttore }
                UNION { ?incidente hash:hasActorType ?tipoAttore }
              }
            } LIMIT 50
        """),
        
        "CQ02_Analytical": ("Quantitative Analysis by Actor Type", """
            SELECT ?tipoAttore (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasActorType ?tipoAttore } UNION { ?inc hash:hasActorType ?tipoAttore }
            } GROUP BY ?tipoAttore ORDER BY DESC(?n)
        """),
        
        "CQ03_Descriptive": ("Correlation between Type and Date", """
            SELECT ?incidente ?tipo ?data WHERE {
              { ?incidente slash:hasEventType ?tipo } UNION { ?incidente hash:hasEventType ?tipo }
              { ?incidente slash:hasEventDate ?data } UNION { ?incidente hash:hasEventDate ?data }
            } LIMIT 20
        """),
        
        "CQ04_Descriptive": ("Organization-Industry Mapping", """
            SELECT ?org ?ind WHERE {
              { ?inc slash:hasOrganization ?org } UNION { ?inc hash:hasOrganization ?org }
              { ?inc slash:hasIndustry ?ind } UNION { ?inc hash:hasIndustry ?ind }
            } LIMIT 20
        """),
        
        "CQ05_Analytical": ("Industry Ranking by Volume", """
            SELECT ?industria (COUNT(?incidente) AS ?totale) WHERE {
              { ?incidente slash:hasIndustry ?industria } UNION { ?incidente hash:hasIndustry ?industria }
            } GROUP BY ?industria ORDER BY DESC(?totale)
        """),
        
        "CQ06_Analytical": ("Temporal Analysis Post-2020", """
            SELECT ?incidente ?data WHERE {
              { ?incidente slash:hasEventDate ?data } UNION { ?incidente hash:hasEventDate ?data }
              FILTER(?data > "2020-01-01T00:00:00"^^xsd:dateTime)
            } ORDER BY ?data LIMIT 20
        """),
        
        "CQ07_Analytical": ("Subtype Distribution by Industry", """
            SELECT ?industria ?sottotipo (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasIndustry ?industria } UNION { ?inc hash:hasIndustry ?industria }
              { ?inc slash:hasEventSubtype ?sottotipo } UNION { ?inc hash:hasEventSubtype ?sottotipo }
            } GROUP BY ?industria ?sottotipo ORDER BY ?industria DESC(?n)
        """),
        
        "CQ08_Structural": ("TBox Evolution - New Classes", """
            SELECT ?classe ?super WHERE {
              ?classe rdfs:subClassOf ?super .
              FILTER(isIRI(?classe) && !strstarts(str(?classe), "http://www.w3.org"))
            } LIMIT 20
        """),
        
        "CQ09_Analytical": ("Detection of Incomplete Records", """
            SELECT (COUNT(DISTINCT ?inc) AS ?incompleti) WHERE {
              { ?inc slash:hasEventDate ?d } UNION { ?inc hash:hasEventDate ?d }
              FILTER NOT EXISTS {
                { ?inc slash:hasOrganization ?o } UNION { ?inc hash:hasOrganization ?o }
              }
            }
        """),
        
        "CQ10_Structural": ("Validation of isType_of Relations", """
            SELECT ?incidente ?tipo WHERE {
              { ?incidente slash:isType_of ?tipo } UNION { ?incidente hash:isType_of ?tipo }
            } LIMIT 20
        """),
        
        "CQ11_Analytical": ("Monthly Attack Trends", """
            SELECT ?mese (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasMonth ?mese } UNION { ?inc hash:hasMonth ?mese }
            } GROUP BY ?mese ORDER BY ?mese
        """),
        
        "CQ12_Analytical": ("Geographic Distribution of Incidents", """
            SELECT ?paese (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasCountry ?paese } UNION { ?inc hash:hasCountry ?paese }
            } GROUP BY ?paese ORDER BY DESC(?n)
        """),
        
        "CQ13_Analytical": ("Actor-Attack Type Correlation", """
            SELECT ?tipoAttore ?tipoAttacco (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasActorType ?tipoAttore } UNION { ?inc hash:hasActorType ?tipoAttore }
              { ?inc slash:hasEventType ?tipoAttacco } UNION { ?inc hash:hasEventType ?tipoAttacco }
            } GROUP BY ?tipoAttore ?tipoAttacco ORDER BY DESC(?n)
        """),
        
        "CQ15_Analytical": ("Analysis of Prevalent Motivations", """
            SELECT ?sottotipo (COUNT(?inc) AS ?tot) WHERE {
              { ?inc slash:hasEventSubtype ?sottotipo } UNION { ?inc hash:hasEventSubtype ?sottotipo }
            } GROUP BY ?sottotipo ORDER BY DESC(?tot)
        """),
        
        "CQ16_Structural": ("Chain Actor-Incident-Type", """
            SELECT ?tipoAttore ?incidente ?tipoAttacco ?industria WHERE {
              { ?incidente slash:hasActorType ?tipoAttore } UNION { ?incidente hash:hasActorType ?tipoAttore }
              { ?incidente slash:hasEventType ?tipoAttacco } UNION { ?incidente hash:hasEventType ?tipoAttacco }
              { ?incidente slash:hasIndustry ?industria } UNION { ?incidente hash:hasIndustry ?industria }
            } LIMIT 20
        """),
        
        "CQ18_Analytical": ("Behaviour Analysis by Industry", """
            SELECT ?industria ?beh (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasIndustry ?industria } UNION { ?inc hash:hasIndustry ?industria }
              { ?inc slash:behaviour ?beh } UNION { ?inc hash:behaviour ?beh }
            } GROUP BY ?industria ?beh ORDER BY ?industria DESC(?n)
        """),
        
        "CQ19_Analytical": ("Behaviour vs Type Correlation", """
            SELECT ?beh ?tipo (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:behaviour ?beh } UNION { ?inc hash:behaviour ?beh }
              { ?inc slash:hasEventType ?tipo } UNION { ?inc hash:hasEventType ?tipo }
            } GROUP BY ?beh ?tipo ORDER BY ?beh DESC(?n)
        """),
        
        "CQ20_Structural": ("Individuals per Parent Class", """
            SELECT ?super (COUNT(?i) AS ?n) WHERE {
              ?i a ?classe .
              ?classe rdfs:subClassOf ?super .
            } GROUP BY ?super ORDER BY DESC(?n) LIMIT 20
        """),
        
        "CQ21_Comparative": ("New Classes from Inference", """
            SELECT DISTINCT ?newClass WHERE {
              ?newClass a owl:Class .
              ?newClass rdfs:subClassOf* ?parent .
              FILTER(!strstarts(str(?newClass), "http://www.w3.org"))
            } LIMIT 30
        """),
        
        "CQ22_Comparative": ("Property Coverage Analysis", """
            SELECT ?prop (COUNT(?s) AS ?usage) WHERE {
              ?s ?prop ?o .
              FILTER(?prop != rdf:type)
            } GROUP BY ?prop ORDER BY DESC(?usage) LIMIT 20
        """),

        "CQ23_Comparative": ("Explicit vs Inferred Types Count", """
            SELECT ?class (COUNT(?i) AS ?count) WHERE {
              ?i a ?class .
              FILTER(!strstarts(str(?class), "http://www.w3.org"))
            } GROUP BY ?class ORDER BY DESC(?count) LIMIT 20
        """),

        "CQ24_Comparative": ("Deep Hierarchical Instances", """
            SELECT ?instance ?deepClass WHERE {
              ?instance a ?deepClass .
              ?deepClass rdfs:subClassOf+ ?topClass .
              ?topClass rdfs:subClassOf* owl:Thing .
              FILTER(!strstarts(str(?deepClass), "http://www.w3.org"))
            } LIMIT 20
        """),

        "CQ27_Comparative": ("Semantic Richness per Industry", """
            SELECT ?ind (COUNT(DISTINCT ?type) AS ?variety) WHERE {
              { ?inc slash:hasIndustry ?ind } UNION { ?inc hash:hasIndustry ?ind }
              { ?inc slash:hasEventType ?type } UNION { ?inc hash:hasEventType ?type }
            } GROUP BY ?ind ORDER BY DESC(?variety) LIMIT 20
        """),

        "CQ28_Comparative": ("Cross-Domain Actor Analysis", """
            SELECT ?actorType ?ind1 ?ind2 (COUNT(?inc) AS ?n) WHERE {
              { ?inc slash:hasActorType ?actorType } UNION { ?inc hash:hasActorType ?actorType }
              { ?inc slash:hasIndustry ?ind1 } UNION { ?inc hash:hasIndustry ?ind1 }
              { ?inc slash:hasIndustry ?ind2 } UNION { ?inc hash:hasIndustry ?ind2 }
              FILTER(?ind1 != ?ind2)
            } GROUP BY ?actorType ?ind1 ?ind2 ORDER BY DESC(?n) LIMIT 20
        """),

        "CQ29_Comparative": ("Inference Impact on Date Ranges", """
            SELECT ?type (MIN(?d) AS ?startDate) (MAX(?d) AS ?endDate) WHERE {
              { ?inc a ?type } UNION { ?inc slash:hasEventType ?type } UNION { ?inc hash:hasEventType ?type }
              { ?inc slash:hasEventDate ?d } UNION { ?inc hash:hasEventDate ?d }
              FILTER(!strstarts(str(?type), "http://www.w3.org"))
            } GROUP BY ?type LIMIT 20
        """),

        "CQ31_Effective": ("Identification of Actionable Targets", """
            SELECT ?org ?paese ?tipoAttacco WHERE {
              { ?inc slash:hasOrganization ?org } UNION { ?inc hash:hasOrganization ?org }
              { ?inc slash:hasCountry ?paese } UNION { ?inc hash:hasCountry ?paese }
              { ?inc slash:hasEventType ?tipoAttacco } UNION { ?inc hash:hasEventType ?tipoAttacco }
              FILTER(?paese = "Italy" || ?paese = "USA")
            } LIMIT 10
        """),

        "CQ32_Effective": ("Critical Incident Filtering for Logic Response", """
            SELECT ?incidente WHERE {
              { ?incidente slash:hasEventSubtype ?s } UNION { ?incidente hash:hasEventSubtype ?s }
              { ?incidente slash:hasIndustry ?ind } UNION { ?incidente hash:hasIndustry ?ind }
              FILTER(REGEX(str(?s), "Ransomware", "i") && ?ind = "Healthcare")
            } LIMIT 10
        """),

        "CQ33_Effective": ("Active Chain Detection for Mitigation", """
            SELECT ?actor ?target WHERE {
              ?inc slash:hasActorType ?actor .
              ?inc slash:hasOrganization ?target .
              FILTER EXISTS { ?inc slash:behaviour ?b }
            } LIMIT 15
        """),

        "CQ34_Effective": ("Mapping Vulnerable Nodes for System Update", """
            SELECT DISTINCT ?ind WHERE {
              ?inc slash:hasIndustry ?ind .
              FILTER NOT EXISTS { ?inc slash:hasEventDate ?d }
            }
        """),

        "CQ35_Effective": ("Validation of Operational Subtype Consistency", """
            SELECT ?inc ?sub WHERE {
              ?inc a ?type .
              ?inc slash:hasEventSubtype ?sub .
              FILTER(?type != ?sub)
            } LIMIT 20
        """),

        "CQ36_Effective": ("Cross-Reference Actor-Motivation for Triage", """
            SELECT ?attore ?motivo (COUNT(?inc) AS ?c) WHERE {
              ?inc slash:hasActorType ?attore .
              ?inc slash:hasEventSubtype ?motivo .
            } GROUP BY ?attore ?motivo HAVING (COUNT(?inc) > 1)
        """),

        "CQ37_Effective": ("Temporal Alert for Recurring Patterns", """
            SELECT ?org ?data WHERE {
              ?inc slash:hasOrganization ?org .
              ?inc slash:hasEventDate ?data .
              FILTER(?data > "2024-01-01T00:00:00"^^xsd:dateTime)
            } ORDER BY DESC(?data) LIMIT 10
        """),

        "CQ38_Effective": ("Dependency Validation for Inferred Linkage", """
            SELECT ?s ?o WHERE {
              ?s slash:isType_of ?type .
              ?o slash:hasEventType ?type .
              FILTER(?s != ?o)
            } LIMIT 10
        """),

        "CQ39_Effective": ("Filtering High-Impact Industry Events", """
            SELECT ?ind (COUNT(?inc) AS ?n) WHERE {
              ?inc slash:hasIndustry ?ind .
              ?inc slash:hasActorType ?act .
              FILTER(?act = "State-Sponsored")
            } GROUP BY ?ind ORDER BY DESC(?n)
        """),

        "CQ40_Effective": ("Execution Logic: Node-Attribute Verification", """
            SELECT ?inc ?prop ?val WHERE {
              ?inc rdf:type slash:Incident .
              ?inc ?prop ?val .
              FILTER(isLiteral(?val) && datatype(?val) = xsd:dateTime)
            } LIMIT 10
        """)
    }
    
    return {qid: (prefixes + sparql, desc) for qid, (desc, sparql) in queries.items()}


def run_competency_queries(onto_path: str, output_file: str) -> Tuple[int, int]:
    """
    Execute all competency queries and write results to file.
    
    Args:
        onto_path: Path to the ontology file in Turtle format
        output_file: Path to output results file
        
    Returns:
        Tuple of (executed_count, informative_count)
    """
    g = rdflib.Graph()
    g.parse(onto_path, format="turtle")
    
    queries = get_queries()
    
    executed_count = 0
    informative_count = 0
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("COMPETENCY QUESTIONS REPORT\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Ontology: {onto_path}\n")
        f.write(f"Total triples: {len(g)}\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("QUERY CLASSIFICATION SUMMARY\n")
        f.write("=" * 60 + "\n")
        
        descriptive = sum(1 for qid in queries if "_Descriptive" in qid)
        analytical = sum(1 for qid in queries if "_Analytical" in qid)
        structural = sum(1 for qid in queries if "_Structural" in qid)
        comparative = sum(1 for qid in queries if "_Comparative" in qid)
        effective = sum(1 for qid in queries if "_Effective" in qid)
        
        f.write(f"Descriptive Queries: {descriptive}\n")
        f.write(f"Analytical Queries: {analytical}\n")
        f.write(f"Structural Queries: {structural}\n")
        f.write(f"Comparative Queries: {comparative}\n")
        f.write(f"Effective Queries: {effective}\n")
        f.write(f"Total Queries: {len(queries)}\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 60 + "\n\n")
        
        for qid, (sparql, description) in queries.items():
            f.write(f"QUERY: {qid} - {description}\n")
            f.write("-" * 50 + "\n")
            
            start_time = time.time()
            try:
                results = g.query(sparql)
                exec_time = time.time() - start_time
                executed_count += 1
                
                result_count = len(results)
                
                if result_count == 0:
                    f.write(f"Status: EXECUTED (No results returned) - Time: {exec_time:.4f}s\n")
                    f.write("Result Table: [Empty]\n")
                else:
                    informative_count += 1
                    f.write(f"Status: INFORMATIVE ({result_count} results) - Time: {exec_time:.4f}s\n\n")
                    
                    vars_list = [str(v) for v in results.vars]
                    f.write(" | ".join(vars_list) + "\n")
                    f.write("-" * 30 + "\n")
                    
                    display_limit = 20
                    for i, row in enumerate(results):
                        if i >= display_limit:
                            f.write(f"... and {result_count - display_limit} more rows\n")
                            break
                        line = [str(val).split('/')[-1].split('#')[-1] if val is not None else "None" for val in row]
                        f.write(" | ".join(line) + "\n")
                        
            except Exception as e:
                f.write(f"Status: ERROR - {e}\n")
            
            f.write("\n" + "=" * 50 + "\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Queries Executed: {executed_count}/{len(queries)}\n")
        f.write(f"Informative Queries: {informative_count}/{len(queries)}\n")
        f.write(f"Coverage: {round(informative_count/len(queries)*100, 1) if queries else 0}%\n")
    
    return executed_count, informative_count


if __name__ == "__main__":
    run_competency_queries("UCO_INFERRED.ttl", "RISULTATI_QUERY_CQ.txt")