"""Firebase Authentication 이메일·비밀번호 로그인.

Firebase Auth REST API(signInWithPassword)를 호출한다.
웹 API 키는 `st.secrets["firebase"]["api_key"]`에서 읽고 코드에 적지 않는다.

실패는 아래 예외로 구분해 돌려준다. 화면은 `except AuthError`로 한 번에 받거나
필요한 하위 예외만 골라 받는다.

    AuthError
    ├── InvalidInputError       이메일·비밀번호가 비어 있거나 이메일 형식이 틀림
    ├── InvalidCredentialsError 이메일 또는 비밀번호가 틀림 (어느 쪽인지 모름)
    │   ├── WrongPasswordError  비밀번호가 틀림
    │   └── UserNotFoundError   없는 계정
    ├── UserDisabledError       관리자가 비활성화한 계정
    ├── TooManyAttemptsError    시도 횟수 초과로 잠시 막힘
    ├── NetworkError            연결 실패, 시간 초과, Firebase 서버 오류
    └── AuthConfigError         API 키가 없거나 잘못됨 (설정 문제)

주의: Firebase 프로젝트에 "이메일 열거 보호(Email enumeration protection)"가
켜져 있으면(2023년 9월 이후 만든 프로젝트는 기본값) Firebase가 틀린 비밀번호와
없는 계정을 구분하지 않고 INVALID_LOGIN_CREDENTIALS 하나로 응답한다.
이때는 InvalidCredentialsError가 난다.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
DEFAULT_TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------- 예외


class AuthError(Exception):
    """로그인 실패의 공통 부모. `message`는 화면에 그대로 보여 줄 수 있는 문장이다."""

    message = "로그인에 실패했습니다."

    def __init__(self, message: str | None = None, *, code: str | None = None):
        self.message = message or self.message
        self.code = code  # Firebase가 돌려준 오류 코드 (디버깅용)
        super().__init__(self.message)


class InvalidInputError(AuthError):
    message = "이메일과 비밀번호를 올바르게 입력해 주세요."


class InvalidCredentialsError(AuthError):
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class WrongPasswordError(InvalidCredentialsError):
    message = "비밀번호가 올바르지 않습니다."


class UserNotFoundError(InvalidCredentialsError):
    message = "등록되지 않은 계정입니다."


class UserDisabledError(AuthError):
    message = "사용이 중지된 계정입니다. 관리자에게 문의해 주세요."


class TooManyAttemptsError(AuthError):
    message = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."


class NetworkError(AuthError):
    message = "인증 서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."


class AuthConfigError(AuthError):
    message = "로그인 설정에 문제가 있습니다. 관리자에게 문의해 주세요."


# Firebase 오류 코드 → 예외
_ERROR_MAP: dict[str, type[AuthError]] = {
    "EMAIL_NOT_FOUND": UserNotFoundError,
    "INVALID_PASSWORD": WrongPasswordError,
    "INVALID_LOGIN_CREDENTIALS": InvalidCredentialsError,
    "USER_DISABLED": UserDisabledError,
    "TOO_MANY_ATTEMPTS_TRY_LATER": TooManyAttemptsError,
    "INVALID_EMAIL": InvalidInputError,
    "MISSING_PASSWORD": InvalidInputError,
    "MISSING_EMAIL": InvalidInputError,
    "API_KEY_INVALID": AuthConfigError,
    "API_KEY_EXPIRED": AuthConfigError,
}


# ---------------------------------------------------------------- 결과


@dataclass(frozen=True)
class AuthUser:
    """로그인한 사용자. 비밀번호는 담지 않는다."""

    uid: str
    email: str
    id_token: str
    refresh_token: str
    expires_in: int  # id_token 유효 시간(초)


# ---------------------------------------------------------------- 로그인


def sign_in(
    email: str,
    password: str,
    *,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> AuthUser:
    """이메일·비밀번호로 로그인하고 AuthUser를 돌려준다. 실패하면 AuthError 계열을 낸다.

    api_key를 넘기지 않으면 st.secrets에서 읽는다. (테스트에서는 직접 넘긴다)
    """
    email = (email or "").strip()
    if not email or not password or "@" not in email:
        raise InvalidInputError()

    key = api_key if api_key is not None else _read_api_key()

    try:
        response = requests.post(
            SIGN_IN_URL,
            params={"key": key},
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise NetworkError("인증 서버 응답이 너무 늦습니다. 잠시 후 다시 시도해 주세요.") from exc
    except requests.RequestException as exc:
        raise NetworkError() from exc

    if response.status_code >= 500:
        raise NetworkError(
            "인증 서버에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
            code=f"HTTP_{response.status_code}",
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise AuthError(code=f"HTTP_{response.status_code}") from exc

    if response.status_code != 200:
        code = _error_code(data)
        raise _ERROR_MAP.get(code, AuthError)(code=code)

    try:
        return AuthUser(
            uid=data["localId"],
            email=data.get("email", email),
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            expires_in=int(data.get("expiresIn", 3600)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError(code="BAD_RESPONSE") from exc


def _error_code(data: object) -> str:
    """Firebase 오류 응답에서 코드만 꺼낸다.

    예: {"error": {"message": "TOO_MANY_ATTEMPTS_TRY_LATER : Access to this ..."}}
        API 키 오류는 message가 문장이고 코드는 details[].reason에 있다.
    """
    if not isinstance(data, dict) or not isinstance(data.get("error"), dict):
        return "UNKNOWN"
    error = data["error"]

    for detail in error.get("details") or []:
        if isinstance(detail, dict) and detail.get("reason") in _ERROR_MAP:
            return detail["reason"]

    message = str(error.get("message", ""))
    return message.split(" : ", 1)[0].strip() or "UNKNOWN"


def _read_api_key() -> str:
    """st.secrets에서 웹 API 키를 읽는다. streamlit은 여기서만 import해서
    테스트가 streamlit·secrets 없이도 돌 수 있게 한다."""
    import streamlit as st

    try:
        key = st.secrets["firebase"]["api_key"]
    except (KeyError, FileNotFoundError) as exc:
        raise AuthConfigError(
            "Firebase API 키가 설정되지 않았습니다. .streamlit/secrets.toml을 확인해 주세요.",
            code="MISSING_API_KEY",
        ) from exc
    if not key:
        raise AuthConfigError(
            "Firebase API 키가 비어 있습니다. .streamlit/secrets.toml을 확인해 주세요.",
            code="MISSING_API_KEY",
        )
    return key
