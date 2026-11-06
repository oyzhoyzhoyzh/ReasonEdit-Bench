"""Task taxonomy for reasoning-based image editing.

We factor the space along two axes.  ``domain`` captures *what kind of
knowledge* the edit requires, and ``type`` captures the *structural shape of the
required inference*.  Every type ships with (i) a natural-language definition,
(ii) the scene evidence that makes it instantiable, and (iii) the structural
constraints enforced by the schema validator.

The causal part of the annotation follows the structural-causal-model (SCM)
convention of Pearl: nodes are object/attribute variables, edges are causal
relations, and an edit is a ``do``-intervention on one variable.  Descendants of
the intervention must change; non-descendants must be preserved.  This gives the
benchmark an objective, non-pixel-level notion of correctness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskType:
    key: str
    domain: str
    name_en: str
    name_zh: str
    definition: str
    scene_evidence: str
    min_chain: int
    min_effects: int
    min_nodes: int
    guidance: str = ""


DOMAINS = {
    "commonsense": "常识推理",
    "causal": "因果逻辑",
    "multi_step": "多步链式推理",
}

TASK_TYPES: dict[str, TaskType] = {
    # ---------------------------------------------------------- commonsense --
    "physical": TaskType(
        key="physical",
        domain="commonsense",
        name_en="Physical commonsense",
        name_zh="物理常识编辑",
        definition=(
            "The edit must obey physical regularities (gravity, heat transfer, "
            "phase change, light and shadow geometry) rather than merely relabel "
            "an object."
        ),
        scene_evidence="an object whose state is governed by a physical process",
        min_chain=3,
        min_effects=2,
        min_nodes=3,
        guidance=(
            "simulate a physical process (melting, freezing, falling, spilling, "
            "evaporating, shadow formation) and keep the result physically plausible"
        ),
    ),
    "social": TaskType(
        key="social",
        domain="commonsense",
        name_en="Social commonsense",
        name_zh="社会常识编辑",
        definition=(
            "The edit must respect social and cultural regularities, i.e. the "
            "co-occurring cues that make a scene read as a particular social event."
        ),
        scene_evidence="people or event cues that imply a social situation",
        min_chain=3,
        min_effects=3,
        min_nodes=4,
        guidance=(
            "change how the scene reads socially or culturally; at least three "
            "co-occurring cues (people's activity, props, lighting, arrangement) "
            "must change together"
        ),
    ),
    "functional": TaskType(
        key="functional",
        domain="commonsense",
        name_en="Functional commonsense",
        name_zh="功能常识编辑",
        definition=(
            "The edit must respect object affordances and their functional "
            "consequences for the contacting objects."
        ),
        scene_evidence="a container, tool or appliance plus its target object",
        min_chain=3,
        min_effects=2,
        min_nodes=3,
        guidance=(
            "exercise an object's affordance on its target object (fill, pour, "
            "charge, cook, open); the tool and its target must both be updated"
        ),
    ),
    # --------------------------------------------------------------- causal --
    "single": TaskType(
        key="single",
        domain="causal",
        name_en="Single cause, single effect",
        name_zh="单因单果编辑",
        definition=(
            "A single intervention on one variable triggers exactly one dominant "
            "downstream effect besides the intervention itself."
        ),
        scene_evidence="a controllable source (lamp, tap, curtain) with a visible effect",
        min_chain=2,
        min_effects=2,
        min_nodes=3,
        guidance=(
            "one intervention, and exactly one primary downstream variable besides "
            "the intervention itself"
        ),
    ),
    "multi": TaskType(
        key="multi",
        domain="causal",
        name_en="Multi-cause, multi-effect",
        name_zh="多因多果编辑",
        definition=(
            "One intervention propagates to at least two distinct effect variables, "
            "or two interventions jointly produce their effects."
        ),
        scene_evidence="a scene-level driver (weather, light, water) with several dependents",
        min_chain=3,
        min_effects=3,
        min_nodes=4,
        guidance=(
            "a single intervention must propagate to at least two different effect "
            "variables, or two interventions combine into their joint effects"
        ),
    ),
    "counterfactual": TaskType(
        key="counterfactual",
        domain="causal",
        name_en="Counterfactual edit",
        name_zh="反事实编辑",
        definition=(
            "The edit asks what the scene would look like had a realized cause been "
            "absent or different; the dependent variables must be re-derived."
        ),
        scene_evidence="a visible effect whose original cause can be identified",
        min_chain=3,
        min_effects=2,
        min_nodes=3,
        guidance=(
            "phrase the instruction as a counterfactual about a cause that is already "
            "realized in the image (for example 'if the room had never been lit by "
            "that lamp'), and re-derive every dependent variable"
        ),
    ),
    # ----------------------------------------------------------- multi-step --
    "sequential": TaskType(
        key="sequential",
        domain="multi_step",
        name_en="Ordered sequential edit",
        name_zh="顺序操作编辑",
        definition=(
            "Several edits must be executed in a stated order; swapping the order "
            "changes the outcome or makes a later step undefined."
        ),
        scene_evidence="objects that can undergo two dependent transformations",
        min_chain=3,
        min_effects=3,
        min_nodes=3,
        guidance=(
            "put two or more ordered operations joined by 'then' or 'before' into "
            "the instruction, where the later operation depends on the state left "
            "by the earlier one"
        ),
    ),
    "conditional": TaskType(
        key="conditional",
        domain="multi_step",
        name_en="Conditional branch edit",
        name_zh="条件分支编辑",
        definition=(
            "The instruction contains a condition on the observed scene; the model "
            "must read the state first and then apply the matching branch only."
        ),
        scene_evidence="a binary, visually resolvable state (open/closed, on/off, day/night)",
        min_chain=3,
        min_effects=2,
        min_nodes=3,
        guidance=(
            "put an explicit condition about the observed scene into the instruction "
            "('if the curtain is open ... otherwise ...'); only the branch that "
            "matches the image may be applied"
        ),
    ),
    "long_horizon": TaskType(
        key="long_horizon",
        domain="multi_step",
        name_en="Long-horizon dependency edit",
        name_zh="长程依赖编辑",
        definition=(
            "A later edit depends on the state created by an earlier one, separated "
            "by a spatial or semantic jump in the scene."
        ),
        scene_evidence="a relocated object and a second region that receives it",
        min_chain=4,
        min_effects=3,
        min_nodes=4,
        guidance=(
            "use at least four steps, where the final edit consumes the space or "
            "state freed by an earlier one"
        ),
    ),
}
DOMAIN_TYPES = {
    d: [t.key for t in TASK_TYPES.values() if t.domain == d] for d in DOMAINS
}


# --------------------------------------------------------------------------- #
# prompting
# --------------------------------------------------------------------------- #
SCENE_SYSTEM = (
    "You are a meticulous visual annotator. You only report what is visible in the "
    "image and you never invent objects. Answers are strict JSON."
)

SCENE_PROMPT = """Analyse the image and describe its editable scene structure.

Return JSON with exactly these keys:
{
  "caption": "one sentence describing the image",
  "scene_type": "short scene label, e.g. indoor living room / outdoor street / kitchen",
  "time_of_day": "day|night|dusk|dawn|unclear",
  "weather": "clear|cloudy|rain|snow|fog|unclear",
  "lighting": "short phrase, e.g. bright daylight / dim warm indoor light",
  "objects": [
    {
      "name": "concrete noun phrase for one object",
      "bbox": [x1, y1, x2, y2],          // integers 0-1000, relative to image size
      "confidence": 0.0-1.0,
      "attributes": {"colour": "...", "state": "...", "material": "..."},
      "region": "the area of the image the object sits in, e.g. left foreground"
    }
  ],
  "entities": ["names of objects that are central to the scene, at most 6"],
  "relations": ["short spatial or causal relations between the central entities"]
}

Rules:
- list 5-12 objects, ordered by visual salience.
- only include objects you can actually point to; keep bounding boxes tight.
- if a state matters (lamp on/off, door open/closed, cup full/empty), put it in
  attributes.state and make sure it matches what you see.
- do not use the key "state" at the top level.
"""

TASK_SYSTEM = (
    "You design evaluation tasks for instruction-based image editing. You are "
    "rigorous about causality: an edit is described by an intervention on one "
    "variable and the downstream variables that must follow. Answers are strict JSON."
)

# The proposer receives the image, the scene inventory and the taxonomy.
TASK_PROMPT = """You are given an image and its structured scene inventory.

SCENE INVENTORY
{inventory}

Design ONE task for a *reasoning-based image editing* benchmark.  The requested
type is **{type_key}**; every field must serve that type.

{type_spec}

A reasoning-based edit differs from a surface edit: the instruction names only the
intervention, and the correct output is determined by knowledge of the world
(physics, social conventions, object function) or by chained logic. The model has
to infer the remaining effects itself.

Return one JSON object:
{{
  "type": "{type_key}",
  "instruction": "the user instruction, natural and short (max 30 words)",
  "scm": {{
    "nodes": [
      {{"id": "n1", "label": "object or variable name",
        "kind": "object|attribute|event", "region": [x1,y1,x2,y2],
        "state_before": "what it is now"}}
    ],
    "edges": [
      {{"src": "n1", "dst": "n2", "relation": "causes|enables|prevents",
        "mechanism": "why the change propagates"}}
    ],
    "intervention": {{"node": "n1", "variable": "state", "from": "...", "to": "..."}}
  }},
  "reasoning_chain": [
    {{"step": 1, "thought": "one short inference the model must make",
      "region": [x1,y1,x2,y2]}}
  ],
  "effects": [
    {{"id": "e1", "statement": "a consequence that must be visible after the edit",
      "probe": "a single yes/no question that verifies this consequence in the edited image",
      "region": [x1,y1,x2,y2], "ordinal": 1, "is_descendant": true}}
  ],
  "preserved": [
    {{"id": "p1", "statement": "a fact that must remain unchanged",
      "probe": "a single yes/no question that verifies it is unchanged"}}
  ],
  "counterfactual": {{
    "instruction": "a plausible but causally wrong edit of the same image",
    "violated_edge": "n1->n2",
    "reason": "why that edit breaks the causal relation"
  }}
}}

Hard requirements:
- "type" must be the bare key copied exactly from the list above (for example
  "sequential"); never append the domain name in brackets;
- the reasoning chain must be a genuine derivation, not a restatement: give one
  step per inference, and respect the structural minimum of the chosen type;
- the intervention variable must be visibly present in the image;
- every entry of "effects" must be a *descendant* of the intervention node in the
  graph you wrote, and must be checkable by looking at the edited image alone;
- the "probe" must be answerable with yes or no and must not mention the
  instruction (a judge sees only the edited image);
- for sequential or long_horizon tasks set "ordinal" so the required order is
  explicit; for conditional tasks, first state the observed branch in the
  instruction and keep the probes consistent with that branch;
- "preserved" must contain 2-4 facts that a careless edit would plausibly destroy
  (identity of the people, objects in other regions, background layout);
- all regions use integers 0-1000 relative to the image; omit "region" rather
  than guessing wildly.

Add a key "salient_note" holding one short remark on what makes the hardest
effect hard.

BREVITY BUDGET (the reply is truncated if you exceed it, so stay well inside it):
- the reply contains exactly these top-level keys and no others: type, instruction,
  scm, reasoning_chain, effects, preserved, counterfactual, salient_note. Never add
  metadata such as version, licence, notes, test set or model ability;
- at most 6 nodes and 6 edges, labels of at most 5 words;
- exactly 3 or 4 reasoning steps (long_horizon needs 4), each thought of at most
  15 words;
- 2 or 3 effects, each "statement" of at most 12 words and each "probe" of at
  most 15 words;
- 2 or 3 preserved facts, each of at most 12 words;
- instruction of at most 25 words, counterfactual of at most 20 words,
  counterfactual reason of at most 15 words.
Reply with the JSON object and nothing else.

Worked example of the expected depth (type "single"):
  instruction: "Switch off the desk lamp."
  nodes: lamp (on); lamp switch (on); room brightness (bright); wall shadow (sharp)
  edges: lamp switch -> lamp; lamp -> room brightness; lamp -> wall shadow
  intervention: do(lamp switch = off)
  reasoning_chain: 1 the switch is on so the bulb is lit; 2 once the bulb is off the
    room loses its main light source; 3 the shadow cast by the lamp disappears as well
  effects: "the lamp is dark"; "the room is dimmer"; "the wall shadow is gone"
  preserved: "the desk and its objects are unchanged"; "the daylight through the
    window is unchanged"
"""


VALID_KEYS = {
    "type", "instruction", "scm", "reasoning_chain", "effects", "preserved",
    "counterfactual", "salient_note",
}


def type_specs_text(keys: list[str] | None = None) -> str:
    keys = keys or list(TASK_TYPES)
    lines = []
    for k in keys:
        t = TASK_TYPES[k]
        lines.append(
            f"- {t.key} ({t.domain}): {t.definition} Scene requirement: {t.scene_evidence}. "
            f"Structural minimums: >= {t.min_nodes} graph nodes, >= {t.min_chain} reasoning "
            f"steps, >= {t.min_effects} required effects. How to instantiate: {t.guidance}."
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
class ValidationError(ValueError):
    pass


def _bbox_ok(box: Any) -> bool:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return False
    try:
        x1, y1, x2, y2 = (float(v) for v in box)
    except (TypeError, ValueError):
        return False
    return all(0 <= v <= 1000 for v in (x1, y1, x2, y2)) and (x2 - x1) > 5 and (y2 - y1) > 5


def _clip_bbox(box, lo=0.0, hi=1000.0):
    if not box:
        return None
    x1, y1, x2, y2 = (float(v) for v in box)
    x1, x2 = sorted((max(lo, min(hi, x1)), max(lo, min(hi, x2))))
    y1, y2 = sorted((max(lo, min(hi, y1)), max(lo, min(hi, y2))))
    if (x2 - x1) < 8 or (y2 - y1) < 8:
        return None
    return [int(round(v)) for v in (x1, y1, x2, y2)]


def normalize_task(task: dict, image_id: str) -> dict:
    """Normalise a raw proposer output and enforce the structural contract."""
    if not isinstance(task, dict):
        raise ValidationError("task is not an object")
    ttype = re.split(r"[\s(\[{]", str(task.get("type", "")).strip())[0].strip().lower()
    if ttype not in TASK_TYPES:
        raise ValidationError(f"unknown type {ttype!r}")
    spec = TASK_TYPES[ttype]
    instruction = str(task.get("instruction", "")).strip()
    if not (8 <= len(instruction) <= 240):
        raise ValidationError("instruction missing or out of length range")

    scm = task.get("scm") or {}
    nodes = []
    seen = set()
    for n in scm.get("nodes", []) or []:
        nid = str(n.get("id", "")).strip()
        label = str(n.get("label", "")).strip()
        if not nid or not label or nid in seen:
            continue
        seen.add(nid)
        nodes.append({
            "id": nid,
            "label": label,
            "kind": str(n.get("kind", "object")),
            "region": _clip_bbox(n.get("region")),
            "state_before": str(n.get("state_before", "")).strip(),
        })
    if len(nodes) < spec.min_nodes:
        raise ValidationError(f"graph has {len(nodes)} nodes < {spec.min_nodes}")

    edges = []
    for e in scm.get("edges", []) or []:
        src, dst = str(e.get("src", "")).strip(), str(e.get("dst", "")).strip()
        if src in seen and dst in seen and src != dst:
            edges.append({
                "src": src,
                "dst": dst,
                "relation": str(e.get("relation", "causes")),
                "mechanism": str(e.get("mechanism", "")).strip(),
            })
    if not edges:
        raise ValidationError("graph has no valid edges")

    iv = scm.get("intervention") or {}
    iv_node = str(iv.get("node", "")).strip()
    if iv_node not in seen:
        raise ValidationError("intervention node not in graph")
    intervention = {
        "node": iv_node,
        "variable": str(iv.get("variable", "state")),
        "from": str(iv.get("from", "")).strip(),
        "to": str(iv.get("to", "")).strip(),
    }

    # descendants of the intervention (BFS over the directed graph)
    adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        adj[e["src"]].append(e["dst"])
    desc, frontier = set(), [iv_node]
    while frontier:
        cur = frontier.pop()
        for nxt in adj[cur]:
            if nxt not in desc:
                desc.add(nxt)
                frontier.append(nxt)

    chain = []
    for i, s in enumerate(task.get("reasoning_chain", []) or [], start=1):
        thought = str(s.get("thought", "")).strip()
        if not thought:
            continue
        chain.append({"step": i, "thought": thought, "region": _clip_bbox(s.get("region"))})
    if len(chain) < spec.min_chain:
        raise ValidationError(f"chain length {len(chain)} < {spec.min_chain}")

    effects = []
    for i, e in enumerate(task.get("effects", []) or [], start=1):
        probe = str(e.get("probe", "")).strip()
        if not probe:
            continue
        effects.append({
            "id": str(e.get("id") or f"e{i}"),
            "statement": str(e.get("statement", "")).strip(),
            "probe": probe if probe.endswith("?") else probe + "?",
            "region": _clip_bbox(e.get("region")),
            "ordinal": int(e.get("ordinal", i) or i),
            "is_descendant": bool(e.get("is_descendant", True)),
        })
    if len(effects) < spec.min_effects:
        raise ValidationError(f"{len(effects)} effects < {spec.min_effects}")

    preserved = []
    for i, p in enumerate(task.get("preserved", []) or [], start=1):
        probe = str(p.get("probe", "")).strip()
        if not probe:
            continue
        preserved.append({
            "id": str(p.get("id") or f"p{i}"),
            "statement": str(p.get("statement", "")).strip(),
            "probe": probe if probe.endswith("?") else probe + "?",
            "region": _clip_bbox(p.get("region")),
        })
    if len(preserved) < 2:
        raise ValidationError("fewer than 2 preservation probes")

    cf = task.get("counterfactual") or {}
    counterfactual = {
        "instruction": str(cf.get("instruction", "")).strip(),
        "violated_edge": str(cf.get("violated_edge", "")).strip(),
        "reason": str(cf.get("reason", "")).strip(),
    }
    if len(counterfactual["instruction"]) < 8:
        raise ValidationError("counterfactual instruction missing")

    return {
        "id": f"{image_id}_{ttype}",
        "image_id": image_id,
        "domain": spec.domain,
        "type": ttype,
        "instruction": instruction,
        "scm": {"nodes": nodes, "edges": edges, "intervention": intervention},
        "reasoning_chain": chain,
        "effects": effects,
        "preserved": preserved,
        "counterfactual": counterfactual,
        "salient_note": str(task.get("salient_note", "")).strip(),
        "descendants": sorted(desc),
    }


def score_difficulty(item: dict) -> str:
    """Deterministic difficulty label from structural statistics.

    The index is a fixed linear combination of the structural statistics that the
    annotation already carries, so the label can be recomputed without any model.
    """
    nodes = len(item["scm"]["nodes"])
    edges = len(item["scm"]["edges"])
    depth = graph_depth(item)
    chain = len(item["reasoning_chain"])
    effects = len(item["effects"])
    index = (
        0.30 * max(0, nodes - 3)
        + 0.25 * max(0, edges - 3)
        + 0.55 * depth
        + 0.35 * max(0, chain - 2)
        + 0.30 * max(0, effects - 2)
    )
    if index >= 2.4:
        return "hard"
    if index >= 1.5:
        return "medium"
    return "easy"


def graph_depth(item: dict) -> int:
    """Longest directed path length (in edges) from the intervention node."""
    nodes = {n["id"]: n for n in item["scm"]["nodes"]}
    adj: dict[str, list[str]] = {k: [] for k in nodes}
    for e in item["scm"]["edges"]:
        adj[e["src"]].append(e["dst"])
    root = item["scm"]["intervention"]["node"]
    best = 0
    stack = [(root, 0, {root})]
    while stack:
        cur, d, visited = stack.pop()
        best = max(best, d)
        for nxt in adj[cur]:
            if nxt not in visited:
                stack.append((nxt, d + 1, visited | {nxt}))
    return best


def graph_stats(item: dict) -> dict:
    return {
        "num_nodes": len(item["scm"]["nodes"]),
        "num_edges": len(item["scm"]["edges"]),
        "depth": graph_depth(item),
        "chain_length": len(item["reasoning_chain"]),
        "num_effects": len(item["effects"]),
        "num_preserved": len(item["preserved"]),
    }
