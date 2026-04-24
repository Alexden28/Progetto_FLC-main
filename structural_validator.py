"""OOPS!-inspired structural checks over the final ontology.

Flags three families of issues:
- [P08] classes, individuals or properties without rdfs:comment
- [P11] object properties without explicit rdfs:domain / rdfs:range
- [P13] object properties without an inverse (warning only)

The function returns a plain list of strings, so the caller decides whether
to print, log, or pipe them into a report.
"""
from pathlib import Path

import rdflib
from rdflib import OWL, RDF, RDFS


def _short_name(uri) -> str:
    return str(uri).split("/")[-1].split("#")[-1]


def _parse(file_path: Path) -> rdflib.Graph:
    g = rdflib.Graph()
    ext = file_path.suffix.lower()
    fmt = "xml" if ext in (".xml", ".owl") else "turtle"
    g.parse(str(file_path), format=fmt)
    return g


def run_structural_check(file_path) -> list[str]:
    g = _parse(Path(file_path))
    issues: list[str] = []

    for cls in g.subjects(RDF.type, OWL.Class):
        if not list(g.objects(cls, RDFS.comment)):
            issues.append(f"[P08] Missing comment for Class: {_short_name(cls)}")

    seen = set()
    for s in g.subjects(RDF.type, None):
        if s in seen:
            continue
        seen.add(s)
        is_class = (s, RDF.type, OWL.Class) in g
        is_obj_prop = (s, RDF.type, OWL.ObjectProperty) in g
        if is_class or is_obj_prop:
            continue
        if not list(g.objects(s, RDFS.comment)):
            issues.append(
                f"[P08] Missing comment for Individual/Property: {_short_name(s)}"
            )

    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        name = _short_name(prop)
        if not list(g.objects(prop, RDFS.domain)):
            issues.append(f"[P11] Missing Domain for Property: {name}")
        if not list(g.objects(prop, RDFS.range)):
            issues.append(f"[P11] Missing Range for Property: {name}")
        if not list(g.objects(prop, OWL.inverseOf)):
            issues.append(f"[P13-Warning] No inverse relation for: {name}")

    return issues


if __name__ == "__main__":
    from config import UCO_FINAL_COMP_TTL, UCO_FINAL_COMP_XML

    candidate = UCO_FINAL_COMP_XML if UCO_FINAL_COMP_XML.exists() else UCO_FINAL_COMP_TTL
    if candidate.exists():
        for issue in run_structural_check(candidate):
            print(issue)
