"""테스트 공용 도우미: 테스트용 작은 DICOM 파일을 코드로 만든다.

실제 영상(data/, *.dcm)은 저장소와 CI에 없으므로, 테스트에 필요한 DICOM은
pydicom으로 그때그때 임시 폴더(tmp_path)에 만든다.
"""

import io

import numpy as np
import pytest
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.encaps import encapsulate
from pydicom.uid import (
    ExplicitVRLittleEndian,
    JPEGBaseline8Bit,
    SecondaryCaptureImageStorage,
    generate_uid,
)


def build_dataset(
    pixels: np.ndarray | None,
    *,
    photometric: str = "MONOCHROME2",
    slope=None,
    intercept=None,
    window=None,
    jpeg: bool = False,
    **tags,
) -> FileDataset:
    """pixels(2차원 uint8/uint16/int16)로 DICOM Dataset을 만든다. pixels=None이면 픽셀 없음."""
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = JPEGBaseline8Bit if jpeg else ExplicitVRLittleEndian

    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.PatientID = "test-patient-0001"
    ds.PatientName = "Test^Patient"
    ds.PatientBirthDate = "19000101"
    ds.PatientSex = "O"
    ds.Modality = "CR"
    ds.BodyPartExamined = "CHEST"
    ds.ViewPosition = "PA"
    ds.PixelSpacing = [0.14, 0.14]

    if pixels is not None:
        ds.Rows, ds.Columns = pixels.shape
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = photometric
        bits = pixels.dtype.itemsize * 8
        ds.BitsAllocated = bits
        ds.BitsStored = bits
        ds.HighBit = bits - 1
        ds.PixelRepresentation = 1 if np.issubdtype(pixels.dtype, np.signedinteger) else 0
        if jpeg:
            buffer = io.BytesIO()
            Image.fromarray(pixels).save(buffer, format="JPEG", quality=95)
            ds.PixelData = encapsulate([buffer.getvalue()])
            ds["PixelData"].VR = "OB"
        else:
            ds.PixelData = pixels.tobytes()

    if slope is not None:
        ds.RescaleSlope = slope
    if intercept is not None:
        ds.RescaleIntercept = intercept
    if window is not None:
        ds.WindowCenter, ds.WindowWidth = window
    for name, value in tags.items():
        setattr(ds, name, value)
    return ds


@pytest.fixture
def make_dicom(tmp_path):
    """make_dicom(pixels, **옵션) → 임시 .dcm 파일 경로."""
    counter = {"n": 0}

    def _make(pixels, **options):
        counter["n"] += 1
        path = tmp_path / f"test_{counter['n']}.dcm"
        build_dataset(pixels, **options).save_as(path, enforce_file_format=True)
        return path

    return _make
