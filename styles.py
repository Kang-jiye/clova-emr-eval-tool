# styles.py
import streamlit as st

def inject_styles() -> None:
    st.markdown(
        """
    <style>
    .fixed-progress {
        position: sticky;
        top: 0;
        z-index: 999;
        background: white;
        padding: 10px 0 6px 0;
    }
    .title-box {
        padding:14px 16px;
        border:1px solid #e5e7eb;
        background:#f8fafc;
        border-radius:12px;
        margin-bottom:12px;
    }
    .section-box {
        padding:10px 12px;
        border-left:4px solid #2563eb;
        background:#f9fafb;
        border-radius:8px;
        margin:8px 0;
        font-weight:600;
    }
    .pill {
        display:inline-block;
        padding:2px 8px;
        border-radius:999px;
        background:#eef2ff;
        color:#3730a3;
        font-weight:600;
        border:1px solid #e5e7eb;
    }
    .gen-label {
        font-weight: 700;
        margin: 10px 0 6px 0;
    }
    .gen-box {
        border:1px solid #e5e7eb;
        border-radius:8px;
        padding:10px;
        background:#ffffff;
        margin:6px 0 12px 0;
    }
    .gen-empty {
        border:1px dashed #e5e7eb;
        border-radius:8px;
        min-height:26px;
        background:#fafafa;
        margin:6px 0 12px 0;
    }
    .muted {
        color:#6b7280;
        font-size:0.92rem;
    }
    .likert-desc {
        font-size: 0.78rem;
        color: #6b7280;
        line-height: 1.35;
        margin: .25rem 0 .5rem 0;
    }
    .likert-desc b {
        font-weight: 600;
    }

    /* 🔥 왼쪽 메인 컬럼 전체 스크롤 적용 */
    div[data-testid="column"]:first-child {
        max-height: 70vh;
        overflow-y: auto;
        padding-right: 10px;
    }
    div[data-testid="column"]:first-child::-webkit-scrollbar {
        width: 8px;
    }
    div[data-testid="column"]:first-child::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    div[data-testid="column"]:first-child::-webkit-scrollbar-thumb {
        background: #c5c5c5;
        border-radius: 4px;
    }
    div[data-testid="column"]:first-child::-webkit-scrollbar-thumb:hover {
        background: #9b9b9b;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )