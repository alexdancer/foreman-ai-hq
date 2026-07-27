from __future__ import annotations

import re

# Shared because two discovery paths parse CLI output that interleaves model ids
# with header rows and setup guidance: Worker Harness model discovery and pi
# orchestrator inventory discovery. One guard, so the two cannot drift.
MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")


def looks_like_model_id(model: str) -> bool:
    """True when a token from CLI output is plausibly a model id rather than prose.

    Rejects the column header of a model table and any line whose model column
    reads ``model``/``models`` — which is what makes pi's ``provider model ...``
    header and its ``No models available. Use /login ...`` guidance fall out.
    """
    if not model or not MODEL_ID_PATTERN.fullmatch(model):
        return False
    lowered = model.lower()
    if lowered.startswith("model"):
        return False
    return any(char.isdigit() or char in "/-_.:" for char in model)
