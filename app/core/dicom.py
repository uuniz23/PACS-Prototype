"""DICOM 파일 읽기.

`load_dicom()`은 .dcm 파일을 읽어 픽셀 배열과 화면·처리에 필요한 메타정보만 돌려준다.
streamlit, firebase_admin을 import하지 않는다.

처리 규칙
- RescaleSlope / RescaleIntercept: **적용한다.** 픽셀 값 = 저장값 x slope + intercept.
  CT의 HU처럼 의미 있는 값으로 바꾸기 위해서다. 태그가 없으면 slope=1, intercept=0.
  그래서 픽셀 배열은 항상 float32로 돌려준다.
- MONOCHROME1(값이 클수록 어두움): **픽셀 값은 바꾸지 않는다.**
  값의 의미(원본 데이터)를 유지하고, 화면에 보여 줄 때만 밝기를 뒤집는다.
  `DicomMeta.is_monochrome1`을 보고 `windowing.apply_window(..., invert=True)`로 처리하며,
  `windowing.render()`는 이를 자동으로 한다.
- 지원 범위: 흑백(SamplesPerPixel=1) 단일 프레임 2차원 영상.
  압축 형식은 pydicom이 기본으로 풀 수 있는 것(비압축, RLE, JPEG Baseline 등 Pillow로 가능한 것)만.
  컬러 영상, 여러 프레임 영상은 DicomReadError를 낸다.

개인정보
- 메타정보에는 환자 이름, 생년월일, 성별, 나이 등을 담지 않는다.
- `patient_id`는 라벨 CSV와 영상을 맞추는 내부용이다. 화면에 그대로 표시하지 않는다.
  실수로 출력되지 않도록 `repr()`에서도 숨긴다.
"""

from __future__ import annotations

import io
import os
import warnings
from dataclasses import dataclass, field
from typing import BinaryIO, Union

import numpy as np
import pydicom
from pydicom.errors import InvalidDicomError

DicomSource = Union[str, os.PathLike, bytes, BinaryIO]


class DicomReadError(Exception):
    """DICOM을 읽을 수 없음. `message`는 화면에 그대로 보여 줄 수 있는 문장이다."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DicomNoPixelDataError(DicomReadError):
    """DICOM 파일이지만 영상(픽셀 데이터)이 들어 있지 않음."""


@dataclass(frozen=True)
class DicomMeta:
    """화면·처리에 필요한 메타정보만 담는다."""

    rows: int  # 높이(세로 픽셀 수) = pixels.shape[0]
    columns: int  # 너비(가로 픽셀 수) = pixels.shape[1]
    photometric_interpretation: str  # "MONOCHROME1" 또는 "MONOCHROME2"
    bits_stored: int | None
    rescale_slope: float
    rescale_intercept: float
    window_center: float | None  # 헤더 기본 window. 없으면 None
    window_width: float | None
    pixel_spacing: tuple[float, float] | None  # (행 간격, 열 간격) mm
    modality: str | None  # 예: "CR", "CT"
    body_part: str | None  # 예: "CHEST"
    view_position: str | None  # 예: "PA", "AP"
    patient_id: str | None = field(default=None, repr=False)  # 내부 매칭용, 화면 표시 금지

    @property
    def is_monochrome1(self) -> bool:
        return self.photometric_interpretation == "MONOCHROME1"


@dataclass(frozen=True)
class DicomImage:
    pixels: np.ndarray  # float32, shape (rows, columns) = (높이, 너비), rescale 적용됨
    meta: DicomMeta


def load_dicom(source: DicomSource) -> DicomImage:
    """DICOM을 읽어 DicomImage를 돌려준다.

    입력: 파일 경로(str, Path), 파일 내용(bytes), 또는 읽기 가능한 파일 객체
          (예: streamlit 업로드 파일).
    반환: DicomImage. pixels는 float32 2차원 배열 (rows, columns), rescale 적용 값.
    오류:
        DicomNoPixelDataError  픽셀 데이터가 없는 DICOM
        DicomReadError         파일 없음, DICOM 아님, 손상, 지원하지 않는 형식
    """
    ds = _read_dataset(source)

    if "PixelData" not in ds:
        raise DicomNoPixelDataError("영상(픽셀 데이터)이 없는 DICOM 파일입니다.")

    samples = int(ds.get("SamplesPerPixel", 1) or 1)
    if samples != 1:
        raise DicomReadError("컬러 DICOM은 지원하지 않습니다. 흑백 영상만 열 수 있습니다.")
    frames = int(ds.get("NumberOfFrames", 1) or 1)
    if frames != 1:
        raise DicomReadError("여러 프레임 DICOM은 지원하지 않습니다. 단일 영상만 열 수 있습니다.")

    try:
        raw = ds.pixel_array
    except Exception as exc:  # 손상된 픽셀 데이터, 풀 수 없는 압축 형식 등
        raise DicomReadError(f"영상 데이터를 읽을 수 없습니다. (파일 손상 또는 지원하지 않는 압축 형식: {exc})") from exc

    if raw.ndim != 2:
        raise DicomReadError("2차원 흑백 영상만 지원합니다.")

    slope = _to_float(ds.get("RescaleSlope"), default=1.0)
    intercept = _to_float(ds.get("RescaleIntercept"), default=0.0)
    pixels = raw.astype(np.float32) * np.float32(slope) + np.float32(intercept)

    meta = DicomMeta(
        rows=int(pixels.shape[0]),
        columns=int(pixels.shape[1]),
        photometric_interpretation=str(ds.get("PhotometricInterpretation", "MONOCHROME2")),
        bits_stored=_to_int(ds.get("BitsStored")),
        rescale_slope=slope,
        rescale_intercept=intercept,
        window_center=_first_float(ds.get("WindowCenter")),
        window_width=_first_float(ds.get("WindowWidth")),
        pixel_spacing=_pixel_spacing(ds.get("PixelSpacing")),
        modality=_to_str(ds.get("Modality")),
        body_part=_to_str(ds.get("BodyPartExamined")),
        view_position=_to_str(ds.get("ViewPosition")),
        patient_id=_to_str(ds.get("PatientID")),
    )
    return DicomImage(pixels=pixels, meta=meta)


# ---------------------------------------------------------------- 내부 함수


def _read_dataset(source: DicomSource) -> pydicom.Dataset:
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    try:
        # 파일이 중간에 잘리면 pydicom은 오류 대신 경고만 내고 남은 부분을 버린다.
        # (예: 픽셀 데이터 중간에서 잘린 압축 파일 → PixelData가 없는 것처럼 보임)
        # 이 경고를 잡아 '손상'으로 알린다.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ds = pydicom.dcmread(source)
    except FileNotFoundError as exc:
        raise DicomReadError("파일을 찾을 수 없습니다.") from exc
    except InvalidDicomError as exc:
        raise DicomReadError("DICOM 파일이 아닙니다.") from exc
    except Exception as exc:  # 잘린 파일, 깨진 헤더 등
        raise DicomReadError(f"DICOM 파일을 읽을 수 없습니다. (파일 손상: {exc})") from exc

    for warning in caught:
        if "end of file" in str(warning.message).lower():
            raise DicomReadError("DICOM 파일이 중간에 잘려 있습니다. (파일 손상)")
    for warning in caught:  # 그 밖의 경고는 그대로 다시 알린다
        warnings.warn_explicit(warning.message, warning.category, warning.filename, warning.lineno)
    return ds


def _to_float(value, default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _first_float(value) -> float | None:
    """WindowCenter/Width는 값이 여러 개일 수 있다. 첫 번째 값을 쓴다."""
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple, pydicom.multival.MultiValue)):
        if len(value) == 0:
            return None
        value = value[0]
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _to_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pixel_spacing(value) -> tuple[float, float] | None:
    try:
        if value is None or len(value) != 2:
            return None
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return None
