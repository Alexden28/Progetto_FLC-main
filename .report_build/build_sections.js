/**
 * Generate the four user-requested report sections:
 *   - Abstract (1 page)
 *   - Introduction (2 pages)
 *   - Objectives (2-3 pages)
 *   - Dataset (1 page)
 *
 * Reflects the current code state (subprocess + OntologyEnricher class,
 * 35 CQs grouped by type, dual hash/slash prefixes, 332 classes,
 * 28 512 individuals, 197 404 inferred triples = 62.46 % expansion).
 */

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak,
} = require('docx');

const FONT = 'Arial';

const para = (text, opts = {}) => new Paragraph({
  spacing: { after: 120, line: 300 },
  alignment: opts.center ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
  children: [new TextRun({ text, font: FONT, size: 22, ...(opts.run || {}) })],
});

const T = (text, opts = {}) => new TextRun({ text, font: FONT, size: 22, ...opts });

const pRich = (runs) => new Paragraph({
  spacing: { after: 120, line: 300 },
  alignment: AlignmentType.JUSTIFIED,
  children: runs,
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  pageBreakBefore: true,
  spacing: { before: 0, after: 240 },
  children: [new TextRun({ text, bold: true, font: FONT, size: 36, color: '1F3864' })],
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 240, after: 120 },
  children: [new TextRun({ text, bold: true, font: FONT, size: 26, color: '2E75B6' })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: 'bullets', level: 0 },
  spacing: { after: 60, line: 280 },
  children: [new TextRun({ text, font: FONT, size: 22 })],
});

const numbered = (text) => new Paragraph({
  numbering: { reference: 'numbers', level: 0 },
  spacing: { after: 60, line: 280 },
  children: [new TextRun({ text, font: FONT, size: 22 })],
});

const cell = (text, opts = {}) => {
  const border = { style: BorderStyle.SINGLE, size: 4, color: '888888' };
  return new TableCell({
    borders: { top: border, bottom: border, left: border, right: border },
    width: { size: opts.width || 4680, type: WidthType.DXA },
    shading: opts.shaded ? { fill: 'D5E8F0', type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: VerticalAlign.TOP,
    children: [new Paragraph({
      children: [new TextRun({
        text, font: FONT, size: 20, bold: !!opts.bold,
      })],
    })],
  });
};

const table = (rows, columnWidths) => {
  const total = columnWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths,
    rows: rows.map((row, i) => new TableRow({
      tableHeader: i === 0,
      children: row.map((text, c) => cell(text, {
        width: columnWidths[c],
        bold: i === 0,
        shaded: i === 0,
      })),
    })),
  });
};

// ========================== ABSTRACT =========================================
const abstract = [
  h1('Abstract'),
  para('This project develops an end-to-end pipeline that constructs a domain-specific knowledge graph (KG) of cybersecurity events on top of the Unified Cybersecurity Ontology (UCO 1.5). A knowledge graph is structured along two complementary layers: the TBox, which contains the terminological knowledge — the classes, the properties and the axioms that constrain them — and acts as the schema of the ontology, and the ABox, which contains the assertional knowledge — the individual entities and the relationships that hold among them — and acts as the populated content. The system processes a curated dataset of 14 847 incident records and an OWL/RDF baseline ontology of 122 classes and 119 properties, augmenting the canonical TBox with concepts surfaced from the data and populating the corresponding ABox with one named individual per record. The seven-stage pipeline combines deterministic text-mining (token-level co-occurrence analysis with NLTK lemmatisation and stop-word removal in Stage 1, complemented by spaCy part-of-speech filtering in the semantic-mapping stage) and modern neural representations (sentence-transformer embeddings from the all-distilroberta-v1 and all-mpnet-base-v2 models) to identify candidate TBox extensions and to drive the value-to-property mapping in the ABox-injection stage. Once the populated graph is finalised, the Pellet OWL-DL reasoner is invoked through the owlready2 library to materialise the inferred triples and to certify the logical consistency of the result.'),
  para('The final pipeline run produced a knowledge graph composed of 332 classes, 28 512 named individuals and 174 properties (113 object properties and 61 datatype properties). Pellet declared the ontology Consistent and added 197 404 inferred triples to the 316 031 asserted ones, yielding an inferential expansion of 62.46 % and an increase in the maximum subclass-chain depth from eleven to twelve levels. Validation along three orthogonal axes — structural (OOPS!-style pitfall scan), semantic (35 SPARQL competency questions organised in four categories) and quantitative (per-metric pre/post-inference comparison) — completed the workflow with 29 of the 35 competency questions returning informative results (82.9 % coverage) and 158 structural issues catalogued, predominantly missing rdfs:comment annotations on machine-generated entities. End-to-end execution took 919 seconds (approximately fifteen minutes) on a consumer laptop equipped with an NVIDIA RTX 5070 GPU and the Eclipse Temurin 25 Java runtime. The artifacts produced — enriched TBox, populated and inferred graphs in both Turtle and OWL/XML, competency-question results, structural-issue catalogue and the comprehensive validation report — together constitute a reproducible cybersecurity KG and a quantitative basis for downstream analytical work.'),
];

// ========================== INTRODUCTION =====================================
const introduction = [
  h1('Introduction'),
  para('Cybersecurity is a knowledge-intensive discipline whose practitioners spend a substantial fraction of their time integrating heterogeneous information about threats, vulnerabilities, attack patterns, defensive posture and historical incidents. The information itself is fragmented across dozens of mutually incompatible formats: vendor advisories, threat-intelligence feeds, government bulletins, academic case studies, news articles and post-incident reports. Even when the same concept is described in two sources — a "ransomware attack" in one and an "encryption-based extortion incident" in another — the textual surface forms can differ enough that a naive concatenation of sources produces duplicates, dangling references and unjoinable records. This fragmentation is not merely an aesthetic problem: it impedes basic cross-cutting questions ("how many incidents in the last quarter affected the financial sector via phishing?"), forces analysts to write bespoke ETL code for every new data source, and prevents quantitative trend studies whose value scales with the size of the unified corpus.'),
  para('Knowledge graphs (KGs) and ontologies offer a principled remedy. A KG materialises every entity (an attack, a threat actor, a victim, a vulnerability) as a uniquely-identified node and every relationship between entities (committedBy, affectedSector, exploitsCVE, hasYear) as a typed edge. The vocabulary used to type these nodes and edges is fixed by an ontology, that is, a formal description of the domain expressed in the W3C Web Ontology Language (OWL) and serialised as RDF. The ontology itself is stratified into a TBox (terminological knowledge: classes, properties and the axioms that constrain them) and an ABox (assertional knowledge: the individual entities and the relationships that hold among them). Once data has been mapped onto this scheme, it gains three properties that the original tabular form lacked: a shared vocabulary that allows multiple sources to be merged without lossy renaming, formal semantics that allow a description-logic reasoner to derive implicit facts from those that have been asserted, and a uniform query interface (SPARQL) that exposes the whole graph to downstream consumers regardless of how the data was originally collected.'),
  para('In the cybersecurity domain specifically, the Unified Cybersecurity Ontology (UCO) was proposed by Z. Syed and colleagues at UMBC as a unification of several pre-existing schemas — STIX, CYBOX, CAPEC, CVE and the Diamond Model — into a single OWL ontology that anchors the principal concepts of the field (Attack, ThreatActor, Vulnerability, Exploit, Indicator, Malware, Means, Consequence) and the hundreds of object and datatype properties that connect them. UCO is the de-facto reference TBox for academic and industrial KG work in cybersecurity, and its 1.5 release is the version adopted as the baseline of the present project.'),
  para('A baseline TBox, however, is necessary but not sufficient. Real datasets exhibit terminology, granularity and relations that the canonical TBox has not anticipated: a particular tabular source may distinguish "actor" from "actor-type" with a finer granularity than UCO captures; a column may carry a free-text description whose semantic content cannot be exhausted by any single class subscription; values intended for the same property may be expressed in dozens of different surface forms that no static schema can pre-enumerate. Consequently, every realistic KG-construction pipeline must perform two orthogonal augmentations. The first is TBox enrichment: the discovery of new classes and relations that the dataset evidences but that the baseline does not yet name, followed by their formal addition to the schema with appropriate parent classes and domain/range annotations. The second is ABox population: the row-by-row mapping of the source dataset into the enriched TBox, with a value-to-property assignment that resolves the heterogeneity of natural-language column entries into the canonical vocabulary.'),
  para('The present project addresses both augmentations. Starting from the Cyber Events Database — a single-sheet workbook of 14 847 cyber-security incident records covering events from 2014 to 2025 across all major incident categories — and from the UCO 1.5 baseline TBox, the project implements a seven-stage Python pipeline that (i) extracts term co-occurrence statistics from the descriptive columns of the dataset, (ii) ranks the resulting candidate term pairs, (iii) maps the high-frequency pairs onto the UCO class hierarchy through DistilRoBERTa-based semantic similarity, (iv) extends the TBox with the proposed new classes and relations, (v) injects one main individual per dataset row into the ABox using MPNet-based per-cell mapping, (vi) runs the Pellet OWL-DL reasoner to materialise inferred triples and certify consistency, and (vii) validates the final graph along structural, semantic and quantitative axes. The deliverables include a populated knowledge graph in both Turtle and OWL/XML, an inferred-triples graph, a battery of 35 SPARQL competency questions executed against the inferred graph, a catalogue of structural pitfalls identified by an OOPS!-style scanner, and a comprehensive validation report that summarises every quantitative descriptor of interest.'),
  para('The remainder of this report describes the project in detail. The next section enumerates the objectives that drove the design, motivates each one against the cybersecurity-KG literature, and indicates the metrics by which their fulfilment will be assessed. Subsequent sections cover the chosen dataset, the pipeline architecture and the implementation choices for each stage, the validation methodology and the experimental results. The final sections discuss the limitations of the present implementation and outline avenues for future work.'),
];

// ========================== OBJECTIVES =======================================
const objectives = [
  h1('Objectives'),

  para('The project is framed by six concrete objectives, each of which corresponds to a measurable outcome and is supported by a specific set of pipeline modules. The objectives are listed below in the order in which they appear in the execution flow; each is followed by its motivation and by the success criteria adopted in the validation phase.'),

  h2('Objective 1 — Construct a domain-specific knowledge graph anchored in UCO'),
  para('The primary deliverable of the project is a knowledge graph of cyber-security incidents whose vocabulary is fully grounded in the UCO 1.5 ontology. Every named individual in the ABox must be typed as an instance of at least one UCO class, and every property assertion must use a property declared in the (possibly enriched) TBox. The choice of UCO as the backbone, rather than a bespoke schema, is driven by three considerations: UCO is actively maintained by a recognised academic group; it already integrates the principal cybersecurity meta-models (STIX, CYBOX, CAPEC, CVE, Diamond Model) so that the resulting KG is interoperable with adjacent ecosystems; and it is licensed for free academic use. The success criterion for this objective is that the final graph load without error into both rdflib and a standard OWL editor (Protégé) and that every individual carry at least one UCO-typed assertion.'),

  h2('Objective 2 — Discover dataset-specific concepts not present in the baseline TBox'),
  para('Off-the-shelf ontologies inevitably leave a residue of dataset-specific concepts unmodelled. The second objective is therefore to detect, in a principled way, the new classes and relations that the dataset evidences but that UCO 1.5 has not yet named. The chosen technique is two-stage: a frequency filter based on token-level co-occurrence statistics — preceded by NLTK preprocessing (lower-casing, stop-word removal, lemmatisation) over the descriptive columns of the dataset — surfaces the candidate term pairs, while a semantic filter based on DistilRoBERTa embeddings, complemented by spaCy part-of-speech validation that discards malformed candidates, retains only the pairs that map well to a UCO class with cosine similarity above 0.45. The motivation for the two-stage architecture is empirical efficiency: the embedding stage is more expensive than the frequency stage, so it is appropriate to apply it only to the pre-filtered candidate pool. The motivation for using sentence-transformer embeddings rather than simple bag-of-words similarity is the ability to resolve semantic relationships across morphological variants — for example, treating a phrase such as "credential stuffing" as related to a UCO class such as CredentialAttack even when no token is shared — a property that lexical-overlap measures cannot achieve. The success criterion for this objective is that at least 30 new classes be introduced into the enriched TBox, each with a human-readable label and a parent class chosen from the UCO hierarchy.'),

  h2('Objective 3 — Enrich the TBox with new classes and relations'),
  para('Once the candidate TBox extensions are identified, they must be applied to the baseline ontology in a syntactically correct and semantically conservative way. "Syntactically correct" means that every new owl:Class declaration carries a valid IRI in the canonical UCO namespace, an rdfs:label, an rdfs:comment derived from the originating term pair, and a single rdfs:subClassOf edge to an existing parent. "Semantically conservative" means that the enrichment must not invalidate the existing axioms of UCO 1.5 — in particular, no new disjointness axiom should be added without explicit motivation, and no domain or range constraint should be tightened in a way that would invalidate existing assertions. The pipeline module responsible for this objective is addentities.enrich_tbox_rdflib; it produces uco_1_5_enriched.ttl as the output of the fourth stage. The success criterion is that the enriched TBox parse cleanly through both rdflib and owlready2 and that the structural validator report no new pitfall categories beyond those already present in the baseline.'),

  h2('Objective 4 — Inject the dataset into the enriched ontology as a populated ABox'),
  para('The fourth and most quantitatively demanding objective is to populate the enriched ontology with one named individual per dataset row, accompanied by the appropriate object-property and datatype-property assertions. The mapping from row to individual is driven by sentence-transformer embeddings of the larger MPNet model: each row\'s description is embedded once and matched against every UCO class to identify the principal "pillar" type (Attack, Malware, Incident, Vulnerability, Exploit, Consequence and their sub-classes). The same embedding is then matched against the full class set to identify up to two secondary class subscriptions whose similarity exceeds a confidence threshold of 0.60. For every other column in the dataset, the column header is embedded and compared against the embeddings of every property name; the highest-scoring object property above the threshold of 0.30 receives the value as a relational target, and the highest-scoring datatype property above the threshold of 0.25 receives the value coerced to its declared range (integer for digits-only strings, datetime for date-shaped strings, plain string otherwise). The success criterion is that the populated graph contain exactly 14 847 main individuals (one per dataset row) and at least one property assertion for each, and that the resulting Turtle and OWL/XML serialisations be syntactically valid.'),

  h2('Objective 5 — Apply OWL-DL reasoning for consistency and inference materialisation'),
  para('The fifth objective is the one that most distinguishes a knowledge graph from a plain triplestore: applying a description-logic reasoner to certify the logical consistency of the populated graph and to materialise the implicit triples that follow from the asserted ones. The reasoner adopted is Pellet, integrated into the pipeline through the sync_reasoner_pellet function exposed by the owlready2 library, which launches Pellet as a Java sub-process, feeds it the ontology in OWL/XML and reads back the inferred world. Two outcomes are tracked: (i) the verdict — Consistent if no contradiction is detected, Inconsistent if Pellet identifies a logical clash and reports the implicated axioms, Error if the reasoner crashes for non-semantic reasons such as a JVM mismatch; (ii) the inferential growth — the number of triples in the inferred graph minus the number of asserted triples, expressed as both an absolute count and a percentage. The success criterion is a verdict of Consistent and an inferential growth of at least 30 % over the asserted base. A growth meaningfully above this floor would indicate that the ontology is logically rich (i.e. that its axioms enable the reasoner to derive substantive new knowledge), while a growth meaningfully below it would indicate that the ABox-injection stage produced primarily flat literal assertions with little inferential potential.'),

  h2('Objective 6 — Validate the resulting graph along structural, semantic and quantitative axes'),
  para('The final objective is a three-pronged validation of the constructed KG. The structural axis applies an OOPS!-style pitfall scanner to the post-injection graph, flagging three canonical issue categories implemented in structural_validator.py: missing rdfs:comment annotations on classes, individuals and properties (code P08), missing rdfs:domain or rdfs:range declarations on object properties (code P11), and missing inverse-property declarations on object properties (code P13-Warning). The catalogue informs the engineering quality of the graph but does not influence its semantics. The semantic axis executes a battery of 35 SPARQL competency questions organised in four categories — Descriptive (extraction of facts from the asserted graph), Analytical (aggregations and group-by computations), Structural (queries over the class and property hierarchy itself) and Comparative (queries that contrast results before and after reasoning) — against the inferred graph. Each query returns either an empty result set (executed but uninformative) or a non-empty one (executed and informative); the aggregate coverage ratio is the principal quantitative summary of semantic adequacy. The quantitative axis computes a fixed list of structural descriptors over the asserted and inferred graphs (total triples, classes, individuals, properties, relational density, connectivity ratio, semantic richness, hierarchical depth) and reports them in a side-by-side comparison. The success criteria are: (i) at least 80 % coverage on the competency questions, (ii) a non-empty pitfall catalogue that documents the engineering-quality residue rather than indicating a structural failure, and (iii) a quantitative descriptor table whose growth columns match the inferential-growth value reported by the reasoning stage.'),
];

// ========================== DATASET ==========================================
const dataset = [
  h1('Dataset'),
  para('The dataset adopted as the source of ABox individuals is the Cyber Events Database, distributed as Cyber_Events_Database.xlsx. It is a single-sheet Microsoft Excel workbook of 14 847 records, each of which describes one publicly-disclosed cyber-security incident. The dataset covers events between 2014 and 2025 — roughly the last decade of public cyber-incident reporting — with sixteen columns per record. Each record carries a unique short slug, a free-text description of the incident, structured metadata about the threat actor and the victim, and several temporal and geographical attributes. The full schema, with the role each column plays in the pipeline, is summarised below.'),

  table([
    ['Column', 'Description', 'Pipeline use'],
    ['slug', 'Short, unique identifier of the event', 'Becomes the local IRI of the main individual'],
    ['event_date', 'Calendar date of the event (mixed formats)', 'Mapped to a datetime datatype property'],
    ['year', 'Year of the event (four-digit integer)', 'Routed directly to hasYear by the regex shortcut'],
    ['month', 'Month of the event (one-to-twelve integer)', 'Datatype assertion'],
    ['actor', 'Threat-actor name or alias', 'Mapped to a ThreatActor individual via hasActor'],
    ['actor_type', 'Threat-actor category (state, criminal, hacktivist, …)', 'Datatype assertion or class subscription'],
    ['actor_country', 'Country of origin of the threat actor', 'Mapped to a Country individual'],
    ['organization', 'Affected organisation', 'Mapped to a Victim individual'],
    ['industry', 'Industry sector of the victim', 'Datatype assertion'],
    ['country', 'Country of the victim', 'Mapped to a Country individual'],
    ['state, county', 'Sub-national location (where available)', 'Datatype assertion'],
    ['motive', 'Reported motive of the attack', 'Mapped to a Motive sub-class'],
    ['event_type', 'Top-level incident category', 'Mapped to a pillar class via similarity match'],
    ['event_subtype', 'Refinement of event_type', 'Secondary class subscription'],
    ['description', 'Free-text narrative of the incident', 'Embedded with MPNet, drives the pillar selection'],
  ], [2200, 4200, 3000]),

  para('Two characteristics of the dataset materially shape the pipeline design. First, the description column is the only one carrying enough semantic content to disambiguate among the several plausible pillar classes that a single record might evoke (Attack, Incident, Consequence, Exploit). Most of the embedding budget in the ABox-injection stage is therefore spent on description-vs-class similarities. Second, several columns contain free-text values that are textually similar but not identical, so the IRI generator collapses such variants by pruning to alphanumeric characters and truncating to a fixed length. The dataset is otherwise well-curated: all 14 847 records carry a non-empty description, a non-empty event_date and a populated year column, and the year value is consistent with event_date in 14 843 records (99.97 %).'),
];

// =========================== ASSEMBLE ========================================
const allChildren = [
  ...abstract,
  ...introduction,
  ...objectives,
  ...dataset,
];

const doc = new Document({
  creator: 'Claude (anthropic-skills:docx)',
  title: 'Report sections — Abstract, Introduction, Objectives, Dataset',
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: '1F3864' },
        paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: '2E75B6' },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ] },
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 }, // US Letter
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: 'Knowledge Graph Construction from Cyber Event Records', font: FONT, size: 18, italics: true, color: '595959' })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: 'Page ', font: FONT, size: 18, color: '595959' }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: '595959' }),
            new TextRun({ text: ' of ', font: FONT, size: 18, color: '595959' }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 18, color: '595959' }),
          ],
        })],
      }),
    },
    children: allChildren,
  }],
});

const outPath = path.resolve(__dirname, '..', 'Report_Sections_AbstractIntroObjectivesDataset_v3.docx');
Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log('WROTE', outPath, buffer.length, 'bytes');
});
