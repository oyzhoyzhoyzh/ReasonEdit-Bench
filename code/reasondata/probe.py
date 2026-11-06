"""Region-grounded causal probing (RGCP).

Whole-image VLM judging is unreliable on editing tasks because a single
plausible-looking region can dominate the verdict.  We therefore verify every
sub-proposition on the *region it is about*: the region is cropped from the
source image and from the edited image, the two crops are placed side by side
with BEFORE / AFTER labels, and the judge answers a single yes-no question.

Three probe families are generated from the annotation:

``tcs``  did the intervention variable itself change as requested?
``dps``  did each descendant effect appear?           (reasoning verification)
``nps``  did each non-descendant fact survive?        (collateral damage)
``qua``  does the result still look like a photograph? (generation quality)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageDraw

from . import config
from .vlm import VLMResponse, extract_json


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #
def region_to_box(region, size, min_side=140, pad=0.12):
    """Convert a 0-1000 relative region into a padded pixel box."""
    w, h = size
    if not region:
        return (0, 0, w, h)
    x1, y1, x2, y2 = region
    bw, bh = (x2 - x1) / 1000 * w, (y2 - y1) / 1000 * h
    x1, y1 = x1 / 1000 * w, y1 / 1000 * h
    x2, y2 = x1 + bw, y1 + bh
    px, py = pad * bw, pad * bh
    x1, y1, x2, y2 = x1 - px, y1 - py, x2 + px, y2 + py
    # enforce a minimum crop so that tiny objects stay judgeable
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if x2 - x1 < min_side:
        x1, x2 = cx - min_side / 2, cx + min_side / 2
    if y2 - y1 < min_side:
        y1, y2 = cy - min_side / 2, cy + min_side / 2
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 16 or y2 - y1 < 16:
        return (0, 0, w, h)
    return (int(x1), int(y1), int(x2), int(y2))


def _labeled(img: Image.Image, text: str) -> Image.Image:
    band = 26
    out = Image.new("RGB", (img.width, img.height + band), (255, 255, 255))
    out.paste(img, (0, band))
    d = ImageDraw.Draw(out)
    d.text((6, 6), text, fill=(0, 0, 0))
    return out


def side_by_side(before: Image.Image, after: Image.Image, label_after="AFTER") -> Image.Image:
    h = max(before.height, after.height)

    def fit(im):
        if im.height != h:
            s = h / im.height
            return im.resize((max(1, int(im.width * s)), h), Image.LANCZOS)
        return im

    b, a = fit(before), fit(after)
    canvas = Image.new("RGB", (b.width + a.width + 8, h + 26), (255, 255, 255))
    canvas.paste(_labeled(b, "BEFORE"), (0, 0))
    canvas.paste(_labeled(a, label_after), (b.width + 8, 0))
    return canvas


def crop_pair(src: Image.Image, edt: Image.Image, region) -> Image.Image:
    box_s = region_to_box(region, src.size)
    box_e = region_to_box(region, edt.size)
    return side_by_side(src.crop(box_s), edt.crop(box_e))


def resize_max(img: Image.Image, max_side: int) -> Image.Image:
    if max(img.size) <= max_side:
        return img
    s = max_side / max(img.size)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                      Image.LANCZOS)


# --------------------------------------------------------------------------- #
# probe definitions
# --------------------------------------------------------------------------- #
@dataclass
class Probe:
    pid: str
    item_id: str
    system: str
    kind: str          # tcs | dps | nps | qua
    question: str
    region: list | None
    weight: float = 1.0
    ordinal: int = 0

    def to_dict(self):
        return asdict(self)


def build_probes(item: dict, system: str, output_path: Path) -> list[Probe]:
    iv = item["scm"]["intervention"]
    node_label = next((n["label"] for n in item["scm"]["nodes"] if n["id"] == iv["node"]),
                      iv["node"])
    target_region = next((n["region"] for n in item["scm"]["nodes"] if n["id"] == iv["node"]),
                         None)
    to_v = iv["to"] or "the requested state"
    probes = [
        Probe(f"{item['id']}|{system}|tcs", item["id"], system, "tcs",
              f"Compared with the BEFORE panel, is this true of the AFTER panel: the "
              f"{iv['variable']} of the {node_label} is now {to_v}?",
              target_region),
        Probe(f"{item['id']}|{system}|qua", item["id"], system, "qua",
              "Does the AFTER panel look like one coherent photograph, without "
              "visible seams, blur, duplicated or floating objects?",
              None),
    ]
    for e in item["effects"]:
        # A required effect can occasionally be an explicitly requested state that
        # must remain true. Such a probe preserves a non-descendant and therefore
        # belongs to NPS rather than DPS.
        kind = "dps" if e.get("is_descendant", True) else "nps"
        probes.append(Probe(f"{item['id']}|{system}|{kind}|{e['id']}", item["id"], system,
                            kind, e["probe"], e.get("region"),
                            ordinal=int(e.get("ordinal", 0) or 0)))
    for p in item["preserved"]:
        probes.append(Probe(f"{item['id']}|{system}|nps|{p['id']}", item["id"], system,
                            "nps", p["probe"], p.get("region")))
    return probes


# --------------------------------------------------------------------------- #
# judging
# --------------------------------------------------------------------------- #
PROBE_SYSTEM = (
    "You are a careful visual judge for an image-editing benchmark. You compare a "
    "BEFORE panel and an AFTER panel of the same photograph and answer one yes/no "
    "question about the AFTER panel. Judge only what is visible. If the panel does "
    "not contain enough information, answer \"unclear\". Output strict JSON."
)

PROBE_TEMPLATE = (
    "The attached image contains two panels of the same photograph: the left panel is "
    "labelled BEFORE and the right panel is labelled AFTER.\n"
    "Question: {question}\n"
    "Reply with JSON only: {{\"answer\": \"yes\"|\"no\"|\"unclear\", "
    "\"evidence\": \"at most twelve words\"}}"
)


def probe_inputs(probe: Probe, src: Image.Image, edt: Image.Image,
                 max_image_side: int = 768) -> tuple[str, Image.Image]:
    """The exact prompt and the exact canvas a probe is judged on."""
    if probe.region:
        canvas = crop_pair(src, edt, probe.region)
    else:
        canvas = side_by_side(resize_max(src, max_image_side // 2),
                              resize_max(edt, max_image_side // 2))
        canvas = resize_max(canvas, max_image_side)
    canvas = resize_max(canvas, max_image_side)
    return PROBE_TEMPLATE.format(question=probe.question), canvas


def record_from_answer(probe: Probe, text: str, latency: float = 0.0) -> dict:
    """Parse one judge reply into the stored probe record."""
    try:
        data = extract_json(text)
        ans = str(data.get("answer", "")).strip().lower()
        evidence = str(data.get("evidence", ""))[:120]
    except Exception:  # noqa: BLE001
        low = text.lower()
        ans = ("yes" if "yes" in low else "no" if "no" in low else "unclear")
        evidence = text.strip()[:120]
    value = {"yes": 1.0, "no": 0.0, "unclear": 0.5}.get(ans, 0.5)
    return {"pid": probe.pid, "item_id": probe.item_id, "system": probe.system,
            "kind": probe.kind, "question": probe.question, "answer": ans,
            "value": value, "evidence": evidence, "region": probe.region,
            "ordinal": probe.ordinal, "latency": latency}


def judge_probe(client, probe: Probe, src: Image.Image, edt: Image.Image,
                max_image_side: int = 768) -> dict:
    prompt, canvas = probe_inputs(probe, src, edt, max_image_side)
    t0 = time.time()
    resp: VLMResponse = client.chat(prompt, images=[canvas], system=PROBE_SYSTEM,
                                    temperature=0.0, max_tokens=2000)
    return record_from_answer(probe, resp.text, time.time() - t0)


def read_probe_jsonl(path: Path) -> dict:
    out = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["pid"]] = r
    return out
