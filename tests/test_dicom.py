"""app.core.dicom 테스트. 테스트용 DICOM은 conftest.py의 make_dicom으로 만든다."""

import io

import numpy as np
import pytest

from app.core.dicom import DicomNoPixelDataError, DicomReadError, load_dicom
from tests.conftest import build_dataset


def sample_pixels():
    """4행 x 6열 (높이 4, 너비 6) 영상. 위치마다 값이 달라 순서를 확인할 수 있다."""
    return np.arange(24, dtype=np.uint16).reshape(4, 6) * 100


def test_reads_size_and_pixel_values(make_dicom):
    pixels = sample_pixels()
    image = load_dicom(make_dicom(pixels))

    assert image.pixels.shape == (4, 6)  # (행, 열) = (높이, 너비)
    assert image.meta.rows == 4
    assert image.meta.columns == 6
    assert image.pixels.dtype == np.float32
    np.testing.assert_array_equal(image.pixels, pixels.astype(np.float32))
    assert image.pixels[0, 5] == 500  # 0행(맨 위) 5열(맨 오른쪽)


def test_reads_metadata(make_dicom):
    meta = load_dicom(make_dicom(sample_pixels(), window=(1000, 2000))).meta

    assert meta.photometric_interpretation == "MONOCHROME2"
    assert not meta.is_monochrome1
    assert meta.bits_stored == 16
    assert meta.window_center == 1000
    assert meta.window_width == 2000
    assert meta.pixel_spacing == (0.14, 0.14)
    assert meta.modality == "CR"
    assert meta.body_part == "CHEST"
    assert meta.view_position == "PA"
    assert meta.patient_id == "test-patient-0001"


def test_patient_info_is_not_exposed(make_dicom):
    meta = load_dicom(make_dicom(sample_pixels())).meta

    for hidden in ("patient_name", "patient_birth_date", "patient_sex", "patient_age"):
        assert not hasattr(meta, hidden)
    text = repr(meta)
    assert "test-patient-0001" not in text  # 출력해도 환자 ID가 보이지 않는다
    assert "Test^Patient" not in text


def test_rescale_slope_and_intercept_are_applied(make_dicom):
    stored = np.array([[0, 1000], [2000, 3000]], dtype=np.uint16)
    image = load_dicom(make_dicom(stored, slope=1, intercept=-1024))
    np.testing.assert_array_equal(image.pixels, [[-1024, -24], [976, 1976]])

    image = load_dicom(make_dicom(stored, slope=0.5, intercept=10))
    np.testing.assert_array_equal(image.pixels, [[10, 510], [1010, 1510]])
    assert image.meta.rescale_slope == 0.5


def test_signed_pixels(make_dicom):
    stored = np.array([[-1000, 0], [500, 32767]], dtype=np.int16)
    np.testing.assert_array_equal(load_dicom(make_dicom(stored)).pixels, stored)


def test_monochrome1_pixels_are_not_inverted(make_dicom):
    stored = np.array([[0, 255]], dtype=np.uint8)
    image = load_dicom(make_dicom(stored, photometric="MONOCHROME1"))

    assert image.meta.is_monochrome1
    np.testing.assert_array_equal(image.pixels, [[0, 255]])  # 값은 그대로, 반전은 화면 표시 때


def test_reads_jpeg_compressed_dicom(make_dicom):
    """실제 데이터처럼 JPEG Baseline으로 압축된 8비트 DICOM. 손실 압축이라 값은 근사."""
    stored = np.full((32, 48), 40, dtype=np.uint8)
    stored[:, 24:] = 210
    image = load_dicom(make_dicom(stored, jpeg=True))

    assert image.pixels.shape == (32, 48)
    assert abs(image.pixels[5, 5] - 40) <= 3
    assert abs(image.pixels[5, 40] - 210) <= 3


@pytest.mark.parametrize("wrap", [lambda p: p.read_bytes(), lambda p: io.BytesIO(p.read_bytes()), str])
def test_accepts_bytes_file_object_and_str_path(make_dicom, wrap):
    """경로뿐 아니라 업로드 파일처럼 bytes·파일 객체도 읽는다."""
    path = make_dicom(sample_pixels())
    assert load_dicom(wrap(path)).pixels.shape == (4, 6)


def test_no_pixel_data(make_dicom):
    with pytest.raises(DicomNoPixelDataError) as exc_info:
        load_dicom(make_dicom(None))
    assert isinstance(exc_info.value, DicomReadError)
    assert exc_info.value.message


def test_missing_file(tmp_path):
    with pytest.raises(DicomReadError):
        load_dicom(tmp_path / "nothing.dcm")


def test_not_a_dicom_file(tmp_path):
    path = tmp_path / "fake.dcm"
    path.write_bytes(b"this is not a dicom file" * 10)
    with pytest.raises(DicomReadError):
        load_dicom(path)


@pytest.mark.parametrize("keep", [0.3, 0.6, 0.95])
def test_truncated_file(make_dicom, tmp_path, keep):
    """파일 뒷부분이 잘린 손상 파일 (헤더 중간, 픽셀 중간에서 잘림)."""
    data = make_dicom(np.zeros((64, 64), dtype=np.uint16)).read_bytes()
    broken = tmp_path / "broken.dcm"
    broken.write_bytes(data[: int(len(data) * keep)])
    with pytest.raises(DicomReadError):
        load_dicom(broken)


@pytest.mark.parametrize("keep", [0.5, 0.9])
def test_truncated_jpeg_file_is_not_reported_as_no_pixel(make_dicom, tmp_path, keep):
    """압축 파일이 픽셀 데이터 중간에서 잘리면 '픽셀 없음'이 아니라 '손상'으로 알린다."""
    data = make_dicom(np.random.default_rng(0).integers(0, 255, (128, 128), dtype=np.uint8), jpeg=True).read_bytes()
    broken = tmp_path / "broken.dcm"
    broken.write_bytes(data[: int(len(data) * keep)])
    with pytest.raises(DicomReadError) as exc_info:
        load_dicom(broken)
    assert not isinstance(exc_info.value, DicomNoPixelDataError)
    assert "손상" in exc_info.value.message


def test_corrupted_jpeg_pixel_data(tmp_path):
    ds = build_dataset(np.zeros((16, 16), dtype=np.uint8), jpeg=True)
    ds.PixelData = ds.PixelData[:40] + b"\x00" * 40  # 압축 데이터 손상
    path = tmp_path / "bad_jpeg.dcm"
    ds.save_as(path, enforce_file_format=True)
    with pytest.raises(DicomReadError):
        load_dicom(path)


def test_color_dicom_is_rejected(tmp_path):
    ds = build_dataset(np.zeros((4, 4), dtype=np.uint8))
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.PlanarConfiguration = 0
    ds.PixelData = rgb.tobytes()
    path = tmp_path / "color.dcm"
    ds.save_as(path, enforce_file_format=True)
    with pytest.raises(DicomReadError, match="컬러"):
        load_dicom(path)


def test_multi_frame_dicom_is_rejected(tmp_path):
    frames = np.zeros((2, 4, 4), dtype=np.uint8)
    ds = build_dataset(frames[0])
    ds.NumberOfFrames = 2
    ds.PixelData = frames.tobytes()
    path = tmp_path / "multi.dcm"
    ds.save_as(path, enforce_file_format=True)
    with pytest.raises(DicomReadError, match="프레임"):
        load_dicom(path)
