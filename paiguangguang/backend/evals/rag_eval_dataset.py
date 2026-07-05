from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def get_rag_eval_dataset_path() -> Path:
    return Path(__file__).with_name("rag_eval_dataset.json")


def load_rag_eval_dataset(path: str | Path | None = None) -> dict[str, Any]:
    dataset_path = Path(path) if path is not None else get_rag_eval_dataset_path()
    with dataset_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
