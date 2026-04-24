"""Central configuration for the UCO enrichment pipeline.

All paths, thresholds, and model names used across modules are defined here so
that changing a location or a hyperparameter happens in one place.

The module exposes:
- Directory constants (PROJECT_ROOT)
- File paths for every artefact consumed or produced by the pipeline
- Thresholds and model identifiers, each with a rationale comment
- The canonical RDF namespace and a Namespace object ready for rdflib use
"""
from pathlib import Path
from rdflib import Namespace

PROJECT_ROOT = Path(__file__).resolve().parent

# Canonical namespace. The baseline TBox (uco_1_5.ttl) uses the slash form;
# we keep the same form everywhere (enrichment, ABox, final graph) so that
# SPARQL queries do not need a UNION over two prefixes.
UCO_NS_IRI = "http://ffrdc.ebiquity.umbc.edu/ns/ontology/"
UCO = Namespace(UCO_NS_IRI)
UCO_PREFIX = "uco"

# Input data
CYBER_EVENTS_XLSX = PROJECT_ROOT / "Cyber_Events_Database.xlsx"
BASELINE_TBOX_TTL = PROJECT_ROOT / "uco_1_5.ttl"

# Intermediate artefacts
COOCCURRENCE_MATRIX_XLSX = PROJECT_ROOT / "matrice_cooccorrenze.xlsx"
COOCCURRENCE_RANK_XLSX = PROJECT_ROOT / "classifica_cooccorrenze.xlsx"
ONTOLOGY_ADD_XLSX = PROJECT_ROOT / "ontologyadd.xlsx"
ENRICHED_TBOX_TTL = PROJECT_ROOT / "uco_1_5_enriched.ttl"

# Final artefacts
UCO_FINAL_TTL = PROJECT_ROOT / "UCO_FINAL.ttl"
UCO_FINAL_XML = PROJECT_ROOT / "UCO_FINAL.xml"
UCO_FINAL_COMP_TTL = PROJECT_ROOT / "UCO_FINAL_COMP.ttl"
UCO_FINAL_COMP_XML = PROJECT_ROOT / "UCO_FINAL_COMP.xml"
UCO_INFERRED_TTL = PROJECT_ROOT / "UCO_INFERRED.ttl"

# Reports
LOG_VALIDATION = PROJECT_ROOT / "LOG_VALIDAZIONE.txt"
CQ_RESULTS = PROJECT_ROOT / "RISULTATI_QUERY_CQ.txt"
KB_COMPARISON = PROJECT_ROOT / "KB_COMPARISON.txt"

# --- Hyperparameters ---

# Text processing
TOP_TOKEN_COUNT = 1000
# Only term pairs with more than COOCCURRENCE_THRESHOLD joint mentions survive
# the frequency filter; 100 empirically strips hapax pairs while keeping enough
# candidates (~1k) for the semantic mapping step.
COOCCURRENCE_THRESHOLD = 100

# Semantic mapping thresholds (findcouples.py)
# Cosine similarity between a candidate term pair and the UCO class embedding.
# 0.45 balances recall and precision on the cyber domain (below it, unrelated
# surface-form matches leak in; above, valid variants like "credential theft"
# vs "CredentialAccess" are dropped).
SEMANTIC_SIMILARITY_THRESHOLD = 0.45

# ABox injection thresholds (kbonto.py)
# Column-name vs property-name similarity. Object properties need a stronger
# signal than datatype ones because a mis-typed subject/object pair pollutes
# the graph, while a mis-typed literal only adds an orphan value.
OBJECT_PROPERTY_SIMILARITY = 0.30
DATA_PROPERTY_SIMILARITY = 0.25
# Secondary class assignment: an instance may belong to more than one class
# when the event description strongly evokes a second concept.
SECONDARY_CLASS_SIMILARITY = 0.60

# Model identifiers
FINDCOUPLES_MODEL = "sentence-transformers/all-distilroberta-v1"
# We use a stronger sentence encoder here because the text is longer
# (full descriptions) and the downstream decisions are more expensive to
# get wrong (ABox injection vs. a ranked list of term pairs).
KBONTO_MODEL = "all-mpnet-base-v2"

# Reasoner
JAVA_MEMORY_MB = 16000

# Competency queries
CQ_INFORMATIVE_MIN_ROWS = 1
# Queries returning at least this many rows are flagged as "rich" in the
# commentary; below this they are still informative but considered weak.
CQ_RICH_MIN_ROWS = 5
