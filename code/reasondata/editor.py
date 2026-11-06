"""Editing model back ends.

Every back end implements the same two methods::

    edit(image: PIL.Image, instruction: str, **kw) -> PIL.Image
    name: str

so that the evaluation loop in ``run_edit.py`` is model agnostic.
"""

from __future__ import annotations

import time
from pathlib import Path

import torch
from PIL import Image

from . import config


def _bnb4bit_config():
    """4-bit (nf4) quantization spec for the FLUX transformer.

    The 12B transformer plus T5-XXL is 34 GB in bf16 and does not fit on a 32 GB card;
    bf16 therefore forces host offload, which costs ~36 GB of system RAM per process and
    makes every step ~50x slower.  4-bit keeps both resident on the card, and matches the
    4-bit checkpoint already used for Qwen-Image-Edit.
    """
    from diffusers import PipelineQuantizationConfig

    return PipelineQuantizationConfig(
        quant_backend="bitsandbytes_4bit",
        quant_kwargs={"load_in_4bit": True, "bnb_4bit_quant_type": "nf4",
                      "bnb_4bit_compute_dtype": torch.bfloat16},
        components_to_quantize=["transformer"],
    )


class BaseEditor:
    name = "base"

    def __init__(self, device: str = "cuda:0"):
        self.device = device

    def edit(self, image: Image.Image, instruction: str, **kw) -> Image.Image:
        raise NotImplementedError

    @staticmethod
    def _resize_for_model(image: Image.Image, max_side: int = 1024) -> Image.Image:
        if max(image.size) > max_side:
            s = max_side / max(image.size)
            image = image.resize((max(1, int(image.width * s)), max(1, int(image.height * s))),
                                 Image.LANCZOS)
        return image


class InstructPix2PixEditor(BaseEditor):
    name = "instructpix2pix"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None):
        from diffusers import StableDiffusionInstructPix2PixPipeline, EulerAncestralDiscreteScheduler

        super().__init__(device)
        model_id = model_id or config.MODELS["instructpix2pix"]
        self.pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16, safety_checker=None
        )
        self.pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(self.pipe.scheduler.config)
        self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES["instructpix2pix"]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0, **kw) -> Image.Image:
        img = self._resize_for_model(image, 768)
        out = self.pipe(
            instruction, image=img,
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            image_guidance_scale=float(kw.get("image_guidance", self.cfg["image_guidance"])),
            guidance_scale=float(kw.get("guidance", self.cfg["guidance"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


class QwenImageEditEditor(BaseEditor):
    name = "qwen_image_edit"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None,
                 cpu_offload: bool = False, load_in_4bit: bool = True,
                 device_map: str | None = None):
        from diffusers import QwenImageEditPlusPipeline

        super().__init__(device)
        model_id = model_id or config.MODELS["qwen_image_edit"]
        dtype = torch.bfloat16
        kwargs = {"torch_dtype": dtype}
        if device_map:
            kwargs["device_map"] = device_map
        self.pipe = QwenImageEditPlusPipeline.from_pretrained(model_id, **kwargs)
        if not load_in_4bit:
            from .dequantize_qwen import dequantize_4bit_linears

            dequantize_4bit_linears(self.pipe.transformer, dtype)
            dequantize_4bit_linears(self.pipe.text_encoder, dtype)
        if cpu_offload:
            self.pipe.enable_model_cpu_offload()
        elif not device_map:
            self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES["qwen_image_edit"]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0,
             negative_prompt: str = " ", **kw) -> Image.Image:
        img = self._resize_for_model(image, 1024)
        out = self.pipe(
            image=img, prompt=instruction, negative_prompt=negative_prompt,
            true_cfg_scale=float(kw.get("guidance", self.cfg["guidance"])),
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


class FluxFillEditor(BaseEditor):
    """FLUX.1-Fill driven as a full-frame instruction editor.

    The released checkpoint is an inpainting model, so we pass an all-white mask.
    This is the strongest local diffusion editor whose licence permits research
    use, and it receives exactly the same instruction string as every other model.
    """

    name = "flux_fill"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None,
                 cpu_offload: bool = False, load_in_4bit: bool = True):
        from diffusers import FluxFillPipeline

        super().__init__(device)
        model_id = model_id or config.MODELS["flux_fill"]
        # A 12B transformer plus T5-XXL (34 GB) does not fit on a 32 GB card; 4-bit
        # weights keep both resident, whereas bf16 forces host offload that needs 36 GB
        # of system RAM per process.  Qwen-Image-Edit is likewise run 4-bit.
        kwargs = dict(torch_dtype=torch.bfloat16)
        if load_in_4bit:
            kwargs["quantization_config"] = _bnb4bit_config()
        self.pipe = FluxFillPipeline.from_pretrained(model_id, **kwargs)
        if cpu_offload:
            self.pipe.enable_model_cpu_offload(device=device)
        else:
            # also required after on-the-fly quantization, which otherwise leaves the
            # whole pipeline on the CPU
            self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES["flux_fill"]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0, **kw) -> Image.Image:
        img = self._resize_for_model(image, 1024)
        mask = Image.new("L", img.size, 255)
        out = self.pipe(
            prompt=instruction, image=img, mask_image=mask,
            height=img.height, width=img.width,
            guidance_scale=float(kw.get("guidance", self.cfg["guidance"])),
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


class FluxKontextEditor(BaseEditor):
    """FLUX.1-Kontext-dev: a strong open instruction-driven editor.

    The checkpoint is 12B in bf16 and does not fit beside its text encoders on a 32 GB
    card, so the pipeline is run with model CPU offload; the instruction string is the
    same as every other system's.
    """

    name = "flux_kontext"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None,
                 cpu_offload: bool = False, load_in_4bit: bool = True):
        from diffusers import FluxKontextPipeline

        super().__init__(device)
        model_id = model_id or config.MODELS["flux_kontext"]
        kwargs = dict(torch_dtype=torch.bfloat16)
        if load_in_4bit:
            kwargs["quantization_config"] = _bnb4bit_config()
        self.pipe = FluxKontextPipeline.from_pretrained(model_id, **kwargs)
        if cpu_offload:
            self.pipe.enable_model_cpu_offload(device=device)
        else:
            self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES["flux_kontext"]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0, **kw) -> Image.Image:
        img = self._resize_for_model(image, 1024)
        out = self.pipe(
            image=img, prompt=instruction,
            guidance_scale=float(kw.get("guidance", self.cfg["guidance"])),
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


class SDInpaintEditor(BaseEditor):
    """SD1.5 / SD2 inpainting driven as full-frame prompt-only regeneration.

    Two more backbones of the prompt-only family, so that the comparison does not rest
    on a single generator scale.
    """

    def __init__(self, device: str = "cuda:0", model_id: str | None = None,
                 profile: str = "sd15_inpaint"):
        from diffusers import StableDiffusionInpaintPipeline

        super().__init__(device)
        model_id = model_id or config.MODELS[profile]
        self.pipe = StableDiffusionInpaintPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16)
        self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES[profile]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0, **kw) -> Image.Image:
        img = self._resize_for_model(image, 768)
        img = img.resize((768, 768), Image.LANCZOS)
        mask = Image.new("L", img.size, 255)
        out = self.pipe(
            prompt=instruction, image=img, mask_image=mask,
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            guidance_scale=float(kw.get("guidance", self.cfg["guidance"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


class SD15InpaintEditor(SDInpaintEditor):
    name = "sd15_inpaint"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None, **kw):
        super().__init__(device=device, model_id=model_id, profile="sd15_inpaint")


class SD2InpaintEditor(SDInpaintEditor):
    name = "sd2_inpaint"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None, **kw):
        super().__init__(device=device, model_id=model_id, profile="sd2_inpaint")


class SDXLInpaintEditor(BaseEditor):
    """Prompt-only regeneration baseline (no instruction tuning)."""

    name = "sdxl_inpaint"

    def __init__(self, device: str = "cuda:0", model_id: str | None = None):
        from diffusers import StableDiffusionXLInpaintPipeline

        super().__init__(device)
        model_id = model_id or (
            f"{config.HF_CACHE}/diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
        )
        self.pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16
        )
        self.pipe.to(device)
        self.pipe.set_progress_bar_config(disable=True)
        self.cfg = config.EDIT_PROFILES["sd15_inpaint"]

    @torch.inference_mode()
    def edit(self, image: Image.Image, instruction: str, seed: int = 0, **kw) -> Image.Image:
        img = self._resize_for_model(image, 1024)
        img = img.resize((1024, 1024), Image.LANCZOS)
        mask = Image.new("L", img.size, 255)
        out = self.pipe(
            prompt=instruction, image=img, mask_image=mask,
            num_inference_steps=int(kw.get("steps", self.cfg["steps"])),
            guidance_scale=float(kw.get("guidance", self.cfg["guidance"])),
            generator=torch.Generator(device=self.device).manual_seed(seed),
        ).images[0]
        return out


REGISTRY = {
    "instructpix2pix": InstructPix2PixEditor,
    "qwen_image_edit": QwenImageEditEditor,
    "flux_fill": FluxFillEditor,
    "flux_kontext": FluxKontextEditor,
    "sdxl_inpaint": SDXLInpaintEditor,
    "sd15_inpaint": SD15InpaintEditor,
    "sd2_inpaint": SD2InpaintEditor,
}


def build_editor(name: str, device: str = "cuda:0", **kw) -> BaseEditor:
    base = name
    if name.startswith("qwen_image_edit"):
        base = "qwen_image_edit"
    if base not in REGISTRY:
        raise KeyError(f"unknown editor {name!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[base](device=device, **kw)
