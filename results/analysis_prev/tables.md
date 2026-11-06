# ReasonEdit-Bench results

## Overall (all 300 items)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| InstructPix2Pix | 0.316 | 0.443 | 0.624 | 0.461 | 0.191 | 0.000 | 23.605 | 0.646 | 0.322 |
| Qwen-Image-Edit | 0.616 | 0.597 | 0.882 | 0.698 | 0.302 | 0.110 | 22.645 | 0.878 | 0.198 |
| Qwen-Image-Edit + CoT | 0.681 | 0.584 | 0.880 | 0.715 | 0.268 | 0.132 | 22.758 | 0.873 | 0.224 |
| Qwen-Image-Edit + Oracle-SCM | 0.000 | 0.167 | 0.833 | 0.333 | 0.000 | 0.000 | 23.993 | 0.765 | 0.227 |
| SDXL-Inpaint | 0.437 | 0.450 | 0.235 | 0.374 | 0.168 | 0.000 | 26.263 | 0.307 | 0.599 |

## CCS by Task domain

### InstructPix2Pix
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.465 | 0.471 | 0.591 | 0.000 | 108 |
| commonsense | 0.467 | 0.443 | 0.671 | 0.000 | 108 |
| multi_step | 0.451 | 0.416 | 0.610 | 0.000 | 108 |

### Qwen-Image-Edit
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.776 | 0.623 | 0.944 | 0.185 | 27 |
| commonsense | 0.653 | 0.625 | 0.798 | 0.071 | 28 |
| multi_step | 0.668 | 0.540 | 0.907 | 0.074 | 27 |

### Qwen-Image-Edit + CoT
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.759 | 0.595 | 0.912 | 0.160 | 50 |
| commonsense | 0.732 | 0.654 | 0.817 | 0.157 | 51 |
| multi_step | 0.655 | 0.503 | 0.912 | 0.078 | 51 |

### Qwen-Image-Edit + Oracle-SCM
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| commonsense | 0.444 | 0.333 | 1.000 | 0.000 | 1 |
| multi_step | 0.222 | 0.000 | 0.667 | 0.000 | 1 |

### SDXL-Inpaint
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.392 | 0.495 | 0.205 | 0.000 | 108 |
| commonsense | 0.382 | 0.452 | 0.273 | 0.000 | 108 |
| multi_step | 0.347 | 0.402 | 0.226 | 0.000 | 108 |

## CCS by Difficulty

### InstructPix2Pix
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.472 | 0.448 | 0.651 | 0.000 | 84 |
| hard | 0.435 | 0.426 | 0.549 | 0.000 | 83 |
| medium | 0.469 | 0.450 | 0.649 | 0.000 | 157 |

### Qwen-Image-Edit
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.765 | 0.592 | 0.912 | 0.211 | 19 |
| hard | 0.690 | 0.535 | 0.931 | 0.000 | 24 |
| medium | 0.671 | 0.637 | 0.838 | 0.128 | 39 |

### Qwen-Image-Edit + CoT
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.739 | 0.577 | 0.921 | 0.231 | 39 |
| hard | 0.682 | 0.500 | 0.895 | 0.047 | 43 |
| medium | 0.722 | 0.639 | 0.848 | 0.129 | 70 |

### Qwen-Image-Edit + Oracle-SCM
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| hard | 0.222 | 0.000 | 0.667 | 0.000 | 1 |
| medium | 0.444 | 0.333 | 1.000 | 0.000 | 1 |

### SDXL-Inpaint
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.399 | 0.484 | 0.225 | 0.000 | 84 |
| hard | 0.341 | 0.398 | 0.229 | 0.000 | 83 |
| medium | 0.377 | 0.459 | 0.243 | 0.000 | 157 |

## CCS by Fine-grained task type

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
| conditional | 0.812 | 0.806 | 0.907 | 0.222 | 9 |
| counterfactual | 0.744 | 0.602 | 0.963 | 0.222 | 9 |
| functional | 0.679 | 0.667 | 0.870 | 0.222 | 9 |
| long_horizon | 0.525 | 0.315 | 0.926 | 0.000 | 9 |
| multi | 0.753 | 0.630 | 0.907 | 0.111 | 9 |
| physical | 0.578 | 0.500 | 0.783 | 0.000 | 10 |
| sequential | 0.667 | 0.500 | 0.889 | 0.000 | 9 |
| single | 0.830 | 0.639 | 0.963 | 0.222 | 9 |
| social | 0.710 | 0.722 | 0.741 | 0.000 | 9 |

### Qwen-Image-Edit + CoT
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.680 | 0.539 | 0.912 | 0.176 | 17 |
| counterfactual | 0.762 | 0.682 | 0.917 | 0.188 | 16 |
| functional | 0.768 | 0.735 | 0.892 | 0.176 | 17 |
| long_horizon | 0.565 | 0.412 | 0.902 | 0.000 | 17 |
| multi | 0.752 | 0.520 | 0.882 | 0.118 | 17 |
| physical | 0.673 | 0.588 | 0.784 | 0.235 | 17 |
| sequential | 0.719 | 0.559 | 0.922 | 0.059 | 17 |
| single | 0.763 | 0.588 | 0.936 | 0.176 | 17 |
| social | 0.755 | 0.637 | 0.775 | 0.059 | 17 |

### Qwen-Image-Edit + Oracle-SCM
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| long_horizon | 0.222 | 0.000 | 0.667 | 0.000 | 1 |
| physical | 0.444 | 0.333 | 1.000 | 0.000 | 1 |

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
| social | 0.383 | 0.403 | 0.287 | 0.000 | 36 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| InstructPix2Pix | 0.000 | 0.361 | 0.213 | 0.377 | 0.006 | 0.043 |
| Qwen-Image-Edit | 0.110 | 0.280 | 0.366 | 0.146 | 0.061 | 0.037 |
| Qwen-Image-Edit + CoT | 0.132 | 0.224 | 0.375 | 0.138 | 0.046 | 0.086 |
| Qwen-Image-Edit + Oracle-SCM | 0.000 | 0.500 | 0.000 | 0.500 | 0.000 | 0.000 |
| SDXL-Inpaint | 0.000 | 0.000 | 0.259 | 0.673 | 0.000 | 0.068 |
