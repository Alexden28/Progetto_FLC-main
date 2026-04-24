# Progetto FLC — Arricchimento Automatico della UCO

Pipeline end-to-end per estendere l'ontologia **UCO (Unified Cybersecurity Ontology)**
con conoscenza estratta dal *Cyber Events Database*, validarla tramite il
reasoner **Pellet** e interrogarla tramite **Competency Questions SPARQL**.

## Obiettivi

1. **Estrarre concetti** dal corpus `Cyber_Events_Database.xlsx` tramite
   analisi di co-occorrenze e mapping semantico contro la TBox UCO.
2. **Arricchire la TBox** aggiungendo nuove classi sotto-classate alle UCO
   piu' affini.
3. **Iniettare ABox**: per ogni riga del dataset creare un individuo
   collegato alla classe piu' plausibile e popolare le sue proprieta'.
4. **Validare** la KB risultante con Pellet (coerenza logica), controlli
   strutturali (pitfall OOPS!) e 20 Competency Questions SPARQL.
5. **Comparare** KB iniziale e finale per evidenziare l'effettivo
   contributo della pipeline.

## Struttura della Pipeline

```
Cyber_Events_Database.xlsx
        |
        v
 [1] cooccorrenze.py          --> matrice_cooccorrenze.xlsx
        |
        v
 [2] cooccorrenzeclassifier.py --> classifica_cooccorrenze.xlsx
        |
        v                             +-- uco_1_5.ttl (baseline)
 [3] findcouples.py            -------+
        |                             v
        +--> ontologyadd.xlsx   (manualmente curato)
        |
        v
 [4] addentities.py            --> uco_1_5_enriched.ttl
        |
        v
 [5] kbonto.py                 --> UCO_FINAL_COMP.{ttl,xml}
        |
        v
 [6] main.py (reasoning)       --> UCO_FINAL.{ttl,xml}, UCO_INFERRED.ttl
        |
        v
 [7] Report                    --> LOG_VALIDAZIONE.txt,
                                  RISULTATI_QUERY_CQ.txt,
                                  KB_COMPARISON.txt
```

Ogni stage comunica tramite file; i path e le soglie sono definiti in
`config.py`.

## Moduli

| Modulo | Ingresso | Uscita | Ruolo |
| ------ | -------- | ------ | ----- |
| `cooccorrenze.py` | `Cyber_Events_Database.xlsx` | `matrice_cooccorrenze.xlsx` | Tokenizza, lemmatizza, costruisce la matrice dei primi 1000 termini |
| `cooccorrenzeclassifier.py` | matrice | `classifica_cooccorrenze.xlsx` | Ordina le coppie con co-occorrenza > soglia |
| `findcouples.py` | classifica + `uco_1_5.ttl` | `ontologyadd.xlsx` | Mappa ogni coppia alla classe UCO piu' simile (embedding + cosine) |
| `addentities.py` | `ontologyadd.xlsx` + `uco_1_5.ttl` | `uco_1_5_enriched.ttl` | Aggiunge nuove `owl:Class` alla TBox |
| `kbonto.py` | TBox arricchita + dataset | `UCO_FINAL_COMP.{ttl,xml}` | Inietta ABox, coerenza domini/range, genera inverse |
| `main.py` | `UCO_FINAL_COMP.xml` | `UCO_INFERRED.ttl`, `UCO_FINAL.{ttl,xml}`, report | Orchestratore: reasoning, validazione, CQ, confronto KB |
| `main_tag.py` | `UCO_FINAL_COMP.xml` | come sopra | Shortcut: salta l'arricchimento e ri-esegue solo inferenza/validazione |
| `structural_validator.py` | grafo finale | lista di criticita' | Pitfall strutturali (P08, P11, P13) |
| `competecy_questions.py` | `UCO_INFERRED.ttl` | `RISULTATI_QUERY_CQ.txt` | 20 CQ SPARQL con verdetto informative/empty/error |
| `kb_comparison.py` | baseline + finale | `KB_COMPARISON.txt` | Confronto qualitativo tra TBox iniziale e KB finale |
| `namespace_utils.py` | grafo | grafo | Normalizza tutti gli IRI sul namespace UCO canonico |
| `config.py` | — | — | Path, soglie, modelli, namespace |

## Requisiti e Setup

```bash
pip install -r requirements.txt

python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('omw-1.4'); nltk.download('punkt')"
python -m spacy download en_core_web_sm
```

Serve **Java** raggiungibile da `owlready2` per Pellet. Su Windows il
percorso di default e' quello di Oracle Java 8; se Java e' altrove,
modificare `main.setup_java()`.

## Modalita' di Esecuzione

**Pipeline completa** (dalla matrice di co-occorrenze al report finale):

```bash
python main.py
```

**Solo validazione / reasoning** (assume `UCO_FINAL_COMP.xml` gia' prodotto):

```bash
python main_tag.py
```

**Solo confronto KB iniziale vs finale** (richiede i due grafi):

```bash
python kb_comparison.py
```

**Solo CQ sul grafo inferito**:

```bash
python competecy_questions.py
```

## Scelte Progettuali

### Soglie
| Parametro | Valore | Rationale |
| --------- | ------ | --------- |
| `TOP_TOKEN_COUNT` | 1000 | Frontiera fra costo computazionale (matrice 1000x1000) e copertura del corpus |
| `COOCCURRENCE_THRESHOLD` | 100 | Filtra coppie rare che tipicamente sono hapax; mantiene ~1k candidate |
| `SEMANTIC_SIMILARITY_THRESHOLD` | 0.45 | Sopra 0.50 si perdono varianti lessicali; sotto 0.40 entrano falsi positivi |
| `OBJECT_PROPERTY_SIMILARITY` | 0.30 | Le proprieta' di oggetto richiedono piu' evidenza perche' un mismatch collega due individui sbagliati |
| `DATA_PROPERTY_SIMILARITY` | 0.25 | Piu' permissiva: un literal errato e' solo dato orfano |
| `SECONDARY_CLASS_SIMILARITY` | 0.60 | Un individuo puo' appartenere a piu' classi solo con evidenza forte |
| `CQ_RICH_MIN_ROWS` | 5 | Soglia per classificare una CQ come *rich* nel verdetto |

### Modelli
- `sentence-transformers/all-distilroberta-v1` in `findcouples.py`
  (compatto, testi brevi ~5 token per coppia).
- `all-mpnet-base-v2` in `kbonto.py` (piu' forte: descrizioni lunghe, le
  decisioni influenzano la ABox).
- Pellet via `owlready2.sync_reasoner_pellet` per inferenza di proprieta'
  (OWL-DL) con 16 GB di heap Java.

### Namespace RDF
L'ontologia UCO usa `http://ffrdc.ebiquity.umbc.edu/ns/ontology/` (forma
con slash). `owlready2` durante la serializzazione tende ad aggiungere
`#` al fragment, generando IRI nel formato `ontology/#Nome`. Il modulo
`namespace_utils.normalize()` riscrive tutti gli IRI nella forma
canonica definita in `config.UCO_NS_IRI`, cosi' le Competency Questions
non devono piu' fare `UNION` su due prefissi.

### Euristiche ABox
- Scelta del *pillar*: per ogni descrizione si misura la similarita' con
  le classi figlie di `Attack / Malware / Incident / Vulnerability /
  Exploit / Consequence` e si instanzia sotto la piu' vicina.
- Classi secondarie: si aggiungono fino a 2 classi ulteriori quando la
  descrizione supera `SECONDARY_CLASS_SIMILARITY` con esse.
- Target di object property: se il nome di colonna contiene `victim` si
  mappa su `Victim*`, se contiene `actor` o `launched` su `ThreatActor*`.
- Generazione inversa: se una object property manca di `owl:inverseOf`,
  se ne crea una derivata dal nome (`hasX` -> `isX_of`).

## Output

### LOG_VALIDAZIONE.txt
Metriche di crescita inferenziale (coefficiente di espansione, densita'
relazionale, ricchezza semantica), profondita' gerarchica, esito
Pellet, esito CQ (informative/empty/error), elenco pitfall.

### RISULTATI_QUERY_CQ.txt
Per ciascuna delle 20 CQ:
- `intent` (cosa chiede la query)
- `expected` (cosa rappresenta una risposta utile)
- **verdetto**: `INFORMATIVE (rich/sparse)` / `EXECUTED-EMPTY` / `ERROR`
- commento e campione dei risultati

In testa un riepilogo con i conteggi per categoria.

### KB_COMPARISON.txt
Confronto **iniziale vs finale**: triple, classi, individui,
proprieta'. Include campioni commentati di:
- classi nuove (nome, label, classe padre)
- individui nuovi (IRI, classi, commento)
- proprieta' ora popolate che la baseline dichiarava inutilizzate

## Riferimenti

- Wisniewski, Potoniec, Lawrynowicz, Keet — *Competency Questions and
  SPARQL-OWL Queries Dataset and Analysis*.
  [arxiv.org/abs/1811.09529](https://arxiv.org/abs/1811.09529)
- Gangemi, Lippolis, Lodi, Nuzzolese — *Automatically Drafting Ontologies
  from Competency Questions with FrODO*, ISTC-CNR.
