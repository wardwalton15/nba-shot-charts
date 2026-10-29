from pathlib import Path

import pandas as pd

_CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
IMG_DIR = _CACHE_DIR / "images"


def cache_path(key: str) -> Path:
    _CACHE_DIR.mkdir(exist_ok=True)
    return _CACHE_DIR / f"{key}.parquet"


def load_from_cache(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_parquet(path)
    return None


def save_to_cache(df: pd.DataFrame, path: Path) -> None:
    df.to_parquet(path, index=False)
