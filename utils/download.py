# utils/download.py
from typing import Dict, Any, List

import pandas as pd

from constants import DOWNLOAD_COLUMNS, EMR_SECTIONS

def compute_new_ids(df: pd.DataFrame, answers: Dict[int, Dict[str, Any]]) -> None:
    counter = 1
    for idx in range(len(df)):
        ans = answers.get(idx)
        if ans and ans.get("saved"):
            ans["new_id"] = f"E{counter:03d}"
            counter += 1

def build_download_df(df: pd.DataFrame, answers: Dict[int, Dict[str, Any]]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    records: List[Dict[str, Any]] = []

    compute_new_ids(df, answers)

    for idx in range(len(df)):
        ans = answers.get(idx)
        if not ans or not ans.get("saved"):
            continue
        row = df.iloc[idx]
        base: Dict[str, Any] = {
            "새_구분자": ans.get("new_id", ""),
            "원_구분자": str(row["구분자"]) if "구분자" in df.columns else "",
        }
        for i in range(5):
            base[f"리커트_{i+1}_점수"] = ans.get("likert", {}).get(i)
        for label, key in EMR_SECTIONS:
            base[label] = ans.get("emr", {}).get(key, "")
        records.append(base)

    out = pd.DataFrame(records)
    if out.empty:
        return pd.DataFrame(columns=DOWNLOAD_COLUMNS)
    for c in DOWNLOAD_COLUMNS:
        if c not in out.columns:
            out[c] = ""
    return out[DOWNLOAD_COLUMNS]