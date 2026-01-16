import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re

# --- 페이지 설정 ---
st.set_page_config(page_title="선용품 무역통계 실무 대시보드", layout="wide", initial_sidebar_state="expanded")

# --- 스타일링 ---
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 로드 및 전처리 ---
@st.cache_data
def load_and_clean_data():
    all_files = [f for f in os.listdir('.') if f.endswith('.csv') and '환급대상물품' in f]
    combined_list = []
    
    for file in all_files:
        try:
            # 파일명에서 연도 추출
            year = re.search(r'\d{4}', file).group()
            
            # 관세청 특유의 3단 헤더 처리 (건수/금액 데이터는 3행부터 시작)
            df = pd.read_csv(file, skiprows=3, header=None)
            
            # 필요한 컬럼 정의: 0(코드), 1(항구명), 26(연간합계건수), 27(연간합계금액)
            # 파일 구조에 따라 마지막 두 컬럼이 합계이므로 iloc 사용
            df_subset = df.iloc[:, [0, 1, -2, -1]]
            df_subset.columns = ['항구코드', '항구명', '연간건수', '연간금액']
            df_subset['연도'] = year
            
            # 데이터 정제: 쉼표 제거 및 숫자 변환
            for col in ['연간건수', '연간금액']:
                df_subset[col] = pd.to_numeric(df_subset[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 유효한 항구 데이터만 남김
            df_subset = df_subset.dropna(subset=['항구명'])
            df_subset = df_subset[~df_subset['항구명'].str.contains('합계|항구명', na=False)]
            
            combined_list.append(df_subset)
        except Exception as e:
            continue
            
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# 데이터 불러오기
df = load_and_clean_data()

# --- 사이드바 구성 ---
st.sidebar.title("🚢 선용품 무역 대시보드")
if not df.empty:
    st.sidebar.success(f"데이터 로드 완료: {df['연도'].min()} ~ {df['연도'].max()}")
    
    # 필터 설정
    selected_ports = st.sidebar.multiselect(
        "분석 대상 항구 선택",
        options=sorted(df['항구명'].unique()),
        default=['부산항', '인천항', '울산항', '광양항']
    )
    
    year_range = st.sidebar.slider(
        "분석 기간 선택",
        int(df['연도'].min()), int(df['연도'].max()),
        (int(df['연도'].min()), int(df['연도'].max()))
    )

    # 필터 적용
    mask = (df['항구명'].isin(selected_ports)) & (df['연도'].astype(int).between(year_range[0], year_range[1]))
    filtered_df = df[mask].sort_values(['연도', '연간금액'], ascending=[True, False])
else:
    st.sidebar.error("CSV 파일을 찾을 수 없습니다.")
    st.stop()

# --- 메인 대시보드 화면 ---
# 1. KPI 지표 섹션
st.header("📌 주요 무역 지표 (Selected Range)")
kpi1, kpi2, kpi3 = st.columns(3)

total_val = filtered_df['연간금액'].sum()
total_qty = filtered_df['연간건수'].sum()
avg_val = total_val / total_qty if total_qty > 0 else 0

with kpi1:
    st.metric("누적 거래 금액", f"${total_val:,.0f}")
with kpi2:
    st.metric("누적 거래 건수", f"{total_qty:,.0f} 건")
with kpi3:
    st.metric("건당 평균 거래액", f"${avg_val:,.2f}")

st.divider()

# 2. 시각화 섹션
tab1, tab2 = st.tabs(["📊 연도별 추이 분석", "🗺️ 항구별 비교"])

with tab1:
    st.subheader("연도별 선용품 무역 거래액 변화")
    # 라인 차트
    fig_line = px.line(
        filtered_df, x='연도', y='연간금액', color='항구명',
        markers=True, text=None,
        labels={'연간금액': '거래 금액 (USD)', '연도': '연도'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_line.update_layout(hovermode="x unified")
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    col_a, col_b = st.columns(2)
    latest_year = filtered_df['연도'].max()
    latest_df = filtered_df[filtered_df['연도'] == latest_year]
    
    with col_a:
        st.subheader(f"{latest_year}년 항구별 거래액 비중")
        fig_pie = px.pie(latest_df, values='연간금액', names='항구명', hole=0.4)
        st.plotly_chart(fig_pie)
        
    with col_b:
        st.subheader(f"{latest_year}년 항구별 건수 순위")
        fig_bar = px.bar(latest_df.sort_values('연간건수'), x='연간건수', y='항구명', orientation='h',
                         color='연간건수', color_continuous_scale='Blues')
        st.plotly_chart(fig_bar)

# 3. 데이터 상세 내역 및 다운로드
st.divider()
st.subheader("📋 상세 데이터 (정제됨)")
st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

# 엑셀 다운로드 기능 대용으로 CSV 변환 버튼
csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 정제된 데이터 CSV 다운로드",
    data=csv,
    file_name='cleansed_trade_data.csv',
    mime='text/csv',
)

# 4. 국가 기준정보 (Master Data) 사이드 팝업 기능
with st.expander("🌐 무역구제 국가 기준정보 참조"):
    country_file = '산업통상부_무역구제 국가 기준정보_20251211.csv'
    if os.path.exists(country_file):
        country_df = pd.read_csv(country_file)
        st.dataframe(country_df, use_container_width=True)
    else:
        st.info("국가 기준정보 파일을 찾을 수 없습니다.")