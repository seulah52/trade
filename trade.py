import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="관세청 선용품 무역통계", layout="wide")

st.title("🚢 전국 항구별 선용품 무역통계 분석")
st.markdown("관세청 '환급대상 선용품' 데이터를 기반으로 한 연도별 통계입니다.")

@st.cache_data
def load_combined_data():
    # '환급대상물품'이 포함된 CSV 파일만 필터링
    files = [f for f in os.listdir('.') if f.endswith('.csv') and '환급대상물품' in f]
    
    if not files:
        return pd.DataFrame()

    all_data = []
    for f in files:
        try:
            # 파일명에서 연도 4자리 숫자 추출
            import re
            year_match = re.search(r'\d{4}', f)
            year = year_match.group() if year_match else "Unknown"
            
            # 데이터 로드: 3번째 줄(index 2)부터가 실제 데이터 헤더 시작
            # 하지만 컬럼명이 중복되므로 직접 지정하는 것이 안전함
            df_raw = pd.read_csv(f, skiprows=3, header=None)
            
            # 우리가 필요한 것: 0번(코드), 1번(항구명), 뒤에서 2번째(연간건수), 마지막(연간금액)
            df_cleaned = df_raw.iloc[:, [0, 1, -2, -1]]
            df_cleaned.columns = ['항구코드', '항구명', '건수', '금액', '연도'] # 연도 컬럼 추가를 위해 공간 확보
            df_cleaned['연도'] = year
            
            # 숫자 데이터 정제 (쉼표 제거 및 숫자 변환)
            for col in ['건수', '금액']:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col].astype(str).str.replace(',', ''), errors='coerce')
            
            # 항구명이 비어있거나 '합계'인 행 제외
            df_cleaned = df_cleaned.dropna(subset=['항구명'])
            df_cleaned = df_cleaned[~df_cleaned['항구명'].str.contains('합계|항구명', na=False)]
            
            all_data.append(df_cleaned)
        except Exception as e:
            st.error(f"파일 읽기 오류 ({f}): {e}")
            continue
            
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# 데이터 로드 실행
df = load_combined_data()

if df.empty:
    st.warning("⚠️ CSV 데이터를 찾을 수 없습니다.")
    st.info("""
    **해결 방법:**
    1. VS Code 폴더 안에 CSV 파일들이 있는지 확인하세요.
    2. GitHub Desktop에서 왼쪽 목록에 CSV 파일들이 보인다면 **Commit** 버튼을 누르세요.
    3. 상단의 **Push origin** 버튼을 눌러 GitHub 서버로 업로드하세요.
    """)
else:
    # --- 시각화 섹션 ---
    # 사이드바 항구 선택
    all_ports = sorted(df['항구명'].unique())
    selected_ports = st.sidebar.multiselect("분석할 항구를 선택하세요", options=all_ports, default=all_ports[:5])
    
    if not selected_ports:
        st.info("왼쪽 사이드바에서 항구를 선택해 주세요.")
    else:
        filtered_df = df[df['항구명'].isin(selected_ports)].sort_values(['연도', '금액'], ascending=[True, False])

        # KPI 메트릭
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("총 분석 연도", f"{df['연도'].nunique()}개년")
        with m2:
            total_val = filtered_df['금액'].sum()
            st.metric("선택 항구 총 거래액", f"${total_val:,.0f}")
        with m3:
            total_qty = filtered_df['건수'].sum()
            st.metric("선택 항구 총 건수", f"{total_qty:,.0f}건")

        st.divider()

        # 메인 차트 1: 연도별 추이
        st.subheader("📊 항구별 거래 금액 추이")
        fig_line = px.line(filtered_df, x='연도', y='금액', color='항구명', markers=True,
                           template='plotly_white', height=500)
        st.plotly_chart(fig_line, use_container_width=True)

        # 메인 차트 2: 최신 연도 비중
        c1, c2 = st.columns(2)
        latest_year = df['연도'].max()
        with c1:
            st.subheader(f"📅 {latest_year}년 항구별 비중")
            pie_data = df[df['연도'] == latest_year].nlargest(10, '금액')
            fig_pie = px.pie(pie_data, values='금액', names='항구명', hole=0.3)
            st.plotly_chart(fig_pie)
        
        with c2:
            st.subheader("📑 데이터 상세 보기")
            st.dataframe(filtered_df[['연도', '항구명', '건수', '금액']], use_container_width=True, hide_index=True)