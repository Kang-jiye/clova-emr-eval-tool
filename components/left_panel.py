# components/left_panel.py
import streamlit as st

from constants import PRIMARY_LABELS
from utils.parser import parse_clova_sections
from utils.text_utils import (
    fmt_dialogue,
    normalize_dash_bullets,
    format_ros,
    bullets_to_html_list,
)


def render_left_panel(container, row, idx):
    """좌측 패널: 대상 데이터 + 대화 스크립트 + CLOVA 생성 결과
    idx 인자는 현재 사용하지 않지만, app.py 호출 형식과 맞추기 위해 받기만 합니다.
    """

    with container:

        # --------------------------
        # 제목 박스
        # --------------------------
        st.markdown(
            "<div class='section-box'>대화 및 CLOVA Charty 평가 참고 데이터</div>",
            unsafe_allow_html=True,
        )

        # --------------------------
        # 대상 데이터 (구분자 + 진료일시)
        # --------------------------
        
        # 구분자
        gu = str(row["구분자"]) if "구분자" in row.index else ""

        # 진료일시 (datetime 또는 문자열)
        dt = ""
        if "진료일시" in row.index:
            raw_dt = row["진료일시"]
            if hasattr(raw_dt, "strftime"):
                dt = raw_dt.strftime("%Y-%m-%d %H:%M")
            else:
                dt = str(raw_dt)

        # 한 줄에 pill 두 개로 표시
        html = "<div style='display:flex; gap:8px; align-items:center; flex-wrap:wrap;'>"
        html += f"<span class='pill'>{gu}</span>"
        if dt and dt.lower() != "nan":
            html += (
                "<span class='pill' "
                "style='background:#e0f2fe; color:#0369a1; border-color:#bae6fd;'>"
                f"{dt}</span>"
            )
        html += "</div>"

        st.markdown(html, unsafe_allow_html=True)
        st.markdown(" ")

        # --------------------------
        # 대화 스크립트
        # --------------------------
        with st.expander("대화 스크립트", expanded=True):
            st.markdown(
                fmt_dialogue(str(row["대화 스크립트"])),
                unsafe_allow_html=True,
            )

        # --------------------------
        # CLOVA 생성 결과
        # --------------------------
        with st.expander("CLOVA Charty 생성 결과", expanded=True):
            primary, others = parse_clova_sections(str(row["생성결과"]))

            for lb in PRIMARY_LABELS:
                st.markdown(
                    f"<div class='gen-label'>{lb}</div>",
                    unsafe_allow_html=True,
                )

                body = primary.get(lb, "")
                if body:
                    if lb == "계통문진":
                        clean_body = format_ros(body)
                    else:
                        clean_body = normalize_dash_bullets(body)

                    html_body = bullets_to_html_list(clean_body)
                    st.markdown(
                        f"<div class='gen-box'>{html_body}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("<div class='gen-empty'></div>", unsafe_allow_html=True)

            # 기타 섹션
            if others:
                st.markdown(
                    "<div class='gen-label'>기타</div>",
                    unsafe_allow_html=True,
                )

                chunks = []
                for title, content in others:
                    cleaned = normalize_dash_bullets(content)
                    inner_html = bullets_to_html_list(cleaned)
                    chunks.append(f"<div><b>{title}</b></div>{inner_html}")

                merged = "<br>".join(chunks)

                st.markdown(
                    f"<div class='gen-box'>{merged}</div>",
                    unsafe_allow_html=True,
                )