"""app.services.auth 로그인 함수 테스트.

실제 Firebase에 접속하지 않고 requests.post를 가짜로 바꿔서 응답별 동작을 확인한다.
"""

import pytest
import requests

from app.services import auth
from app.services.auth import (
    AuthConfigError,
    AuthError,
    AuthUser,
    InvalidCredentialsError,
    InvalidInputError,
    NetworkError,
    TooManyAttemptsError,
    UserDisabledError,
    UserNotFoundError,
    WrongPasswordError,
    sign_in,
)

FAKE_KEY = "test-api-key"


class FakeResponse:
    def __init__(self, status_code, data=None, *, bad_json=False):
        self.status_code = status_code
        self._data = data
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._data


def firebase_error(message, status=400, reason=None):
    error = {"code": status, "message": message}
    if reason:
        error["details"] = [{"reason": reason}]
    return FakeResponse(status, {"error": error})


@pytest.fixture
def fake_post(monkeypatch):
    """requests.post를 가짜로 바꾼다. fake_post.response에 돌려줄 응답(또는 예외)을 넣는다."""

    class Fake:
        response = None
        calls = []

        def __call__(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

    fake = Fake()
    fake.calls = []
    monkeypatch.setattr(auth.requests, "post", fake)
    return fake


def test_sign_in_success(fake_post):
    fake_post.response = FakeResponse(
        200,
        {
            "localId": "uid-123",
            "email": "user@example.com",
            "idToken": "id-token",
            "refreshToken": "refresh-token",
            "expiresIn": "3600",
        },
    )

    user = sign_in(" user@example.com ", "pw123456", api_key=FAKE_KEY)

    assert user == AuthUser("uid-123", "user@example.com", "id-token", "refresh-token", 3600)
    url, kwargs = fake_post.calls[0]
    assert url == auth.SIGN_IN_URL
    assert kwargs["params"] == {"key": FAKE_KEY}
    assert kwargs["json"] == {
        "email": "user@example.com",
        "password": "pw123456",
        "returnSecureToken": True,
    }
    assert kwargs["timeout"] > 0


@pytest.mark.parametrize(
    "message, expected",
    [
        ("INVALID_PASSWORD", WrongPasswordError),
        ("EMAIL_NOT_FOUND", UserNotFoundError),
        ("INVALID_LOGIN_CREDENTIALS", InvalidCredentialsError),
        ("USER_DISABLED", UserDisabledError),
        ("TOO_MANY_ATTEMPTS_TRY_LATER : Access to this account has been disabled", TooManyAttemptsError),
        ("INVALID_EMAIL", InvalidInputError),
        ("SOMETHING_NEW", AuthError),
    ],
)
def test_sign_in_firebase_errors(fake_post, message, expected):
    fake_post.response = firebase_error(message)

    with pytest.raises(expected) as exc_info:
        sign_in("user@example.com", "pw", api_key=FAKE_KEY)

    assert type(exc_info.value) is expected
    assert exc_info.value.message  # 화면에 보여 줄 문장이 있어야 한다


def test_wrong_password_and_missing_user_are_different(fake_post):
    """비밀번호 오류와 없는 계정은 서로 다른 예외지만 둘 다 InvalidCredentialsError로도 잡힌다."""
    fake_post.response = firebase_error("INVALID_PASSWORD")
    with pytest.raises(WrongPasswordError) as wrong:
        sign_in("user@example.com", "pw", api_key=FAKE_KEY)

    fake_post.response = firebase_error("EMAIL_NOT_FOUND")
    with pytest.raises(UserNotFoundError) as missing:
        sign_in("nobody@example.com", "pw", api_key=FAKE_KEY)

    assert wrong.value.message != missing.value.message
    assert isinstance(wrong.value, InvalidCredentialsError)
    assert isinstance(missing.value, InvalidCredentialsError)


def test_invalid_api_key_is_config_error(fake_post):
    fake_post.response = firebase_error(
        "API key not valid. Please pass a valid API key.", reason="API_KEY_INVALID"
    )
    with pytest.raises(AuthConfigError):
        sign_in("user@example.com", "pw", api_key="wrong-key")


@pytest.mark.parametrize(
    "exc",
    [requests.ConnectionError("no network"), requests.Timeout("slow")],
)
def test_network_errors(fake_post, exc):
    fake_post.response = exc
    with pytest.raises(NetworkError):
        sign_in("user@example.com", "pw", api_key=FAKE_KEY)


def test_server_error_is_network_error(fake_post):
    fake_post.response = FakeResponse(503, bad_json=True)
    with pytest.raises(NetworkError):
        sign_in("user@example.com", "pw", api_key=FAKE_KEY)


def test_non_json_response(fake_post):
    fake_post.response = FakeResponse(400, bad_json=True)
    with pytest.raises(AuthError):
        sign_in("user@example.com", "pw", api_key=FAKE_KEY)


@pytest.mark.parametrize(
    "email, password",
    [("", "pw"), ("user@example.com", ""), ("   ", "pw"), ("not-an-email", "pw"), (None, None)],
)
def test_invalid_input_does_not_call_firebase(fake_post, email, password):
    with pytest.raises(InvalidInputError):
        sign_in(email, password, api_key=FAKE_KEY)
    assert fake_post.calls == []


def test_missing_api_key_in_secrets(fake_post, monkeypatch):
    """secrets.toml에 키가 없으면 Firebase를 호출하지 않고 설정 오류를 낸다."""

    def no_key():
        raise AuthConfigError(code="MISSING_API_KEY")

    monkeypatch.setattr(auth, "_read_api_key", no_key)
    with pytest.raises(AuthConfigError):
        sign_in("user@example.com", "pw")
    assert fake_post.calls == []
