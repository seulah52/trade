import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# 페이지 설정
st.set_page_config(page_title="관세청 선용품 무역통계 분석", layout="wide")

st.title("🚢 전국 항구별 선용품 무역통계 실무 대시보드")
st.info("파일 구조를 분석하여 2015년~2025년 데이터를 통합합니다.")

@st.cache_data
def load_all_trade_data():
    # '환급대상물품'이 포함된 CSV 파일만 수집
    files = [f for f in os.listdir('.') if f.endswith('.csv') and '환급대상물품' in f]
    
    all_years_data = []
    
    for f in files:
        try:
            # 1. 연도 추출 (파일명에서 ' - 20XX년' 형태를 찾음)
            year_match = re.search(r'(\d{4})년', f)
            year = year_match.group(1) if year_match else "Unknown"
            
            # 2. 데이터 읽기 (상단 헤더 3줄 스킵)
            # 업로드된 파일 구조상 3행부터 실제 데이터 시작
            df_raw = pd.read_csv(f, skiprows=3, header=None)
            
            # 3. 필요한 컬럼만 추출 (0:코드, 1:항구명, 마지막-1:연간건수, 마지막:연간금액)
            # iloc을 사용하여 컬럼 이름에 의존하지 않고 위치로 가져옴
            df_subset = df_raw.iloc[:, [0, 1, len(df_raw.columns)-2, len(df_raw.columns)-1]]
            df_subset.columns = ['항구코드', '항구명', '건수', '금액']
            df_subset['연도'] = year
            
            # 4. 데이터 정제 (숫자 변환 및 불필요한 행 제거)
            for col in ['건수', '금액']:
                df_subset[col] = pd.to_numeric(df_subset[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 항구명이 비어있거나 '합계'가 포함된 행 필터링
            df_subset = df_subset.dropna(subset=['항구명'])
            df_subset = df_subset[~df_subset['항구명'].str.contains('합계|항구명|항구', na=False)]
            
            all_years_data.append(df_subset)
        except Exception as e:
            st.error(f"파일 처리 중 오류 발생 ({f}): {e}")
            
    return pd.concat(all_years_data, ignore_index=True) if all_years_data else pd.DataFrame()

# 데이터 로드
df = load_all_trade_data()

if df.empty:
    st.warning("⚠️ 분석 가능한 CSV 파일을 찾지 못했습니다. 파일이 GitHub에 Push 되었는지 확인하세요.")
else:
    # --- 시각화 부분 ---
    st.sidebar.header("📊 분석 필터")
    
    # 항구 선택 (최다 거래액 순으로 정렬하여 표시)
    port_rank = df.groupby('항구명')['금액'].sum().sort_values(ascending=False).index.tolist()
    selected_ports = st.sidebar.multiselect("분석할 항구 선택", options=port_rank, default=port_rank[:5])
    
    filtered_df = df[df['항구명'].isin(selected_ports)].sort_values('연도')

    # KPI 메트릭
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 거래 금액", f"${filtered_df['금액'].sum():,.0f}")
    with c2:
        st.metric("총 거래 건수", f"{filtered_df['건수'].sum():,.0f}건")
    with c3:
        st.metric("분석 대상 항구", f"{len(selected_ports)}개")

    st.divider()

    # 차트 1: 연도별 금액 추이
    st.subheader("📈 연도별 선용품 거래액 추이")
    fig_line = px.line(filtered_df, x='연도', y='금액', color='항구명', markers=True, 
                       template='plotly_white', height=500)
    st.plotly_chart(fig_line, use_container_width=True)

    # 차트 2: 항구별 비교
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("💰 항구별 누적 거래액 비중")
        fig_pie = px.pie(filtered_df, values='금액', names='항구명', hole=0.3)
        st.plotly_chart(fig_pie)
    
    with col_right:
        st.subheader("📋 선택 데이터 상세 내역")
        st.dataframe(filtered_df.sort_values(['연도', '금액'], ascending=[False, False]), 
                     use_container_width=True, hide_index=True)

    # 데이터 다운로드 버튼
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 정제된 데이터 다운로드 (CSV)", data=csv, file_name="trade_analysis.csv")