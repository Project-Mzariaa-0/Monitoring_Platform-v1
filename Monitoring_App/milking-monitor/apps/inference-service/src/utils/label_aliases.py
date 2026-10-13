from __future__ import annotations

RAW_TO_CANONICAL = {
    "pipe_sprayer": "spray_bottle",
    "teat_cup_on": "teat_cups_attached",
    "teat_cup_off": "teat_cups_detached",
    "dip_applicator": "dip_applicator",
    "stripping_cup": "stripping_cup",
    "person": "person",
}


def normalize_class_name(class_name: str | None) -> str:
    if class_name is None:
        return ""
    key = class_name.strip()
    return RAW_TO_CANONICAL.get(key, key)
