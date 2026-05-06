import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# --- [설정] 페이지 레이아웃 및 제목 설정 ---
st.set_page_config(
    page_title="서울시 따릉이 데이터 분석 대시보드",
    layout="wide", # 화면을 넓게 사용하도록 설정
    initial_sidebar_state="expanded"
)

st.title("🚲 서울시 따릉이 이용 현황 분석 대시보드")
st.markdown("""
이 대시보드는 따릉이 공공데이터를 활용하여 **자치구별 의존도, 이용자 특성, 대여권별 패턴**을 분석합니다.
데이터를 통해 따릉이가 서울 시민의 삶에 어떻게 녹아있는지 확인해보세요!
""")

# --- [DB 연결] 데이터베이스 파일 존재 여부 확인 ---
db_path = 'bicycle.db'

if not os.path.exists(db_path):
    st.error(f"⚠️ '{db_path}' 파일이 폴더 내에 존재하지 않습니다. 데이터베이스 파일을 확인해주세요.")
    st.stop() # 파일이 없으면 여기서 실행 중단

# SQL 쿼리를 실행하고 결과를 데이터프레임으로 가져오는 함수
def run_query(query):
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error("SQL 실행 중 오류가 발생했습니다.")
        st.code(query, language="sql")
        st.exception(e)
        st.stop()

# ---------------------------------------------------------
# 1. 자치구별 생활형 따릉이 의존도 분석
# ---------------------------------------------------------
st.divider()
st.header("1. 자치구별 생활형 따릉이 의존도 분석")

# [SQL] 이용정보와 대여소 테이블을 조인하여 자치구별 통계 산출
query_1 = """
SELECT *
FROM 대여소;
"""

query_use = """
SELECT *
FROM 이용정보;
"""

df_station = run_query(query_1)
df_use = run_query(query_use)

# 대여소 테이블 컬럼명 강제 정리
df_station = df_station.rename(columns={
    df_station.columns[0]: "대여소번호",
    df_station.columns[2]: "자치구"
})

# 이용정보 테이블 컬럼명 강제 정리
df_use = df_use.rename(columns={
    df_use.columns[2]: "대여소번호"
})
df_station = df_station.drop_duplicates(subset=["대여소번호"])
df_use = df_use.drop_duplicates(subset=["대여소번호"])
df_station = df_station.drop_duplicates(subset=["대여소번호"])
df_district = df_use.merge(
    df_station[["대여소번호", "자치구"]],
    on="대여소번호",
    how="inner"
)

df_district = df_district.groupby("자치구").agg(
    총이용건수=("이용건수", "sum"),
    총이용시간=("이용시간", "sum"),
    총이동거리=("이동거리", "sum")
).reset_index()

df_district["건당평균이용시간"] = (
    df_district["총이용시간"] / df_district["총이용건수"]
).round(2)

df_district["건당평균이동거리"] = (
    df_district["총이동거리"] / df_district["총이용건수"]
).round(2)

df_district = df_district.sort_values("총이용건수", ascending=False)

# 컬럼을 나누어 시각화와 SQL/인사이트 배치
col1, col2 = st.columns([2, 1])

with col1:
    # 이용건수 기준 가로 막대 차트
    fig1 = px.bar(
        df_district, 
        x='총이용건수', 
        y='자치구', 
        orientation='h',
        title="자치구별 총 이용건수 (내림차순)",
        color='총이용건수',
        color_continuous_scale='Blues'
    )
    fig1.update_layout(yaxis={'categoryorder':'total ascending'}) # 보기 좋게 정렬
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🔍 사용된 SQL")
    st.code(query_1, language='sql')
    
    st.subheader("💡 분석 인사이트")
    st.info("""
    - 이용건수가 상위권인 자치구는 주로 업무 지구나 주거 밀집 지역일 가능성이 높습니다.
    - 평균 이동거리가 짧으면서 이용건수가 많은 구는 따릉이를 '라스트 마일(지하철역-집)' 이동 수단으로 활발히 활용하고 있음을 보여줍니다.
    """)


# ---------------------------------------------------------
# 2. 성별/연령대별 따릉이 핵심 이용층 분석
# ---------------------------------------------------------
st.divider()
st.header("2. 성별/연령대별 따릉이 핵심 이용층 분석")

# [SQL] 성별과 연령대별로 그룹화하여 이용건수 합산
query_2 = """
SELECT 
    성별, 
    연령대코드, 
    SUM(이용건수) AS 총이용건수
FROM 이용정보
WHERE 성별 IS NOT NULL AND 성별 != ''
GROUP BY 성별, 연령대코드
ORDER BY 연령대코드
"""

df_user = run_query(query_2)

col3, col4 = st.columns([2, 1])

with col3:
    # 성별과 연령대를 조합한 그룹 막대 차트
    fig2 = px.bar(
        df_user,
        x='연령대코드',
        y='총이용건수',
        color='성별',
        barmode='group',
        title="성별 및 연령대별 이용 패턴",
        labels={'연령대코드': '연령대', '총이용건수': '이용건수'}
    )
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    st.subheader("🔍 사용된 SQL")
    st.code(query_2, language='sql')
    
    st.subheader("💡 분석 인사이트")
    st.info("""
    - 특정 성별이나 연령대(예: 2030세대)에 이용이 집중되어 있는지 확인할 수 있습니다.
    - 성별에 따른 이용건수 차이를 통해 타겟 마케팅이나 안전 교육 대상 설정의 근거로 활용할 수 있습니다.
    """)


# ---------------------------------------------------------
# 3. 대여권 유형별 이용 목적 차이 분석
# ---------------------------------------------------------
st.divider()
st.header("3. 대여권 유형별 이용 목적 차이 분석")

# [SQL] 대여구분코드(일일권, 정기권 등)에 따른 이용량 및 평균 수치 계산
query_3 = """
SELECT 
    대여구분코드,
    SUM(이용건수) AS 총이용건수,
    ROUND(AVG(이용시간), 1) AS 평균이용시간,
    ROUND(AVG(이동거리), 1) AS 평균이동거리
FROM 이용정보
GROUP BY 대여구분코드
"""

df_ticket = run_query(query_3)

col5, col6 = st.columns([2, 1])

with col5:
    # 대여구분코드별 평균 이용시간과 이동거리 시각화
    # 사용자가 보기 편하도록 멀티 셀렉트 기능을 넣을 수도 있지만, 여기선 바로 시각화합니다.
    fig3 = px.bar(
        df_ticket,
        x='대여구분코드',
        y=['평균이용시간', '평균이동거리'],
        barmode='group',
        title="대여권 유형별 이용 패턴 비교 (시간 vs 거리)"
    )
    st.plotly_chart(fig3, use_container_width=True)

with col6:
    st.subheader("🔍 사용된 SQL")
    st.code(query_3, language='sql')
    
    st.subheader("💡 분석 인사이트")
    st.info("""
    - **정기권** 이용자는 이용건수는 많으나 평균 이용시간이 짧은 '출퇴근용' 패턴을 보일 확률이 높습니다.
    - 반면, **일일권/단체권** 이용자는 이용건수는 적어도 평균 이용시간과 거리가 긴 '레저/관광용' 패턴을 보입니다.
    """)

st.caption("Data Source: 서울특별시 공공자전거 이용정보 DB")
