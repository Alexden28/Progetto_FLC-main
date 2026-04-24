"""Executes the 20 Competency Questions against the final inferred graph.

Every query is annotated with:

- `intent`: the informational need the CQ captures (what we ask the KB to
  demonstrate);
- `expected`: what a useful answer looks like (so the report can tell apart
  an *executed-but-empty* query from an *informative* one).

After running, each query is classified as:

- `informative`: returned at least `CQ_INFORMATIVE_MIN_ROWS` rows. These are
  further split into `rich` (>= `CQ_RICH_MIN_ROWS`) and `sparse`.
- `executed-but-empty`: the query ran without error but produced 0 rows, so
  it is a valid SPARQL signature that the KB cannot answer today.
- `error`: the query could not be executed (malformed or unsupported).

The final `RISULTATI_QUERY_CQ.txt` contains a summary table, the per-query
verdict with commentary, and a sample of the result set.

Input : UCO_INFERRED.ttl (or any TTL file)
Output: RISULTATI_QUERY_CQ.txt
"""
from dataclasses import dataclass, field
import time
from typing import Callable, Optional

import rdflib

from config import (
    CQ_INFORMATIVE_MIN_ROWS,
    CQ_RESULTS,
    CQ_RICH_MIN_ROWS,
    UCO_INFERRED_TTL,
    UCO_NS_IRI,
)

_PREFIXES = f"""
    PREFIX uco: <{UCO_NS_IRI}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


@dataclass
class CompetencyQuery:
    cq_id: str
    title: str
    intent: str
    expected: str
    sparql: str
    sample_size: int = 20


_QUERIES: list[CompetencyQuery] = [
    CompetencyQuery(
        "CQ1",
        "Estrazione Incidenti-Date-Attori",
        "Per ogni incidente datato, quale tipo di attore risulta associato?",
        "Righe incidente-data con valore di tipoAttore quando noto.",
        """
        SELECT ?incidente ?data ?tipoAttore WHERE {
          ?incidente uco:hasEventDate ?data .
          OPTIONAL { ?incidente uco:hasActorType ?tipoAttore }
        } LIMIT 50
        """,
    ),
    CompetencyQuery(
        "CQ2",
        "Analisi quantitativa per Attore",
        "Qual e' la distribuzione degli incidenti per tipo di attore?",
        "Classifica aggregata tipo-attore -> conteggio.",
        """
        SELECT ?tipoAttore (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasActorType ?tipoAttore .
        } GROUP BY ?tipoAttore ORDER BY DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ3",
        "Correlazione Tipo-Data",
        "Quali tipi di evento sono stati osservati in quali date?",
        "Incrocio incidente-tipo-data.",
        """
        SELECT ?incidente ?tipo ?data WHERE {
          ?incidente uco:hasEventType ?tipo .
          ?incidente uco:hasEventDate ?data .
        } LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ4",
        "Mapping Organizzazione-Industria",
        "Quale settore industriale e' stato colpito per ciascuna organizzazione vittima?",
        "Coppie organizzazione-industria.",
        """
        SELECT ?org ?ind WHERE {
          ?inc uco:hasOrganization ?org .
          ?inc uco:hasIndustry ?ind .
        } LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ5",
        "Classifica Settori per Volume",
        "Quali settori risultano maggiormente bersagliati?",
        "Aggregato industria -> conteggio incidenti, ordinato discendente.",
        """
        SELECT ?industria (COUNT(?incidente) AS ?totale) WHERE {
          ?incidente uco:hasIndustry ?industria .
        } GROUP BY ?industria ORDER BY DESC(?totale)
        """,
    ),
    CompetencyQuery(
        "CQ6",
        "Analisi Temporale post-2020",
        "Quali incidenti sono stati registrati dal 2020 in poi?",
        "Elenco incidente-data filtrato temporalmente.",
        """
        SELECT ?incidente ?data WHERE {
          ?incidente uco:hasEventDate ?data .
          FILTER(?data > "2020-01-01T00:00:00"^^xsd:dateTime)
        } ORDER BY ?data LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ7",
        "Distribuzione Sottotipi per Settore",
        "Quali sottotipi di evento prevalgono in ciascun settore?",
        "Aggregato industria-sottotipo -> conteggio.",
        """
        SELECT ?industria ?sottotipo (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasIndustry ?industria .
          ?inc uco:hasEventSubtype ?sottotipo .
        } GROUP BY ?industria ?sottotipo ORDER BY ?industria DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ8",
        "Evoluzione TBox (Nuove Classi)",
        "Quali nuove classi sono state aggiunte sotto classi padre non standard?",
        "Coppie subclasse-superclasse ristrette al namespace UCO.",
        """
        SELECT ?classe ?super WHERE {
          ?classe rdfs:subClassOf ?super .
          FILTER(isIRI(?classe) && strstarts(str(?classe), "%NS%"))
        } LIMIT 20
        """.replace("%NS%", UCO_NS_IRI),
    ),
    CompetencyQuery(
        "CQ9",
        "Rilevamento Record Incompleti",
        "Quanti incidenti sono privi di organizzazione vittima?",
        "Conteggio unico incidenti con data ma senza organizzazione.",
        """
        SELECT (COUNT(DISTINCT ?inc) AS ?incompleti) WHERE {
          ?inc uco:hasEventDate ?d .
          FILTER NOT EXISTS { ?inc uco:hasOrganization ?o }
        }
        """,
    ),
    CompetencyQuery(
        "CQ10",
        "Validazione Relazioni isType_of",
        "Quali incidenti vengono classificati tramite la relazione inversa isType_of?",
        "Coppie incidente-tipo derivanti dall'inversa generata.",
        """
        SELECT ?incidente ?tipo WHERE {
          ?incidente uco:isType_of ?tipo .
        } LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ11",
        "Trend Mensile degli Attacchi",
        "Come si distribuiscono gli attacchi nei mesi dell'anno?",
        "Aggregato mese -> conteggio.",
        """
        SELECT ?mese (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasMonth ?mese .
        } GROUP BY ?mese ORDER BY ?mese
        """,
    ),
    CompetencyQuery(
        "CQ12",
        "Analisi Geografica degli Incidenti",
        "Da quali paesi provengono gli incidenti?",
        "Aggregato paese -> conteggio, discendente.",
        """
        SELECT ?paese (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasCountry ?paese .
        } GROUP BY ?paese ORDER BY DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ13",
        "Correlazione Attore-Tipo Attacco",
        "Quali tipi di attacco sono preferiti da ciascun tipo di attore?",
        "Aggregato attore-tipo -> conteggio.",
        """
        SELECT ?tipoAttore ?tipoAttacco (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasActorType ?tipoAttore .
          ?inc uco:hasEventType ?tipoAttacco .
        } GROUP BY ?tipoAttore ?tipoAttacco ORDER BY DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ14",
        "Rilevamento Sottoclassi Senza Istanze",
        "Quali classi UCO non hanno ancora individui associati?",
        "Lista classi popolabili ma vuote.",
        """
        SELECT ?classe WHERE {
          ?classe a owl:Class .
          FILTER NOT EXISTS { ?i a ?classe }
          FILTER(isIRI(?classe) && strstarts(str(?classe), "%NS%"))
        }
        """.replace("%NS%", UCO_NS_IRI),
    ),
    CompetencyQuery(
        "CQ15",
        "Analisi delle Motivazioni prevalenti",
        "Quali sottotipi di evento risultano piu' frequenti?",
        "Aggregato sottotipo -> conteggio.",
        """
        SELECT ?sottotipo (COUNT(?inc) AS ?tot) WHERE {
          ?inc uco:hasEventSubtype ?sottotipo .
        } GROUP BY ?sottotipo ORDER BY DESC(?tot)
        """,
    ),
    CompetencyQuery(
        "CQ16",
        "Catena Attore -> Incidente -> Tipo",
        "Come si collegano attore, tipo di attacco e settore bersaglio?",
        "Tuple attore-incidente-tipo-industria.",
        """
        SELECT ?tipoAttore ?incidente ?tipoAttacco ?industria WHERE {
          ?incidente uco:hasActorType ?tipoAttore .
          ?incidente uco:hasEventType ?tipoAttacco .
          ?incidente uco:hasIndustry ?industria .
        } LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ17",
        "Individui con Attributi Multipli",
        "Quali incidenti possiedono almeno quattro attributi letterali distinti?",
        "Incidenti con molti valori datatype -> indicatore di completezza.",
        """
        SELECT ?inc (COUNT(DISTINCT ?p) AS ?nProp) WHERE {
          ?inc uco:hasEventDate ?d .
          ?inc ?p ?v .
          FILTER(isLiteral(?v))
        } GROUP BY ?inc HAVING (?nProp >= 4) ORDER BY DESC(?nProp) LIMIT 20
        """,
    ),
    CompetencyQuery(
        "CQ18",
        "Analisi Behaviour per Settore",
        "Quale comportamento (behaviour) emerge nei diversi settori?",
        "Aggregato industria-behaviour -> conteggio.",
        """
        SELECT ?industria ?beh (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:hasIndustry ?industria .
          ?inc uco:behaviour ?beh .
        } GROUP BY ?industria ?beh ORDER BY ?industria DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ19",
        "Behaviour vs Tipo di attacco",
        "Quali behaviour risultano ricorrenti in quali tipi di attacco?",
        "Aggregato behaviour-tipo -> conteggio.",
        """
        SELECT ?beh ?tipo (COUNT(?inc) AS ?n) WHERE {
          ?inc uco:behaviour ?beh .
          ?inc uco:hasEventType ?tipo .
        } GROUP BY ?beh ?tipo ORDER BY ?beh DESC(?n)
        """,
    ),
    CompetencyQuery(
        "CQ20",
        "Individui per Classe Madre",
        "Come si distribuiscono gli individui tra le superclassi?",
        "Aggregato superclasse -> conteggio individui delle sottoclassi.",
        """
        SELECT ?super (COUNT(?i) AS ?n) WHERE {
          ?i a ?classe .
          ?classe rdfs:subClassOf ?super .
        } GROUP BY ?super ORDER BY DESC(?n) LIMIT 20
        """,
    ),
]


@dataclass
class CQResult:
    query: CompetencyQuery
    status: str  # informative | executed-empty | error
    richness: str  # rich | sparse | none | n/a
    row_count: int
    vars: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    error: Optional[str] = None

    def verdict_line(self) -> str:
        if self.status == "error":
            return f"{self.query.cq_id} ERROR : {self.error}"
        if self.status == "executed-empty":
            return (
                f"{self.query.cq_id} EXECUTED-EMPTY : 0 righe - "
                f"la KB non contiene ancora dati per questo pattern"
            )
        tag = "RICH" if self.richness == "rich" else "SPARSE"
        return (
            f"{self.query.cq_id} INFORMATIVE ({tag}) : {self.row_count} righe"
        )


def _short(value) -> str:
    if value is None:
        return "None"
    s = str(value)
    return s.split("/")[-1].split("#")[-1] if s.startswith("http") else s


def _execute(g: rdflib.Graph, cq: CompetencyQuery) -> CQResult:
    try:
        results = g.query(_PREFIXES + cq.sparql)
    except Exception as exc:  # keep the catch wide: SPARQL errors vary wildly
        return CQResult(cq, "error", "n/a", 0, error=str(exc))

    vars_list = [str(v) for v in results.vars] if results.vars else []
    rows = [[_short(v) for v in row] for row in results]
    count = len(rows)

    if count < CQ_INFORMATIVE_MIN_ROWS:
        return CQResult(cq, "executed-empty", "none", 0, vars=vars_list)

    richness = "rich" if count >= CQ_RICH_MIN_ROWS else "sparse"
    return CQResult(cq, "informative", richness, count, vars=vars_list, rows=rows)


def _write_summary(out, results: list[CQResult]) -> None:
    total = len(results)
    informative = [r for r in results if r.status == "informative"]
    rich = [r for r in informative if r.richness == "rich"]
    empty = [r for r in results if r.status == "executed-empty"]
    errors = [r for r in results if r.status == "error"]

    out.write("SOMMARIO\n")
    out.write(f"Totale CQ eseguite      : {total}\n")
    out.write(f"Informative (>=1 riga)  : {len(informative)}  "
              f"(rich >= {CQ_RICH_MIN_ROWS}: {len(rich)})\n")
    out.write(f"Eseguite ma vuote       : {len(empty)}\n")
    out.write(f"Errore di esecuzione    : {len(errors)}\n")
    out.write("\nVERDETTO PER QUERY\n")
    for r in results:
        out.write(f"  {r.verdict_line()}\n")
    out.write("\n")


def run_competency_queries(
    onto_path=UCO_INFERRED_TTL,
    output_file=CQ_RESULTS,
    queries: Optional[list[CompetencyQuery]] = None,
    parse_format: str = "turtle",
    progress: Optional[Callable[[str], None]] = None,
) -> list[CQResult]:
    g = rdflib.Graph()
    g.parse(str(onto_path), format=parse_format)

    queries = queries or _QUERIES
    results: list[CQResult] = []
    for cq in queries:
        if progress:
            progress(cq.cq_id)
        results.append(_execute(g, cq))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("COMPETENCY QUESTIONS REPORT\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source graph: {onto_path}\n\n")

        _write_summary(f, results)

        for r in results:
            f.write(f"QUERY {r.query.cq_id}: {r.query.title}\n")
            f.write(f"Intento   : {r.query.intent}\n")
            f.write(f"Atteso    : {r.query.expected}\n")
            f.write(f"Stato     : {r.verdict_line()}\n")

            if r.status == "error":
                f.write(f"Errore    : {r.error}\n")
            elif r.status == "executed-empty":
                f.write("Commento  : la query ha un pattern valido ma non trova "
                        "istanze nella KB corrente. Potenziali cause: classi "
                        "ancora senza istanze oppure proprieta' mai popolata.\n")
            else:
                f.write(f"Commento  : {r.query.intent} - la KB risponde con "
                        f"{r.row_count} righe, classificate come '{r.richness}'.\n")
                if r.vars:
                    f.write("Campi     : " + " | ".join(r.vars) + "\n")
                for row in r.rows[: r.query.sample_size]:
                    f.write("  - " + " | ".join(row) + "\n")
                if r.row_count > r.query.sample_size:
                    f.write(f"  ... (+{r.row_count - r.query.sample_size} righe)\n")

            f.write("\n" + "-" * 60 + "\n\n")

    return results


if __name__ == "__main__":
    run_competency_queries()
