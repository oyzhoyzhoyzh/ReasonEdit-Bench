# ReasonEdit-Bench results

## Overall (all 108 items, 12 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| qwen_multiseed_s20260924 | 0.644 | 0.527 | 0.900 | 0.690 | 0.306 | 0.074 | -- | -- | -- |
| qwen_multiseed_s20260924__cot | 0.699 | 0.591 | 0.863 | 0.718 | 0.338 | 0.111 | -- | -- | -- |
| qwen_multiseed_s20260924__oracle | 0.704 | 0.667 | 0.849 | 0.740 | 0.449 | 0.167 | -- | -- | -- |
| qwen_multiseed_s20260924__scaffold_full | 0.653 | 0.596 | 0.914 | 0.721 | 0.356 | 0.167 | -- | -- | -- |
| qwen_multiseed_s20260925 | 0.625 | 0.549 | 0.904 | 0.693 | 0.375 | 0.139 | -- | -- | -- |
| qwen_multiseed_s20260925__cot | 0.648 | 0.584 | 0.875 | 0.702 | 0.333 | 0.120 | -- | -- | -- |
| qwen_multiseed_s20260925__oracle | 0.694 | 0.650 | 0.890 | 0.745 | 0.389 | 0.185 | -- | -- | -- |
| qwen_multiseed_s20260925__scaffold_full | 0.634 | 0.610 | 0.915 | 0.720 | 0.403 | 0.167 | -- | -- | -- |
| qwen_multiseed_s20260926 | 0.611 | 0.544 | 0.867 | 0.674 | 0.269 | 0.093 | -- | -- | -- |
| qwen_multiseed_s20260926__cot | 0.625 | 0.585 | 0.870 | 0.693 | 0.278 | 0.111 | -- | -- | -- |
| qwen_multiseed_s20260926__oracle | 0.648 | 0.647 | 0.864 | 0.720 | 0.370 | 0.139 | -- | -- | -- |
| qwen_multiseed_s20260926__scaffold_full | 0.630 | 0.578 | 0.906 | 0.704 | 0.338 | 0.139 | -- | -- | -- |

## CCS by Task domain

### qwen_multiseed_s20260924
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.699 | 0.444 | 0.903 | 0.056 | 36 |
| commonsense | 0.698 | 0.611 | 0.843 | 0.111 | 36 |
| multi_step | 0.674 | 0.525 | 0.954 | 0.056 | 36 |

### qwen_multiseed_s20260924__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.738 | 0.565 | 0.856 | 0.111 | 36 |
| commonsense | 0.721 | 0.641 | 0.815 | 0.083 | 36 |
| multi_step | 0.694 | 0.567 | 0.917 | 0.139 | 36 |

### qwen_multiseed_s20260924__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.731 | 0.662 | 0.810 | 0.139 | 36 |
| commonsense | 0.762 | 0.701 | 0.833 | 0.194 | 36 |
| multi_step | 0.726 | 0.637 | 0.903 | 0.167 | 36 |

### qwen_multiseed_s20260924__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.748 | 0.611 | 0.940 | 0.250 | 36 |
| commonsense | 0.718 | 0.627 | 0.875 | 0.139 | 36 |
| multi_step | 0.696 | 0.551 | 0.926 | 0.111 | 36 |

### qwen_multiseed_s20260925
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.671 | 0.481 | 0.921 | 0.083 | 36 |
| commonsense | 0.723 | 0.637 | 0.838 | 0.167 | 36 |
| multi_step | 0.684 | 0.530 | 0.954 | 0.167 | 36 |

### qwen_multiseed_s20260925__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.713 | 0.551 | 0.866 | 0.083 | 36 |
| commonsense | 0.721 | 0.657 | 0.824 | 0.139 | 36 |
| multi_step | 0.674 | 0.544 | 0.935 | 0.139 | 36 |

### qwen_multiseed_s20260925__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.739 | 0.671 | 0.866 | 0.167 | 36 |
| commonsense | 0.802 | 0.722 | 0.880 | 0.222 | 36 |
| multi_step | 0.693 | 0.556 | 0.926 | 0.167 | 36 |

### qwen_multiseed_s20260925__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.748 | 0.648 | 0.917 | 0.194 | 36 |
| commonsense | 0.719 | 0.616 | 0.875 | 0.167 | 36 |
| multi_step | 0.692 | 0.567 | 0.954 | 0.139 | 36 |

### qwen_multiseed_s20260926
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.729 | 0.516 | 0.894 | 0.111 | 36 |
| commonsense | 0.670 | 0.618 | 0.780 | 0.056 | 36 |
| multi_step | 0.623 | 0.498 | 0.926 | 0.111 | 36 |

### qwen_multiseed_s20260926__cot
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.765 | 0.581 | 0.866 | 0.139 | 36 |
| commonsense | 0.681 | 0.678 | 0.810 | 0.083 | 36 |
| multi_step | 0.634 | 0.495 | 0.935 | 0.111 | 36 |

### qwen_multiseed_s20260926__oracle
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.740 | 0.660 | 0.838 | 0.139 | 36 |
| commonsense | 0.745 | 0.718 | 0.838 | 0.167 | 36 |
| multi_step | 0.674 | 0.565 | 0.917 | 0.111 | 36 |

### qwen_multiseed_s20260926__scaffold_full
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| causal | 0.733 | 0.583 | 0.935 | 0.194 | 36 |
| commonsense | 0.697 | 0.609 | 0.856 | 0.083 | 36 |
| multi_step | 0.684 | 0.542 | 0.926 | 0.139 | 36 |

## CCS by Difficulty

### qwen_multiseed_s20260924
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.659 | 0.450 | 0.867 | 0.080 | 25 |
| hard | 0.669 | 0.492 | 0.952 | 0.032 | 31 |
| medium | 0.717 | 0.585 | 0.885 | 0.096 | 52 |

### qwen_multiseed_s20260924__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.690 | 0.530 | 0.800 | 0.160 | 25 |
| hard | 0.673 | 0.530 | 0.909 | 0.032 | 31 |
| medium | 0.757 | 0.657 | 0.865 | 0.135 | 52 |

### qwen_multiseed_s20260924__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.772 | 0.730 | 0.807 | 0.240 | 25 |
| hard | 0.693 | 0.589 | 0.860 | 0.097 | 31 |
| medium | 0.752 | 0.683 | 0.862 | 0.173 | 52 |

### qwen_multiseed_s20260924__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.709 | 0.560 | 0.887 | 0.240 | 25 |
| hard | 0.698 | 0.540 | 0.909 | 0.032 | 31 |
| medium | 0.740 | 0.647 | 0.929 | 0.212 | 52 |

### qwen_multiseed_s20260925
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.686 | 0.490 | 0.927 | 0.160 | 25 |
| hard | 0.669 | 0.503 | 0.957 | 0.032 | 31 |
| medium | 0.710 | 0.606 | 0.862 | 0.192 | 52 |

### qwen_multiseed_s20260925__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.708 | 0.530 | 0.893 | 0.120 | 25 |
| hard | 0.666 | 0.546 | 0.919 | 0.065 | 31 |
| medium | 0.722 | 0.633 | 0.840 | 0.154 | 52 |

### qwen_multiseed_s20260925__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.731 | 0.580 | 0.873 | 0.160 | 25 |
| hard | 0.716 | 0.605 | 0.914 | 0.129 | 31 |
| medium | 0.769 | 0.710 | 0.885 | 0.231 | 52 |

### qwen_multiseed_s20260925__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.700 | 0.560 | 0.900 | 0.160 | 25 |
| hard | 0.678 | 0.556 | 0.946 | 0.097 | 31 |
| medium | 0.754 | 0.667 | 0.904 | 0.212 | 52 |

### qwen_multiseed_s20260926
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.672 | 0.450 | 0.887 | 0.200 | 25 |
| hard | 0.646 | 0.524 | 0.882 | 0.032 | 31 |
| medium | 0.691 | 0.601 | 0.848 | 0.077 | 52 |

### qwen_multiseed_s20260926__cot
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.693 | 0.540 | 0.840 | 0.200 | 25 |
| hard | 0.646 | 0.519 | 0.871 | 0.065 | 31 |
| medium | 0.722 | 0.646 | 0.885 | 0.096 | 52 |

### qwen_multiseed_s20260926__oracle
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.754 | 0.670 | 0.833 | 0.240 | 25 |
| hard | 0.636 | 0.575 | 0.833 | 0.032 | 31 |
| medium | 0.753 | 0.679 | 0.897 | 0.154 | 52 |

### qwen_multiseed_s20260926__scaffold_full
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.700 | 0.520 | 0.840 | 0.200 | 25 |
| hard | 0.649 | 0.527 | 0.903 | 0.065 | 31 |
| medium | 0.740 | 0.636 | 0.939 | 0.154 | 52 |

## CCS by Fine-grained task type

### qwen_multiseed_s20260924
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.706 | 0.479 | 0.889 | 0.083 | 12 |
| counterfactual | 0.727 | 0.500 | 0.972 | 0.000 | 12 |
| functional | 0.681 | 0.667 | 0.875 | 0.083 | 12 |
| long_horizon | 0.602 | 0.500 | 0.972 | 0.000 | 12 |
| multi | 0.727 | 0.500 | 0.806 | 0.083 | 12 |
| physical | 0.657 | 0.556 | 0.833 | 0.167 | 12 |
| sequential | 0.713 | 0.597 | 1.000 | 0.083 | 12 |
| single | 0.644 | 0.333 | 0.931 | 0.083 | 12 |
| social | 0.755 | 0.611 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260924__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.734 | 0.562 | 0.889 | 0.250 | 12 |
| counterfactual | 0.801 | 0.681 | 0.931 | 0.167 | 12 |
| functional | 0.706 | 0.688 | 0.847 | 0.083 | 12 |
| long_horizon | 0.593 | 0.500 | 0.861 | 0.000 | 12 |
| multi | 0.736 | 0.556 | 0.778 | 0.083 | 12 |
| physical | 0.685 | 0.583 | 0.806 | 0.083 | 12 |
| sequential | 0.755 | 0.639 | 1.000 | 0.167 | 12 |
| single | 0.676 | 0.458 | 0.861 | 0.083 | 12 |
| social | 0.773 | 0.653 | 0.792 | 0.083 | 12 |

### qwen_multiseed_s20260924__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.859 | 0.688 | 0.931 | 0.333 | 12 |
| counterfactual | 0.731 | 0.611 | 0.875 | 0.167 | 12 |
| functional | 0.759 | 0.750 | 0.861 | 0.167 | 12 |
| long_horizon | 0.588 | 0.542 | 0.889 | 0.083 | 12 |
| multi | 0.741 | 0.667 | 0.764 | 0.083 | 12 |
| physical | 0.669 | 0.660 | 0.764 | 0.250 | 12 |
| sequential | 0.731 | 0.681 | 0.889 | 0.083 | 12 |
| single | 0.722 | 0.708 | 0.792 | 0.167 | 12 |
| social | 0.856 | 0.694 | 0.875 | 0.167 | 12 |

### qwen_multiseed_s20260924__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.773 | 0.583 | 0.944 | 0.250 | 12 |
| counterfactual | 0.829 | 0.819 | 1.000 | 0.333 | 12 |
| functional | 0.648 | 0.542 | 0.944 | 0.083 | 12 |
| long_horizon | 0.616 | 0.472 | 0.917 | 0.000 | 12 |
| multi | 0.736 | 0.472 | 0.944 | 0.250 | 12 |
| physical | 0.715 | 0.701 | 0.819 | 0.250 | 12 |
| sequential | 0.699 | 0.597 | 0.917 | 0.083 | 12 |
| single | 0.681 | 0.542 | 0.875 | 0.167 | 12 |
| social | 0.792 | 0.639 | 0.861 | 0.083 | 12 |

### qwen_multiseed_s20260925
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.757 | 0.562 | 0.917 | 0.333 | 12 |
| counterfactual | 0.634 | 0.472 | 0.931 | 0.000 | 12 |
| functional | 0.738 | 0.646 | 0.861 | 0.250 | 12 |
| long_horizon | 0.565 | 0.431 | 0.972 | 0.000 | 12 |
| multi | 0.722 | 0.556 | 0.903 | 0.167 | 12 |
| physical | 0.681 | 0.583 | 0.833 | 0.167 | 12 |
| sequential | 0.731 | 0.597 | 0.972 | 0.167 | 12 |
| single | 0.657 | 0.417 | 0.931 | 0.083 | 12 |
| social | 0.750 | 0.681 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260925__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.752 | 0.562 | 0.944 | 0.250 | 12 |
| counterfactual | 0.741 | 0.542 | 0.931 | 0.083 | 12 |
| functional | 0.662 | 0.583 | 0.861 | 0.167 | 12 |
| long_horizon | 0.542 | 0.458 | 0.917 | 0.000 | 12 |
| multi | 0.722 | 0.611 | 0.847 | 0.167 | 12 |
| physical | 0.653 | 0.625 | 0.792 | 0.167 | 12 |
| sequential | 0.727 | 0.611 | 0.944 | 0.167 | 12 |
| single | 0.676 | 0.500 | 0.819 | 0.000 | 12 |
| social | 0.847 | 0.764 | 0.819 | 0.083 | 12 |

### qwen_multiseed_s20260925__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.759 | 0.500 | 0.944 | 0.333 | 12 |
| counterfactual | 0.713 | 0.639 | 0.875 | 0.167 | 12 |
| functional | 0.752 | 0.688 | 0.903 | 0.167 | 12 |
| long_horizon | 0.560 | 0.458 | 0.889 | 0.000 | 12 |
| multi | 0.759 | 0.750 | 0.903 | 0.250 | 12 |
| physical | 0.789 | 0.743 | 0.875 | 0.250 | 12 |
| sequential | 0.759 | 0.708 | 0.944 | 0.167 | 12 |
| single | 0.745 | 0.625 | 0.819 | 0.083 | 12 |
| social | 0.866 | 0.736 | 0.861 | 0.250 | 12 |

### qwen_multiseed_s20260925__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.775 | 0.604 | 0.972 | 0.167 | 12 |
| counterfactual | 0.801 | 0.764 | 0.972 | 0.083 | 12 |
| functional | 0.690 | 0.625 | 0.903 | 0.167 | 12 |
| long_horizon | 0.565 | 0.431 | 0.889 | 0.000 | 12 |
| multi | 0.764 | 0.639 | 0.944 | 0.333 | 12 |
| physical | 0.648 | 0.556 | 0.847 | 0.250 | 12 |
| sequential | 0.736 | 0.667 | 1.000 | 0.250 | 12 |
| single | 0.681 | 0.542 | 0.833 | 0.167 | 12 |
| social | 0.819 | 0.667 | 0.875 | 0.083 | 12 |

### qwen_multiseed_s20260926
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.688 | 0.521 | 0.917 | 0.250 | 12 |
| counterfactual | 0.750 | 0.597 | 0.903 | 0.083 | 12 |
| functional | 0.694 | 0.625 | 0.875 | 0.083 | 12 |
| long_horizon | 0.519 | 0.417 | 0.889 | 0.000 | 12 |
| multi | 0.759 | 0.556 | 0.847 | 0.083 | 12 |
| physical | 0.590 | 0.562 | 0.792 | 0.083 | 12 |
| sequential | 0.662 | 0.556 | 0.972 | 0.083 | 12 |
| single | 0.678 | 0.396 | 0.931 | 0.167 | 12 |
| social | 0.725 | 0.667 | 0.674 | 0.000 | 12 |

### qwen_multiseed_s20260926__cot
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.694 | 0.500 | 0.917 | 0.250 | 12 |
| counterfactual | 0.787 | 0.667 | 0.903 | 0.167 | 12 |
| functional | 0.722 | 0.708 | 0.875 | 0.083 | 12 |
| long_horizon | 0.523 | 0.361 | 0.917 | 0.000 | 12 |
| multi | 0.773 | 0.556 | 0.806 | 0.083 | 12 |
| physical | 0.562 | 0.660 | 0.778 | 0.083 | 12 |
| sequential | 0.685 | 0.625 | 0.972 | 0.083 | 12 |
| single | 0.734 | 0.521 | 0.889 | 0.167 | 12 |
| social | 0.759 | 0.667 | 0.778 | 0.083 | 12 |

### qwen_multiseed_s20260926__oracle
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.801 | 0.583 | 0.944 | 0.333 | 12 |
| counterfactual | 0.725 | 0.646 | 0.861 | 0.167 | 12 |
| functional | 0.701 | 0.729 | 0.833 | 0.167 | 12 |
| long_horizon | 0.523 | 0.500 | 0.861 | 0.000 | 12 |
| multi | 0.731 | 0.667 | 0.819 | 0.167 | 12 |
| physical | 0.697 | 0.701 | 0.806 | 0.250 | 12 |
| sequential | 0.699 | 0.611 | 0.944 | 0.000 | 12 |
| single | 0.764 | 0.667 | 0.833 | 0.083 | 12 |
| social | 0.838 | 0.722 | 0.875 | 0.083 | 12 |

### qwen_multiseed_s20260926__scaffold_full
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| conditional | 0.810 | 0.583 | 0.972 | 0.250 | 12 |
| counterfactual | 0.741 | 0.611 | 0.944 | 0.083 | 12 |
| functional | 0.713 | 0.667 | 0.847 | 0.083 | 12 |
| long_horizon | 0.523 | 0.458 | 0.861 | 0.000 | 12 |
| multi | 0.764 | 0.583 | 1.000 | 0.250 | 12 |
| physical | 0.600 | 0.535 | 0.847 | 0.083 | 12 |
| sequential | 0.718 | 0.583 | 0.944 | 0.167 | 12 |
| single | 0.694 | 0.556 | 0.861 | 0.250 | 12 |
| social | 0.778 | 0.625 | 0.875 | 0.083 | 12 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| qwen_multiseed_s20260924 | 0.074 | 0.417 | 0.426 | 0.000 | 0.056 | 0.028 |
| qwen_multiseed_s20260924__cot | 0.111 | 0.352 | 0.444 | 0.000 | 0.028 | 0.065 |
| qwen_multiseed_s20260924__oracle | 0.167 | 0.343 | 0.343 | 0.000 | 0.065 | 0.083 |
| qwen_multiseed_s20260924__scaffold_full | 0.167 | 0.407 | 0.343 | 0.000 | 0.056 | 0.028 |
| qwen_multiseed_s20260925 | 0.139 | 0.435 | 0.333 | 0.000 | 0.046 | 0.046 |
| qwen_multiseed_s20260925__cot | 0.120 | 0.398 | 0.370 | 0.000 | 0.046 | 0.065 |
| qwen_multiseed_s20260925__oracle | 0.185 | 0.352 | 0.352 | 0.000 | 0.065 | 0.046 |
| qwen_multiseed_s20260925__scaffold_full | 0.167 | 0.407 | 0.324 | 0.000 | 0.056 | 0.046 |
| qwen_multiseed_s20260926 | 0.093 | 0.454 | 0.380 | 0.000 | 0.037 | 0.037 |
| qwen_multiseed_s20260926__cot | 0.111 | 0.426 | 0.380 | 0.000 | 0.028 | 0.056 |
| qwen_multiseed_s20260926__oracle | 0.139 | 0.398 | 0.324 | 0.000 | 0.065 | 0.074 |
| qwen_multiseed_s20260926__scaffold_full | 0.139 | 0.426 | 0.361 | 0.000 | 0.028 | 0.046 |
