"""로그인 상태(세션) 관리.

로그인한 사용자는 st.session_state에 AuthUser로 저장한다. 비밀번호는 저장하지 않는다.
세션은 브라우저 탭 단위이므로 새로고침하면 다시 로그인해야 한다.
"""

from __future__ import annotations

import streamlit as st

from app.services.auth import AuthUser

_USER_KEY = "auth_user"


def get_current_user() -> AuthUser | None:
    """로그인한 사용자를 돌려준다. 로그인 전이면 None."""
    return st.session_state.get(_USER_KEY)


def is_logged_in() -> bool:
    return get_current_user() is not None


def set_current_user(user: AuthUser) -> None:
    st.session_state[_USER_KEY] = user


def logout() -> None:
    """로그아웃. 이전 사용자의 화면 상태가 남지 않도록 세션 전체를 지운다."""
    st.session_state.clear()
