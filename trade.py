import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="관세청 선용품 무역통계", layout="wide")

st.title("🚢 전국 항구별 선용품 무역통계 분석")

# 1. 데이터 로드 함수 (헤더 3줄 처리)
@st.cache_data
def load_combined_data():
    # 파일 목록 (업로드하신 파일명 패턴 기반)
    files = [f for f in os.listdir('.') if f.endswith('.csv') and '환급대상물품' in f]
    
    all_data = []
    for f in files:
        try:
            # 연도 추출 (파일명에서 '2025' 등 4자리 숫자)
            year = "".join(filter(str.isdigit, f))[:4]
            
            # 데이터 읽기: 0, 1번 행은 무시하고 2번 행부터 데이터로 인식
            df = pd.read_csv(f, skiprows=2)
            
            # 컬럼명 정리 (항구, 항구명, ..., 연간합계_건수, 연간합계_금액)
            # 마지막 두 컬럼이 연간 합계 건수와 금액입니다.
            df = df.iloc[:, [0, 1, -2, -1]] 
            df.columns = ['항구코드', '항구명', '연간합계_건수', '연간합계_금액']
            df['연도'] = year
            
            # 숫자 데이터 변환 (쉼표 제거)
            df['연간합계_금액'] = pd.to_numeric(df['연간합계_금액'].astype(str).str.replace(',', ''), errors='coerce')
            df['연간합계_건수'] = pd.to_numeric(df['연간합계_건수'].astype(str).str.replace(',', ''), errors='coerce')
            
            all_data.append(df.dropna(subset=['항구명']))
        except:
            continue
            
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 데이터 로드
df = load_combined_data()

if df.empty:
    st.error("데이터 파일을 찾을 수 없습니다. CSV 파일들이 코드와 같은 폴더에 있는지 확인하세요.")
else:
    # 사이드바 필터
    st.sidebar.header("🔍 검색 필터")
    target_ports = st.sidebar.multiselect("분석할 항구 선택", options=df['항구명'].unique(), default=['부산항', '인천항', '울산항', '마산항'])
    
    filtered_df = df[df['항구명'].isin(target_ports)].sort_values('연도')

    # KPI 지표
    m1, m2 = st.columns(2)
    with m1:
        total_amt = filtered_df['연간합계_금액'].sum()
        st.metric("선택 항구 총 거래액", f"${total_amt:,.0f}")
    with m2:
        total_cnt = filtered_df['연간합계_건수'].sum()
        st.metric("선택 항구 총 거래 건수", f"{total_cnt:,.0f}건")

    st.divider()

    # 시각화 1: 연도별 거래 규모 추이
    st.subheader("📈 연도별 선용품 거래 규모 추이 (환급대상)")
    fig = px.line(filtered_df, x='연도', y='연간합계_금액', color='항구명', markers=True,
                  labels={'연간합계_금액': '거래 금액 ($)'}, template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

    # 시각화 2: 항구별 비중 (가장 최근 연도 기준)
    st.subheader("📊 최신 연도 기준 항구별 비중")
    latest_year = filtered_df['연도'].max()
    pie_data = filtered_df[filtered_df['연도'] == latest_year]
    
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(pie_data, values='연간합계_금액', names='항구명', hole=0.4, title=f"{latest_year}년 금액 기준")
        st.plotly_chart(fig_pie)
    with c2:
        st.write(f"**{latest_year}년 상세 데이터**")
        st.dataframe(pie_data[['항구명', '연간합계_건수', '연간합계_금액']].reset_index(drop=True), use_container_width=True)