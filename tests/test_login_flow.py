"""로그인 화면 흐름 테스트 (Streamlit AppTest).

앱을 켜면 로그인 화면만 보이고, 로그인 → 로그아웃 → 재로그인이 되는지 확인한다.
Firebase는 호출하지 않고 requests.post를 가짜로 바꾼다.
"""

import pytest
from streamlit.testing.v1 import AppTest

from app.services import auth

SUCCESS = {
    "localId": "uid-1",
    "email": "reviewer@example.com",
    "idToken": "id-token",
    "refreshToken": "refresh-token",
    "expiresIn": "3600",
}


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


@pytest.fixture
def firebase(monkeypatch):
    """비밀번호가 'correct-pw'일 때만 성공하는 가짜 Firebase."""

    def fake_post(url, *, params, json, timeout):
        if json["password"] == "correct-pw":
            return FakeResponse(200, SUCCESS)
        return FakeResponse(400, {"error": {"code": 400, "message": "INVALID_PASSWORD"}})

    monkeypatch.setattr(auth.requests, "post", fake_post)


@pytest.fixture
def app(firebase):
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30)
    at.secrets["firebase"] = {"api_key": "test-api-key"}
    return at.run()


def login(at, email, password):
    at.text_input[0].input(email)
    at.text_input[1].input(password)
    at.button[0].click()
    return at.run()


def is_login_page(at):
    return any("로그인" in t.value for t in at.title)


def test_shows_only_login_page_before_login(app):
    assert not app.exception
    assert is_login_page(app)
    assert len(app.sidebar.button) == 0  # 사이드바(메인 메뉴)가 보이지 않는다


def test_wrong_password_shows_error_and_stays_on_login(app):
    login(app, "reviewer@example.com", "wrong-pw")

    assert is_login_page(app)
    assert [e.value for e in app.error] == ["비밀번호가 올바르지 않습니다."]


def test_login_logout_relogin(app):
    login(app, "reviewer@example.com", "correct-pw")
    assert not app.exception
    assert not is_login_page(app)
    assert any("reviewer@example.com" in m.value for m in app.sidebar.markdown)

    app.sidebar.button[0].click().run()  # 로그아웃
    assert is_login_page(app)
    assert "auth_user" not in app.session_state

    login(app, "reviewer@example.com", "correct-pw")
    assert not is_login_page(app)
