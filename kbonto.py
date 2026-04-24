"""Step 5/6 of the enrichment pipeline.

Injects ABox individuals into the enriched TBox. For each row of the cyber
event database we:

1. Pick the best-matching "pillar" class (Attack / Malware / Incident / ...)
   for the description and instantiate one individual per row.
2. Attach up to two additional classes when the description strongly evokes
   them (secondary-class threshold).
3. For every other column, decide whether it maps to an existing object or
   datatype property via cosine similarity against property names; values
   are then coerced to the property range.

The resulting graph is written both as OWL/XML (for the reasoner) and as
Turtle (for inspection), with all IRIs normalised to the canonical namespace.

Input : uco_1_5_enriched.ttl, Cyber_Events_Database.xlsx
Output: UCO_FINAL_COMP.xml, UCO_FINAL_COMP.ttl
"""
import os
import re
from datetime import datetime

import pandas as pd
import rdflib
import torch
from owlready2 import (
    DataPropertyClass,
    ObjectProperty,
    ObjectPropertyClass,
    Thing,
    get_ontology,
    types,
)
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

from config import (
    CYBER_EVENTS_XLSX,
    DATA_PROPERTY_SIMILARITY,
    ENRICHED_TBOX_TTL,
    KBONTO_MODEL,
    OBJECT_PROPERTY_SIMILARITY,
    PROJECT_ROOT,
    SECONDARY_CLASS_SIMILARITY,
    UCO_FINAL_COMP_TTL,
    UCO_FINAL_COMP_XML,
)
from namespace_utils import normalize

_PILLAR_KEYWORDS = (
    "attack", "malware", "incident", "vulnerability", "exploit", "consequence",
)
_SKIP_VALUES = {"undetermined", "unknown", "n/a", "nan"}
_NON_ALNUM = re.compile(r"[^a-zA-Z0-9_]")
_YEAR_RE = re.compile(r"\d{4}")


def clean_iri(text: str) -> str:
    sanitised = _NON_ALNUM.sub("_", str(text)).strip("_")[:40]
    return sanitised or "unknown_entity"


def adapt_value_by_range(val_str: str, prop):
    """Coerce `val_str` to the datatype suggested by `prop.range`."""
    p_range = prop.range
    if int in p_range or any("integer" in str(r).lower() for r in p_range):
        digits = re.sub(r"\D", "", str(val_str))
        return int(digits[:4]) if digits else 0
    if datetime in p_range or any("datetime" in str(r).lower() for r in p_range):
        if _YEAR_RE.fullmatch(str(val_str)):
            return datetime(int(val_str), 1, 1)
        return pd.to_datetime(val_str).to_pydatetime()
    return str(val_str)


def _ensure_domain_and_range(prop) -> None:
    if not prop.domain:
        prop.domain = [Thing]
    if not prop.range:
        prop.range = [str if isinstance(prop, DataPropertyClass) else Thing]


def _ensure_inverse(prop) -> None:
    if not isinstance(prop, ObjectPropertyClass) or prop.inverse_property:
        return
    base = prop.name
    inv_name = f"is_{base}_of" if not base.startswith("has") else base.replace("has", "is") + "_of"
    new_inv = types.new_class(inv_name, (ObjectProperty,))
    new_inv.inverse_property = prop
    if prop.range:
        new_inv.domain = prop.range
    if prop.domain:
        new_inv.range = prop.domain


def _collect_pillar_classes(all_classes):
    pillar_bases = [
        c for c in all_classes if any(k in c.name.lower() for k in _PILLAR_KEYWORDS)
    ]
    pillar_set = set(pillar_bases)
    for base in pillar_bases:
        pillar_set.update(base.descendants())
    return list(pillar_set)


def _pick_target_class(col: str, all_classes):
    lowered = col.lower()
    if "victim" in lowered:
        return next((c for c in all_classes if "Victim" in c.name), Thing)
    if "actor" in lowered or "launched" in lowered:
        return next((c for c in all_classes if "ThreatActor" in c.name), Thing)
    return Thing


def _bridge_ttl_to_xml(ttl_path, xml_path) -> None:
    """owlready2 parses OWL/XML; convert the enriched TTL first."""
    g = rdflib.Graph()
    g.parse(str(ttl_path), format="turtle")
    g.serialize(destination=str(xml_path), format="xml")


def run_validated_injection() -> None:
    bridge_xml = PROJECT_ROOT / "temp_uco_bridge.owl"
    temp_nt = PROJECT_ROOT / "temp_final.nt"

    try:
        _bridge_ttl_to_xml(ENRICHED_TBOX_TTL, bridge_xml)

        model = SentenceTransformer(KBONTO_MODEL)
        onto = get_ontology(str(bridge_xml.resolve())).load()
        df = pd.read_excel(CYBER_EVENTS_XLSX)

        with onto:
            for prop in list(onto.properties()):
                _ensure_domain_and_range(prop)
                _ensure_inverse(prop)

            for cls in onto.classes():
                if not cls.comment:
                    cls.comment.append(
                        f"Formal definition for {cls.name} within the cybersecurity domain."
                    )

            all_classes = list(onto.classes())
            pillar_list = _collect_pillar_classes(all_classes)
            all_props = list(onto.properties())
            obj_props = [p for p in all_props if isinstance(p, ObjectPropertyClass)]
            dat_props = [p for p in all_props if isinstance(p, DataPropertyClass)]
            prop_year = next(
                (p for p in dat_props if "hasyear" in p.name.lower()), None
            )

            pillar_embs = model.encode(
                [c.name for c in pillar_list], convert_to_tensor=True,
            )
            class_embs = model.encode(
                [c.name for c in all_classes], convert_to_tensor=True,
            )
            obj_embs = model.encode(
                [p.name for p in obj_props], convert_to_tensor=True,
            )
            dat_embs = model.encode(
                [p.name for p in dat_props], convert_to_tensor=True,
            )

            for _, row in tqdm(df.iterrows(), total=len(df), desc="ABox injection"):
                description = str(row.get("description", ""))
                desc_emb = model.encode(description, convert_to_tensor=True)

                pillar_sims = util.cos_sim(desc_emb, pillar_embs)[0]
                best_pillar = pillar_list[pillar_sims.argmax().item()]
                main_inst = best_pillar(clean_iri(row["slug"]))

                top_vals, top_idxs = torch.topk(
                    util.cos_sim(desc_emb, class_embs)[0], k=3,
                )
                for score, idx in zip(top_vals, top_idxs):
                    target_cls = all_classes[idx.item()]
                    if score > SECONDARY_CLASS_SIMILARITY and target_cls not in main_inst.is_a:
                        main_inst.is_a.append(target_cls)

                if description and description.lower() != "nan":
                    main_inst.comment.append(description)

                for col, val in row.items():
                    if col in ("slug", "description") or pd.isna(val):
                        continue
                    val_str = str(val).strip()
                    if val_str.lower() in _SKIP_VALUES:
                        continue

                    is_year = bool(_YEAR_RE.fullmatch(val_str))
                    col_emb = model.encode(str(col), convert_to_tensor=True)

                    obj_sims = util.cos_sim(col_emb, obj_embs)[0]
                    if obj_sims.max() > OBJECT_PROPERTY_SIMILARITY:
                        op = obj_props[obj_sims.argmax()]
                        if "hascve_id" not in op.name.lower():
                            target_cls = _pick_target_class(str(col), all_classes)
                            target_node = target_cls(clean_iri(val_str))
                            if not target_node.comment:
                                target_node.comment.append(f"Entity representing {val_str}")
                            relation = getattr(main_inst, op.python_name)
                            if target_node not in relation:
                                relation.append(target_node)

                    dat_sims = util.cos_sim(col_emb, dat_embs)[0]
                    if dat_sims.max() > DATA_PROPERTY_SIMILARITY:
                        dp = dat_props[dat_sims.argmax()]
                        if is_year and prop_year is not None:
                            dp = prop_year
                        if hasattr(main_inst, dp.python_name):
                            final_val = adapt_value_by_range(val_str, dp)
                            prop_attr = getattr(main_inst, dp.python_name)
                            if isinstance(prop_attr, list):
                                if final_val not in prop_attr:
                                    prop_attr.append(final_val)
                            else:
                                setattr(main_inst, dp.python_name, final_val)

        onto.save(file=str(temp_nt), format="ntriples")

        final_graph = rdflib.Graph()
        final_graph.parse(str(temp_nt), format="nt")
        final_graph = normalize(final_graph)

        final_graph.serialize(destination=str(UCO_FINAL_COMP_XML), format="xml")
        final_graph.serialize(destination=str(UCO_FINAL_COMP_TTL), format="turtle")
    finally:
        for path in (temp_nt, bridge_xml):
            if path.exists():
                os.remove(path)


if __name__ == "__main__":
    run_validated_injection()
