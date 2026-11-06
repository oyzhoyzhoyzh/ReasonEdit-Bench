# ReasonEdit-Bench results

## Overall (all 108 items, 12 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| qwen_multiseed_s20260924 | 0.648 | 0.539 | 0.898 | 0.695 | 0.315 | 0.102 | -- | -- | -- |
| qwen_multiseed_s20260924__cot | 0.694 | 0.579 | 0.861 | 0.712 | 0.264 | 0.093 | -- | -- | -- |
| qwen_multiseed_s20260924__oracle | 0.704 | 0.649 | 0.858 | 0.737 | 0.412 | 0.167 | -- | -- | -- |
| qwen_multiseed_s20260924__scaffold_full | 0.648 | 0.601 | 0.907 | 0.719 | 0.356 | 0.157 | -- | -- | -- |
| qwen_multiseed_s20260925 | 0.625 | 0.546 | 0.903 | 0.691 | 0.347 | 0.120 | -- | -- | -- |
| qwen_multiseed_s20260925__cot | 0.644 | 0.586 | 0.875 | 0.702 | 0.324 | 0.148 | -- | -- | -- |
| qwen_multiseed_s20260925__oracle | 0.690 | 0.650 | 0.897 | 0.746 | 0.389 | 0.176 | -- | -- | -- |
| qwen_multiseed_s20260925__scaffold_full | 0.634 | 0.615 | 0.912 | 0.720 | 0.394 | 0.157 | -- | -- | -- |
| qwen_multiseed_s20260926 | 0.611 | 0.539 | 0.873 | 0.674 | 0.269 | 0.093 | -- | -- | -- |
| qwen_multiseed_s20260926__cot | 0.639 | 0.575 | 0.864 | 0.693 | 0.227 | 0.074 | -- | -- | -- |
| qwen_multiseed_s20260926__oracle | 0.653 | 0.631 | 0.869 | 0.718 | 0.384 | 0.130 | -- | -- | -- |
| qwen_multiseed_s20260926__scaffold_full | 0.620 | 0.588 | 0.903 | 0.704 | 0.375 | 0.167 | -- | -- | -- |

## CCS by Task domain

### qwen_multiseed_s20260924
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.714 | 0.475 | 0.917 | 0.083 | 36 |
| commonsense | 0.692 | 0.609 | 0.829 | 0.111 | 36 |
| multi_step | 0.680 | 0.535 | 0.949 | 0.111 | 36 |

### qwen_multiseed_s20260924__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.743 | 0.581 | 0.856 | 0.139 | 36 |
| commonsense | 0.712 | 0.627 | 0.815 | 0.083 | 36 |
| multi_step | 0.680 | 0.530 | 0.912 | 0.056 | 36 |

### qwen_multiseed_s20260924__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.728 | 0.644 | 0.819 | 0.194 | 36 |
| commonsense | 0.758 | 0.681 | 0.843 | 0.167 | 36 |
| multi_step | 0.725 | 0.623 | 0.912 | 0.139 | 36 |

### qwen_multiseed_s20260924__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.745 | 0.606 | 0.949 | 0.222 | 36 |
| commonsense | 0.717 | 0.641 | 0.856 | 0.111 | 36 |
| multi_step | 0.694 | 0.556 | 0.917 | 0.139 | 36 |

### qwen_multiseed_s20260925
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.667 | 0.472 | 0.917 | 0.056 | 36 |
| commonsense | 0.725 | 0.641 | 0.838 | 0.167 | 36 |
| multi_step | 0.683 | 0.525 | 0.954 | 0.139 | 36 |

### qwen_multiseed_s20260925__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.716 | 0.560 | 0.880 | 0.139 | 36 |
| commonsense | 0.709 | 0.637 | 0.810 | 0.139 | 36 |
| multi_step | 0.680 | 0.562 | 0.935 | 0.167 | 36 |

### qwen_multiseed_s20260925__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.745 | 0.667 | 0.887 | 0.167 | 36 |
| commonsense | 0.796 | 0.718 | 0.880 | 0.222 | 36 |
| multi_step | 0.697 | 0.567 | 0.926 | 0.139 | 36 |

### qwen_multiseed_s20260925__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.750 | 0.667 | 0.917 | 0.167 | 36 |
| commonsense | 0.711 | 0.616 | 0.866 | 0.139 | 36 |
| multi_step | 0.700 | 0.562 | 0.954 | 0.167 | 36 |

### qwen_multiseed_s20260926
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.732 | 0.516 | 0.903 | 0.111 | 36 |
| commonsense | 0.671 | 0.623 | 0.780 | 0.056 | 36 |
| multi_step | 0.620 | 0.479 | 0.935 | 0.111 | 36 |

### qwen_multiseed_s20260926__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.762 | 0.579 | 0.861 | 0.083 | 36 |
| commonsense | 0.684 | 0.671 | 0.796 | 0.083 | 36 |
| multi_step | 0.632 | 0.475 | 0.935 | 0.056 | 36 |

### qwen_multiseed_s20260926__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.733 | 0.639 | 0.838 | 0.111 | 36 |
| commonsense | 0.743 | 0.697 | 0.852 | 0.139 | 36 |
| multi_step | 0.677 | 0.558 | 0.917 | 0.139 | 36 |

### qwen_multiseed_s20260926__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.733 | 0.611 | 0.935 | 0.250 | 36 |
| commonsense | 0.692 | 0.595 | 0.856 | 0.083 | 36 |
| multi_step | 0.686 | 0.558 | 0.917 | 0.167 | 36 |

## CCS by Difficulty

### qwen_multiseed_s20260924
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.671 | 0.440 | 0.873 | 0.120 | 25 |
| hard | 0.673 | 0.503 | 0.952 | 0.032 | 31 |
| medium | 0.720 | 0.609 | 0.878 | 0.135 | 52 |

### qwen_multiseed_s20260924__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.672 | 0.470 | 0.807 | 0.120 | 25 |
| hard | 0.671 | 0.524 | 0.909 | 0.032 | 31 |
| medium | 0.755 | 0.665 | 0.859 | 0.115 | 52 |

### qwen_multiseed_s20260924__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.763 | 0.690 | 0.820 | 0.200 | 25 |
| hard | 0.700 | 0.589 | 0.882 | 0.129 | 31 |
| medium | 0.746 | 0.665 | 0.862 | 0.173 | 52 |

### qwen_multiseed_s20260924__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.684 | 0.540 | 0.853 | 0.200 | 25 |
| hard | 0.703 | 0.556 | 0.909 | 0.065 | 31 |
| medium | 0.745 | 0.657 | 0.933 | 0.192 | 52 |

### qwen_multiseed_s20260925
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.686 | 0.490 | 0.927 | 0.160 | 25 |
| hard | 0.675 | 0.519 | 0.957 | 0.032 | 31 |
| medium | 0.704 | 0.590 | 0.859 | 0.154 | 52 |

### qwen_multiseed_s20260925__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.694 | 0.510 | 0.893 | 0.160 | 25 |
| hard | 0.662 | 0.535 | 0.919 | 0.065 | 31 |
| medium | 0.729 | 0.654 | 0.840 | 0.192 | 52 |

### qwen_multiseed_s20260925__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.741 | 0.590 | 0.893 | 0.120 | 25 |
| hard | 0.707 | 0.605 | 0.903 | 0.129 | 31 |
| medium | 0.771 | 0.707 | 0.896 | 0.231 | 52 |

### qwen_multiseed_s20260925__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.697 | 0.570 | 0.900 | 0.160 | 25 |
| hard | 0.677 | 0.562 | 0.935 | 0.065 | 31 |
| medium | 0.758 | 0.668 | 0.904 | 0.212 | 52 |

### qwen_multiseed_s20260926
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.677 | 0.450 | 0.900 | 0.200 | 25 |
| hard | 0.635 | 0.503 | 0.871 | 0.032 | 31 |
| medium | 0.697 | 0.604 | 0.861 | 0.077 | 52 |

### qwen_multiseed_s20260926__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.686 | 0.530 | 0.827 | 0.160 | 25 |
| hard | 0.655 | 0.530 | 0.871 | 0.032 | 31 |
| medium | 0.718 | 0.623 | 0.878 | 0.058 | 52 |

### qwen_multiseed_s20260926__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.748 | 0.650 | 0.833 | 0.240 | 25 |
| hard | 0.638 | 0.565 | 0.833 | 0.032 | 31 |
| medium | 0.751 | 0.662 | 0.907 | 0.135 | 52 |

### qwen_multiseed_s20260926__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.693 | 0.540 | 0.840 | 0.240 | 25 |
| hard | 0.649 | 0.527 | 0.903 | 0.065 | 31 |
| medium | 0.741 | 0.647 | 0.933 | 0.192 | 52 |

## CCS by Fine-grained task type

### qwen_multiseed_s20260924
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.725 | 0.479 | 0.903 | 0.167 | 12 |
| counterfactual | 0.741 | 0.542 | 0.972 | 0.083 | 12 |
| functional | 0.660 | 0.646 | 0.833 | 0.083 | 12 |
| long_horizon | 0.597 | 0.486 | 0.972 | 0.000 | 12 |
| multi | 0.736 | 0.528 | 0.806 | 0.083 | 12 |
| physical | 0.657 | 0.556 | 0.833 | 0.167 | 12 |
| sequential | 0.718 | 0.639 | 0.972 | 0.167 | 12 |
| single | 0.664 | 0.354 | 0.972 | 0.083 | 12 |
| social | 0.759 | 0.625 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260924__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.725 | 0.521 | 0.903 | 0.167 | 12 |
| counterfactual | 0.812 | 0.715 | 0.931 | 0.250 | 12 |
| functional | 0.678 | 0.646 | 0.847 | 0.083 | 12 |
| long_horizon | 0.579 | 0.458 | 0.861 | 0.000 | 12 |
| multi | 0.755 | 0.611 | 0.778 | 0.083 | 12 |
| physical | 0.685 | 0.583 | 0.806 | 0.083 | 12 |
| sequential | 0.736 | 0.611 | 0.972 | 0.000 | 12 |
| single | 0.662 | 0.417 | 0.861 | 0.083 | 12 |
| social | 0.773 | 0.653 | 0.792 | 0.083 | 12 |

### qwen_multiseed_s20260924__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.859 | 0.688 | 0.931 | 0.333 | 12 |
| counterfactual | 0.736 | 0.625 | 0.875 | 0.167 | 12 |
| functional | 0.759 | 0.750 | 0.861 | 0.167 | 12 |
| long_horizon | 0.597 | 0.542 | 0.917 | 0.083 | 12 |
| multi | 0.741 | 0.639 | 0.792 | 0.250 | 12 |
| physical | 0.662 | 0.611 | 0.792 | 0.167 | 12 |
| sequential | 0.718 | 0.639 | 0.889 | 0.000 | 12 |
| single | 0.708 | 0.667 | 0.792 | 0.167 | 12 |
| social | 0.852 | 0.681 | 0.875 | 0.167 | 12 |

### qwen_multiseed_s20260924__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.764 | 0.583 | 0.917 | 0.250 | 12 |
| counterfactual | 0.815 | 0.778 | 1.000 | 0.250 | 12 |
| functional | 0.662 | 0.625 | 0.903 | 0.167 | 12 |
| long_horizon | 0.611 | 0.486 | 0.889 | 0.000 | 12 |
| multi | 0.755 | 0.500 | 0.972 | 0.250 | 12 |
| physical | 0.692 | 0.660 | 0.792 | 0.083 | 12 |
| sequential | 0.708 | 0.597 | 0.944 | 0.167 | 12 |
| single | 0.667 | 0.542 | 0.875 | 0.167 | 12 |
| social | 0.796 | 0.639 | 0.875 | 0.083 | 12 |

### qwen_multiseed_s20260925
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.757 | 0.562 | 0.917 | 0.333 | 12 |
| counterfactual | 0.634 | 0.472 | 0.931 | 0.000 | 12 |
| functional | 0.738 | 0.646 | 0.861 | 0.250 | 12 |
| long_horizon | 0.579 | 0.472 | 0.972 | 0.000 | 12 |
| multi | 0.708 | 0.528 | 0.889 | 0.083 | 12 |
| physical | 0.681 | 0.583 | 0.833 | 0.167 | 12 |
| sequential | 0.713 | 0.542 | 0.972 | 0.083 | 12 |
| single | 0.657 | 0.417 | 0.931 | 0.083 | 12 |
| social | 0.755 | 0.694 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260925__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.766 | 0.604 | 0.944 | 0.333 | 12 |
| counterfactual | 0.750 | 0.569 | 0.931 | 0.083 | 12 |
| functional | 0.641 | 0.562 | 0.819 | 0.167 | 12 |
| long_horizon | 0.546 | 0.472 | 0.917 | 0.000 | 12 |
| multi | 0.722 | 0.611 | 0.847 | 0.250 | 12 |
| physical | 0.639 | 0.583 | 0.792 | 0.167 | 12 |
| sequential | 0.727 | 0.611 | 0.944 | 0.167 | 12 |
| single | 0.676 | 0.500 | 0.861 | 0.083 | 12 |
| social | 0.847 | 0.764 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260925__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.766 | 0.521 | 0.944 | 0.250 | 12 |
| counterfactual | 0.708 | 0.625 | 0.875 | 0.167 | 12 |
| functional | 0.752 | 0.688 | 0.903 | 0.167 | 12 |
| long_horizon | 0.556 | 0.472 | 0.861 | 0.000 | 12 |
| multi | 0.759 | 0.750 | 0.903 | 0.250 | 12 |
| physical | 0.789 | 0.743 | 0.875 | 0.250 | 12 |
| sequential | 0.769 | 0.708 | 0.972 | 0.167 | 12 |
| single | 0.766 | 0.625 | 0.882 | 0.083 | 12 |
| social | 0.847 | 0.722 | 0.861 | 0.250 | 12 |

### qwen_multiseed_s20260925__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.817 | 0.646 | 0.972 | 0.250 | 12 |
| counterfactual | 0.806 | 0.778 | 0.972 | 0.083 | 12 |
| functional | 0.662 | 0.583 | 0.903 | 0.083 | 12 |
| long_horizon | 0.565 | 0.431 | 0.889 | 0.000 | 12 |
| multi | 0.764 | 0.639 | 0.944 | 0.333 | 12 |
| physical | 0.653 | 0.597 | 0.819 | 0.250 | 12 |
| sequential | 0.718 | 0.611 | 1.000 | 0.250 | 12 |
| single | 0.681 | 0.583 | 0.833 | 0.083 | 12 |
| social | 0.819 | 0.667 | 0.875 | 0.083 | 12 |

### qwen_multiseed_s20260926
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.688 | 0.521 | 0.917 | 0.250 | 12 |
| counterfactual | 0.750 | 0.597 | 0.903 | 0.083 | 12 |
| functional | 0.694 | 0.625 | 0.875 | 0.083 | 12 |
| long_horizon | 0.500 | 0.361 | 0.889 | 0.000 | 12 |
| multi | 0.769 | 0.556 | 0.875 | 0.083 | 12 |
| physical | 0.590 | 0.562 | 0.792 | 0.083 | 12 |
| sequential | 0.671 | 0.556 | 1.000 | 0.083 | 12 |
| single | 0.678 | 0.396 | 0.931 | 0.167 | 12 |
| social | 0.729 | 0.681 | 0.674 | 0.000 | 12 |

### qwen_multiseed_s20260926__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.688 | 0.479 | 0.917 | 0.167 | 12 |
| counterfactual | 0.785 | 0.660 | 0.903 | 0.000 | 12 |
| functional | 0.701 | 0.688 | 0.833 | 0.083 | 12 |
| long_horizon | 0.542 | 0.375 | 0.917 | 0.000 | 12 |
| multi | 0.778 | 0.556 | 0.819 | 0.083 | 12 |
| physical | 0.562 | 0.660 | 0.778 | 0.083 | 12 |
| sequential | 0.667 | 0.569 | 0.972 | 0.000 | 12 |
| single | 0.725 | 0.521 | 0.861 | 0.167 | 12 |
| social | 0.787 | 0.667 | 0.778 | 0.083 | 12 |

### qwen_multiseed_s20260926__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.794 | 0.562 | 0.944 | 0.333 | 12 |
| counterfactual | 0.704 | 0.583 | 0.861 | 0.083 | 12 |
| functional | 0.681 | 0.667 | 0.833 | 0.083 | 12 |
| long_horizon | 0.528 | 0.472 | 0.861 | 0.000 | 12 |
| multi | 0.731 | 0.667 | 0.819 | 0.167 | 12 |
| physical | 0.711 | 0.701 | 0.847 | 0.250 | 12 |
| sequential | 0.708 | 0.639 | 0.944 | 0.083 | 12 |
| single | 0.764 | 0.667 | 0.833 | 0.083 | 12 |
| social | 0.838 | 0.722 | 0.875 | 0.083 | 12 |

### qwen_multiseed_s20260926__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.817 | 0.604 | 0.972 | 0.333 | 12 |
| counterfactual | 0.769 | 0.694 | 0.944 | 0.250 | 12 |
| functional | 0.713 | 0.667 | 0.847 | 0.083 | 12 |
| long_horizon | 0.523 | 0.458 | 0.861 | 0.000 | 12 |
| multi | 0.764 | 0.583 | 1.000 | 0.250 | 12 |
| physical | 0.600 | 0.535 | 0.847 | 0.083 | 12 |
| sequential | 0.718 | 0.611 | 0.917 | 0.167 | 12 |
| single | 0.667 | 0.556 | 0.861 | 0.250 | 12 |
| social | 0.764 | 0.583 | 0.875 | 0.083 | 12 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| qwen_multiseed_s20260924 | 0.102 | 0.407 | 0.417 | 0.000 | 0.046 | 0.028 |
| qwen_multiseed_s20260924__cot | 0.093 | 0.352 | 0.472 | 0.000 | 0.028 | 0.056 |
| qwen_multiseed_s20260924__oracle | 0.167 | 0.343 | 0.361 | 0.000 | 0.056 | 0.074 |
| qwen_multiseed_s20260924__scaffold_full | 0.157 | 0.407 | 0.352 | 0.000 | 0.046 | 0.037 |
| qwen_multiseed_s20260925 | 0.120 | 0.435 | 0.352 | 0.000 | 0.046 | 0.046 |
| qwen_multiseed_s20260925__cot | 0.148 | 0.407 | 0.361 | 0.000 | 0.037 | 0.046 |
| qwen_multiseed_s20260925__oracle | 0.176 | 0.361 | 0.352 | 0.000 | 0.056 | 0.056 |
| qwen_multiseed_s20260925__scaffold_full | 0.157 | 0.407 | 0.306 | 0.000 | 0.065 | 0.065 |
| qwen_multiseed_s20260926 | 0.093 | 0.454 | 0.380 | 0.000 | 0.037 | 0.037 |
| qwen_multiseed_s20260926__cot | 0.074 | 0.417 | 0.417 | 0.000 | 0.037 | 0.056 |
| qwen_multiseed_s20260926__oracle | 0.130 | 0.398 | 0.343 | 0.000 | 0.065 | 0.065 |
| qwen_multiseed_s20260926__scaffold_full | 0.167 | 0.435 | 0.324 | 0.000 | 0.028 | 0.046 |
