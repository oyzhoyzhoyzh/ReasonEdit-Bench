# ReasonEdit-Bench results

## Overall (all 324 items, 2 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| instructpix2pix__cf | 0.216 | 0.360 | 0.553 | 0.377 | 0.151 | 0.012 | 22.286 | 0.628 | 0.327 |
| qwen_image_edit__cf | 0.375 | 0.409 | 0.871 | 0.552 | 0.219 | 0.049 | 21.953 | 0.883 | 0.184 |

## CCS by Task domain

### instructpix2pix__cf
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.385 | 0.409 | 0.529 | 0.019 | 108 |
| commonsense | 0.364 | 0.343 | 0.559 | 0.009 | 108 |
| multi_step | 0.380 | 0.329 | 0.571 | 0.009 | 108 |

### qwen_image_edit__cf
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.583 | 0.421 | 0.878 | 0.037 | 108 |
| commonsense | 0.544 | 0.407 | 0.860 | 0.074 | 108 |
| multi_step | 0.528 | 0.400 | 0.875 | 0.037 | 108 |

## CCS by Difficulty

### instructpix2pix__cf
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.408 | 0.405 | 0.611 | 0.024 | 84 |
| hard | 0.343 | 0.321 | 0.490 | 0.000 | 83 |
| medium | 0.378 | 0.357 | 0.556 | 0.013 | 157 |

### qwen_image_edit__cf
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.554 | 0.396 | 0.843 | 0.083 | 84 |
| hard | 0.525 | 0.396 | 0.898 | 0.036 | 83 |
| medium | 0.565 | 0.424 | 0.872 | 0.038 | 157 |

## CCS by Fine-grained task type

### instructpix2pix__cf
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.448 | 0.370 | 0.694 | 0.028 | 36 |
| counterfactual | 0.421 | 0.495 | 0.435 | 0.028 | 36 |
| functional | 0.357 | 0.368 | 0.537 | 0.000 | 36 |
| long_horizon | 0.302 | 0.264 | 0.477 | 0.000 | 36 |
| multi | 0.360 | 0.361 | 0.593 | 0.000 | 36 |
| physical | 0.396 | 0.431 | 0.535 | 0.028 | 36 |
| sequential | 0.390 | 0.352 | 0.542 | 0.000 | 36 |
| single | 0.375 | 0.370 | 0.560 | 0.028 | 36 |
| social | 0.340 | 0.231 | 0.606 | 0.000 | 36 |

### qwen_image_edit__cf
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.517 | 0.394 | 0.810 | 0.056 | 36 |
| counterfactual | 0.620 | 0.421 | 0.884 | 0.056 | 36 |
| functional | 0.551 | 0.454 | 0.852 | 0.083 | 36 |
| long_horizon | 0.483 | 0.370 | 0.940 | 0.000 | 36 |
| multi | 0.557 | 0.491 | 0.847 | 0.000 | 36 |
| physical | 0.560 | 0.491 | 0.870 | 0.111 | 36 |
| sequential | 0.585 | 0.435 | 0.875 | 0.056 | 36 |
| single | 0.571 | 0.352 | 0.903 | 0.056 | 36 |
| social | 0.522 | 0.278 | 0.859 | 0.028 | 36 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| instructpix2pix__cf | 0.012 | 0.302 | 0.167 | 0.497 | 0.000 | 0.022 |
| qwen_image_edit__cf | 0.049 | 0.395 | 0.296 | 0.247 | 0.000 | 0.012 |
