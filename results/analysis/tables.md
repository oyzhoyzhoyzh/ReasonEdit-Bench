# ReasonEdit-Bench results

## Overall (all 324 items, 9 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| FLUX.1-Fill | 0.427 | 0.418 | 0.209 | 0.351 | 0.130 | 0.003 | 17.247 | 0.060 | 0.815 |
| InstructPix2Pix | 0.316 | 0.443 | 0.624 | 0.461 | 0.191 | 0.000 | 23.605 | 0.646 | 0.322 |
| Qwen-Image-Edit | 0.594 | 0.549 | 0.900 | 0.681 | 0.285 | 0.105 | 22.436 | 0.875 | 0.201 |
| Qwen-Image-Edit + CoT | 0.645 | 0.595 | 0.882 | 0.707 | 0.282 | 0.111 | 22.623 | 0.865 | 0.225 |
| Qwen-Image-Edit + Oracle-SCM | 0.644 | 0.647 | 0.887 | 0.726 | 0.350 | 0.139 | 22.640 | 0.847 | 0.260 |
| Qwen-Image-Edit + CausalScaffold | 0.634 | 0.633 | 0.904 | 0.724 | 0.321 | 0.173 | 22.562 | 0.859 | 0.242 |
| SD1.5-Inpaint | 0.449 | 0.471 | 0.212 | 0.377 | 0.198 | 0.000 | 26.026 | 0.229 | 0.741 |
| SD2-Inpaint | 0.463 | 0.463 | 0.217 | 0.381 | 0.182 | 0.000 | 26.245 | 0.231 | 0.741 |
| SDXL-Inpaint | 0.437 | 0.450 | 0.236 | 0.374 | 0.168 | 0.000 | 26.263 | 0.307 | 0.599 |

## CCS by Task domain

### FLUX.1-Fill
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.414 | 0.495 | 0.200 | 0.009 | 108 |
| commonsense | 0.311 | 0.365 | 0.245 | 0.000 | 108 |
| multi_step | 0.329 | 0.393 | 0.182 | 0.000 | 108 |

### InstructPix2Pix
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.465 | 0.471 | 0.591 | 0.000 | 108 |
| commonsense | 0.467 | 0.443 | 0.671 | 0.000 | 108 |
| multi_step | 0.451 | 0.416 | 0.610 | 0.000 | 108 |

### Qwen-Image-Edit
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.710 | 0.535 | 0.937 | 0.139 | 108 |
| commonsense | 0.691 | 0.610 | 0.841 | 0.120 | 108 |
| multi_step | 0.643 | 0.502 | 0.923 | 0.056 | 108 |

### Qwen-Image-Edit + CausalScaffold
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.781 | 0.676 | 0.918 | 0.259 | 108 |
| commonsense | 0.744 | 0.667 | 0.873 | 0.204 | 108 |
| multi_step | 0.647 | 0.556 | 0.921 | 0.056 | 108 |

### Qwen-Image-Edit + CoT
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.753 | 0.608 | 0.897 | 0.111 | 108 |
| commonsense | 0.721 | 0.656 | 0.836 | 0.148 | 108 |
| multi_step | 0.648 | 0.520 | 0.914 | 0.074 | 108 |

### Qwen-Image-Edit + Oracle-SCM
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.756 | 0.669 | 0.887 | 0.185 | 108 |
| commonsense | 0.741 | 0.707 | 0.873 | 0.148 | 108 |
| multi_step | 0.680 | 0.565 | 0.901 | 0.083 | 108 |

### SD1.5-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.396 | 0.488 | 0.181 | 0.000 | 108 |
| commonsense | 0.365 | 0.452 | 0.269 | 0.000 | 108 |
| multi_step | 0.371 | 0.475 | 0.184 | 0.000 | 108 |

### SD2-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.401 | 0.511 | 0.216 | 0.000 | 108 |
| commonsense | 0.384 | 0.447 | 0.257 | 0.000 | 108 |
| multi_step | 0.357 | 0.431 | 0.177 | 0.000 | 108 |

### SDXL-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.392 | 0.495 | 0.205 | 0.000 | 108 |
| commonsense | 0.383 | 0.452 | 0.275 | 0.000 | 108 |
| multi_step | 0.347 | 0.402 | 0.226 | 0.000 | 108 |

## CCS by Difficulty

### FLUX.1-Fill
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.357 | 0.393 | 0.203 | 0.012 | 84 |
| hard | 0.323 | 0.398 | 0.215 | 0.000 | 83 |
| medium | 0.363 | 0.442 | 0.209 | 0.000 | 157 |

### InstructPix2Pix
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.472 | 0.448 | 0.651 | 0.000 | 84 |
| hard | 0.435 | 0.426 | 0.549 | 0.000 | 83 |
| medium | 0.469 | 0.450 | 0.649 | 0.000 | 157 |

### Qwen-Image-Edit
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.693 | 0.521 | 0.938 | 0.167 | 84 |
| hard | 0.650 | 0.513 | 0.926 | 0.036 | 83 |
| medium | 0.691 | 0.584 | 0.866 | 0.108 | 157 |

### Qwen-Image-Edit + CausalScaffold
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.772 | 0.679 | 0.923 | 0.262 | 84 |
| hard | 0.649 | 0.555 | 0.886 | 0.060 | 83 |
| medium | 0.738 | 0.650 | 0.904 | 0.185 | 157 |

### Qwen-Image-Edit + CoT
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.724 | 0.592 | 0.918 | 0.167 | 84 |
| hard | 0.656 | 0.543 | 0.896 | 0.060 | 83 |
| medium | 0.726 | 0.623 | 0.857 | 0.108 | 157 |

### Qwen-Image-Edit + Oracle-SCM
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.752 | 0.653 | 0.883 | 0.238 | 84 |
| hard | 0.680 | 0.606 | 0.880 | 0.060 | 83 |
| medium | 0.736 | 0.665 | 0.894 | 0.127 | 157 |

### SD1.5-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.372 | 0.440 | 0.200 | 0.000 | 84 |
| hard | 0.353 | 0.480 | 0.217 | 0.000 | 83 |
| medium | 0.393 | 0.484 | 0.215 | 0.000 | 157 |

### SD2-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.392 | 0.457 | 0.213 | 0.000 | 84 |
| hard | 0.364 | 0.455 | 0.227 | 0.000 | 83 |
| medium | 0.384 | 0.470 | 0.213 | 0.000 | 157 |

### SDXL-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.399 | 0.484 | 0.225 | 0.000 | 84 |
| hard | 0.341 | 0.398 | 0.229 | 0.000 | 83 |
| medium | 0.378 | 0.459 | 0.245 | 0.000 | 157 |

## CCS by Fine-grained task type

### FLUX.1-Fill
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.327 | 0.359 | 0.220 | 0.000 | 36 |
| counterfactual | 0.441 | 0.509 | 0.190 | 0.000 | 36 |
| functional | 0.333 | 0.433 | 0.220 | 0.000 | 36 |
| long_horizon | 0.290 | 0.431 | 0.162 | 0.000 | 36 |
| multi | 0.421 | 0.537 | 0.211 | 0.000 | 36 |
| physical | 0.359 | 0.375 | 0.271 | 0.000 | 36 |
| sequential | 0.370 | 0.389 | 0.164 | 0.000 | 36 |
| single | 0.380 | 0.440 | 0.199 | 0.028 | 36 |
| social | 0.242 | 0.287 | 0.245 | 0.000 | 36 |

### InstructPix2Pix
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.493 | 0.456 | 0.676 | 0.000 | 36 |
| counterfactual | 0.465 | 0.535 | 0.650 | 0.000 | 36 |
| functional | 0.408 | 0.414 | 0.644 | 0.000 | 36 |
| long_horizon | 0.397 | 0.412 | 0.472 | 0.000 | 36 |
| multi | 0.471 | 0.435 | 0.604 | 0.000 | 36 |
| physical | 0.510 | 0.465 | 0.648 | 0.000 | 36 |
| sequential | 0.465 | 0.380 | 0.681 | 0.000 | 36 |
| single | 0.460 | 0.444 | 0.519 | 0.000 | 36 |
| social | 0.483 | 0.449 | 0.722 | 0.000 | 36 |

### Qwen-Image-Edit
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.657 | 0.498 | 0.903 | 0.111 | 36 |
| counterfactual | 0.689 | 0.553 | 0.958 | 0.167 | 36 |
| functional | 0.704 | 0.646 | 0.896 | 0.194 | 36 |
| long_horizon | 0.569 | 0.500 | 0.944 | 0.000 | 36 |
| multi | 0.738 | 0.546 | 0.903 | 0.083 | 36 |
| physical | 0.714 | 0.620 | 0.868 | 0.167 | 36 |
| sequential | 0.704 | 0.509 | 0.921 | 0.056 | 36 |
| single | 0.703 | 0.507 | 0.949 | 0.167 | 36 |
| social | 0.654 | 0.565 | 0.759 | 0.000 | 36 |

### Qwen-Image-Edit + CausalScaffold
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.701 | 0.590 | 0.931 | 0.111 | 36 |
| counterfactual | 0.736 | 0.662 | 0.894 | 0.194 | 36 |
| functional | 0.718 | 0.685 | 0.914 | 0.194 | 36 |
| long_horizon | 0.537 | 0.514 | 0.917 | 0.000 | 36 |
| multi | 0.799 | 0.657 | 0.935 | 0.222 | 36 |
| physical | 0.738 | 0.646 | 0.873 | 0.250 | 36 |
| sequential | 0.702 | 0.565 | 0.917 | 0.056 | 36 |
| single | 0.809 | 0.708 | 0.926 | 0.361 | 36 |
| social | 0.775 | 0.671 | 0.833 | 0.167 | 36 |

### Qwen-Image-Edit + CoT
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.654 | 0.505 | 0.889 | 0.111 | 36 |
| counterfactual | 0.739 | 0.611 | 0.912 | 0.139 | 36 |
| functional | 0.724 | 0.681 | 0.866 | 0.194 | 36 |
| long_horizon | 0.549 | 0.491 | 0.935 | 0.000 | 36 |
| multi | 0.762 | 0.616 | 0.852 | 0.083 | 36 |
| physical | 0.736 | 0.681 | 0.861 | 0.222 | 36 |
| sequential | 0.739 | 0.565 | 0.917 | 0.111 | 36 |
| single | 0.758 | 0.597 | 0.928 | 0.111 | 36 |
| social | 0.704 | 0.606 | 0.782 | 0.028 | 36 |

### Qwen-Image-Edit + Oracle-SCM
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.708 | 0.569 | 0.861 | 0.194 | 36 |
| counterfactual | 0.746 | 0.627 | 0.917 | 0.139 | 36 |
| functional | 0.721 | 0.692 | 0.917 | 0.194 | 36 |
| long_horizon | 0.585 | 0.560 | 0.931 | 0.028 | 36 |
| multi | 0.755 | 0.657 | 0.884 | 0.139 | 36 |
| physical | 0.737 | 0.748 | 0.838 | 0.167 | 36 |
| sequential | 0.747 | 0.565 | 0.912 | 0.028 | 36 |
| single | 0.769 | 0.722 | 0.861 | 0.278 | 36 |
| social | 0.765 | 0.681 | 0.866 | 0.083 | 36 |

### SD1.5-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.394 | 0.461 | 0.164 | 0.000 | 36 |
| counterfactual | 0.417 | 0.565 | 0.188 | 0.000 | 36 |
| functional | 0.352 | 0.486 | 0.222 | 0.000 | 36 |
| long_horizon | 0.309 | 0.481 | 0.222 | 0.000 | 36 |
| multi | 0.414 | 0.486 | 0.185 | 0.000 | 36 |
| physical | 0.407 | 0.454 | 0.308 | 0.000 | 36 |
| sequential | 0.410 | 0.481 | 0.167 | 0.000 | 36 |
| single | 0.356 | 0.412 | 0.171 | 0.000 | 36 |
| social | 0.338 | 0.417 | 0.277 | 0.000 | 36 |

### SD2-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.399 | 0.426 | 0.174 | 0.000 | 36 |
| counterfactual | 0.410 | 0.546 | 0.241 | 0.000 | 36 |
| functional | 0.367 | 0.475 | 0.211 | 0.000 | 36 |
| long_horizon | 0.312 | 0.403 | 0.185 | 0.000 | 36 |
| multi | 0.407 | 0.546 | 0.176 | 0.000 | 36 |
| physical | 0.404 | 0.444 | 0.280 | 0.000 | 36 |
| sequential | 0.360 | 0.463 | 0.171 | 0.000 | 36 |
| single | 0.386 | 0.440 | 0.231 | 0.000 | 36 |
| social | 0.382 | 0.421 | 0.281 | 0.000 | 36 |

### SDXL-Inpaint
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.395 | 0.437 | 0.220 | 0.000 | 36 |
| counterfactual | 0.388 | 0.558 | 0.218 | 0.000 | 36 |
| functional | 0.388 | 0.507 | 0.227 | 0.000 | 36 |
| long_horizon | 0.316 | 0.394 | 0.236 | 0.000 | 36 |
| multi | 0.418 | 0.481 | 0.204 | 0.000 | 36 |
| physical | 0.376 | 0.447 | 0.306 | 0.000 | 36 |
| sequential | 0.329 | 0.375 | 0.222 | 0.000 | 36 |
| single | 0.370 | 0.444 | 0.194 | 0.000 | 36 |
| social | 0.385 | 0.403 | 0.294 | 0.000 | 36 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| FLUX.1-Fill | 0.003 | 0.000 | 0.235 | 0.731 | 0.000 | 0.031 |
| InstructPix2Pix | 0.000 | 0.361 | 0.213 | 0.377 | 0.006 | 0.043 |
| Qwen-Image-Edit | 0.105 | 0.293 | 0.361 | 0.160 | 0.040 | 0.040 |
| Qwen-Image-Edit + CoT | 0.111 | 0.241 | 0.373 | 0.160 | 0.049 | 0.065 |
| Qwen-Image-Edit + Oracle-SCM | 0.139 | 0.204 | 0.352 | 0.194 | 0.062 | 0.049 |
| Qwen-Image-Edit + CausalScaffold | 0.173 | 0.256 | 0.299 | 0.151 | 0.077 | 0.043 |
| SD1.5-Inpaint | 0.000 | 0.000 | 0.278 | 0.670 | 0.000 | 0.052 |
| SD2-Inpaint | 0.000 | 0.000 | 0.299 | 0.664 | 0.003 | 0.034 |
| SDXL-Inpaint | 0.000 | 0.000 | 0.259 | 0.673 | 0.000 | 0.068 |
