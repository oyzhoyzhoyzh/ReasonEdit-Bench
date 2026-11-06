# ReasonEdit-Bench results

## Overall (all 108 items, 3 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| flux_kontext_s1 | 0.380 | 0.414 | 0.848 | 0.547 | 0.208 | 0.019 | -- | -- | -- |
| flux_kontext_s2 | 0.449 | 0.434 | 0.809 | 0.564 | 0.222 | 0.028 | -- | -- | -- |
| flux_kontext_s3 | 0.398 | 0.432 | 0.847 | 0.559 | 0.167 | 0.009 | -- | -- | -- |

## CCS by Task domain

### flux_kontext_s1
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.561 | 0.454 | 0.840 | 0.000 | 36 |
| commonsense | 0.530 | 0.373 | 0.829 | 0.000 | 36 |
| multi_step | 0.551 | 0.417 | 0.875 | 0.056 | 36 |

### flux_kontext_s2
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.582 | 0.477 | 0.810 | 0.028 | 36 |
| commonsense | 0.544 | 0.403 | 0.785 | 0.000 | 36 |
| multi_step | 0.567 | 0.424 | 0.833 | 0.056 | 36 |

### flux_kontext_s3
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.592 | 0.479 | 0.880 | 0.000 | 36 |
| commonsense | 0.568 | 0.449 | 0.838 | 0.000 | 36 |
| multi_step | 0.518 | 0.368 | 0.824 | 0.028 | 36 |

## CCS by Difficulty

### flux_kontext_s1
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.511 | 0.240 | 0.873 | 0.000 | 25 |
| hard | 0.510 | 0.422 | 0.833 | 0.000 | 31 |
| medium | 0.587 | 0.494 | 0.845 | 0.038 | 52 |

### flux_kontext_s2
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.559 | 0.250 | 0.867 | 0.000 | 25 |
| hard | 0.516 | 0.444 | 0.750 | 0.000 | 31 |
| medium | 0.596 | 0.518 | 0.817 | 0.058 | 52 |

### flux_kontext_s3
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.524 | 0.280 | 0.893 | 0.000 | 25 |
| hard | 0.524 | 0.411 | 0.806 | 0.000 | 31 |
| medium | 0.597 | 0.518 | 0.849 | 0.019 | 52 |

## CCS by Fine-grained task type

### flux_kontext_s1
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.597 | 0.417 | 0.917 | 0.167 | 12 |
| counterfactual | 0.641 | 0.562 | 0.903 | 0.000 | 12 |
| functional | 0.530 | 0.354 | 0.903 | 0.000 | 12 |
| long_horizon | 0.495 | 0.403 | 0.792 | 0.000 | 12 |
| multi | 0.477 | 0.458 | 0.806 | 0.000 | 12 |
| physical | 0.505 | 0.333 | 0.764 | 0.000 | 12 |
| sequential | 0.560 | 0.431 | 0.917 | 0.000 | 12 |
| single | 0.565 | 0.340 | 0.812 | 0.000 | 12 |
| social | 0.556 | 0.431 | 0.819 | 0.000 | 12 |

### flux_kontext_s2
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.660 | 0.438 | 0.917 | 0.167 | 12 |
| counterfactual | 0.623 | 0.590 | 0.903 | 0.000 | 12 |
| functional | 0.530 | 0.312 | 0.944 | 0.000 | 12 |
| long_horizon | 0.463 | 0.431 | 0.750 | 0.000 | 12 |
| multi | 0.593 | 0.569 | 0.792 | 0.083 | 12 |
| physical | 0.519 | 0.438 | 0.660 | 0.000 | 12 |
| sequential | 0.579 | 0.403 | 0.833 | 0.000 | 12 |
| single | 0.530 | 0.271 | 0.736 | 0.000 | 12 |
| social | 0.583 | 0.458 | 0.750 | 0.000 | 12 |

### flux_kontext_s3
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.539 | 0.354 | 0.889 | 0.083 | 12 |
| counterfactual | 0.604 | 0.549 | 0.889 | 0.000 | 12 |
| functional | 0.544 | 0.438 | 0.944 | 0.000 | 12 |
| long_horizon | 0.491 | 0.361 | 0.778 | 0.000 | 12 |
| multi | 0.602 | 0.597 | 0.875 | 0.000 | 12 |
| physical | 0.516 | 0.382 | 0.750 | 0.000 | 12 |
| sequential | 0.523 | 0.389 | 0.806 | 0.000 | 12 |
| single | 0.569 | 0.292 | 0.875 | 0.000 | 12 |
| social | 0.644 | 0.528 | 0.819 | 0.000 | 12 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| flux_kontext_s1 | 0.019 | 0.778 | 0.167 | 0.000 | 0.019 | 0.019 |
| flux_kontext_s2 | 0.028 | 0.704 | 0.222 | 0.000 | 0.019 | 0.028 |
| flux_kontext_s3 | 0.009 | 0.778 | 0.185 | 0.000 | 0.019 | 0.009 |
