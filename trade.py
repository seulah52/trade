import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os

# 페이지 설정
st.set_page_config(page_title="관세청 선용품 무역통계 대시보드", layout="wide")

st.title("🚢 전국 항구별 선용품 무역통계 분석")
st.markdown("관세청 데이터를 기반으로 한 연도별 선용품 무역 트렌드 대시보드입니다.")

# 1. 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    # 파일 경로 리스트 (실제 환경에 맞춰 수정 필요)
    # 여기서는 예시로 2021~2025년 일반 통계 파일만 합치는 로직을 보여드립니다.
    files = [
        '관세청_전국 항구별 선용품 무역통계_20251231.xlsx - 2025년.csv',
        '관세청_전국 항구별 선용품 무역통계_20251231.xlsx - 2024년.csv',
        '관세청_전국 항구별 선용품 무역통계_20251231.xlsx - 2023년.csv',
        '관세청_전국 항구별 선용품 무역통계_20251231.xlsx - 2022년.csv',
        '관세청_전국 항구별 선용품 무역통계_20251231.xlsx - 2021년.csv'
    ]
    
    all_years = []
    for f in files:
        if os.path.exists(f):
            year = f.split(' - ')[1][:4]
            # 헤더가 복잡하므로 3행부터 읽거나 컬럼을 직접 지정해야 함
            df = pd.read_csv(f, skiprows=3) 
            # 실제 파일 구조에 맞게 컬럼명 재정의 (항구, 품목, 연간합계_금액 등)
            # 여기서는 '연간 합계' 컬럼의 위치를 찾아 데이터를 추출합니다.
            df['연도'] = year
            all_years.append(df)
    
    return pd.concat(all_years, ignore_index=True)

# 데이터 불러오기 (파일이 없을 경우 대비 에러 처리)
try:
    df_raw = load_data()
    # 데이터 클렌징 (예시: '합계' 행 제외 및 숫자 변환)
    df_raw = df_raw.dropna(subset=['항구'])
    df_filtered = df_raw[df_raw['품목분류\n(대분류명)'] != '합계']
    
    # 2. 사이드바 필터
    st.sidebar.header("🔍 데이터 필터")
    selected_ports = st.sidebar.multiselect("분석할 항구를 선택하세요", 
                                            options=df_filtered['항구'].unique(),
                                            default=df_filtered['항구'].unique()[:5])
    
    if not selected_ports:
        st.warning("항구를 하나 이상 선택해주세요.")
        st.stop()

    final_df = df_filtered[df_filtered['항구'].isin(selected_ports)]

    # 3. 상단 KPI 지표
    # '연간 합계' 금액 컬럼을 숫자로 변환 (쉼표 제거 등)
    col_total_amt = final_df.columns[-2] # 파일 구조상 끝에서 두번째가 보통 연간 합계 금액
    final_df[col_total_amt] = pd.to_numeric(final_df[col_total_amt].replace(',', ''), errors='coerce').fillna(0)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("총 분석 항구 수", f"{len(selected_ports)}개")
    with m2:
        total_val = final_df[col_total_amt].sum()
        st.metric("선용품 총 거래액", f"{total_val:,.0f} USD")
    with m3:
        st.metric("최다 품목", final_df.groupby('품목분류\n(대분류명)')[col_total_amt].sum().idxmax())

    st.divider()

    # 4. 시각화 섹션
    c1, c2 = st.columns([6, 4])

    with c1:
        st.subheader("📈 연도별/항구별 거래 규모 추이")
        # 연도별 합계 계산
        trend_df = final_df.groupby(['연도', '항구'])[col_total_amt].sum().reset_index()
        fig_line = px.line(trend_df, x='연도', y=col_total_amt, color='항구', 
                           markers=True, template='plotly_white',
                           labels={col_total_amt: '거래 금액 (USD)'})
        st.plotly_chart(fig_line, use_container_width=True)

    with c2:
        st.subheader("🍰 항구별 거래 비중")
        fig_pie = px.pie(trend_df, values=col_total_amt, names='항구', 
                         hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("📦 주요 품목별 순위 (TOP 10)")
        item_df = final_df.groupby('품목분류\n(대분류명)')[col_total_amt].sum().sort_values(ascending=True).tail(10).reset_index()
        fig_bar = px.bar(item_df, x=col_total_amt, y='품목분류\n(대분류명)', orientation='h',
                         color=col_total_amt, color_continuous_scale='Viridis')
        st.plotly_chart(fig_bar, use_container_width=True)

    with c4:
        st.subheader("📋 세부 데이터 요약")
        st.dataframe(final_df[['연도', '항구', '품목분류\n(대분류명)', col_total_amt]].sort_values(by='연도', ascending=False), 
                     use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"데이터를 로드하는 중 오류가 발생했습니다: {e}")
    st.info("파일 이름이 코드와 일치하는지, 데이터 경로가 올바른지 확인해주세요.")