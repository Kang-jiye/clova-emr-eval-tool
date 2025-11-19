# app.py
from io import BytesIO
from typing import Dict, Any, List, Tuple, cast
import re

import pandas as pd
import streamlit as st

# ---------------- App Config ----------------
st.set_page_config(
    page_title="CLOVA Charty 생성 EMR 평가 및 정답 데이터 구축",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Debug toggle ----
DEBUG = st.sidebar.toggle("디버그 모드", value=False, help="원문/파싱 결과를 화면에 표시합니다.")
# 디버그: 현재 실행 중인 파일 경로 확인
st.sidebar.caption(f"▶ Running file: {__file__}")

# ---------------- Constants ----------------
REQUIRED_COLS = ["구분자", "대화 스크립트", "생성결과"]

LIKERT_ITEMS = [
    "정확성(Accuracy)",
    "환각여부(Hallucination)",
    "충실성(Throughness)",
    "맥락 통합성(Contextual Coherence)",
    "편향여부(Bias)",
]

# 각 항목의 고정 세부 설명
LIKERT_FIXED_DESC = {
    0: ["생성된 결과가 사실과 일치하며, 잘못된 정보나 수치 오류가 없음", " ", "5점: 모든 정보가 사실과 일치하며, 수치, 이름, 시간, 용어에 오류가 없음", "4점: 사소한 표현 차이는 있으나, 의미 왜곡이나 사실 오류가 없음", "3점: 전반적으로 정확하나, 1-2개의 모호한 표현 혹은 약간의 수치 오류 존재", "2점: 여러 항목에서 사실 또는 용어 오류가 관찰되어 검토가 필요", "1점: 잘못된 정보가 여러 곳에 포함되어 기록을 신뢰하기 어려움"],
    1: ["생성된 EMR이 대화 스크립트로 검증 가능한 내용만을 포함, 근거없는 추정 및 허위 내용 포함하지 않음", " ","5점: 모든 내용이 대화 스크립트에서 직접 확인 가능하며 추가적 창작 없음","4점: 대부분 스크립트 기반으로 경미한 요약 또는 해석 정도 존재하며, 근거가 있음", "3점: 일부 문장은 스크립트 근거가 불분명하나 전체 맥락 이해해 있어서 문제가 없음", "2점: 여러 문장에서 근거 불문명 또는 추정 성격의 문장 존재", "1점: 스크립트와 무관한 정보가 다수 포함되어 허위 생성에 가까움"],
    2: ["기록이 환자의 환자의 주요 정보를 빠짐없이 포함하며, 의미있는 내용의 누락이 없음", " ","5점: 환자 상태 및 주호소, 과거력 등 핵심 내용이 모두 기록되어 누락 없음","4점: 대부분의 핵심 정보가 포함되어 있으나, 부차적 세부 항목 1-2개 누락", "3점: 핵심 정보는 대체로 있지만, 중요 세부(e.g. 기간 또는 증상 강도) 부족", "2점: 여러개의 주요 정보가 누락되어 상황 파악이 어려움", "1점: 환자 문제 또는 주요 사실이 대부분 누락되어있음"],
    3: ["대화 스크립트의 핵심 사실들을 논리적으로 연결되며 일관된 흐릅으로 정리하여 읽는 사람이 환자 상태를 자연스럽게 이해할 수 있음", " ", "5점: 정보가 시간-원인-결과 순서로 자연스럽게 이어지고 중복 및 모순이 없으며, 단락 구성이 명료하여 읽자마자 환자 상태 파악 가능","4점: 전반적으로 잘 통합되어 있으며, 경미한 어색함이나 약한 연결은 있으나 이해헤는 지장 없음", "3점: 핵심 정보는 있으나, 문맥 전환이 부자연스럽고 요점이 분산됨", "2점: 사실만을 나열하여 문맥이 매끄럽지 못하고 이해가 어려우며 재구성이 필요함", "1점: 논리 흐름이 무너져 전체 의미 파악이 불가하며 임상적 맥락 상실"],
    4: ["기록이 환자의 개인적 특성(나이, 성별 등)에 기반한 추정이나 편견을 포함하지 않으며, 대화 스크립트에서 검증 가능한 정보만 포함", " ","5점: 환자의 나이, 성별 등에 대한 해석 및 평가에 대한 언급이 전혀 없으며, 대화에서 언급된 사실만 기술","4점: 전반적으로 객관적이고 중립적이지만, 사실을 해치지 않는 선에서 약간의 암시적 표현 및 경미한 추정이 포함됨", "3점: 대부분 중립적이나 전체 의미에는 큰 왜곡이 없는 선에서 일부 문장에 평가적 어투나 단정적 표현이 존재", "2점: 환자의 나이, 습관 등에 근거하여 원인이나 결과를 추정 및 단정하는 문장이 여러 곳에 존재하며 근거가 불분명함", "1점: 사실에 기반하지 않고, 환자에 대한 주관적 판단 및 평가 표현이 다수 표현되어 있으며 편향이 심함"]
}

# 좌측 생성결과 표시 규칙 (과거력 포함)
PRIMARY_LABELS = ["주호소", "현병력", "과거력", "개인력 및 사회력", "계통문진", "신체검진"]
EXCLUDE_LABELS = ["진단명", "진단", "진료계획", "진료 계획", "계획"]

EMR_SECTIONS = [
    ("주호소", "chief_complaint"),
    ("현병력", "present_illness"),
    ("과거력", "past_history"),
    ("계통문진", "review_of_systems"),
    ("신체검진", "physical_exam"),
    ("기타", "other"),
]

# 다운로드 컬럼(근거 컬럼 없음)
DOWNLOAD_COLUMNS: List[str] = (
    ["새_구분자", "원_구분자"]
    + [f"리커트_{i+1}_점수" for i in range(5)]
    + [label for (label, _) in EMR_SECTIONS]
)

# 라벨 패턴: 줄 시작~끝에서 라벨만 있는 줄만 라벨로 인정(콜론 유무 허용)
LABEL_PATTERN_STR = r"^\s*(주호소|현병력|과거력|개인력\s*및\s*사회력|(?:계통문진|통문진)|신체검진|진단명|진단|진료\s*계획|진료계획|계획)\s*[:：]?\s*$"

# ---------------- Session State ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "answers" not in st.session_state:
    st.session_state.answers = cast(Dict[int, Dict[str, Any]], {})
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "ignore_radio_once" not in st.session_state:
    st.session_state.ignore_radio_once = False
if "upload_token" not in st.session_state:
    st.session_state.upload_token = None

# ---------------- Sidebar: Upload / Progress / Download ----------------
st.sidebar.header("1) 평가 데이터 업로드")
file = st.sidebar.file_uploader("엑셀(.xlsx) 또는 CSV 업로드", type=["xlsx", "csv"])

if file is not None:
    token = (file.name, getattr(file, "size", None))
    if token != st.session_state.upload_token:
        try:
            if file.name.lower().endswith(".xlsx"):
                df = pd.read_excel(file, engine="openpyxl")
            else:
                file.seek(0)
                try:
                    df = pd.read_csv(file)
                except UnicodeDecodeError:
                    file.seek(0)
                    df = pd.read_csv(file, encoding="cp949")
            df.columns = [str(c).strip() for c in df.columns]
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                st.sidebar.error(f"필수 컬럼 누락: {', '.join(missing)}")
                st.sidebar.write("현재 컬럼:", list(df.columns))
            else:
                st.session_state.df = df
                st.session_state.current_idx = 0
                st.session_state.answers = {}
                st.session_state.ignore_radio_once = True
                st.session_state.upload_token = token
                st.rerun()
        except Exception as e:
            st.sidebar.exception(e)

st.sidebar.divider()
st.sidebar.subheader("2) 진행 현황 / 항목 이동")

if st.session_state.df is not None:
    df = st.session_state.df
    options = list(range(len(df)))

    def label_for(i: int) -> str:
        row_id = str(df.iloc[i]["구분자"])
        done = st.session_state.answers.get(i, {}).get("saved", False)
        return ("✅ " if done else "⬜ ") + row_id

    chosen = st.sidebar.radio(
        "항목 선택",
        options=options,
        format_func=label_for,
        index=st.session_state.current_idx if options else 0,
        label_visibility="collapsed",
    )
    if st.session_state.ignore_radio_once:
        st.session_state.ignore_radio_once = False
    else:
        if chosen is not None and chosen != st.session_state.current_idx:
            st.session_state.current_idx = int(chosen)

    total = len(df)
    done = sum(1 for v in st.session_state.answers.values() if v.get("saved"))
    st.sidebar.progress(0 if total == 0 else done / total)
    st.sidebar.caption(f"완료 {done} / 총 {total} | 남은 {max(total - done, 0)}")
else:
    st.sidebar.info("엑셀 업로드 후 진행 현황이 표시됩니다.")

st.sidebar.divider()
st.sidebar.subheader("3) 결과 다운로드")

def compute_new_ids() -> None:
    df = st.session_state.df
    if df is None:
        return
    counter = 1
    for idx in range(len(df)):
        ans = st.session_state.answers.get(idx)
        if ans and ans.get("saved"):
            ans["new_id"] = f"E{counter:03d}"
            counter += 1

def build_download_df() -> pd.DataFrame:
    df = st.session_state.df
    if df is None:
        return pd.DataFrame()
    records = []
    compute_new_ids()
    for idx in range(len(df)):
        ans = st.session_state.answers.get(idx)
        if not ans or not ans.get("saved"):
            continue
        row = df.iloc[idx]
        base = {
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

out_df = build_download_df()
all_done = (
    st.session_state.df is not None
    and len(st.session_state.df) > 0
    and sum(1 for v in st.session_state.answers.values() if v.get("saved")) == len(st.session_state.df)
)
if all_done and not out_df.empty:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="results")
    st.sidebar.download_button(
        label="모두 완료됨: 결과 엑셀 다운로드",
        data=buffer.getvalue(),
        file_name="evaluation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.sidebar.caption("모든 항목 저장 완료 후 다운로드가 활성화됩니다.")

# ---------------- CSS ----------------
st.markdown("""
<style>
.fixed-progress {position: sticky; top: 0; z-index: 999; background: white; padding: 10px 0 6px 0;}
.title-box {padding:14px 16px; border:1px solid #e5e7eb; background:#f8fafc; border-radius:12px; margin-bottom:12px;}
.section-box {padding:10px 12px; border-left:4px solid #2563eb; background:#f9fafb; border-radius:8px; margin:8px 0; font-weight:600;}
.mono {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono","Courier New", monospace; white-space: pre-wrap;}
.gen-block {font-size: 0.95rem; line-height: 1.55;}
.pill {display:inline-block; padding:2px 8px; border-radius:999px; background:#eef2ff; color:#3730a3; font-weight:600; border:1px solid #e5e7eb;}
.card {border:1px solid #e5e7eb; background:#ffffff; border-radius:10px; padding:10px 12px; margin:8px 0;}
.card h4 {margin:0 0 6px 0;}
.muted {color:#6b7280; font-size:0.92rem;}

/* 생성결과 전용 박스 스타일 */
.gen-label { font-weight: 700; margin: 10px 0 6px 0; }
.gen-box { border:1px solid #e5e7eb; border-radius:8px; padding:10px; background:#ffffff; margin:6px 0 12px 0; }
.gen-empty { border:1px dashed #e5e7eb; border-radius:8px; min-height:26px; background:#fafafa; margin:6px 0 12px 0; }

/* ▼ LIKERT_FIXED_DESC 전용: 더 작은 글씨 + 첫 문장만 볼드 */
.likert-desc {
  font-size: 0.78rem;
  color: #6b7280;
  line-height: 1.35;
  margin: .25rem 0 .5rem 0;
}
.likert-desc b {
  font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------------- Formatting Helpers ----------------

BULLET_CHARS_CLASS = r"\-–—•·∙◦\*●○◉"

def fmt_dialogue(txt: str) -> str:
    pat = re.compile(r"(참석자([1-5]))\s*[:：]?", flags=re.MULTILINE)
    txt = pat.sub(r"\n\n**\1**: ", txt or "")
    return txt.replace("\n", "  \n")

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\\n", "\n").replace("/n", "\n")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(ln.strip() for ln in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.replace("\u200b", "").replace("\u00a0", " ")
    return s.strip()

def apply_bullet_newline(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = "\n".join(ln.strip() for ln in t.split("\n"))
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = t.replace("\u200b", "").replace("\u00a0", " ")
    t = re.sub(fr"(?:(?<=^)|(?<=\n)|(?<=[.!?…\)]))\s*[{BULLET_CHARS_CLASS}]\s+(?=\S)", "\n- ", t)
    t = re.sub(fr"\s[{BULLET_CHARS_CLASS}]\s", "\n- ", t)
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
    if not text:
        return ""
    t = text.replace("\r\n","\n").replace("\r","\n")
    lines = [ln.strip() for ln in t.split("\n")]
    out = []
    had_bullet = False
    for ln in lines:
        if not ln:
            continue
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
    if not text:
        return ""
    t = text.replace("\r\n","\n").replace("\r","\n")
    t = re.sub(r"[;，、]+", "\n", t)
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    parsed = []
    for ln in lines:
        ln = re.sub(fr"^[{BULLET_CHARS_CLASS}]\s*", "", ln).strip()
        parts = re.split(r"\s*,\s*", ln)
        for p in parts:
            m = re.match(r"([A-Za-z][A-Za-z/\s]+?)\s*:\s*([+-])$", p.strip())
            if m:
                name = re.sub(r"\s+", " ", m.group(1)).strip()
                sign = m.group(2)
                parsed.append(f"{name}: {sign}")
    if parsed:
        return "\n".join(parsed)
    return normalize_dash_bullets(text)

def bullets_to_html_list(text: str) -> str:
    if not text:
        return "<div></div>"
    lines = [ln for ln in text.split("\n") if ln.strip()]
    bullet_lines = [re.sub(r"^-\s*", "", ln).strip() for ln in lines if re.match(r"^-\s+", ln)]
    def html_escape(s: str) -> str:
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&#39;"))
    if bullet_lines:
        items = "".join(f"<li>{html_escape(item)}</li>" for item in bullet_lines)
        return f"<ul>{items}</ul>"
    safe = "<br>".join(html_escape(ln) for ln in lines)
    return f"<div>{safe}</div>"

# ---------------- Parser (라인 스캔) ----------------
def parse_clova_sections(raw: str) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    text = _normalize_text(raw or "")
    if not text:
        return ({lb: "" for lb in PRIMARY_LABELS}, [])
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    label_re = re.compile(LABEL_PATTERN_STR)
    mapping_all: Dict[str, List[str]] = {}
    current_label: str = ""
    seen_any_label = False
    def _normalize_label(lab: str) -> str:
        if re.fullmatch(r"진료\s*계획", lab):
            return "진료 계획"
        if re.fullmatch(r"개인력\s*및\s*사회력", lab):
            return "개인력 및 사회력"
        if re.fullmatch(r"(?:계통문진|통문진)", lab):
            return "계통문진"
        return lab
    for ln in lines:
        m = label_re.match(ln.strip())
        if m:
            seen_any_label = True
            lab = _normalize_label(m.group(1))
            current_label = lab
            if lab not in mapping_all:
                mapping_all[lab] = []
            continue
        if current_label:
            mapping_all[current_label].append(ln)
        else:
            mapping_all.setdefault("_prefix", []).append(ln)
    if not seen_any_label:
        primary_fallback = {lb: "" for lb in PRIMARY_LABELS}
        primary_fallback["현병력"] = text
        return primary_fallback, []
    if "_prefix" in mapping_all:
        prefix_text = _normalize_text("\n".join(mapping_all.pop("_prefix")))
        if prefix_text:
            mapping_all.setdefault("현병력", [])
            mapping_all["현병력"] = [prefix_text] + mapping_all.get("현병력", [])
    merged_all: Dict[str, str] = {}
    for k, v in mapping_all.items():
        if not isinstance(v, list):
            continue
        merged = _normalize_text("\n".join(v))
        merged_all[k] = merged
    primary: Dict[str, str] = {lb: _normalize_text(merged_all.get(lb, "")) for lb in PRIMARY_LABELS}
    other_items: List[Tuple[str, str]] = []
    for k, v in merged_all.items():
        if k in PRIMARY_LABELS or k in EXCLUDE_LABELS:
            continue
        if k == "_prefix":
            continue
        if v:
            other_items.append((k, v))
    return primary, other_items

# ---------------- Title & Progress ----------------
st.markdown("<div class='title-box'><h3 style='margin:0'>CLOVA Charty 생성 EMR 평가 및 정답 데이터 구축</h3></div>", unsafe_allow_html=True)

def render_top_progress():
    df = st.session_state.df
    total = len(df) if df is not None else 0
    done = sum(1 for v in st.session_state.answers.values() if v.get("saved"))
    remaining = max(total - done, 0)
    with st.container():
        st.markdown("<div class='fixed-progress'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.subheader("진행 현황")
            if total > 0:
                st.progress(done / total)
        with c2:
            st.metric("완료", f"{done} / {total}")
        with c3:
            st.metric("남은 문항", f"{remaining}")
        st.markdown("</div>", unsafe_allow_html=True)

render_top_progress()

if st.session_state.df is None:
    st.info("좌측 사이드바에서 평가 데이터(.xlsx/CSV)를 업로드하세요.\n\n필수 컬럼: [구분자, 대화 스크립트, 생성결과]")
    st.stop()

# ---------------- Navigation ----------------
n_rows = len(st.session_state.df)
nav_left, nav_right = st.columns([1, 1])
with nav_left:
    if st.button("◀ 이전"):
        st.session_state.current_idx = max(0, st.session_state.current_idx - 1)
        st.session_state.ignore_radio_once = True
        st.rerun()
with nav_right:
    if st.button("다음 ▶"):
        st.session_state.current_idx = min(n_rows - 1, st.session_state.current_idx + 1)
        st.session_state.ignore_radio_once = True
        st.rerun()

idx = st.session_state.current_idx
row = st.session_state.df.iloc[idx]
prev = st.session_state.answers.get(idx, {})

# ---------------- Optional Debug for this row ----------------
if DEBUG:
    st.info("디버그: 생성결과 원문/라벨 감지 미리보기")
    raw = str(row["생성결과"])
    st.caption("원문 repr (앞 1500자)")
    st.code(repr(raw)[:1500])
    found = []
    lab_re = re.compile(LABEL_PATTERN_STR)
    for ln in raw.replace("\r\n","\n").replace("\r","\n").split("\n"):
        m = lab_re.match(ln.strip())
        if m:
            found.append(m.group(1))
    st.caption(f"감지된 라벨들: {found}")

# ---------------- Two-Panel Layout ----------------
left, right = st.columns([1, 1])

with left:
    st.markdown("<div class='section-box'>대화 및 CLOVA Charty 평가 참고 데이터</div>", unsafe_allow_html=True)
    st.markdown("**대상 데이터**")
    st.markdown(f"<span class='pill'>{row['구분자']}</span>", unsafe_allow_html=True)
    with st.expander("대화 스크립트", expanded=True):
        st.markdown(f"{fmt_dialogue(str(row['대화 스크립트']))}", unsafe_allow_html=True)
    with st.expander("CLOVA Charty 생성 결과", expanded=True):
        primary, others = parse_clova_sections(str(row["생성결과"]))
        for lb in PRIMARY_LABELS:
            st.markdown(f"<div class='gen-label'>{lb}</div>", unsafe_allow_html=True)
            body = primary.get(lb, "")
            if body:
                if lb == "계통문진":
                    clean_body = format_ros(body)
                else:
                    clean_body = normalize_dash_bullets(body)
                html = bullets_to_html_list(clean_body)
                st.markdown(f"<div class='gen-box'>{html}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='gen-empty'></div>", unsafe_allow_html=True)
        if others:
            st.markdown(f"<div class='gen-label'>기타</div>", unsafe_allow_html=True)
            lines = []
            for title, content in others:
                cleaned = normalize_dash_bullets(content)
                html_inner = bullets_to_html_list(cleaned)
                lines.append(f"<div><b>{title}</b></div>{html_inner}")
            html = "<br>".join(lines)
            st.markdown(f"<div class='gen-box'>{html}</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='section-box'>평가 및 데이터 작성</div>", unsafe_allow_html=True)
    with st.form(key=f"form_{idx}"):

        # 1) 평가 적합 여부
        with st.expander("1) 평가 적합 여부", expanded=False):
            st.markdown("<div class='muted'>대화 스크립트를 읽고 해당 평가를 진행할 수 있는 스크립트 인지 여부를 표시해주세요.</div>", unsafe_allow_html=True)
            suitable = st.radio(
                "적합 여부",
                options=["Y", "N"],
                index=(["Y", "N"].index(prev.get("suitable", "Y")) if prev.get("suitable") in ["Y", "N"] else 0),
                horizontal=True,
            )

        # 2) CLOVA Charty 결과 품질 평가 (고정 설명 + 점수만)
        with st.expander("2) CLOVA Charty 결과 품질 평가", expanded=True):
            
            likert_scores: Dict[int, int] = {}
            for i, label in enumerate(LIKERT_ITEMS):
                st.markdown(f"**{i+1}. {label}**")

                # --- 세부 설명: 불릿 X, 첫 문장 볼드, 작은 글씨 ---
                def html_escape(s: str) -> str:
                    return (s.replace("&", "&amp;")
                             .replace("<", "&lt;")
                             .replace(">", "&gt;")
                             .replace('"', "&quot;")
                             .replace("'", "&#39;"))

                desc_items = LIKERT_FIXED_DESC.get(i, [])
                if desc_items:
                    first = html_escape(desc_items[0])
                    rest = [html_escape(x) for x in desc_items[1:]]
                    rest_html = "<br>".join(rest) if rest else ""
                    st.markdown(
                        f"<div class='likert-desc'><b>{first}</b>" + (f"<br>{rest_html}" if rest_html else "") + "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("<div class='likert-desc'></div>", unsafe_allow_html=True)
                # ---------------------------------------------

                likert_scores[i] = st.radio(
                    "점수 선택",
                    options=[1, 2, 3, 4, 5],
                    index=(int(prev.get("likert", {}).get(i, 3)) - 1) if prev.get("likert") else 2,
                    horizontal=True,
                    key=f"likert_{idx}_{i}",
                )
                st.markdown("---")

        # 3) 대화 기반 의무기록 생성
        with st.expander("3) 대화 기반 의무기록 생성", expanded=True):
            st.markdown("<div class='muted'>대화 스크립트를 참고하여 초진기록 항목에 맞는 내용을 작성해주세요. 항목에 해당되는 내용이 없다면 쓰지 않아도 됩니다.</div>", unsafe_allow_html=True)
            emr_vals: Dict[str, str] = {}
            for label, key_name in EMR_SECTIONS:
                emr_vals[key_name] = st.text_area(
                    label,
                    value=str(prev.get("emr", {}).get(key_name, "")),
                    key=f"emr_{idx}_{key_name}",
                    height=120,
                )

        csave, cnext = st.columns([1, 3])
        with csave:
            submitted = st.form_submit_button("저장")
        with cnext:
            submitted_next = st.form_submit_button("저장 후 다음")

        if submitted or submitted_next:
            st.session_state.answers[idx] = {
                "suitable": suitable,
                "likert": likert_scores,
                "emr": emr_vals,
                "saved": True,
            }
            if submitted_next:
                next_idx = min(idx + 1, len(st.session_state.df) - 1)
                st.session_state.current_idx = next_idx
                st.session_state.ignore_radio_once = True
            st.success("저장되었습니다.")
            st.rerun()
