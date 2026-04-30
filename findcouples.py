"""
Step 3: Semantic Mapping

This module maps extracted term pairs to existing ontology classes using 
semantic similarity computed via sentence-transformers. It loads the base 
ontology, extracts class embeddings, and ranks candidate mappings based on 
cosine similarity. Only mappings above a threshold (0.45) are retained.

Output serves as input for TBox enrichment in Step 4.
"""

import pandas as pd
import torch
import spacy
from transformers import AutoTokenizer, AutoModel
from rdflib import Graph, RDF, OWL, RDFS
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


class OntologyEnricher:
    
    def __init__(self, model_name="sentence-transformers/all-distilroberta-v1"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.ontology_classes = {}

    def _is_valid_concept(self, text):
        doc = nlp(text)
        has_verb = any(token.pos_ in ["VERB", "AUX"] for token in doc)
        has_noun = any(token.pos_ in ["NOUN", "PROPN"] for token in doc)
        stop_technical = {"list", "including", "affected", "occurred", "notified", "may", "notice"}
        has_stop = any(token.text.lower() in stop_technical for token in doc)
        return has_noun and not has_verb and not has_stop

    def _get_embedding(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).numpy()

    def load_ontology(self, file_path):
        g = Graph()
        try:
            g.parse(file_path)
        except Exception:
            g.parse(file_path, format="xml")
            
        for cls in g.subjects(RDF.type, OWL.Class):
            tech_name = str(cls).replace('#', '/').split('/')[-1]
            if tech_name in ["Class", "Thing", ""] or "ransomware" in tech_name.lower():
                continue
            
            comments = " ".join([str(o) for o in g.objects(cls, RDFS.comment)])
            labels = " ".join([str(o) for o in g.objects(cls, RDFS.label)])
            
            combined_description = f"{tech_name} {labels} {comments}".strip()
            self.ontology_classes[tech_name] = self._get_embedding(combined_description)

    def run(self, input_xlsx, ontology_path, output_xlsx):
        self.load_ontology(ontology_path)
        df = pd.read_excel(input_xlsx)
        
        results_list = []
        class_names = list(self.ontology_classes.keys())
        class_vectors = list(self.ontology_classes.values())

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Mapping Semantico"):
            candidate = f"{row['Parola1']} {row['Parola2']}".lower()
            
            if "ransomware" in candidate:
                continue
            if not self._is_valid_concept(candidate):
                continue
            
            candidate_vector = self._get_embedding(candidate)
            similarities = [cosine_similarity(candidate_vector, cv)[0][0] for cv in class_vectors]
            
            ranked = sorted(zip(class_names, similarities), key=lambda x: x[1], reverse=True)
            best_match, top_score = ranked[0]

            if top_score >= 0.45:
                results_list.append({
                    "Concept": candidate,
                    "UCO_Parent_Class": best_match,
                    "Similarity_Score": round(float(top_score), 3)
                })

        pd.DataFrame(results_list).sort_values("Similarity_Score", ascending=False).to_excel(output_xlsx, index=False)


if __name__ == "__main__":
    enricher = OntologyEnricher()
    enricher.run("classifica_cooccorrenze.xlsx", "uco_1_5.ttl", "ontologyadd.xlsx")
