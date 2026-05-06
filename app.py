import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

st.set_page_config(
    page_title="서울시 따릉이 데이터 분석 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("서울시 따릉이 이용 현황 분석 대시보드")
st.markdown("""
이 대시보드는 따릉이 공공데이터를 활용하여 **자치구별 의존도, 이용자 특성, 대여권별 패턴**을 분석합니다.
""")

db_path = "bicycle.db"

if not os.path.exists(db_path):
    st.error("'bicycle.db' 파일이 폴더 안에 없습니다.")
    st.stop()

def load_table(table_name):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
    conn.close()

    # 컬럼명 앞뒤 공백 제거 + 중복 컬럼 제거
    df.columns = df.columns.astype(str).str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def normalize_id(x):
    if pd.isna(x):
        return None
    x = str(x).strip()
    if x.endswith(".0"):
        x = x[:-2]
    return x.lstrip("0") or "0"

# 데이터 불러오기
df_station = load_table("대여소")
df_use = load_table("이용정보")

# 대여소 컬럼명 안전 정리
if "대여소번호" not in df_station.columns:
    df_station = df_station.rename(columns={df_station.columns[0]: "대여소번호"})

if "자치구" not in df_station.columns:
    df_station = df_station.rename(columns={df_station.columns[2]: "자치구"})

# 이용정보 컬럼명 안전 정리
if "대여소번호" not in df_use.columns:
    df_use = df_use.rename(columns={df_use.columns[2]: "대여소번호"})

# 숫자형 변환
for col in ["이용건수", "이용시간", "이동거리"]:
    df_use[col] = pd.to_numeric(df_use[col], errors="coerce").fillna(0)

# 대여소번호 형식 통일
df_station["대여소번호"] = df_station["대여소번호"].apply(normalize_id)
df_use["대여소번호"] = df_use["대여소번호"].apply(normalize_id)

# 대여소번호 중복 제거 후 자치구 붙이기
df_station_clean = df_station[["대여소번호", "자치구"]].dropna()
df_station_clean = df_station_clean.drop_duplicates(subset=["대여소번호"])

station_map = dict(zip(df_station_clean["대여소번호"], df_station_clean["자치구"]))
df_use["자치구"] = df_use["대여소번호"].map(station_map)

# ---------------------------------------------------------
# 1. 자치구별 생활형 따릉이 의존도 분석
# ---------------------------------------------------------
st.divider()
st.header("1. 자치구별 생활형 따릉이 의존도 분석")

df_district = df_use.dropna(subset=["자치구"]).groupby("자치구").agg(
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

query_1 = """
SELECT
    D.자치구,
    SUM(I.이용건수) AS 총이용건수,
    ROUND(SUM(I.이용시간) * 1.0 / SUM(I.이용건수), 2) AS 건당평균이용시간,
    ROUND(SUM(I.이동거리) * 1.0 / SUM(I.이용건수), 2) AS 건당평균이동거리
FROM 이용정보 I
JOIN 대여소 D
ON I.대여소번호 = D.대여소번호
GROUP BY D.자치구
ORDER BY 총이용건수 DESC;
"""

col1, col2 = st.columns([2, 1])

with col1:
    fig1 = px.bar(
        df_district,
        x="총이용건수",
        y="자치구",
        orientation="h",
        title="자치구별 총 이용건수",
        color="총이용건수",
        color_continuous_scale="Blues"
    )
    fig1.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("사용된 SQL")
    st.code(query_1, language="sql")

    st.subheader("분석 인사이트")
    st.info("""
    - 이용건수가 높은 자치구는 따릉이가 생활 이동수단으로 활발히 활용되는 지역입니다.
    - 평균 이동거리와 평균 이용시간을 함께 보면 단순 이용량뿐 아니라 이동 목적의 차이도 파악할 수 있습니다.
    """)

# ---------------------------------------------------------
# 2. 성별/연령대별 따릉이 핵심 이용층 분석
# ---------------------------------------------------------
st.divider()
st.header("2. 성별/연령대별 따릉이 핵심 이용층 분석")

df_user = df_use.copy()
df_user["성별"] = df_user["성별"].fillna("").astype(str).str.strip()
df_user["연령대코드"] = df_user["연령대코드"].fillna("미상").astype(str).str.strip()

df_user = df_user[df_user["성별"] != ""]

df_user_grouped = df_user.groupby(["성별", "연령대코드"]).agg(
    총이용건수=("이용건수", "sum")
).reset_index()

df_user_grouped = df_user_grouped.sort_values("연령대코드")

query_2 = """
SELECT
    성별,
    연령대코드,
    SUM(이용건수) AS 총이용건수
FROM 이용정보
WHERE 성별 IS NOT NULL AND 성별 != ''
GROUP BY 성별, 연령대코드
ORDER BY 연령대코드;
"""

col3, col4 = st.columns([2, 1])

with col3:
    fig2 = px.bar(
        df_user_grouped,
        x="연령대코드",
        y="총이용건수",
        color="성별",
        barmode="group",
        title="성별 및 연령대별 이용 패턴"
    )
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    st.subheader("사용된 SQL")
    st.code(query_2, language="sql")

    st.subheader("분석 인사이트")
    st.info("""
    - 성별과 연령대별 이용량을 비교하면 따릉이의 핵심 이용자층을 확인할 수 있습니다.
    - 이용이 집중된 연령대는 향후 안전 캠페인, 요금제 설계, 서비스 개선의 주요 대상이 될 수 있습니다.
    """)

# ---------------------------------------------------------
# 3. 대여권 유형별 이용 목적 차이 분석
# ---------------------------------------------------------
st.divider()
st.header("3. 대여권 유형별 이용 목적 차이 분석")

df_ticket = df_use.copy()
df_ticket["대여구분코드"] = df_ticket["대여구분코드"].fillna("미상").astype(str).str.strip()

df_ticket_grouped = df_ticket.groupby("대여구분코드").agg(
    총이용건수=("이용건수", "sum"),
    평균이용시간=("이용시간", "mean"),
    평균이동거리=("이동거리", "mean")
).reset_index()

df_ticket_grouped["평균이용시간"] = df_ticket_grouped["평균이용시간"].round(1)
df_ticket_grouped["평균이동거리"] = df_ticket_grouped["평균이동거리"].round(1)

query_3 = """
SELECT
    대여구분코드,
    SUM(이용건수) AS 총이용건수,
    ROUND(AVG(이용시간), 1) AS 평균이용시간,
    ROUND(AVG(이동거리), 1) AS 평균이동거리
FROM 이용정보
GROUP BY 대여구분코드;
"""

col5, col6 = st.columns([2, 1])

with col5:
    fig3 = px.bar(
        df_ticket_grouped,
        x="대여구분코드",
        y=["평균이용시간", "평균이동거리"],
        barmode="group",
        title="대여권 유형별 이용 패턴 비교"
    )
    st.plotly_chart(fig3, use_container_width=True)

with col6:
    st.subheader("사용된 SQL")
    st.code(query_3, language="sql")

    st.subheader("분석 인사이트")
    st.info("""
    - 정기권은 반복적이고 생활형 이동 목적에 가까운 이용 패턴을 보일 수 있습니다.
    - 일일권은 상대적으로 관광, 여가, 비정기적 이동 목적과 연결될 가능성이 있습니다.
    """)

st.caption("Data Source: 서울특별시 공공자전거 이용정보 DB")
