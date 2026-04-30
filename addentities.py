"""
Step 4: TBox Enrichment

This module enriches the ontology's TBox by adding new classes derived from 
the semantic mapping step. It reads mappings from ontologyadd.xlsx and creates 
new classes as subclasses of matched parent classes using RDFLib.

The enriched ontology is saved in Turtle format for downstream ABox injection.
"""

import pandas as pd
from rdflib import Graph, Literal, RDF, RDFS, OWL, Namespace, URIRef
import os


def enrich_tbox_rdflib():
    INPUT_TTL = "uco_1_5.ttl"
    EXCEL_ADD = "ontologyadd.xlsx"
    OUTPUT_TTL = "uco_1_5_enriched.ttl"
    
    g = Graph()
    g.parse(INPUT_TTL, format="turtle")
    
    UCO = Namespace("http://ffrdc.ebiquity.umbc.edu/ns/ontology/")
    g.bind("uco", UCO)

    df = pd.read_excel(EXCEL_ADD)
 
    class_map = {}
    for cls in g.subjects(RDF.type, OWL.Class):
        short_name = str(cls).split('#')[-1].split('/')[-1].lower()
        class_map[short_name] = cls

    added_count = 0
    for _, row in df.iterrows():
        concept = str(row['Concept']).strip()
        parent_label = str(row['UCO_Parent_Class']).strip().lower()
        
        class_name_formatted = concept.title().replace(" ", "")
        new_class_uri = UCO[class_name_formatted]
        
        parent_uri = class_map.get(parent_label)
        
        if not parent_uri:
            for name, uri in class_map.items():
                if parent_label in name:
                    parent_uri = uri
                    break
        
        if not parent_uri:
            parent_uri = OWL.Thing

        g.add((new_class_uri, RDF.type, OWL.Class))
        g.add((new_class_uri, RDFS.subClassOf, parent_uri))
        g.add((new_class_uri, RDFS.label, Literal(concept)))

        class_map[class_name_formatted.lower()] = new_class_uri
        added_count += 1

    g.serialize(destination=OUTPUT_TTL, format="turtle")


if __name__ == "__main__":
    enrich_tbox_rdflib()
