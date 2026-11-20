"""비즈니스 로직 및 데이터 처리 함수 모음 (테스트 대상)"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def generate_sample_pacs_data(n_samples: int = 150, seed: int = 42) -> pd.DataFrame:
    """PACS 검사 이력 샘플 데이터프레임을 생성합니다."""
    np.random.seed(seed)

    modalities = ["CT", "MRI", "X-Ray", "Ultrasound", "Mammography"]
    body_parts = ["Chest", "Brain", "Abdomen", "Spine", "Extremity"]
    statuses = ["대기", "판독중", "판독완료"]
    departments = ["영상의학과", "신경과", "정형외과", "내과", "응급의학과"]

    base_date = datetime.now() - timedelta(days=30)
    dates = [
        base_date + timedelta(days=int(np.random.randint(0, 30)), hours=int(np.random.randint(0, 24)))
        for _ in range(n_samples)
    ]

    data = {
        "accession_no": [f"ACC{20240000 + i}" for i in range(1, n_samples + 1)],
        "patient_id": [f"P{1000 + (i % 50)}" for i in range(n_samples)],
        "timestamp": dates,
        "modality": np.random.choice(modalities, size=n_samples, p=[0.3, 0.25, 0.25, 0.15, 0.05]),
        "body_part": np.random.choice(body_parts, size=n_samples),
        "department": np.random.choice(departments, size=n_samples),
        "status": np.random.choice(statuses, size=n_samples, p=[0.2, 0.2, 0.6]),
        "image_count": np.random.randint(5, 500, size=n_samples),
        "urgency": np.random.choice(["보통", "긴급", "응급"], size=n_samples, p=[0.7, 0.2, 0.1]),
    }

    df = pd.DataFrame(data)
    df.sort_values(by="timestamp", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def filter_pacs_data(
    df: pd.DataFrame,
    modalities: list[str] | None = None,
    statuses: list[str] | None = None,
    urgency: list[str] | None = None,
) -> pd.DataFrame:
    """조건에 따라 PACS 데이터를 필터링합니다."""
    filtered = df.copy()

    if modalities:
        filtered = filtered[filtered["modality"].isin(modalities)]
    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]
    if urgency:
        filtered = filtered[filtered["urgency"].isin(urgency)]

    return filtered


def calculate_summary_metrics(df: pd.DataFrame) -> dict:
    """대시보드 요약 지표를 계산합니다."""
    total_studies = len(df)
    completed_studies = int((df["status"] == "판독완료").sum())
    pending_studies = int((df["status"] == "대기").sum())
    in_progress_studies = int((df["status"] == "판독중").sum())
    emergency_studies = int((df["urgency"] == "응급").sum())
    total_images = int(df["image_count"].sum()) if not df.empty else 0

    completion_rate = (completed_studies / total_studies * 100) if total_studies > 0 else 0.0

    return {
        "total_studies": total_studies,
        "completed_studies": completed_studies,
        "pending_studies": pending_studies,
        "in_progress_studies": in_progress_studies,
        "emergency_studies": emergency_studies,
        "completion_rate": round(completion_rate, 1),
        "total_images": total_images,
    }
