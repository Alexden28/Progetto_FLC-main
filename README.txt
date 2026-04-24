C.E.D.xlsx --> cooccorrenze.py --> matrice_cooccorrenze.xlsx --> cooccorrenzeclassifier.py --> classifica_cooccorrenze --> findcouples.py--
--> uco_1_5.ttl(ttl viene letto meglio di owl) + ontologyadd.xlsx --> addentities.py --> uco_1_5_enriched.ttl --> kbonto.py --> UCO_FINAL.ttl

RUNNARE main.py SE PROCESSO COMPLETO, main_tag.py SE SOLO INFERENZA E VALIDAZIONE

ELIMINATI A MANO LIMITI DATATYPE ALLE DATE -- PROBLEMA DI VARIABILE IRRILEVABILE

REASONER : Pellet

QUERY SPARQL DI PROVA: Query_SPARQL_Prova.txt (Utilizzabile plugin integrato per SPARQL Query)

installare dopo requirements:

import nltk
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('punkt')

python -m spacy download en_core_web_sm

CAMBIARE ALL'EVENIENZA PERCORSO JAVA IN MAIN PER PELLET

Il sistema integra il ragionatore logico Pellet per l'analisi di coerenza,
 verificando l'assenza di contraddizioni logiche tra classi e individui dopo l'arricchimento della TBox e della ABox.
L'esecuzione delle Competency Questions tramite query SPARQL funge da test di validazione funzionale, 
accertando che la base di conoscenza sia in grado di rispondere ai requisiti informativi definiti dal dominio. 
L'intera pipeline è automatizzata da `main.py` che coordina sequenzialmente l'installazione delle dipendenze, 
l'elaborazione dei dati, l'inferenza semantica e la generazione della reportistica finale,
 garantendo la portabilità del processo su diverse macchine tramite la gestione dei percorsi relativi.

 Fonti:

 https://arxiv.org/abs/1811.09529  ---  Cornell University

 Competency Questions and SPARQL-OWL Queries Dataset and Analysis
Dawid Wisniewski, Jedrzej Potoniec, Agnieszka Lawrynowicz, C. Maria Keet

Competency Questions (CQs) are natural language questions outlining and constraining the scope of knowledge represented by an ontology. 
Despite that CQs are a part of several ontology engineering methodologies, we have observed that the actual publication of CQs for the available ontologies is very limited
 and even scarcer is the publication of their respective formalisations in terms of, e.g., SPARQL queries. This paper aims to contribute to addressing the engineering 
 shortcomings of using CQs in ontology development, to facilitate wider use of CQs. In order to understand the relation between CQs and the queries over the ontology to test 
 the CQs on an ontology, we gather, analyse, and publicly release a set of 234 CQs and their translations to SPARQL-OWL for several ontologies in different domains developed 
 by different groups. We analysed the CQs in two principal ways. The first stage focused on a linguistic analysis of the natural language text itself, i.e., a lexico-syntactic 
 analysis without any presuppositions of ontology elements, and a subsequent step of semantic analysis in order to find patterns. This increased diversity of CQ sources 
 resulted in a 5-fold increase of hitherto published patterns, to 106 distinct CQ patterns, which have a limited subset of few patterns shared across the CQ sets from the 
 different ontologies. Next, we analysed the relation between the found CQ patterns and the 46 SPARQL-OWL query signatures, which revealed that one CQ pattern may be realised 
by more than one SPARQL-OWL query signature, and vice versa. We hope that our work will contribute to establishing 
common practices, templates, automation, and user tools that will support CQ formulation, formalisation, execution, and general management.

https://iris.cnr.it/retrieve/49c38a25-d0b4-4b32-a350-c390b845b111/prod_470987-doc_191162.pdf  --  ISTC-CNR

Automatically Drafting Ontologies from
Competency Questions with FrODO
Aldo GANGEMI a,b, Anna Sofia LIPPOLIS a, Giorgia LODI a,
Andrea Giovanni NUZZOLESE a,1,2


Analisi delle Metriche

Coefficiente di Espansione: le regole che definite sono o non sono banali. 

Densità Relazionale: Ogni individuo è connesso mediamente a quasi x altri concetti. 

Ricchezza Semantica: varietà di proprietà rispetto al numero di classi.


Diagnosi dei Pitfalls 

Missing Comments [P08]: Le classi che iniziano con N(es. N9f98c0b...) sono nodi anonimi o classi generate automaticamente durante il processo di iniezione o arricchimento.

Missing Domain/Range [P11]: Le proprietà inverse generate automaticamente (come isMACAddress_of) spesso non ereditano i vincoli di dominio. 
Questo spiega perché il validatore le segnala.

Missing Inverse Relations [P13]: Relazioni come resultsIn sono unidirezionali. Se la logica del dominio non prevede un'azione speculare l'avviso è puramente informativo.