"""app.core.windowing 테스트."""

import numpy as np
import pytest

from app.core.dicom import load_dicom
from app.core.windowing import WindowingError, apply_window, auto_window, render

# level 100, width 200 → lower 0, upper 200
LEVEL, WIDTH = 100, 200


def test_output_is_uint8_and_same_shape():
    pixels = np.zeros((3, 5), dtype=np.int16)
    out = apply_window(pixels, LEVEL, WIDTH)
    assert out.dtype == np.uint8
    assert out.shape == (3, 5)


def test_boundaries_min_center_max():
    pixels = np.array([[0, 100, 200]], dtype=np.float32)  # 최소, 중심, 최대
    np.testing.assert_array_equal(apply_window(pixels, LEVEL, WIDTH), [[0, 128, 255]])


def test_values_outside_window_are_clipped():
    pixels = np.array([[-5000, -1, 201, 70000]], dtype=np.int32)
    np.testing.assert_array_equal(apply_window(pixels, LEVEL, WIDTH), [[0, 0, 255, 255]])


def test_linear_mapping_inside_window():
    pixels = np.array([[50, 150]], dtype=np.uint16)  # 1/4, 3/4 지점
    np.testing.assert_array_equal(apply_window(pixels, LEVEL, WIDTH), [[64, 191]])


def test_level_outside_pixel_range():
    pixels = np.array([[0, 50, 100]], dtype=np.uint8)
    assert apply_window(pixels, 5000, 100).max() == 0  # 모두 window 아래 → 검정
    assert apply_window(pixels, -5000, 100).min() == 255  # 모두 window 위 → 흰색


def test_original_array_is_not_changed():
    pixels = np.array([[0, 100, 200]], dtype=np.float32)
    before = pixels.copy()
    out = apply_window(pixels, LEVEL, WIDTH)
    np.testing.assert_array_equal(pixels, before)
    assert out is not pixels
    assert not np.shares_memory(out, pixels)


def test_no_integer_overflow():
    """int16 계산 중 넘침이 생기지 않는다 (float로 계산)."""
    pixels = np.array([[-32768, 32767]], dtype=np.int16)
    np.testing.assert_array_equal(apply_window(pixels, 0, 65535), [[0, 255]])


def test_invert():
    pixels = np.array([[0, 200]], dtype=np.uint8)
    np.testing.assert_array_equal(apply_window(pixels, LEVEL, WIDTH, invert=True), [[255, 0]])


def test_nan_pixels_become_black():
    pixels = np.array([[np.nan, 200.0]])
    np.testing.assert_array_equal(apply_window(pixels, LEVEL, WIDTH), [[0, 255]])


def test_very_small_width_acts_like_threshold():
    pixels = np.array([[99, 101]], dtype=np.float32)
    np.testing.assert_array_equal(apply_window(pixels, 100, 0.001), [[0, 255]])


@pytest.mark.parametrize("width", [0, -1, -100.5])
def test_width_zero_or_negative_is_error(width):
    with pytest.raises(WindowingError, match="폭"):
        apply_window(np.zeros((2, 2)), LEVEL, width)


@pytest.mark.parametrize(
    "level, width",
    [(float("nan"), 100), (100, float("nan")), (float("inf"), 100), (100, float("inf")), ("abc", 100), (None, 100)],
)
def test_non_finite_or_non_numeric_parameters(level, width):
    with pytest.raises(WindowingError):
        apply_window(np.zeros((2, 2)), level, width)


@pytest.mark.parametrize(
    "pixels",
    [np.zeros((0, 0)), np.zeros(5), np.zeros((2, 2, 3)), np.array([["a", "b"]]), np.zeros((2, 2), dtype=complex)],
)
def test_invalid_pixel_arrays(pixels):
    with pytest.raises(WindowingError):
        apply_window(pixels, LEVEL, WIDTH)


def test_windowing_error_is_value_error():
    with pytest.raises(ValueError):
        apply_window(np.zeros((2, 2)), LEVEL, 0)


def test_auto_window_covers_min_to_max():
    pixels = np.array([[-100, 0], [50, 300]], dtype=np.int16)
    level, width = auto_window(pixels)
    assert (level, width) == (100, 400)
    out = apply_window(pixels, level, width)
    assert out.min() == 0 and out.max() == 255


def test_auto_window_constant_image():
    level, width = auto_window(np.full((3, 3), 42))
    assert level == 42 and width == 1
    out = apply_window(np.full((3, 3), 42), level, width)
    assert out.dtype == np.uint8  # 폭 0 오류 없이 처리된다


def test_auto_window_all_nan():
    with pytest.raises(WindowingError):
        auto_window(np.full((2, 2), np.nan))


def test_render_uses_header_window(make_dicom):
    stored = np.array([[0, 100, 200]], dtype=np.uint16)
    image = load_dicom(make_dicom(stored, window=(100, 200)))
    np.testing.assert_array_equal(render(image), [[0, 128, 255]])


def test_render_without_header_window_uses_min_max(make_dicom):
    stored = np.array([[1000, 3000]], dtype=np.uint16)
    np.testing.assert_array_equal(render(load_dicom(make_dicom(stored))), [[0, 255]])


def test_render_override_level_and_width(make_dicom):
    stored = np.array([[0, 100, 200]], dtype=np.uint16)
    image = load_dicom(make_dicom(stored, window=(100, 200)))
    np.testing.assert_array_equal(render(image, level=50, width=100), [[0, 255, 255]])


def test_render_inverts_monochrome1(make_dicom):
    stored = np.array([[0, 255]], dtype=np.uint8)
    image = load_dicom(make_dicom(stored, photometric="MONOCHROME1"))
    np.testing.assert_array_equal(render(image), [[255, 0]])  # 값이 큰 쪽이 어둡게


def test_render_applies_rescale_before_window(make_dicom):
    """HU로 바뀐 값 기준으로 window가 적용된다 (CT 폐 window 예시)."""
    stored = np.array([[0, 1024, 2048]], dtype=np.uint16)  # HU: -1024, 0, 1024
    image = load_dicom(make_dicom(stored, slope=1, intercept=-1024))
    np.testing.assert_array_equal(render(image, level=0, width=2048), [[0, 128, 255]])
