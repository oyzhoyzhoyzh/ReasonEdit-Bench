"""Unified vision-language model access.

Two backends are supported:

* ``DashScopeClient`` -- OpenAI-compatible HTTP endpoint of the Qwen platform.
  Used for large-scale annotation where throughput matters.
* ``LocalVLM`` -- a locally hosted Qwen-VL checkpoint.  Used for *judging*
  during evaluation so that reported numbers are reproducible offline.

Both expose the same ``chat`` interface and return ``VLMResponse`` records.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import requests
from PIL import Image

from . import config


@dataclass
class VLMResponse:
    text: str
    model: str
    usage: dict = field(default_factory=dict)
    latency: float = 0.0

    def json(self) -> Any:
        return extract_json(self.text)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def encode_image(image: Image.Image, max_side: int = 1280, fmt: str = "JPEG") -> str:
    """Base64-encode a PIL image as a data URL."""
    img = image.convert("RGB")
    if max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=92)
    mime = "image/jpeg" if fmt.upper() == "JPEG" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def extract_json(text: str) -> Any:
    """Best-effort extraction of a JSON object/array from a model reply.

    Some models keep appending fields after the object we asked for (or loop on
    unrelated keys until the token budget runs out).  We therefore scan for the
    first *balanced* JSON value and return it, instead of trusting the trailing
    braces of the reply.
    """
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth, in_str, esc = 0, False, False
        candidates = []
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : i + 1])
        for cand in candidates:
            for attempt in (cand, re.sub(r",\s*([}\]])", r"\1", cand)):
                try:
                    return json.loads(attempt)
                except json.JSONDecodeError:
                    continue

    # last resort: the original greedy slice
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            cand = text[start : end + 1]
            try:
                return json.loads(cand)
            except json.JSONDecodeError:
                cand2 = re.sub(r",\s*([}\]])", r"\1", cand)
                try:
                    return json.loads(cand2)
                except json.JSONDecodeError:
                    continue
    raise ValueError(f"no JSON found in reply: {text[:400]}")


def build_content(prompt: str, images: Sequence[Image.Image] | None = None) -> list[dict]:
    content: list[dict] = []
    for img in images or []:
        content.append({"type": "image_url", "image_url": {"url": encode_image(img)}})
    content.append({"type": "text", "text": prompt})
    return content


# --------------------------------------------------------------------------- #
# backend 1: DashScope HTTP API
# --------------------------------------------------------------------------- #
class DashScopeClient:
    def __init__(self, model: str = config.ANNOT_MODEL, key: str | None = None,
                 base: str | None = None):
        self.model = model
        self.key = key or config.DASHSCOPE_KEY
        self.base = (base or config.DASHSCOPE_BASE).rstrip("/")
        if not self.key:
            raise RuntimeError("DASHSCOPE_API_KEY is not set")
        self.session = requests.Session()

    def chat(self, prompt: str, images: Sequence[Image.Image] | None = None,
             system: str | None = None, temperature: float = 0.2,
             max_tokens: int = 2048, retries: int = 3,
             json_mode: bool = True) -> VLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": build_content(prompt, images)})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

        last_err: Exception | None = None
        for attempt in range(retries):
            t0 = time.time()
            try:
                r = self.session.post(f"{self.base}/chat/completions", headers=headers,
                                      json=payload, timeout=180)
                r.raise_for_status()
                data = r.json()
                msg = data["choices"][0]["message"]
                text = msg.get("content") or msg.get("reasoning_content") or ""
                return VLMResponse(text=text, model=self.model,
                                   usage=data.get("usage", {}), latency=time.time() - t0)
            except Exception as exc:  # noqa: BLE001 - retry on any transport error
                last_err = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"DashScope call failed: {last_err}")

    def chat_many(self, prompts: Sequence[tuple], workers: int = 12,
                  **kwargs) -> list[VLMResponse]:
        """Run many ``(prompt, images)`` requests concurrently, preserving order."""
        out: list[VLMResponse | None] = [None] * len(prompts)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(self.chat, p, imgs, **kwargs): i
                for i, (p, imgs) in enumerate(prompts)
            }
            for fut in as_completed(futs):
                i = futs[fut]
                try:
                    out[i] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    out[i] = VLMResponse(text=f'{{"error": "{exc}"}}', model=self.model)
        return out  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# backend 2: local HF model
# --------------------------------------------------------------------------- #
class LocalVLM:
    """Locally hosted Qwen-VL model run through ``transformers``."""

    _cache: dict[tuple[str, str], "LocalVLM"] = {}

    def __init__(self, model_id: str, device: str = "cuda:0"):
        import torch
        from transformers import AutoProcessor

        try:
            from transformers import AutoModelForImageTextToText as _Auto
        except ImportError:  # older transformers
            from transformers import AutoModelForVision2Seq as _Auto  # type: ignore

        self.torch = torch
        self.model_id = model_id
        self.device = device
        self.processor = AutoProcessor.from_pretrained(model_id)
        kwargs = dict(dtype=torch.bfloat16, device_map=None)
        self.model = _Auto.from_pretrained(model_id, **kwargs)
        self.model.to(device).eval()

    @classmethod
    def get(cls, model_id: str, device: str = "cuda:0") -> "LocalVLM":
        key = (model_id, device)
        if key not in cls._cache:
            cls._cache[key] = cls(model_id, device)
        return cls._cache[key]

    def chat(self, prompt: str, images: Sequence[Image.Image] | None = None,
             system: str | None = None, temperature: float = 0.0,
             max_tokens: int = 1024, **_ignored) -> VLMResponse:
        from qwen_vl_utils import process_vision_info

        messages = []
        if system:
            messages.append({"role": "system", "content": [{"type": "text", "text": system}]})
        content = [{"type": "image", "image": im.convert("RGB")} for im in (images or [])]
        content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": content})

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, videos=video_inputs,
                                padding=True, return_tensors="pt").to(self.device)
        t0 = time.time()
        with self.torch.inference_mode():
            gen = self.model.generate(**inputs, max_new_tokens=max_tokens,
                                      do_sample=temperature > 0,
                                      temperature=max(temperature, 1e-5))
        trimmed = gen[:, inputs.input_ids.shape[1]:]
        out = self.processor.batch_decode(trimmed, skip_special_tokens=True)[0]
        return VLMResponse(text=out, model=self.model_id, latency=time.time() - t0)

    def chat_batch(self, prompts: Sequence[str],
                   images_list: Sequence[Sequence[Image.Image]] | None = None,
                   system: str | None = None, temperature: float = 0.0,
                   max_tokens: int = 1024) -> list[VLMResponse]:
        """Same protocol as :meth:`chat`, with several conversations in one pass.

        The prompts, images and decoding parameters are identical to the sequential
        path; only the batch dimension is added, so a batched run is comparable with
        a sequential one.
        """
        from qwen_vl_utils import process_vision_info

        conversations = []
        for i, prompt in enumerate(prompts):
            messages = []
            if system:
                messages.append({"role": "system",
                                 "content": [{"type": "text", "text": system}]})
            content = [{"type": "image", "image": im.convert("RGB")}
                       for im in (images_list[i] if images_list else [])]
            content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content})
            conversations.append(messages)

        texts = self.processor.apply_chat_template(
            conversations, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(conversations)
        # decoder-only batched generation requires left padding; the Qwen processor
        # defaults to right padding, which silently corrupts every row but the first
        self.processor.tokenizer.padding_side = "left"
        inputs = self.processor(text=texts, images=image_inputs, videos=video_inputs,
                                padding=True, return_tensors="pt").to(self.device)
        t0 = time.time()
        with self.torch.inference_mode():
            gen = self.model.generate(**inputs, max_new_tokens=max_tokens,
                                      do_sample=temperature > 0,
                                      temperature=max(temperature, 1e-5))
        trimmed = gen[:, inputs.input_ids.shape[1]:]
        outs = self.processor.batch_decode(trimmed, skip_special_tokens=True)
        latency = time.time() - t0
        return [VLMResponse(text=o, model=self.model_id, latency=latency) for o in outs]


def get_client(kind: str = "dashscope", model: str | None = None,
               device: str = "cuda:0"):
    if kind == "dashscope":
        return DashScopeClient(model=model or config.ANNOT_MODEL)
    if kind == "local":
        return LocalVLM.get(model or config.MODELS["qwen3vl8b"], device=device)
    raise ValueError(kind)


def run_pooled(fn, items: Iterable, workers: int = 8) -> list:
    items = list(items)
    out: list[Any] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fn, it): i for i, it in enumerate(items)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                out[i] = fut.result()
            except Exception as exc:  # noqa: BLE001
                out[i] = exc
    return out


def chunked(seq: Sequence, size: int) -> Iterable[Sequence]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
