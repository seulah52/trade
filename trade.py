import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="무역구제 국가 기준정보", layout="wide")

st.title("🌐 무역구제 국가 기준정보 대시보드")
st.markdown("산업통상자원부 무역구제 데이터를 기반으로 국가 정보를 관리하고 분석합니다.")

# --- 데이터 로드 함수 (오류 방지 로직 포함) ---
@st.cache_data
def load_data():
    # 폴더 내에서 '무역구제'라는 키워드가 포함된 CSV 파일 찾기
    files = [f for f in os.listdir('.') if '무역구제' in f and f.endswith('.csv')]
    
    if not files:
        return None

    target_file = files[0] # 첫 번째 매칭되는 파일 선택
    
    try:
        # 공공데이터용 인코딩(CP949) 우선 시도
        df = pd.read_csv(target_file, encoding='cp949')
    except:
        # 실패 시 UTF-8 시도
        df = pd.read_csv(target_file, encoding='utf-8-sig')
    
    # 상위 국가분류를 통한 대륙명 매핑
    continent_map = df[df['대륙구분여부'] == 'Y'][['국가아이디', '국가명']]
    mapping_dict = dict(zip(continent_map['국가아이디'], continent_map['국가명']))
    
    # 국가 데이터에 대륙 정보 추가
    df['대륙분류'] = df['상위국가분류아이디'].map(mapping_dict)
    # 대륙 데이터 자체는 '대륙'으로 표시
    df.loc[df['대륙구분여부'] == 'Y', '대륙분류'] = '대륙분류군'
    
    return df

df = load_data()

# --- 데이터가 없을 때의 예외 처리 ---
if df is None:
    st.error("❌ CSV 파일을 찾을 수 없습니다.")
    st.info("GitHub에 '산업통상부_무역구제 국가 기준정보_20251211.csv' 파일이 정확히 Push 되었는지 확인해주세요.")
    st.stop()

# --- 메인 대시보드 ---
st.success(f"✅ 데이터를 성공적으로 불러왔습니다. (총 {len(df)}건)")

# 상단 KPI 지표
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("총 등록 항목", f"{len(df)}건")
with m2:
    actual_countries = len(df[df['대륙구분여부'] == 'N'])
    st.metric("실제 국가 수", f"{actual_countries}개")
with m3:
    st.metric("사용 중인 데이터", f"{len(df[df['사용여부'] == 'Y'])}건")

st.divider()

# 시각화 섹션
col1, col2 = st.columns([6, 4])

with col1:
    st.subheader("📊 대륙별 국가 분포")
    # 대륙별 국가 개수 통계
    stats = df[df['대륙구분여부'] == 'N']['대륙분류'].value_counts().reset_index()
    stats.columns = ['대륙', '국가수']
    
    fig = px.bar(stats, x='대륙', y='국가수', color='대륙', 
                 text_auto=True, color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🔍 국가 검색 및 정보")
    search = st.text_input("찾으시는 국가명(한글/영문) 또는 코드를 입력하세요")
    
    if search:
        result = df[
            df['국가명'].str.contains(search, na=False) | 
            df['국가영문명'].str.contains(search, case=False, na=False) |
            df['국가코드'].str.contains(search, case=False, na=False)
        ]
        st.dataframe(result[['국가코드', '국가명', '국가영문명', '대륙분류']], hide_index=True)

st.divider()

# 전체 데이터 테이블
st.subheader("📋 전체 기준정보 리스트")
st.dataframe(df[['국가코드', '국가명', '국가영문명', '대륙분류', '사용여부']], use_container_width=True)

# 다운로드 버튼
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 정제된 데이터 다운로드 (CSV)", csv, "cleaned_trade_data.csv", "text/csv")