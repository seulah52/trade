import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="관세청 선용품 통계", layout="wide")
st.title("🚢 전국 항구별 선용품 무역통계 (Excel 버전)")

@st.cache_data
def load_excel_data():
    # 폴더 내의 모든 엑셀 파일(.xlsx) 찾기
    files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    
    if not files:
        return pd.DataFrame()

    all_data = []
    for f in files:
        try:
            # 파일명에서 연도 추출 (예: 20251231 -> 2025)
            import re
            year_match = re.search(r'\d{4}', f)
            year = year_match.group() if year_match else "Unknown"
            
            # 엑셀 읽기 (엔진 지정 및 헤더 3줄 스킵)
            # 엑셀은 시트가 여러 개일 수 있으므로 sheet_name=0(첫 번째 시트)을 기본으로 합니다.
            df_raw = pd.read_excel(f, engine='openpyxl', skiprows=3, header=None)
            
            # 필요한 열 선택 (0: 코드, 1: 항구명, -2: 연간건수, -1: 연간금액)
            df_cleaned = df_raw.iloc[:, [0, 1, -2, -1]]
            df_cleaned.columns = ['항구코드', '항구명', '건수', '금액']
            df_cleaned['연도'] = year
            
            # '합계' 행 제거 및 데이터 정제
            df_cleaned = df_cleaned.dropna(subset=['항구명'])
            df_cleaned = df_cleaned[~df_cleaned['항구명'].str.contains('합계|항구명', na=False)]
            
            # 금액 데이터 숫자형 변환
            df_cleaned['금액'] = pd.to_numeric(df_cleaned['금액'], errors='coerce').fillna(0)
            df_cleaned['건수'] = pd.to_numeric(df_cleaned['건수'], errors='coerce').fillna(0)
            
            all_data.append(df_cleaned)
        except Exception as e:
            st.error(f"파일 {f} 처리 중 오류: {e}")
            
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 데이터 로드
df = load_excel_data()

if df.empty:
    st.warning("⚠️ 분석할 엑셀 파일(.xlsx)을 찾을 수 없습니다.")
    st.info("VS Code 폴더에 엑셀 파일을 넣고 GitHub Desktop에서 Push 하셨나요?")
else:
    st.success(f"✅ {df['연도'].nunique()}개 연도 데이터 로드 완료!")
    
    # --- 시각화 ---
    ports = sorted(df['항구명'].unique())
    selected = st.sidebar.multiselect("항구 선택", options=ports, default=ports[:3])
    
    filtered = df[df['항구명'].isin(selected)].sort_values('연도')
    
    fig = px.bar(filtered, x='연도', y='금액', color='항구명', barmode='group',
                 title="항구별 선용품 무역 규모 추이", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(filtered, use_container_width=True)