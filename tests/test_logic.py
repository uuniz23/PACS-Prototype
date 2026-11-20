"""app.logic 비즈니스 로직 단위 테스트"""

import pytest
import pandas as pd
from app.logic import (
    generate_sample_pacs_data,
    filter_pacs_data,
    calculate_summary_metrics,
)


@pytest.fixture
def sample_df():
    """테스트용 샘플 데이터셋 피스처"""
    return generate_sample_pacs_data(n_samples=50, seed=123)


def test_generate_sample_pacs_data(sample_df):
    """샘플 데이터 생성 규격 검증"""
    assert len(sample_df) == 50
    expected_columns = {
        "accession_no",
        "patient_id",
        "timestamp",
        "modality",
        "body_part",
        "department",
        "status",
        "image_count",
        "urgency",
    }
    assert expected_columns.issubset(sample_df.columns)
    assert (sample_df["image_count"] > 0).all()


def test_filter_pacs_data_modality(sample_df):
    """모달리티 필터링 검증"""
    filtered = filter_pacs_data(sample_df, modalities=["CT"])
    assert all(filtered["modality"] == "CT")


def test_filter_pacs_data_multiple_conditions(sample_df):
    """복합 필터링 검증"""
    filtered = filter_pacs_data(
        sample_df,
        modalities=["MRI", "X-Ray"],
        statuses=["판독완료"],
        urgency=["보통"],
    )
    if not filtered.empty:
        assert all(filtered["modality"].isin(["MRI", "X-Ray"]))
        assert all(filtered["status"] == "판독완료")
        assert all(filtered["urgency"] == "보통")


def test_calculate_summary_metrics(sample_df):
    """요약 지표 산출 검증"""
    metrics = calculate_summary_metrics(sample_df)
    assert metrics["total_studies"] == 50
    assert metrics["completed_studies"] + metrics["pending_studies"] + metrics["in_progress_studies"] == 50
    assert 0.0 <= metrics["completion_rate"] <= 100.0
    assert metrics["total_images"] > 0


def test_calculate_summary_metrics_empty():
    """빈 데이터프레임 요약 지표 처리 검증"""
    empty_df = pd.DataFrame(
        columns=[
            "accession_no",
            "patient_id",
            "timestamp",
            "modality",
            "body_part",
            "department",
            "status",
            "image_count",
            "urgency",
        ]
    )
    metrics = calculate_summary_metrics(empty_df)
    assert metrics["total_studies"] == 0
    assert metrics["completed_studies"] == 0
    assert metrics["completion_rate"] == 0.0
    assert metrics["total_images"] == 0
