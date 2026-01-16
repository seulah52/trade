import streamlit as st
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="무역구제 국가 기준정보 시스템", layout="wide")

# --- 데이터 로드 및 전처리 ---
@st.cache_data
def load_data():
    file_path = '산업통상부_무역구제 국가 기준정보_20251211.csv'
    try:
        # 한글 인코딩 대응 (cp949 또는 utf-8-sig)
        df = pd.read_csv(file_path, encoding='cp949')
    except:
        df = pd.read_csv(file_path, encoding='utf-8')

    # 1. 대륙 정보 추출 (대륙구분여부가 'Y'인 데이터)
    continents = df[df['대륙구분여부'] == 'Y'][['국가아이디', '국가명']]
    continent_map = dict(zip(continents['국가아이디'], continents['국가명']))

    # 2. 국가 데이터에 대륙명 매핑
    df['대륙명'] = df['상위국가분류아이디'].map(continent_map)
    
    # 대륙 데이터 자체는 대륙명이 본인 이름이 되도록 수정
    df.loc[df['대륙구분여부'] == 'Y', '대륙명'] = '대륙분류'
    
    return df

df = load_data()

# --- 사이드바: 필터 및 검색 ---
st.sidebar.title("🔍 검색 및 필터")
search_term = st.sidebar.text_input("국가명 또는 코드 검색", help="예: 한국, KOR, Asia")

# 대륙 선택 필터
all_continents = ['전체'] + sorted([str(x) for x in df['대륙명'].unique() if x != '대륙분류'])
selected_continent = st.sidebar.selectbox("대륙별 보기", all_continents)

# 사용여부 필터
usage_filter = st.sidebar.radio("사용 여부", ['전체', 'Y', 'N'], horizontal=True)

# 데이터 필터링 로직
filtered_df = df.copy()

if search_term:
    filtered_df = filtered_df[
        filtered_df['국가명'].str.contains(search_term, case=False, na=False) |
        filtered_df['국가영문명'].str.contains(search_term, case=False, na=False) |
        filtered_df['국가코드'].str.contains(search_term, case=False, na=False)
    ]

if selected_continent != '전체':
    filtered_df = filtered_df[filtered_df['대륙명'] == selected_continent]

if usage_filter != '전체':
    filtered_df = filtered_df[filtered_df['사용여부'] == usage_filter]

# --- 메인 화면 ---
st.title("🌐 무역구제 국가 기준정보 관리 시스템")
st.markdown("산업통상자원부 데이터를 기반으로 한 국가별 마스터 데이터 조회 대시보드입니다.")

# 상단 KPI 지표
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("총 등록 항목", f"{len(df)}건")
with col2:
    st.metric("실제 국가 수", f"{len(df[df['대륙구분여부'] == 'N'])}개")
with col3:
    st.metric("대륙 분류", f"{len(df[df['대륙구분여부'] == 'Y'])}개")
with col4:
    st.metric("현재 필터링 결과", f"{len(filtered_df)}건")

st.divider()

# 시각화 섹션
c1, c2 = st.columns([6, 4])

with c1:
    st.subheader("📊 대륙별 국가 분포")
    # 대륙별 국가 수 계산 (대륙분류 제외)
    geo_stats = df[df['대륙구분여부'] == 'N'].groupby('대륙명').size().reset_index(name='국가수')
    fig = px.bar(geo_stats, x='대륙명', y='국가수', color='대륙명', 
                 text_auto=True, title="대륙별 등록 국가 통계")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("⚙️ 데이터 관리 현황")
    usage_stats = df['사용여부'].value_counts().reset_index()
    fig_pie = px.pie(usage_stats, values='count', names='사용여부', hole=0.4, title="데이터 사용 여부 비중")
    st.plotly_chart(fig_pie, use_container_width=True)

# 상세 데이터 테이블
st.subheader("📋 국가 기준정보 리스트")
display_cols = ['국가코드', '국가명', '국가영문명', '대륙명', '사용여부']
st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)

# 데이터 다운로드 섹션
st.divider()
csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 필터링된 데이터 CSV로 내보내기",
    data=csv,
    file_name='trade_country_reference.csv',
    mime='text/csv',
)