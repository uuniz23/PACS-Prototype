"""로그인 화면. 로그인 전에는 이 화면만 보인다."""

import streamlit as st

from app.components.session import set_current_user
from app.services.auth import AuthError, sign_in


def render_login_page() -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.title("🏥 PACS 로그인")
        st.caption("발급받은 계정의 이메일과 비밀번호를 입력하세요.")

        # key를 주지 않아 비밀번호가 session_state에 남지 않게 한다.
        with st.form("login_form"):
            email = st.text_input("이메일", placeholder="name@example.com")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

        if not submitted:
            return

        try:
            with st.spinner("로그인 중..."):
                user = sign_in(email, password)
        except AuthError as err:
            st.error(err.message)
            return

        set_current_user(user)
        st.rerun()
