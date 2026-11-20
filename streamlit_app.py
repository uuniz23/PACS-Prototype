"""PACS Team - Streamlit 메인 진입점"""

import streamlit as st
from app.utils.helpers import init_session_state
from app.components.sidebar import render_sidebar
from app.pages.home import render_home_page
from app.pages.dashboard import render_dashboard_page


def main():
    st.set_page_config(
        page_title="PACS Team - 의료영상 모니터링",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 1. 세션 상태 초기화
    init_session_state()

    # 2. 사이드바 네비게이션 렌더링
    selected_page = render_sidebar()
    st.session_state.current_page = selected_page

    # 3. 페이지 라우팅
    if selected_page == "홈":
        render_home_page()
    elif selected_page == "대시보드":
        render_dashboard_page()


if __name__ == "__main__":
    main()
