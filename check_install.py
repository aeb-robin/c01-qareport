import streamlit as st

st.title("套件安裝測試")

try:
    import pymysql
    import sqlalchemy
    import pandas
    import plotly
    import streamlit_option_menu
    import dotenv

    st.success("所有套件都有安裝！")
    st.write("PyMySQL 版本:", pymysql.__version__)
except ImportError as e:
    st.error(f"有套件沒安裝: {e}")
