# ReasonEdit-Bench results

## Overall (all 220 items, 2 systems)
| System | TCS | DPS | NPS | CCS | OCS | Succ | CLIP-S | DINO-I | LPIPS |
|---|---|---|---|---|---|---|---|---|---|
| instructpix2pix__surface | 0.373 | 0.438 | 0.655 | 0.488 | -- | 0.109 | 21.773 | 0.734 | 0.321 |
| qwen_image_edit__surface | 0.764 | 0.766 | 0.920 | 0.817 | -- | 0.486 | 19.795 | 0.948 | 0.107 |

## CCS by Task domain

### instructpix2pix__surface
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| surface | 0.488 | 0.438 | 0.655 | 0.109 | 220 |

### qwen_image_edit__surface
| Task domain | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| surface | 0.817 | 0.766 | 0.920 | 0.486 | 220 |

## CCS by Difficulty

### instructpix2pix__surface
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.488 | 0.438 | 0.655 | 0.109 | 220 |

### qwen_image_edit__surface
| Difficulty | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| easy | 0.817 | 0.766 | 0.920 | 0.486 | 220 |

## CCS by Fine-grained task type

### instructpix2pix__surface
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| surface | 0.488 | 0.438 | 0.655 | 0.109 | 220 |

### qwen_image_edit__surface
| Fine-grained task type | CCS | DPS | NPS | Succ | n |
|---|---|---|---|---|---|
| surface | 0.817 | 0.766 | 0.920 | 0.486 | 220 |

## Failure attribution
| System | no error | instruction understanding error | reasoning / planning error | region grounding error | pixel generation error | causal inconsistency |
|---|---|---|---|---|---|---|
| instructpix2pix__surface | 0.109 | 0.245 | 0.114 | 0.382 | 0.005 | 0.145 |
| qwen_image_edit__surface | 0.486 | 0.214 | 0.155 | 0.041 | 0.000 | 0.105 |
