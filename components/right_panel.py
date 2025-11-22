# components/right_panel.py
from typing import Dict, Any

import streamlit as st

from constants import LIKERT_ITEMS, LIKERT_FIXED_DESC, EMR_SECTIONS

def render_right_panel(container, idx: int, prev: Dict[str, Any], df):
    with container:
        st.markdown(
            "<div class='section-box'>평가 및 데이터 작성</div>",
            unsafe_allow_html=True,
        )

        with st.form(key=f"form_{idx}"):

            # 1) 평가 적합 여부
            with st.expander("1) 평가 적합 여부", expanded=False):
                st.markdown(
                    "<div class='muted'>대화 스크립트를 읽고 해당 평가를 진행할 수 있는 스크립트 인지 여부를 표시해주세요.</div>",
                    unsafe_allow_html=True,
                )
                suitable = st.radio(
                    "적합 여부",
                    options=["Y", "N"],
                    index=(
                        ["Y", "N"].index(prev.get("suitable", "Y"))
                        if prev.get("suitable") in ["Y", "N"]
                        else 0
                    ),
                    horizontal=True,
                )

            # 2) CLOVA Charty 결과 품질 평가
            with st.expander("2) CLOVA Charty 결과 품질 평가", expanded=True):
                st.markdown(
                    "<div class='muted'>좌측 패널의 <b>CLOVA Charty 생성 결과</b>를 참고하여, 각 항목을 1~5점으로 평가해주세요.</div>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")

                likert_scores: Dict[int, int] = {}
                for i, label in enumerate(LIKERT_ITEMS):
                    st.markdown(f"**{i+1}. {label}**")

                    # 고정 설명
                    def esc(s: str) -> str:
                        return (
                            s.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                            .replace('"', "&quot;")
                            .replace("'", "&#39;")
                        )

                    desc_items = LIKERT_FIXED_DESC.get(i, [])
                    if desc_items:
                        first = esc(desc_items[0])
                        rest = [esc(x) for x in desc_items[1:]]
                        rest_html = "<br>".join(rest) if rest else ""
                        st.markdown(
                            f"<div class='likert-desc'><b>{first}</b>"
                            + (f"<br>{rest_html}" if rest_html else "")
                            + "</div>",
                            unsafe_allow_html=True,
                        )

                    likert_scores[i] = st.radio(
                        "점수 선택",
                        options=[1, 2, 3, 4, 5],
                        index=(
                            int(prev.get("likert", {}).get(i, 3)) - 1
                            if prev.get("likert")
                            else 2
                        ),
                        horizontal=True,
                        key=f"likert_{idx}_{i}",
                    )
                    st.markdown("---")

            # 3) 대화 기반 의무기록 생성
            with st.expander("3) 대화 기반 의무기록 생성", expanded=True):
                st.markdown(
                    "<div class='muted'>대화 스크립트를 참고하여 초진기록 항목에 맞는 내용을 작성해주세요. 항목에 해당되는 내용이 없다면 쓰지 않아도 됩니다.</div>",
                    unsafe_allow_html=True,
                )
                emr_vals: Dict[str, str] = {}
                for label, key in EMR_SECTIONS:
                    emr_vals[key] = st.text_area(
                        label,
                        value=str(prev.get("emr", {}).get(key, "")),
                        key=f"emr_{idx}_{key}",
                        height=120,
                    )

            # 저장/다음 버튼
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
                    next_idx = min(idx + 1, len(df) - 1)
                    st.session_state.current_idx = next_idx
                    st.session_state.ignore_radio_once = True
                st.success("저장되었습니다.")
                st.rerun()