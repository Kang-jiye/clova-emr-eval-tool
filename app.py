from io import BytesIO
from typing import Dict, Any, cast

import pandas as pd
import streamlit as st

from constants import REQUIRED_COLS
from styles import inject_styles
from components.left_panel import render_left_panel
from components.right_panel import render_right_panel
from utils.download import build_download_df

# ---------------- App Config ----------------
st.set_page_config(
    page_title="CLOVA Charty 생성 EMR 평가 및 정답 데이터 구축",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

# ---------------- Global Styles ----------------
inject_styles()

# ---------------- Sidebar: Upload ----------------
from PIL import Image
import streamlit as st

logo = Image.open("assets/shl_logo.png")

with st.sidebar:
    st.image(logo, use_container_width=True)
    st.markdown("")

st.sidebar.header("1️⃣ 평가 데이터 업로드")
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

            # 컬럼 정리
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

# ---------------- Sidebar: Progress / Navigation ----------------
st.sidebar.divider()
st.sidebar.subheader("2️⃣ 진행 현황 / 항목 이동")

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
        key="nav_radio",
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

# ---------------- Sidebar: Download ----------------
st.sidebar.divider()
st.sidebar.subheader("3️⃣ 결과 다운로드")

if st.session_state.df is not None:
    out_df = build_download_df(st.session_state.df, st.session_state.answers)
    all_done = (
        len(st.session_state.df) > 0
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

# ---------------- Title & Top Progress ----------------
st.markdown(
    "<div class='title-box'><h3 style='margin:0'>CLOVA Charty 생성 EMR 평가 및 정답 데이터 구축</h3></div>",
    unsafe_allow_html=True,
)

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

# ---------------- Stop if no data ----------------
if st.session_state.df is None:
    st.info(
        "좌측 사이드바에서 평가 데이터(.xlsx/CSV)를 업로드하세요.\n\n필수 컬럼: [구분자, 대화 스크립트, 생성결과]"
    )
    st.stop()

# ---------------- Navigation Buttons ----------------
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

# ---------------- Current Row ----------------
idx = st.session_state.current_idx
row = st.session_state.df.iloc[idx]
prev = st.session_state.answers.get(idx, {})

# ---------------- Two-Panel Layout (좌:우 = 5:7) ----------------
left, right = st.columns([5, 7])

render_left_panel(left, row, idx)
render_right_panel(right, idx, prev, st.session_state.df)