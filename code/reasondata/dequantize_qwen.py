"""Materialise an NF4 Qwen-Image-Edit checkpoint as a portable BF16 pipeline.

Some accelerator backends cannot execute the prebuilt bitsandbytes NF4 kernels
at inference time, although their CPU dequantiser is available.  This utility
loads the quantised pipeline on CPU, replaces every ``Linear4bit`` module with
a normal BF16 ``torch.nn.Linear``, and writes a standard diffusers pipeline.
The resulting checkpoint has no dependency on a GPU quantisation kernel.

    python -m reasondata.dequantize_qwen \
        --src /path/to/Qwen-Image-Edit-2509-4bit \
        --out /path/to/Qwen-Image-Edit-2509-bf16
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path

import torch


def _to_cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu()
    return value


def _quant_state_cpu(state):
    """Clone a bitsandbytes QuantState with every tensor on the CPU.

    Moving only the packed weight is insufficient: ``absmax`` and the nested
    scale state can still live on the accelerator.  ``dequantize_4bit`` then
    dispatches to the broken accelerator kernel even though the weights are on
    the CPU.
    """
    from bitsandbytes.functional import QuantState

    state2 = _quant_state_cpu(state.state2) if getattr(state, "nested", False) else None
    return QuantState(
        absmax=_to_cpu(state.absmax),
        shape=state.shape,
        code=_to_cpu(state.code),
        blocksize=state.blocksize,
        quant_type=state.quant_type,
        dtype=state.dtype,
        offset=_to_cpu(state.offset),
        state2=state2,
    )


def _replace(module: torch.nn.Module, dtype: torch.dtype,
             progress: list[int]) -> int:
    import bitsandbytes as bnb
    from bitsandbytes import functional as F

    replaced = 0
    for name, child in list(module.named_children()):
        if isinstance(child, bnb.nn.Linear4bit):
            state = _quant_state_cpu(child.weight.quant_state)
            weight = F.dequantize_4bit(
                child.weight.data.cpu(), state
            ).to(dtype)
            expected = child.out_features * child.in_features
            if weight.numel() != expected:
                raise RuntimeError(
                    f"dequantized {name} has {weight.numel()} values, expected {expected}"
                )
            if not torch.isfinite(weight).all():
                raise RuntimeError(f"dequantized {name} contains non-finite values")
            linear = torch.nn.Linear(
                child.in_features,
                child.out_features,
                bias=child.bias is not None,
                device="cpu",
                dtype=dtype,
            )
            with torch.no_grad():
                linear.weight.copy_(weight.reshape_as(linear.weight))
                if child.bias is not None:
                    linear.bias.copy_(child.bias.data.to(device="cpu", dtype=dtype))
            linear.weight.requires_grad_(False)
            if linear.bias is not None:
                linear.bias.requires_grad_(False)
            setattr(module, name, linear)
            del child
            replaced += 1
            progress[0] += 1
            if progress[0] % 50 == 0:
                print(f"  dequantized {progress[0]}/{progress[1]}", flush=True)
        else:
            replaced += _replace(child, dtype, progress)
    return replaced


def cast_floating(module: torch.nn.Module, dtype: torch.dtype) -> int:
    count = 0
    for submodule in module.modules():
        for _, param in submodule.named_parameters(recurse=False):
            if param.dtype.is_floating_point and param.dtype != dtype:
                param.data = param.data.to(dtype)
                count += 1
        for name, buffer in submodule.named_buffers(recurse=False):
            if buffer.dtype.is_floating_point and buffer.dtype != dtype:
                submodule._buffers[name] = buffer.to(dtype)
                count += 1
    return count


def remove_quantization_config(cfg) -> None:
    """Remove bitsandbytes metadata from a diffusers or transformers config."""
    keys = ("quantization_config", "_load_in_4bit", "load_in_4bit")
    mappings = []
    internal = getattr(cfg, "_internal_dict", None)
    if internal is not None:
        mappings.append(internal)
    if isinstance(cfg, dict):
        mappings.append(cfg)
    for key in keys:
        for mapping in mappings:
            if key in mapping:
                # diffusers wraps this mapping in FrozenDict, whose public
                # deletion methods intentionally raise.  Bypass only here,
                # after the quantized modules have already been materialised.
                if isinstance(mapping, OrderedDict):
                    OrderedDict.__delitem__(mapping, key)
                else:
                    dict.__delitem__(mapping, key)
        # FrozenDict exposes keys as attributes.  Its inherited ``__delattr__``
        # attempts a second mapping deletion after the line above, so only
        # delete attributes on ordinary config objects.
        if not isinstance(cfg, dict) and hasattr(cfg, key):
            try:
                delattr(cfg, key)
            except AttributeError:
                pass


def dequantize_4bit_linears(module: torch.nn.Module,
                            dtype: torch.dtype = torch.bfloat16) -> int:
    """Replace every bitsandbytes Linear4bit layer by a normal BF16 Linear."""
    import bitsandbytes as bnb

    total = sum(isinstance(m, bnb.nn.Linear4bit) for m in module.modules())
    print(f"dequantizing {total} Linear4bit modules under {type(module).__name__}",
          flush=True)
    replaced = _replace(module, dtype, [0, total])
    cast_floating(module, dtype)
    return replaced


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-shard-size", default="8GB")
    args = ap.parse_args()

    from diffusers import QwenImageEditPlusPipeline

    dtype = torch.bfloat16
    pipe = QwenImageEditPlusPipeline.from_pretrained(args.src, torch_dtype=dtype)

    # Do not let the saved component configs request bitsandbytes again.  Perform
    # this before the expensive weight conversion so metadata failures fail fast.
    for component in (pipe.transformer, pipe.text_encoder, pipe.vae):
        cfg = getattr(component, "config", None)
        if cfg is not None:
            remove_quantization_config(cfg)
            if hasattr(cfg, "to_json_string"):
                cfg.to_json_string()

    n_transformer = dequantize_4bit_linears(pipe.transformer, dtype)
    n_text = dequantize_4bit_linears(pipe.text_encoder, dtype)
    # Transformers records the checkpoint conversion used at load time and tries
    # to reverse it on save.  Qwen2.5-VL's reverse transform is not implemented
    # in the installed version.  The state dict already uses canonical module
    # names after loading, so empty conversions save it verbatim.
    if hasattr(pipe.text_encoder, "_weight_conversions"):
        pipe.text_encoder._weight_conversions = []

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe.save_pretrained(out, safe_serialization=True,
                         max_shard_size=args.max_shard_size)
    print(f"dequantized transformer={n_transformer} text_encoder={n_text}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
