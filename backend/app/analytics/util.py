"""Serialization helpers for analytics payloads."""
from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np


def to_native(obj: Any) -> Any:
    """
    Recursively convert numpy / Decimal / pandas artefacts into JSON-safe
    native Python types. NaN/Inf become None. Applied at the API boundary so
    every analytics response serialises cleanly regardless of DB dialect.
    """
    if obj is None:
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [to_native(x) for x in obj.tolist()]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(x) for x in obj]
    return obj
