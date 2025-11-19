# utils/text_utils.py
import re
from typing import List

BULLET_CHARS_CLASS = r"\-–—•·∙◦\*●○◉"

def fmt_dialogue(txt: str) -> str:
    """'참석자1~5' 기준으로 단락 분리 + 굵게 표시."""
    if not txt:
        return ""
    pat = re.compile(r"(참석자([1-5]))\s*[:：]?", flags=re.MULTILINE)
    txt = pat.sub(r"\n\n**\1**: ", txt)
    return txt.replace("\n", "  \n")

def normalize_basic(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\\n", "\n").replace("/n", "\n")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(ln.strip() for ln in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.replace("\u200b", "").replace("\u00a0", " ")
    return s.strip()

def apply_bullet_newline(text: str) -> str:
    """dash 등으로 이어진 내용을 불릿 단위로 정리."""
    if not text:
        return ""
    t = normalize_basic(text)
    # 문장부호/시작 뒤에 오는 불릿 기호들을 표준화
    t = re.sub(
        fr"(?:(?<=^)|(?<=\n)|(?<=[.!?…\)]))\s*[{BULLET_CHARS_CLASS}]\s+(?=\S)",
        "\n- ",
        t,
    )
    # 가운데 ' - ' 패턴도 불릿으로
    t = re.sub(fr"\s[{BULLET_CHARS_CLASS}]\s", "\n- ", t)
    # 줄 맨 앞 불릿 통일
    t = re.sub(fr"^(?:[{BULLET_CHARS_CLASS}])\s*", "- ", t, flags=re.MULTILINE)

    bullet_pat = re.compile(r"(?:^|\n)-\s*(.+?)(?=(?:\n- )|$)", re.DOTALL)
    items = [m.group(1).strip() for m in bullet_pat.finditer(t)]
    if not items:
        return t.strip()

    out_lines: List[str] = []
    for item in items:
        if not re.search(r"[.!?…)]$", item):
            item += "."
        out_lines.append(f"- {item}")
    return "\n".join(out_lines)

def normalize_dash_bullets(text: str) -> str:
    """줄단위로 이미 '-' 가 붙어 있는 경우 정리."""
    if not text:
        return ""
    t = normalize_basic(text)
    lines = [ln for ln in t.split("\n") if ln.strip()]
    out: List[str] = []
    had_bullet = False
    for ln in lines:
        ln2 = re.sub(fr"^[{BULLET_CHARS_CLASS}]\s*", "", ln).strip()
        if ln2 != ln:
            had_bullet = True
        if not re.search(r"[.!?…)]$", ln2):
            ln2 += "."
        out.append(f"- {ln2}")
    if out:
        return "\n".join(out)
    if not had_bullet:
        return apply_bullet_newline(text)
    return ""

def format_ros(text: str) -> str:
    """계통문진: '항목: +/-' 형식 정리."""
    if not text:
        return ""
    t = normalize_basic(text)
    t = re.sub(r"[;，、]+", "\n", t)
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    parsed: List[str] = []
    for ln in lines:
        ln = re.sub(fr"^[{BULLET_CHARS_CLASS}]\s*", "", ln).strip()
        parts = re.split(r"\s*,\s*", ln)
        for p in parts:
            m = re.match(r"([A-Za-z가-힣/\s]+?)\s*:\s*([+-])$", p.strip())
            if m:
                name = re.sub(r"\s+", " ", m.group(1)).strip()
                sign = m.group(2)
                parsed.append(f"{name}: {sign}")
    if parsed:
        return "\n".join(parsed)
    return normalize_dash_bullets(text)

def bullets_to_html_list(text: str) -> str:
    """'- '로 시작하는 줄들을 HTML <ul><li> 로 변환."""
    if not text:
        return "<div></div>"
    lines = [ln for ln in text.split("\n") if ln.strip()]
    bullet_lines = [re.sub(r"^-\s*", "", ln).strip() for ln in lines if re.match(r"^-\s+", ln)]

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    if bullet_lines:
        items = "".join(f"<li>{esc(item)}</li>" for item in bullet_lines)
        return f"<ul>{items}</ul>"
    safe = "<br>".join(esc(ln) for ln in lines)
    return f"<div>{safe}</div>"