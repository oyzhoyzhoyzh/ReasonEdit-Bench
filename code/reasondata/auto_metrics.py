"""Reference-based metrics: CLIPScore, CLIP-I, DINO-I, LPIPS, plus a
region-restricted DINO preservation score.

These are the ``conventional`` layer of the evaluation pyramid and serve as the
control group against which the causal metrics of the paper are compared.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image

from . import config


class AutoMetrics:
    def __init__(self, device: str = "cuda:0"):
        from transformers import CLIPModel, CLIPProcessor, Dinov2Model

        self.device = device
        self.clip = CLIPModel.from_pretrained(config.MODELS["clip"]).to(device).eval()
        self.clip_proc = CLIPProcessor.from_pretrained(config.MODELS["clip"])
        self.dino = Dinov2Model.from_pretrained(config.MODELS["dinov2"]).to(device).eval()
        self._dino_mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
        self._dino_std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)
        self.lpips_fn = None

    # ---------------------------------------------------------------- CLIP --
    @staticmethod
    def _as_tensor(out):
        """transformers 5.x may wrap features in an output object."""
        if torch.is_tensor(out):
            return out
        for attr in ("image_embeds", "text_embeds", "pooler_output", "last_hidden_state"):
            val = getattr(out, attr, None)
            if val is not None:
                return val[:, 0] if attr == "last_hidden_state" else val
        raise TypeError(f"cannot extract embedding tensor from {type(out)}")

    @torch.inference_mode()
    def clip_scores(self, images: list[Image.Image], texts: list[str]) -> list[float]:
        inputs = self.clip_proc(text=texts, images=images, return_tensors="pt",
                                padding=True, truncation=True, max_length=77).to(self.device)
        out = self.clip(**inputs)
        sim = F.cosine_similarity(self._as_tensor(out.image_embeds),
                                  self._as_tensor(out.text_embeds))
        return [float(v) * 100 for v in sim]

    @torch.inference_mode()
    def clip_image_sim(self, a: list[Image.Image], b: list[Image.Image]) -> list[float]:
        ia = self.clip_proc(images=a, return_tensors="pt").to(self.device)
        ib = self.clip_proc(images=b, return_tensors="pt").to(self.device)
        ea = self._as_tensor(self.clip.get_image_features(**ia))
        eb = self._as_tensor(self.clip.get_image_features(**ib))
        return [float(v) for v in F.cosine_similarity(ea, eb)]

    # ---------------------------------------------------------------- DINO --
    def _dino_features(self, images: list[Image.Image]):
        import torchvision.transforms as T

        tf = T.Compose([T.Resize(256), T.CenterCrop(224), T.ToTensor()])
        batch = torch.stack([tf(im.convert("RGB")) for im in images]).to(self.device)
        batch = (batch - self._dino_mean) / self._dino_std
        return self._as_tensor(self.dino(batch))

    @torch.inference_mode()
    def dino_sim(self, a: list[Image.Image], b: list[Image.Image]) -> list[float]:
        fa, fb = self._dino_features(a), self._dino_features(b)
        return [float(v) for v in F.cosine_similarity(fa, fb)]

    # --------------------------------------------------------------- LPIPS --
    @torch.inference_mode()
    def lpips(self, a: list[Image.Image], b: list[Image.Image]) -> list[float]:
        if self.lpips_fn is None:
            import lpips
            self.lpips_fn = lpips.LPIPS(net="alex", verbose=False).to(self.device)
        import torchvision.transforms as T

        tf = T.Compose([T.Resize(256), T.CenterCrop(256), T.ToTensor()])
        ta = torch.stack([tf(im.convert("RGB")) for im in a]).to(self.device) * 2 - 1
        tb = torch.stack([tf(im.convert("RGB")) for im in b]).to(self.device) * 2 - 1
        vals = self.lpips_fn(ta, tb)
        return [float(v) for v in vals.flatten()]

    def all_metrics(self, sources: list[Image.Image], edits: list[Image.Image],
                    instructions: list[str], batch: int = 8) -> list[dict]:
        out: list[dict] = [{} for _ in edits]
        for i in range(0, len(edits), batch):
            s = sources[i : i + batch]
            e = edits[i : i + batch]
            t = instructions[i : i + batch]
            cs = self.clip_scores(e, t)
            ci = self.clip_image_sim(s, e)
            ds = self.dino_sim(s, e)
            lp = self.lpips(s, e)
            for j in range(len(e)):
                out[i + j] = {"clipscore": cs[j], "clip_i": ci[j],
                              "dino_i": ds[j], "lpips": lp[j]}
        return out


def region_preservation_dino(am: AutoMetrics, src: Image.Image, edt: Image.Image,
                             boxes: list, pad: float = 0.0) -> list[float]:
    """DINO similarity of *non-edited* regions (proxy for collateral damage)."""
    from .probe import region_to_box

    a_crops, b_crops = [], []
    for box in boxes:
        bs = region_to_box(box, src.size)
        be = region_to_box(box, edt.size)
        a_crops.append(src.crop(bs))
        b_crops.append(edt.crop(be))
    if not a_crops:
        return []
    return am.dino_sim(a_crops, b_crops)
