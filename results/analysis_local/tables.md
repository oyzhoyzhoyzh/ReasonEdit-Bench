# ReasonEdit-Bench results

## Overall (all 324 items, 9 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| FLUX.1-Fill | 0.273 | 0.295 | 0.118 | 0.229 | 0.160 | 0.000 | 17.247 | 0.060 | 0.815 |
| InstructPix2Pix | 0.262 | 0.416 | 0.589 | 0.422 | 0.174 | 0.006 | 23.605 | 0.646 | 0.322 |
| Qwen-Image-Edit | 0.548 | 0.498 | 0.850 | 0.632 | 0.262 | 0.090 | 22.436 | 0.875 | 0.201 |
| Qwen-Image-Edit + CoT | 0.554 | 0.534 | 0.848 | 0.645 | 0.248 | 0.102 | 22.623 | 0.865 | 0.225 |
| Qwen-Image-Edit + Oracle-SCM | 0.577 | 0.591 | 0.856 | 0.675 | 0.289 | 0.170 | 22.640 | 0.847 | 0.260 |
| Qwen-Image-Edit + CausalScaffold | 0.559 | 0.572 | 0.861 | 0.664 | 0.336 | 0.160 | 22.562 | 0.859 | 0.242 |
| SD1.5-Inpaint | 0.370 | 0.350 | 0.151 | 0.290 | 0.182 | 0.000 | 26.026 | 0.229 | 0.741 |
| SD2-Inpaint | 0.375 | 0.352 | 0.144 | 0.290 | 0.185 | 0.003 | 26.245 | 0.231 | 0.741 |
| SDXL-Inpaint | 0.360 | 0.354 | 0.172 | 0.295 | 0.173 | 0.000 | 26.263 | 0.307 | 0.599 |

## CCS by Task domain

### FLUX.1-Fill
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.278 | 0.357 | 0.086 | 0.000 | 108 |
| commonsense | 0.187 | 0.244 | 0.151 | 0.000 | 108 |
| multi_step | 0.222 | 0.285 | 0.117 | 0.000 | 108 |

### InstructPix2Pix
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.419 | 0.435 | 0.555 | 0.009 | 108 |
| commonsense | 0.440 | 0.419 | 0.641 | 0.009 | 108 |
| multi_step | 0.408 | 0.394 | 0.571 | 0.000 | 108 |

### Qwen-Image-Edit
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.672 | 0.508 | 0.875 | 0.093 | 108 |
| commonsense | 0.633 | 0.529 | 0.782 | 0.120 | 108 |
| multi_step | 0.591 | 0.458 | 0.894 | 0.056 | 108 |

### Qwen-Image-Edit + CausalScaffold
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.736 | 0.636 | 0.869 | 0.231 | 108 |
| commonsense | 0.642 | 0.556 | 0.832 | 0.176 | 108 |
| multi_step | 0.613 | 0.522 | 0.883 | 0.074 | 108 |

### Qwen-Image-Edit + CoT
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.705 | 0.593 | 0.855 | 0.139 | 108 |
| commonsense | 0.645 | 0.553 | 0.807 | 0.120 | 108 |
| multi_step | 0.586 | 0.455 | 0.881 | 0.046 | 108 |

### Qwen-Image-Edit + Oracle-SCM
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.733 | 0.676 | 0.864 | 0.241 | 108 |
| commonsense | 0.687 | 0.647 | 0.835 | 0.185 | 108 |
| multi_step | 0.604 | 0.449 | 0.869 | 0.083 | 108 |

### SD1.5-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.323 | 0.394 | 0.120 | 0.000 | 108 |
| commonsense | 0.253 | 0.295 | 0.176 | 0.000 | 108 |
| multi_step | 0.296 | 0.360 | 0.156 | 0.000 | 108 |

### SD2-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.343 | 0.417 | 0.132 | 0.009 | 108 |
| commonsense | 0.245 | 0.296 | 0.176 | 0.000 | 108 |
| multi_step | 0.282 | 0.342 | 0.123 | 0.000 | 108 |

### SDXL-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.327 | 0.427 | 0.152 | 0.000 | 108 |
| commonsense | 0.278 | 0.301 | 0.198 | 0.000 | 108 |
| multi_step | 0.281 | 0.333 | 0.166 | 0.000 | 108 |

## CCS by Difficulty

### FLUX.1-Fill
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.252 | 0.329 | 0.112 | 0.000 | 84 |
| hard | 0.215 | 0.270 | 0.134 | 0.000 | 83 |
| medium | 0.224 | 0.290 | 0.114 | 0.000 | 157 |

### InstructPix2Pix
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.447 | 0.424 | 0.638 | 0.012 | 84 |
| hard | 0.423 | 0.437 | 0.544 | 0.000 | 83 |
| medium | 0.409 | 0.401 | 0.587 | 0.006 | 157 |

### Qwen-Image-Edit
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.663 | 0.488 | 0.883 | 0.131 | 84 |
| hard | 0.594 | 0.456 | 0.880 | 0.024 | 83 |
| medium | 0.636 | 0.526 | 0.817 | 0.102 | 157 |

### Qwen-Image-Edit + CausalScaffold
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.729 | 0.607 | 0.889 | 0.250 | 84 |
| hard | 0.588 | 0.526 | 0.847 | 0.108 | 83 |
| medium | 0.669 | 0.576 | 0.854 | 0.140 | 157 |

### Qwen-Image-Edit + CoT
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.693 | 0.539 | 0.893 | 0.155 | 84 |
| hard | 0.592 | 0.476 | 0.861 | 0.060 | 83 |
| medium | 0.647 | 0.562 | 0.816 | 0.096 | 157 |

### Qwen-Image-Edit + Oracle-SCM
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.717 | 0.624 | 0.871 | 0.250 | 84 |
| hard | 0.630 | 0.554 | 0.841 | 0.108 | 83 |
| medium | 0.676 | 0.592 | 0.856 | 0.159 | 157 |

### SD1.5-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.312 | 0.338 | 0.159 | 0.000 | 84 |
| hard | 0.259 | 0.355 | 0.163 | 0.000 | 83 |
| medium | 0.295 | 0.352 | 0.140 | 0.000 | 157 |

### SD2-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.328 | 0.401 | 0.162 | 0.012 | 84 |
| hard | 0.279 | 0.359 | 0.141 | 0.000 | 83 |
| medium | 0.275 | 0.321 | 0.136 | 0.000 | 157 |

### SDXL-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.318 | 0.402 | 0.177 | 0.000 | 84 |
| hard | 0.278 | 0.363 | 0.177 | 0.000 | 83 |
| medium | 0.292 | 0.323 | 0.167 | 0.000 | 157 |

## CCS by Fine-grained task type

### FLUX.1-Fill
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.235 | 0.336 | 0.120 | 0.000 | 36 |
| counterfactual | 0.350 | 0.345 | 0.095 | 0.000 | 36 |
| functional | 0.200 | 0.257 | 0.162 | 0.000 | 36 |
| long_horizon | 0.182 | 0.255 | 0.139 | 0.000 | 36 |
| multi | 0.230 | 0.380 | 0.074 | 0.000 | 36 |
| physical | 0.218 | 0.308 | 0.150 | 0.000 | 36 |
| sequential | 0.248 | 0.264 | 0.093 | 0.000 | 36 |
| single | 0.252 | 0.347 | 0.090 | 0.000 | 36 |
| social | 0.144 | 0.167 | 0.141 | 0.000 | 36 |

### InstructPix2Pix
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.454 | 0.426 | 0.616 | 0.000 | 36 |
| counterfactual | 0.438 | 0.500 | 0.593 | 0.000 | 36 |
| functional | 0.421 | 0.387 | 0.653 | 0.000 | 36 |
| long_horizon | 0.384 | 0.421 | 0.495 | 0.000 | 36 |
| multi | 0.440 | 0.449 | 0.565 | 0.000 | 36 |
| physical | 0.458 | 0.491 | 0.604 | 0.000 | 36 |
| sequential | 0.386 | 0.333 | 0.602 | 0.000 | 36 |
| single | 0.380 | 0.356 | 0.507 | 0.028 | 36 |
| social | 0.441 | 0.380 | 0.667 | 0.028 | 36 |

### Qwen-Image-Edit
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.612 | 0.498 | 0.824 | 0.083 | 36 |
| counterfactual | 0.655 | 0.484 | 0.926 | 0.083 | 36 |
| functional | 0.677 | 0.597 | 0.852 | 0.194 | 36 |
| long_horizon | 0.492 | 0.407 | 0.931 | 0.000 | 36 |
| multi | 0.716 | 0.616 | 0.824 | 0.083 | 36 |
| physical | 0.648 | 0.565 | 0.824 | 0.167 | 36 |
| sequential | 0.668 | 0.468 | 0.926 | 0.083 | 36 |
| single | 0.646 | 0.424 | 0.875 | 0.111 | 36 |
| social | 0.574 | 0.426 | 0.671 | 0.000 | 36 |

### Qwen-Image-Edit + CausalScaffold
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.669 | 0.590 | 0.889 | 0.139 | 36 |
| counterfactual | 0.682 | 0.574 | 0.861 | 0.167 | 36 |
| functional | 0.641 | 0.530 | 0.852 | 0.222 | 36 |
| long_horizon | 0.517 | 0.500 | 0.884 | 0.028 | 36 |
| multi | 0.764 | 0.718 | 0.880 | 0.250 | 36 |
| physical | 0.630 | 0.593 | 0.852 | 0.167 | 36 |
| sequential | 0.654 | 0.477 | 0.875 | 0.056 | 36 |
| single | 0.762 | 0.616 | 0.866 | 0.278 | 36 |
| social | 0.654 | 0.546 | 0.792 | 0.139 | 36 |

### Qwen-Image-Edit + CoT
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.590 | 0.477 | 0.833 | 0.083 | 36 |
| counterfactual | 0.715 | 0.597 | 0.880 | 0.111 | 36 |
| functional | 0.655 | 0.590 | 0.847 | 0.222 | 36 |
| long_horizon | 0.502 | 0.426 | 0.912 | 0.000 | 36 |
| multi | 0.682 | 0.634 | 0.801 | 0.111 | 36 |
| physical | 0.634 | 0.574 | 0.815 | 0.111 | 36 |
| sequential | 0.667 | 0.463 | 0.898 | 0.056 | 36 |
| single | 0.718 | 0.549 | 0.884 | 0.194 | 36 |
| social | 0.645 | 0.495 | 0.759 | 0.028 | 36 |

### Qwen-Image-Edit + Oracle-SCM
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.603 | 0.472 | 0.810 | 0.167 | 36 |
| counterfactual | 0.719 | 0.630 | 0.917 | 0.250 | 36 |
| functional | 0.660 | 0.637 | 0.843 | 0.222 | 36 |
| long_horizon | 0.529 | 0.449 | 0.903 | 0.028 | 36 |
| multi | 0.719 | 0.718 | 0.829 | 0.194 | 36 |
| physical | 0.709 | 0.734 | 0.838 | 0.167 | 36 |
| sequential | 0.681 | 0.426 | 0.894 | 0.056 | 36 |
| single | 0.759 | 0.681 | 0.847 | 0.278 | 36 |
| social | 0.691 | 0.569 | 0.824 | 0.167 | 36 |

### SD1.5-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.350 | 0.382 | 0.167 | 0.000 | 36 |
| counterfactual | 0.330 | 0.463 | 0.083 | 0.000 | 36 |
| functional | 0.248 | 0.312 | 0.125 | 0.000 | 36 |
| long_horizon | 0.213 | 0.370 | 0.185 | 0.000 | 36 |
| multi | 0.319 | 0.338 | 0.148 | 0.000 | 36 |
| physical | 0.274 | 0.299 | 0.204 | 0.000 | 36 |
| sequential | 0.324 | 0.329 | 0.116 | 0.000 | 36 |
| single | 0.318 | 0.380 | 0.130 | 0.000 | 36 |
| social | 0.236 | 0.273 | 0.199 | 0.000 | 36 |

### SD2-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.325 | 0.405 | 0.125 | 0.000 | 36 |
| counterfactual | 0.352 | 0.412 | 0.171 | 0.000 | 36 |
| functional | 0.252 | 0.322 | 0.171 | 0.000 | 36 |
| long_horizon | 0.236 | 0.310 | 0.148 | 0.000 | 36 |
| multi | 0.336 | 0.426 | 0.083 | 0.000 | 36 |
| physical | 0.262 | 0.294 | 0.171 | 0.000 | 36 |
| sequential | 0.284 | 0.310 | 0.097 | 0.000 | 36 |
| single | 0.342 | 0.412 | 0.141 | 0.028 | 36 |
| social | 0.222 | 0.273 | 0.185 | 0.000 | 36 |

### SDXL-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.316 | 0.407 | 0.123 | 0.000 | 36 |
| counterfactual | 0.334 | 0.475 | 0.167 | 0.000 | 36 |
| functional | 0.261 | 0.336 | 0.155 | 0.000 | 36 |
| long_horizon | 0.258 | 0.356 | 0.194 | 0.000 | 36 |
| multi | 0.315 | 0.384 | 0.157 | 0.000 | 36 |
| physical | 0.256 | 0.299 | 0.206 | 0.000 | 36 |
| sequential | 0.269 | 0.236 | 0.181 | 0.000 | 36 |
| single | 0.333 | 0.424 | 0.132 | 0.000 | 36 |
| social | 0.316 | 0.269 | 0.234 | 0.000 | 36 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| FLUX.1-Fill | 0.000 | 0.000 | 0.207 | 0.769 | 0.000 | 0.025 |
| InstructPix2Pix | 0.006 | 0.336 | 0.213 | 0.417 | 0.000 | 0.028 |
| Qwen-Image-Edit | 0.090 | 0.287 | 0.401 | 0.176 | 0.000 | 0.046 |
| Qwen-Image-Edit + CoT | 0.102 | 0.262 | 0.389 | 0.191 | 0.000 | 0.056 |
| Qwen-Image-Edit + Oracle-SCM | 0.170 | 0.219 | 0.333 | 0.216 | 0.000 | 0.062 |
| Qwen-Image-Edit + CausalScaffold | 0.160 | 0.259 | 0.346 | 0.194 | 0.000 | 0.040 |
| SD1.5-Inpaint | 0.000 | 0.000 | 0.299 | 0.651 | 0.000 | 0.049 |
| SD2-Inpaint | 0.003 | 0.000 | 0.287 | 0.651 | 0.000 | 0.059 |
| SDXL-Inpaint | 0.000 | 0.000 | 0.290 | 0.667 | 0.000 | 0.043 |
