"""세션 상태 관리 및 캐시 헬퍼 모듈"""

import streamlit as st
import pandas as pd
from app.logic import generate_sample_pacs_data


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """샘플 데이터를 캐시하여 로드합니다."""
    return generate_sample_pacs_data()


def init_session_state() -> None:
    """앱에 필요한 기본 세션 상태들을 초기화합니다."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "홈"
    if "data" not in st.session_state:
        st.session_state.data = load_data()
    if "search_keyword" not in st.session_state:
        st.session_state.search_keyword = ""
