# Cybersecurity Ontology Enrichment Pipeline

## Overview

This pipeline automates the enrichment of the Unified Cybersecurity Ontology (UCO) by extracting knowledge from a structured database of cyber events, performing semantic mapping, injecting instances, and validating the resulting knowledge base through logical reasoning and competency questions.

## Pipeline Objectives

1. **Extract co-occurrence relationships** from cyber event descriptions
2. **Map extracted terms** to existing ontology classes using semantic similarity
3. **Enrich the TBox** with new classes derived from data analysis
4. **Inject ABox individuals** from the Cyber_Events_Database.xlsx
5. **Validate** the enriched ontology through structural checks and SPARQL queries
6. **Perform inference** using the Pellet reasoner to derive implicit knowledge

## Architecture

```
Cyber_Events_Database.xlsx
    │
    ▼
┌─────────────────────┐
│  cooccorrenze.py    │ → matrice_cooccorrenze.xlsx
│  (Step 1)           │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  cooccorrenzeclassifier.py │ → classifica_cooccorrenze.xlsx
│  (Step 2)                  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐      uco_1_5.ttl
│  findcouples.py     │ ←──────────┐
│  (Step 3)           │            │
└─────────────────────┘            │
    │                              │
    ▼                              │
ontologyadd.xlsx                   │
    │                              │
    ▼                              │
┌─────────────────────┐            │
│  addentities.py     │ ←──────────┘
│  (Step 4)           │
└─────────────────────┘
    │
    ▼
uco_1_5_enriched.ttl
    │
    ▼
┌─────────────────────┐      Cyber_Events_Database.xlsx
│  kbonto.py          │ ←──────────────────────────┐
│  (Step 5)           │                            │
└─────────────────────┘                            │
    │                                              │
    ▼                                              │
UCO_FINAL_COMP.xml/ttl ←───────────────────────────┘
    │
    ▼
┌─────────────────────┐
│  main_tag.py        │ → UCO_INFERRED.ttl
│  (Step 6 - Reasoning│   LOG_VALIDAZIONE.txt
│   & Validation)     │   RISULTATI_QUERY_CQ.txt
└─────────────────────┘
```

## Module Descriptions

### Step 1: Co-occurrence Matrix Generation (`cooccorrenze.py`)
- **Input**: `Cyber_Events_Database.xlsx`
- **Output**: `matrice_cooccorrenze.xlsx`
- **Purpose**: Extracts term co-occurrences from event descriptions using NLP preprocessing (tokenization, stopword removal, lemmatization). Identifies top 1000 frequent terms and builds a symmetric co-occurrence matrix.

### Step 2: Co-occurrence Classification (`cooccorrenzeclassifier.py`)
- **Input**: `matrice_cooccorrenze.xlsx`
- **Output**: `classifica_cooccorrenze.xlsx`
- **Purpose**: Filters co-occurrences above a threshold (100) and produces a ranked list of term pairs for semantic mapping.

### Step 3: Semantic Mapping (`findcouples.py`)
- **Input**: `classifica_cooccorrenze.xlsx`, `uco_1_5.ttl`
- **Output**: `ontologyadd.xlsx`
- **Purpose**: Uses sentence-transformers (all-distilroberta-v1) to compute semantic similarity between extracted term pairs and existing ontology classes. Maps candidates to parent classes with similarity ≥ 0.45.

### Step 4: TBox Enrichment (`addentities.py`)
- **Input**: `uco_1_5.ttl`, `ontologyadd.xlsx`
- **Output**: `uco_1_5_enriched.ttl`
- **Purpose**: Adds new classes to the ontology as subclasses of mapped parent classes using RDFLib.

### Step 5: ABox Injection (`kbonto.py`)
- **Input**: `uco_1_5_enriched.ttl`, `Cyber_Events_Database.xlsx`
- **Output**: `UCO_FINAL_COMP.xml`, `UCO_FINAL_COMP.ttl`
- **Purpose**: Injects individuals from the database into the ontology using semantic matching (sentence-transformers all-mpnet-base-v2). Creates instances, assigns types, and populates object/datatype properties based on column semantics.

### Step 6: Reasoning & Validation (`main_tag.py`)
- **Input**: `UCO_FINAL_COMP.xml`
- **Output**: `UCO_INFERRED.ttl`, `LOG_VALIDAZIONE.txt`, `RISULTATI_QUERY_CQ.txt`
- **Purpose**: Runs Pellet reasoner for consistency checking and inference, performs structural validation, executes competency questions (SPARQL), and generates metrics reports.

## Requirements

### Python Dependencies
Install via `pip install -r requirements.txt`:
```
rdflib>=6.3.0
owlready2>=0.44
pandas>=2.0.0
torch>=2.0.0
transformers>=4.30.0
spacy>=3.5.0
scikit-learn>=1.3.0
tqdm>=4.65.0
sentence-transformers>=2.2.0
openpyxl>=3.1.0
```

### External Tools
- **Java 8+**: Required for Pellet reasoner
- **NLTK Data**: 
  ```python
  import nltk
  nltk.download('stopwords')
  nltk.download('wordnet')
  nltk.download('omw-1.4')
  nltk.download('punkt')
  ```
- **spaCy Model**:
  ```bash
  python -m spacy download en_core_web_sm
  ```

## Execution

### Full Pipeline
```bash
python main.py
```
Runs the complete pipeline from co-occurrence extraction to final validation.

### Reasoning & Validation Only
```bash
python main_tag.py
```
Executes only the reasoning and validation steps on existing `UCO_FINAL_COMP.xml`.

## Input/Output Files

| File | Type | Description |
|------|------|-------------|
| `Cyber_Events_Database.xlsx` | Input | Source database of cyber events |
| `uco_1_5.ttl` | Input | Base cybersecurity ontology |
| `matrice_cooccorrenze.xlsx` | Intermediate | Term co-occurrence matrix |
| `classifica_cooccorrenze.xlsx` | Intermediate | Ranked term pairs |
| `ontologyadd.xlsx` | Intermediate | Semantic mappings |
| `uco_1_5_enriched.ttl` | Intermediate | TBox-enriched ontology |
| `UCO_FINAL_COMP.xml/ttl` | Output | Final ontology with ABox |
| `UCO_INFERRED.ttl` | Output | Inferred knowledge base |
| `LOG_VALIDAZIONE.txt` | Output | Validation report with metrics |
| `RISULTATI_QUERY_CQ.txt` | Output | Competency question results |

## Metrics & Evaluation

The pipeline computes the following metrics:

| Metric | Description |
|--------|-------------|
| **Expansion Coefficient** | Percentage increase in triples after inference |
| **Relational Density** | Average connections per individual |
| **Semantic Richness** | Ratio of properties to classes |
| **Hierarchical Depth** | Maximum subclass depth |
| **Connectivity Ratio** | Ratio of individuals to classes |

## Competency Questions

The pipeline includes 20+ SPARQL queries organized by type:

### Descriptive Queries (CQ1-CQ7)
Extract basic information about incidents, actors, dates, and industries.

### Analytical Queries (CQ8-CQ15)
Perform aggregations, temporal analysis, and correlation studies.

### Structural Queries (CQ16-CQ20+)
Validate ontology structure, detect empty classes, and analyze property chains.

## Design Choices

### Thresholds
- **Co-occurrence threshold (100)**: Filters statistical noise while retaining meaningful relationships
- **Semantic similarity (0.45)**: Balances precision and recall in class mapping
- **Top-N terms (1000)**: Ensures computational efficiency without losing coverage

### Models
- **all-distilroberta-v1**: Fast encoding for initial term mapping
- **all-mpnet-base-v2**: Higher quality embeddings for instance injection

### Reasoner
- **Pellet**: Chosen for OWL 2 DL completeness and property value inference

## Known Issues
- Datatype restrictions on date properties must be removed manually before reasoning
- Java path may need configuration in `main.py` for Pellet integration

## References

1. Wisniewski, D., et al. "Competency Questions and SPARQL-OWL Queries Dataset and Analysis." *arXiv:1811.09529* (2018).
2. Gangemi, A., et al. "Automatically Drafting Ontologies from Competency Questions with FrODO." *ISTC-CNR*.

## License
[Specify license if applicable]

## Contact
[Specify contact information if applicable]
