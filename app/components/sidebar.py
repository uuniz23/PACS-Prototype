"""사이드바 네비게이션 및 전역 설정 컴포넌트"""

import streamlit as st


def render_sidebar() -> str:
    """사이드바를 렌더링하고 선택된 페이지 이름을 반환합니다."""
    with st.sidebar:
        st.markdown("## 🏥 **PACS Dashboard**")
        st.caption("의료영상 저장전송시스템 모니터링")
        st.divider()

        # 네비게이션
        pages = ["🏠 홈 (개요)", "📊 영상검사 대시보드"]
        current_idx = 0 if st.session_state.get("current_page") == "홈" else 1

        selected_page = st.radio(
            "메뉴 바로가기",
            options=pages,
            index=current_idx,
            label_visibility="collapsed",
        )

        st.divider()

        # 앱 정보 / 상태
        st.markdown("### ⚙️ 시스템 상태")
        st.success("🟢 PACS 서버: 정상 가동 중")
        st.info("📦 스토리지 사용량: 68% (3.4TB / 5TB)")

        st.divider()
        st.caption("PACS Team v1.0.0")

    return "홈" if "홈" in selected_page else "대시보드"
