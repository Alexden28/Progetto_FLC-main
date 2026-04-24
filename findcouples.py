"""Step 3/6 of the enrichment pipeline.

For every candidate term pair in the co-occurrence ranking, we embed both the
candidate and every class name of the baseline UCO TBox (enriched with its
rdfs:label and rdfs:comment when available). A pair is kept whenever the
cosine similarity against its best-matching UCO class exceeds the
`SEMANTIC_SIMILARITY_THRESHOLD`, and the best match becomes its proposed
parent class. The resulting CSV (`ontologyadd.xlsx`) is manually curated
before feeding the next step.

Input : classifica_cooccorrenze.xlsx, uco_1_5.ttl
Output: ontologyadd.xlsx (columns: Concept, UCO_Parent_Class, Similarity_Score)
"""
import pandas as pd
import spacy
import torch
from rdflib import Graph, OWL, RDF, RDFS
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

from config import (
    BASELINE_TBOX_TTL,
    COOCCURRENCE_RANK_XLSX,
    FINDCOUPLES_MODEL,
    ONTOLOGY_ADD_XLSX,
    SEMANTIC_SIMILARITY_THRESHOLD,
)


def _load_spacy():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        from spacy.cli import download
        download("en_core_web_sm")
        return spacy.load("en_core_web_sm")


class OntologyEnricher:
    STOP_TECHNICAL = {
        "list", "including", "affected", "occurred", "notified", "may", "notice",
    }
    SKIP_CLASS_NAMES = {"Class", "Thing", ""}

    def __init__(self, model_name: str = FINDCOUPLES_MODEL):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.ontology_classes: dict = {}
        self._nlp = _load_spacy()

    def _is_valid_concept(self, text: str) -> bool:
        doc = self._nlp(text)
        has_verb = any(token.pos_ in ("VERB", "AUX") for token in doc)
        has_noun = any(token.pos_ in ("NOUN", "PROPN") for token in doc)
        has_stop = any(token.text.lower() in self.STOP_TECHNICAL for token in doc)
        return has_noun and not has_verb and not has_stop

    def _get_embedding(self, text: str):
        inputs = self.tokenizer(
            text, return_tensors="pt", padding=True, truncation=True, max_length=128,
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).numpy()

    def load_ontology(self, file_path) -> None:
        g = Graph()
        try:
            g.parse(str(file_path))
        except Exception:
            g.parse(str(file_path), format="xml")

        for s in g.subjects(RDF.type, OWL.Class):
            tech_name = str(s).replace("#", "/").split("/")[-1]
            if tech_name in self.SKIP_CLASS_NAMES or "ransomware" in tech_name.lower():
                continue
            comments = " ".join(str(o) for o in g.objects(s, RDFS.comment))
            labels = " ".join(str(o) for o in g.objects(s, RDFS.label))
            description = f"{tech_name} {labels} {comments}".strip()
            self.ontology_classes[tech_name] = self._get_embedding(description)

    def run(
        self,
        input_xlsx=COOCCURRENCE_RANK_XLSX,
        ontology_path=BASELINE_TBOX_TTL,
        output_xlsx=ONTOLOGY_ADD_XLSX,
    ) -> None:
        self.load_ontology(ontology_path)
        df = pd.read_excel(input_xlsx)

        results: list[dict] = []
        class_names = list(self.ontology_classes.keys())
        class_vectors = list(self.ontology_classes.values())

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Semantic mapping"):
            candidate = f"{row['Parola1']} {row['Parola2']}".lower()
            if "ransomware" in candidate or not self._is_valid_concept(candidate):
                continue

            candidate_vector = self._get_embedding(candidate)
            similarities = [
                cosine_similarity(candidate_vector, cv)[0][0] for cv in class_vectors
            ]
            ranked = sorted(
                zip(class_names, similarities), key=lambda x: x[1], reverse=True,
            )
            best_match, top_score = ranked[0]

            if top_score >= SEMANTIC_SIMILARITY_THRESHOLD:
                results.append({
                    "Concept": candidate,
                    "UCO_Parent_Class": best_match,
                    "Similarity_Score": round(float(top_score), 3),
                })

        (pd.DataFrame(results)
            .sort_values("Similarity_Score", ascending=False)
            .to_excel(output_xlsx, index=False))


def run() -> None:
    enricher = OntologyEnricher()
    enricher.run()


if __name__ == "__main__":
    run()
