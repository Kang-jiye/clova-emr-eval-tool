# utils/parser.py
import re
from typing import Dict, List, Tuple

from constants import PRIMARY_LABELS, EXCLUDE_LABELS, LABEL_PATTERN_STR
from utils.text_utils import normalize_basic

def parse_clova_sections(raw: str) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """
    CLOVA 생성결과를 섹션별로 파싱.
    - 줄 단위 라벨(주호소/현병력/과거력/...) 인식
    - 동일 라벨 반복 시 내용 이어붙임
    - 라벨이 하나도 없으면 전체를 '현병력'으로 간주
    """
    text = normalize_basic(raw or "")
    if not text:
        return ({lb: "" for lb in PRIMARY_LABELS}, [])

    lines = text.split("\n")
    label_re = re.compile(LABEL_PATTERN_STR)

    mapping_all: Dict[str, List[str]] = {}
    current_label: str = ""
    seen_any_label = False

    def norm_label(lab: str) -> str:
        if re.fullmatch(r"개인력\s*및\s*사회력", lab):
            return "개인력 및 사회력"
        if re.fullmatch(r"(?:계통문진|통문진)", lab):
            return "계통문진"
        if re.fullmatch(r"진료\s*계획", lab):
            return "진료 계획"
        return lab

    for ln in lines:
        m = label_re.match(ln.strip())
        if m:
            seen_any_label = True
            lab = norm_label(m.group(1))
            current_label = lab
            mapping_all.setdefault(lab, [])
            continue
        if current_label:
            mapping_all.setdefault(current_label, []).append(ln)
        else:
            mapping_all.setdefault("_prefix", []).append(ln)

    if not seen_any_label:
        primary_only = {lb: "" for lb in PRIMARY_LABELS}
        primary_only["현병력"] = text
        return primary_only, []

    # prefix → 현병력에 합치기
    if "_prefix" in mapping_all:
        prefix_txt = normalize_basic("\n".join(mapping_all.pop("_prefix")))
        if prefix_txt:
            mapping_all.setdefault("현병력", [])
            mapping_all["현병력"] = [prefix_txt] + mapping_all.get("현병력", [])

    merged: Dict[str, str] = {}
    for k, v in mapping_all.items():
        if not isinstance(v, list):
            continue
        merged[k] = normalize_basic("\n".join(v))

    primary: Dict[str, str] = {lb: merged.get(lb, "") for lb in PRIMARY_LABELS}

    others: List[Tuple[str, str]] = []
    for k, v in merged.items():
        if k in PRIMARY_LABELS or k in EXCLUDE_LABELS or k == "_prefix":
            continue
        if v:
            others.append((k, v))

    return primary, others