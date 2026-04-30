"""
Structural Validator Module

Performs structural validation of the ontology checking for common pitfalls:
- Missing comments on classes and properties [P08]
- Missing domain/range definitions for object properties [P11]
- Missing inverse relations [P13]

Returns a list of issues found during validation.
"""

import rdflib
from rdflib import RDF, RDFS, OWL
import os


def run_structural_check(file_path: str) -> list:
    g = rdflib.Graph()
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".xml", ".owl"]:
        g.parse(file_path, format="xml")
    else:
        g.parse(file_path, format="turtle")
    
    issues = []
    
    for cls in g.subjects(RDF.type, OWL.Class):
        if not list(g.objects(cls, RDFS.comment)):
            issues.append(f"[P08] Missing comment for Class: {str(cls).split('/')[-1].split('#')[-1]}")
            
    for individual in g.subjects(RDF.type, None):
        is_class = (individual, RDF.type, OWL.Class) in g
        is_obj_prop = (individual, RDF.type, OWL.ObjectProperty) in g
        if not is_class and not is_obj_prop:
            if not list(g.objects(individual, RDFS.comment)):
                issues.append(f"[P08] Missing comment for Individual/Property: {str(individual).split('/')[-1].split('#')[-1]}")

    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not list(g.objects(prop, RDFS.domain)):
            issues.append(f"[P11] Missing Domain for Property: {str(prop).split('/')[-1].split('#')[-1]}")
        if not list(g.objects(prop, RDFS.range)):
            issues.append(f"[P11] Missing Range for Property: {str(prop).split('/')[-1].split('#')[-1]}")

    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not list(g.objects(prop, OWL.inverseOf)):
            issues.append(f"[P13-Warning] No inverse relation for: {str(prop).split('/')[-1].split('#')[-1]}")

    return issues


if __name__ == "__main__":
    file_to_check = "UCO_FINAL_COMP.xml"
    if not os.path.exists(file_to_check):
        file_to_check = "UCO_FINAL_COMP.ttl"
        
    if os.path.exists(file_to_check):
        results = run_structural_check(file_to_check)
        for issue in results:
            pass
