"""대시보드 페이지: 영상검사 데이터 시각화 및 필터링 테이블"""

import streamlit as st
import plotly.express as px
from app.logic import filter_pacs_data, calculate_summary_metrics


def render_dashboard_page():
    st.title("📊 PACS 영상검사 대시보드")
    st.caption("필터를 조정하여 검사 통계 및 세부 목록을 확인할 수 있습니다.")

    raw_df = st.session_state.data

    # 1. 상단 필터 영역
    with st.expander("🔍 검색 및 필터 옵션", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            all_modalities = sorted(list(raw_df["modality"].unique()))
            selected_modalities = st.multiselect(
                "모달리티 (Modality)",
                options=all_modalities,
                default=all_modalities,
            )
        with col2:
            all_statuses = ["대기", "판독중", "판독완료"]
            selected_statuses = st.multiselect(
                "판독 상태",
                options=all_statuses,
                default=all_statuses,
            )
        with col3:
            all_urgency = ["보통", "긴급", "응급"]
            selected_urgency = st.multiselect(
                "긴급도",
                options=all_urgency,
                default=all_urgency,
            )

    # 데이터 필터링 적용
    df = filter_pacs_data(
        raw_df,
        modalities=selected_modalities,
        statuses=selected_statuses,
        urgency=selected_urgency,
    )

    if df.empty:
        st.warning("선택한 필터 조건에 부합하는 검사 내역이 없습니다.")
        return

    # 2. 메트릭 지표
    metrics = calculate_summary_metrics(df)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("선택된 검사", f"{metrics['total_studies']}건")
    m2.metric("판독 완료율", f"{metrics['completion_rate']}%")
    m3.metric("판독 대기 건수", f"{metrics['pending_studies']}건")
    m4.metric("누적 영상 수", f"{metrics['total_images']:,}장")

    st.write("")

    # 3. 차트 영역
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### 모달리티별 검사 비중")
        modality_counts = df["modality"].value_counts().reset_index()
        modality_counts.columns = ["modality", "count"]
        fig_pie = px.pie(
            modality_counts,
            names="modality",
            values="count",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        st.markdown("#### 판독 상태별 분포")
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig_bar = px.bar(
            status_counts,
            x="status",
            y="count",
            color="status",
            color_discrete_map={"판독완료": "#28a745", "판독중": "#ffc107", "대기": "#dc3545"},
            text_auto=True,
        )
        fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    # 4. 검사 목록 데이터 테이블 및 다운로드
    st.markdown("#### 📋 상세 검사 목록")
    st.dataframe(
        df[["accession_no", "patient_id", "timestamp", "modality", "body_part", "department", "status", "urgency", "image_count"]],
        use_container_width=True,
        hide_index=True,
    )

    # CSV 다운로드
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 필터링된 데이터 CSV 다운로드",
        data=csv_data,
        file_name="pacs_filtered_studies.csv",
        mime="text/csv",
    )
