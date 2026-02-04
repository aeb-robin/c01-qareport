import streamlit as st
import os
import logging
from sqlalchemy import create_engine

st.title("Streamlit + MySQL 測試")

# --------------------------
# 套件檢查
# --------------------------
try:
    import pymysql
    import sqlalchemy
    import pandas
    import plotly
    import streamlit_option_menu
    import dotenv
    st.success("✅ 所有套件都有安裝！")
except ImportError as e:
    st.error(f"❌ 套件缺失: {e}")

# --------------------------
# 安全 logging 設定
# --------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# 只設定 console logging，不影響 app
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
logger.info("Logging 初始化完成")

# --------------------------
# MySQL 連線測試
# --------------------------
try:
    # 從 Streamlit Secrets 讀取
    DB_HOST = st.secrets["DB_HOST"]
    DB_PORT = st.secrets["DB_PORT"]
    DB_USER = st.secrets["DB_USER"]
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    DB_NAME = st.secrets["DB_NAME"]

    DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DB_URL, pool_pre_ping=True)

    # 嘗試簡單查詢
    with engine.connect() as conn:
        result = conn.execute("SELECT NOW();")
        now = result.fetchone()[0]
        st.success(f"MySQL 連線成功！現在時間: {now}")

except Exception as e:
    st.error(f"MySQL 連線失敗: {e}")
