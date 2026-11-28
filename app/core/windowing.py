"""Windowing: 픽셀 값을 화면 표시용 8비트(uint8, 0~255) 영상으로 바꾼다.

streamlit, firebase_admin을 import하지 않는다.

계산 방법 (선형)
    lower = level - width / 2,  upper = level + width / 2
    출력 = (값 - lower) / width x 255 를 반올림하고 0~255로 자른다.
    - lower 이하 → 0 (검정), upper 이상 → 255 (흰색)
    - 계산은 float64 복사본에서 하므로 원본 배열은 바뀌지 않는다.
"""

from __future__ import annotations

import math

import numpy as np

from app.core.dicom import DicomImage


class WindowingError(ValueError):
    """잘못된 windowing 입력."""


def apply_window(
    pixels: np.ndarray,
    level: float,
    width: float,
    *,
    invert: bool = False,
) -> np.ndarray:
    """중심값(level)과 폭(width)으로 화면 표시용 영상을 만든다.

    입력:
        pixels  2차원 숫자 배열 (dtype 상관없음, 예: uint8, int16, float32)
        level   window 중심값 (pixels와 같은 단위, 예: HU)
        width   window 폭. 0보다 커야 한다.
        invert  True면 밝기를 뒤집는다 (MONOCHROME1 영상 표시용)
    반환: 새 uint8 배열, 값 범위 0~255, shape는 pixels와 같다.
          window 범위 밖 값은 0 또는 255로 잘린다. NaN 픽셀은 0(검정)으로 둔다.
    오류: WindowingError
        - width가 0 이하이거나 level·width가 숫자가 아님(NaN, 무한대 포함)
        - pixels가 비어 있거나 2차원이 아니거나 숫자 배열이 아님
    """
    level = _finite_number(level, "level")
    width = _finite_number(width, "width")
    if width <= 0:
        raise WindowingError(f"window 폭(width)은 0보다 커야 합니다. (입력: {width})")

    values = _as_float_image(pixels)  # 복사본

    lower = level - width / 2.0
    out = (values - lower) / width * 255.0
    out = np.nan_to_num(out, nan=0.0, posinf=255.0, neginf=0.0)
    out = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    if invert:
        out = 255 - out
    return out


def auto_window(pixels: np.ndarray) -> tuple[float, float]:
    """픽셀 최솟값~최댓값 전체가 보이는 (level, width)를 돌려준다.

    모든 픽셀이 같은 값이면 width=1을 돌려준다 (폭 0이 되지 않게).
    NaN은 무시한다. 오류: WindowingError (빈 배열, 모든 값이 NaN 등)
    """
    values = _as_float_image(pixels)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise WindowingError("유효한 픽셀 값이 없습니다.")
    low, high = float(finite.min()), float(finite.max())
    width = max(high - low, 1.0)
    return (low + high) / 2.0, width


def render(
    image: DicomImage,
    level: float | None = None,
    width: float | None = None,
) -> np.ndarray:
    """DicomImage를 화면 표시용 uint8 영상(0~255)으로 바꾼다. 뷰어용 기본 함수.

    level·width를 주지 않으면 헤더의 WindowCenter/WindowWidth를 쓰고,
    헤더에도 없으면 auto_window()(최솟값~최댓값)를 쓴다.
    MONOCHROME1 영상은 자동으로 밝기를 뒤집어 MONOCHROME2처럼 보이게 한다.
    """
    if level is None or width is None:
        meta = image.meta
        if meta.window_center is not None and meta.window_width is not None and meta.window_width > 0:
            default_level, default_width = meta.window_center, meta.window_width
        else:
            default_level, default_width = auto_window(image.pixels)
        level = default_level if level is None else level
        width = default_width if width is None else width
    return apply_window(image.pixels, level, width, invert=image.meta.is_monochrome1)


# ---------------------------------------------------------------- 내부 함수


def _finite_number(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise WindowingError(f"{name}은(는) 숫자여야 합니다. (입력: {value!r})") from exc
    if not math.isfinite(number):
        raise WindowingError(f"{name}은(는) 유한한 숫자여야 합니다. (입력: {value!r})")
    return number


def _as_float_image(pixels) -> np.ndarray:
    array = np.asarray(pixels)
    if array.ndim != 2:
        raise WindowingError(f"2차원 영상만 지원합니다. (입력 shape: {array.shape})")
    if array.size == 0:
        raise WindowingError("빈 영상입니다.")
    if np.iscomplexobj(array) or not (np.issubdtype(array.dtype, np.number) or array.dtype == np.bool_):
        raise WindowingError(f"숫자 배열이어야 합니다. (입력 dtype: {array.dtype})")
    return array.astype(np.float64, copy=True)
