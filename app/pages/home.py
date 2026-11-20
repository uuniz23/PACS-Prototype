"""홈 페이지: PACS 시스템 소개 및 빠른 현황 안내"""

import streamlit as st
import pandas as pd
from datetime import datetime
from app.logic import calculate_summary_metrics


def render_home_page():
    st.title("🏥 PACS 영상검사 관리 시스템")
    st.markdown(
        """
        **PACS (Picture Archiving and Communication System)** 모니터링 및 분석 대시보드 예시 애플리케이션입니다.  
        병원 내 발생하는 다양한 의료 영상(CT, MRI, X-Ray 등) 검사 현황을 실시간으로 추적하고 분석할 수 있습니다.
        """
    )

    st.write("")

    # 핵심 기능 소개 카드
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("### 📊 실시간 대시보드")
            st.write("검사 진행률, 판독 대기 현황, 장비별 통계를 직관적인 차트로 시각화합니다.")
    with col2:
        with st.container(border=True):
            st.markdown("### 🔍 다차원 필터링")
            st.write("모달리티, 판독 상태, 긴급도에 따른 상세 검색 및 데이터 다운로드를 지원합니다.")
    with col3:
        with st.container(border=True):
            st.markdown("### ⚡ 신속한 응급 대응")
            st.write("응급 판독 대상 건을 별도로 모니터링하여 의료진의 빠른 의사결정을 돕습니다.")

    st.divider()

    # 빠른 현황 요약
    df = st.session_state.data
    metrics = calculate_summary_metrics(df)

    st.subheader("📌 오늘의 요약 현황")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 검사 건수", f"{metrics['total_studies']}건")
    m2.metric("판독 완료율", f"{metrics['completion_rate']}%")
    m3.metric("판독 대기", f"{metrics['pending_studies']}건", delta=f"{metrics['in_progress_studies']}건 진행중", delta_color="inverse")
    m4.metric("🚨 응급 요청", f"{metrics['emergency_studies']}건")

    st.divider()

    # 간이 검사 등록 폼 (인터랙션 예시)
    st.subheader("➕ 신규 영상검사 등록 데모")
    with st.form("new_study_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            patient_id = st.text_input("환자 ID", value="P1099")
            modality = st.selectbox("모달리티", ["CT", "MRI", "X-Ray", "Ultrasound", "Mammography"])
        with c2:
            body_part = st.selectbox("부위", ["Chest", "Brain", "Abdomen", "Spine", "Extremity"])
            department = st.selectbox("진료과", ["영상의학과", "신경과", "정형외과", "내과", "응급의학과"])
        with c3:
            urgency = st.selectbox("긴급도", ["보통", "긴급", "응급"])
            image_count = st.number_input("이미지 수(장)", min_value=1, max_value=2000, value=120)

        submitted = st.form_submit_button("검사 등록", use_container_width=True)

        if submitted:
            new_row = {
                "accession_no": f"ACC{int(datetime.now().timestamp()) % 100000000}",
                "patient_id": patient_id,
                "timestamp": datetime.now(),
                "modality": modality,
                "body_part": body_part,
                "department": department,
                "status": "대기",
                "image_count": int(image_count),
                "urgency": urgency,
            }
            # 세션 데이터에 추가
            st.session_state.data = pd.concat([pd.DataFrame([new_row]), st.session_state.data], ignore_index=True)
            st.success(f"신규 검사(접수번호: {new_row['accession_no']})가 성공적으로 등록되었습니다!")
            st.rerun()
