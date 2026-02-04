from sqlalchemy import create_engine, text
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
import os, time, platform
import logging
import upload
import select_sql
from SQLAlchemyLogHandler import SQLAlchemyLogHandler

os.environ["TZ"] = "Asia/Taipei"
if platform.system() != "Windows":
    time.tzset()

load_dotenv()

DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"




# 建立Logger
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)

# 建立Handler
if not logger.handlers:
    try:
        sqlalchemy_handler = SQLAlchemyLogHandler(DATABASE_URL)
    except Exception as e:
        print(f"無法建立資料庫日誌處理器: {e}")
        st.error("無法建立資料庫日誌處理器，請檢查資料庫連線設定", icon="⚠️")
        st.stop()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    sqlalchemy_handler.setFormatter(formatter)
    logger.addHandler(sqlalchemy_handler) # 加到 logger 上


def chart_as_datatype_container(df,cat,color):

    with st.container(border=1 ,height=400):
        title = f'<span style="color:{color};">{cat}</span> 統計圖表'
        
        fig = go.Figure()

        totals = []
        for date in df['回報日期'].unique():
            total = df[df['回報日期'] == date][cat].sum()
            totals.append(total)
                                        
        # 只顯示月日
        x_labels = [pd.to_datetime(date).strftime('%m-%d') for date in df['回報日期'].unique()]

        fig.add_trace(go.Bar(
            x=x_labels, 
            y=totals, 
            name=cat,
            showlegend=False,
            marker_color=color,
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, 
            y=totals, 
            mode="text",
            text=totals,
            textposition="top center",
            showlegend=False,
        ))
        fig.update_xaxes(type="category")
        fig.update_layout(
            title=title,
            yaxis=dict(tickformat='d'),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

def chart_as_employee_container(df, employee):
    df = df[df['員工'] == employee]
    df = df.drop(columns=['員工'])
    # 轉換成長格式
    df_melt = df.melt(id_vars=["回報日期"], var_name="類別", value_name="數量")
    
    with st.container(border=1):
        title = employee + ' 統計圖表'
        fig =px.line(df_melt,x='回報日期',y='數量',color='類別',markers=True)
        fig.update_layout(
            title=title,
            yaxis=dict(tickformat='d'))
        st.plotly_chart(fig, use_container_width=True)

def set_2columns(df,num1,num2):
    col1, col2 = st.columns([1,1])
    with col1:
        chart_as_employee_container(df, employee_list[num1])
    with col2:
        try:
            chart_as_employee_container(df, employee_list[num2])
        except IndexError:
            return

st.set_page_config(page_title="QA Report", layout="wide")


with st.sidebar:
    selected = option_menu("選單", ["QA統計圖表", "歷史統計查詢", "上傳CSV", "資料查詢與匯出"])

#首頁  QA統計圖表
if selected == "QA統計圖表":
    col1, col2 = st.columns([8,1], vertical_alignment='bottom', width='stretch')
    with col1:
        st.markdown('## QA統計圖表')
    with col2:
        with st.popover("ℹ️"):
            st.write("QA回報統計說明：")
            st.write("新問題 ｢統計給\"分配給\"｣：狀態為已分配，回報日期為今天")
            st.write("今日完成 ｢統計給\"回報人\"｣：狀態為已測試，更新日期為今日")
            st.write("今日完成 ｢統計給\"分配給\"｣：狀態為待測試，更新日期為今日")
            st.write("累積未完成 ｢統計給\"分配給\"｣：狀態為已分配")
            st.write("重要未處理 ｢統計給\"分配給\"｣：狀態為已分配，嚴重性為重要")
            st.write("外部未處理 ｢統計給\"分配給\"｣：狀態為已分配，類別為HAPCS疾管署_愛滋追管系統")
            
    st.markdown('''
    <style>.stVerticalBlock{
    overflow: hidden;
    padding-top: 0rem;
    }</style>''', 
    unsafe_allow_html=True) # 調整CSS隱藏scroll bar

    #依類別分類的內容---------------------------------------------
    logger.info(f'[QA統計圖表] 開始查詢 QA統計圖表')
    start_time = datetime.now()
    df_30 = select_sql.search_last30days_result(logger)
    employee_list = select_sql.search_employee_list(logger)
    category_df = pd.DataFrame(columns=['category','color'])
    category_df['category'] = ['每日完成', '累積未完成', '新問題', '重要未處理', '外部未處理']
    category_df['color'] = ['#83c9ff','#ffabab','#ff2b2b','#7defa1','#0066cc']
    if df_30 is None:
        st.error("查無資料，請確認是否已上傳資料",icon="⚠️")
        logger.error(f"[QA統計圖表]查無資料，請確認是否已上傳資料")
        st.stop()
    col1, col2 = st.columns([1,1])
    try:
        with col1:
            chart_as_datatype_container(df_30,category_df['category'][0],category_df['color'][0])
        with col2:
            chart_as_datatype_container(df_30,category_df['category'][1],category_df['color'][1])

    except IndexError:
        pass
    col1, col2, col3 = st.columns([1,1,1])
    try:
        with col1:
            chart_as_datatype_container(df_30,category_df['category'][2],category_df['color'][2])
        with col2:
            chart_as_datatype_container(df_30,category_df['category'][3],category_df['color'][3])
        with col3:
            chart_as_datatype_container(df_30,category_df['category'][4],category_df['color'][4])
    except IndexError:
        pass
    

    # 依員工分類的內容---------------------------------------------
    for i in range(0,len(employee_list),2):
        set_2columns(df_30,i,i+1)
    
    end_time = datetime.now()
    logger.info(f"[QA統計圖表] 成功查詢 耗時 {end_time - start_time}")


#歷史統計查詢
def history_statistics_tab1():
    with tab1:
        with st.container(border=1):
            col1, col2 = st.columns(spec=[0.7, 0.3], vertical_alignment='bottom')
            with col1:
                daily_date = st.date_input("請選擇日期",datetime.now(), key='daily_date')
            with col2:
                query = st.button("查詢",width='stretch',key='history_search_query')

            if query:
                logger.info(f'[歷史統計查詢-單日統計] 開始查詢 {daily_date} 的統計結果')
                start_time = datetime.now()
                daily_results = select_sql.search_daily_results(daily_date,logger)
                if daily_results is None:
                    st.error("查無資料，請確認日期是否正確或是否已上傳當日資料",icon="⚠️")
                    logger.error(f"[歷史統計查詢-單日統計] 查無資料，請確認日期是否正確或是否已上傳當日資料: {daily_date}")
                    return
                
                under_test = daily_results[daily_results['員工'] == '待測試']['待測試'].values[0]
                daily_results = daily_results[daily_results['員工'] != '待測試']
                options = daily_results.columns.tolist()
                if '員工' in options:
                    options.remove('員工')
                if '待測試' in options:
                    options.remove('待測試')
            
                fig = go.Figure()

                for col in options:
                    fig.add_trace(go.Bar(
                        x=daily_results['員工'],
                        y=daily_results[col],
                        name=col
                    ))

                fig.update_layout(
                    barmode='group',  # 群組顯示
                    xaxis_title="員工",
                    yaxis_title="數量",
                    title=f"{daily_date} 統計結果",
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)
                print(daily_results)
                daily_results = daily_results.rename(columns={
                    "員工": str(daily_date)
                })
                daily_results = daily_results.set_index(str(daily_date))[options]
                daily_results.loc['合計'] = daily_results.sum(axis=0)
                daily_results = daily_results.reset_index()

                red_headers = [str(daily_date), "重要未處理"]

                # 產生 header style
                styles = [
                    {"selector": f"th.col{i}", "props": "color: red; font-weight: bold;"}
                    for i, col in enumerate(daily_results.columns)
                    if col in red_headers
                ]

                styled = daily_results.style.set_table_styles(styles)
                styled = styled.hide(axis="index")

                with st.container(border=1,width=700):
                    st.markdown(styled.to_html(), unsafe_allow_html=True)
                    st.markdown(f"待測試: {under_test}")
                end_time = datetime.now()
                logger.info(f"[歷史統計查詢-單日統計] 成功查詢 {daily_date} 的統計結果，耗時 {end_time - start_time}")

def history_statistics_tab2(employee_list):
    with tab2: 
        with st.container(border=1):      
            col1, col2, col3, col4, col5 = st.columns(spec=[5,0.5,5,5,5], vertical_alignment='bottom')
            with col1:
                start_date = st.date_input("開始日期",datetime.now(), key='history_search_start_date')
            with col2:
                st.markdown("<p style='font-size: 24px;'>～</p>", unsafe_allow_html=True)
            with col3:
                end_date = st.date_input("結束日期",datetime.now(), key='history_search_end_date')
            with col4:
                select_employee = st.selectbox('員工',key='history_search_select_employee' ,options=employee_list)
            with col5:
                query_range = st.button("查詢",width='stretch',key='history_search_query_range')
            if query_range and start_date > end_date:
                st.warning("結束日期需大於或等於開始日期",icon="⚠️")
                logger.warning(f"[歷史統計查詢-區間統計] 結束日期需大於或等於開始日期: {start_date} ~ {end_date}")
                return
            elif query_range and end_date - start_date > pd.Timedelta(days=92):
                st.warning("區間不可超過3個月",icon="⚠️")
                logger.warning(f"[歷史統計查詢-區間統計] 區間不可超過3個月: {start_date} ~ {end_date}")
                return
            if query_range:
                logger.info(f'[歷史統計查詢-區間統計] 開始查詢 {start_date} ~ {end_date} 的統計結果')
                start_time = datetime.now()
                range_df = select_sql.search_range_results(start_date,end_date,logger)
                if range_df is None:
                    st.error("查無資料，請確認日期是否正確或是否已上傳當日資料",icon="⚠️")
                    logger.error(f"[歷史統計查詢-區間統計] 查無資料，請確認日期是否正確或是否已上傳當日資料: {start_date} ~ {end_date}")
                    return

                range_df = range_df.drop(columns=['待測試'])
                
                if select_employee:
                    employee = select_employee
                    range_df = range_df[range_df['員工'] == employee]
                    range_df = range_df.drop(columns=['員工']) 
                    df_melt = range_df.melt(id_vars=["回報日期"], var_name="類別", value_name="數量")
                    fig =px.line(df_melt,x='回報日期',y='數量',color='類別',markers=True)
                    fig.update_layout(yaxis=dict(tickformat='d'))
                    st.plotly_chart(fig, use_container_width=True)
                
                end_time = datetime.now()
                logger.info(f"[歷史統計查詢-區間統計] 成功查詢 {start_date} ~ {end_date} 的統計結果，耗時 {end_time - start_time}")

if selected == "歷史統計查詢":
    col1, col2 = st.columns([8,1], vertical_alignment='bottom', width='stretch')
    with col1:
        st.subheader('歷史統計查詢')
    with col2:
        with st.popover("ℹ️"):
            st.write("QA回報統計說明：")
            st.write("新問題 ｢統計給\"分配給\"｣：狀態為已分配，回報日期為今天")
            st.write("今日完成 ｢統計給\"回報人\"｣：狀態為已測試，更新日期為今日")
            st.write("今日完成 ｢統計給\"分配給\"｣：狀態為待測試，更新日期為今日")
            st.write("累積未完成 ｢統計給\"分配給\"｣：狀態為已分配")
            st.write("重要未處理 ｢統計給\"分配給\"｣：狀態為已分配，嚴重性為重要")
            st.write("外部未處理 ｢統計給\"分配給\"｣：狀態為已分配，類別為HAPCS疾管署_愛滋追管系統")
    

    employee_list = select_sql.search_employee_list(logger)
    tab1, tab2 = st.tabs(["單日統計", "區間統計(不可超過3個月)"])

    history_statistics_tab1()
    history_statistics_tab2(employee_list=employee_list)


#上傳CSV
if selected == "上傳CSV":
    st.subheader('上傳CSV')

    with st.container(border=1):
        # 團隊人員多選區塊
        col1, col2, col3, col4 = st.columns([7,2,1,1], vertical_alignment='bottom')
        with col1:
            team_members = select_sql.get_team_members(logger)
            member_selector = st.multiselect("請選擇本次上傳的團隊人員", team_members, default=team_members, key='upload_selector' ,disabled=True)
        with col2:
            member_input = st.text_input("新增/刪除團隊人員", key='upload_member_input')
        with col3:
            add_member_button = st.button("新增", key='upload_add_member_button', use_container_width=True )
        with col4:
            delete_member_button = st.button("刪除", key='upload_delete_member_button', use_container_width=True )
        if add_member_button:
            if member_input.strip() == "":
                st.warning("請輸入團隊人員名稱", icon="⚠️")
            elif member_input in team_members:
                st.warning("團隊人員已存在", icon="⚠️")
            else:
                upload.add_team_member(member_input, logger)
                st.success(f"成功新增團隊人員: {member_input}", icon="✅")
                logger.info(f"[上傳CSV] 成功新增團隊人員: {member_input}")
            st.rerun()
        if delete_member_button:
            if member_input.strip() == "":
                st.warning("請輸入團隊人員名稱", icon="⚠️")
            elif member_input not in team_members:
                st.warning("團隊人員不存在", icon="⚠️")
            else:
                upload.delete_team_member(member_input, logger)
                st.success(f"成功刪除團隊人員: {member_input}", icon="✅")
                logger.info(f"[上傳CSV] 成功刪除團隊人員: {member_input}")

    # 檔案上傳區塊
    file = st.file_uploader("上傳CSV", ['.csv'],help="請上傳CSV檔案，檔案格式請參考說明文件",key='upload_file_uploader')
    
    if file is not None:
        df = pd.read_csv(file,encoding='utf-8')

        expected_cols = ['編號', '專案', '回報人', '分配給', '優先權',
                         '嚴重性', '出現頻率', '產品版本', '類別', '回報日期',
                         '作業系統', '作業系統版本', '平台類型', '檢視狀態',
                         '已更新', '摘要', '狀態', '問題分析', '已修正版本']
        df.columns = df.columns.str.strip()   # 去掉前後空白
        df.columns = df.columns.str.replace('\ufeff', '')  # 移除BOM字元
        df = df.dropna(axis=0, how='all')     # 移除完全空白的列
        for ex in expected_cols:
            if ex not in df.columns.tolist():
                st.error("CSV 檔案格式不正確，請確認欄位名稱",icon="⚠️")
                logger.error(f"[上傳CSV] CSV 檔案格式不正確，{expected_cols} 其中有欄位缺失")
                st.stop()
        upload_date = st.date_input("上傳檔案最新的回報日期",df['已更新'].max(), key='upload_date')
        upload_date = str(upload_date)
        logger.info(f'[上傳CSV] 開始上傳，日期: {upload_date}，檔案名稱: {file.name}')
        
        with st.spinner("正在處理中，請稍候..."):
            start_time = datetime.now()
            upload.upload(df,upload_date,member_selector,logger)
            end_time = datetime.now()
            logger.info(f"[上傳CSV] 成功上傳 {len(df)} 筆資料，耗時 {end_time - start_time}")
            st.success("處理完成！")


#資料查詢與匯出
def export_data_tab1():
    with tab1:
        with st.container(border=1):
            col1, col2, col3, col4, col5 = st.columns(spec=[6,0.5,6,2,2], vertical_alignment='bottom')
            with col1:
                start_report_date = st.date_input("起始回報日期",None, key='start_report_date')
            with col2:
                st.markdown("<p style='font-size: 24px;'>～</p>", unsafe_allow_html=True)
            with col3:
                end_report_date = st.date_input("結束回報日期",None, key='end_report_date')
            with col4:
                query_range = st.button("查詢",key='all_data_search_query_range',use_container_width=True)
            with col5:
                if query_range:
                    logger.info(f'[資料查詢與匯出-原始資料] 開始查詢 {start_report_date} ~ {end_report_date} 的原始資料(若無日期則查詢全部資料)')
                    start_time = datetime.now()
                    original_df = select_sql.export_original_data(logger)
                    original_df = original_df.set_index('編號')
                    # 檢查日期欄位並自動補齊
                    if start_report_date == None:
                        start_report_date = original_df['回報日期'].min()
                    if end_report_date == None:
                        end_report_date = original_df['回報日期'].max()
                    

                    original_df = original_df[(original_df['回報日期'] >= start_report_date) & (original_df['回報日期'] <= end_report_date)]
                    original_df = original_df.sort_values(by='回報日期', ascending=False)
                    csv_data = original_df.to_csv().encode('utf-8-sig')
                    if start_report_date > end_report_date:
                        download_button = st.button("匯出CSV",key='original_data_disabled_button',disabled=True,use_container_width=True)
                    else:
                        download_button = st.download_button(
                            label='匯出CSV',
                            data=csv_data,
                            file_name='qa_report_original_data.csv',
                            mime='text/csv',
                            use_container_width=True,
                            key='download_csv_button',
                            on_click=lambda: logger.info(f"[資料查詢與匯出-原始資料] 使用者已下載 {len(original_df)} 筆資料，日期區間: {start_report_date} ~ {end_report_date}")
                        )
                        
                    if original_df is None:
                        st.error("查無資料，請確認是否已上傳資料",icon="⚠️")
                        logger.error(f"[資料查詢與匯出-原始資料] 查無資料，請確認是否已上傳資料")
                        return
                else:
                    download_button = st.button("匯出CSV",key='original_data_disabled_button',disabled=True,use_container_width=True)

        if query_range:
            if start_report_date > end_report_date:
                        st.error("Error:起始日期不能晚於結束日期",icon="⚠️")
                        logger.error(f"[資料查詢與匯出-原始資料] 起始日期不能晚於結束日期: {start_report_date} ~ {end_report_date}")
                        return
            st.dataframe(original_df)
            end_time = datetime.now()
            logger.info(f"[資料查詢與匯出-原始資料] 成功查詢 {len(original_df)} 筆資料，日期: {start_report_date} ~ {end_report_date}，耗時 {end_time - start_time}")

def export_data_tab2():
    with tab2:
        with st.container(border=1):
            col1, col2, col3, col4, col5 = st.columns(spec=[6,0.5,6,2,2], vertical_alignment='bottom')
            with col1:
                log_start_date = st.date_input("起始log紀錄日期",None, key='log_start_date')
            with col2:
                st.markdown("<p style='font-size: 24px;'>～</p>", unsafe_allow_html=True)
            with col3:
                log_end_date = st.date_input("結束log紀錄日期",None, key='log_end_date')
            with col4:
                query_range = st.button("查詢",key='log_search_query_range',use_container_width=True)
            with col5:
                if query_range:
                    logger.info(f'[資料查詢與匯出-log紀錄] 開始查詢 {log_start_date} ~ {log_end_date} 的log紀錄(若無日期則查詢全部資料)')
                    start_time = datetime.now()
                    log_start_date = datetime.combine(log_start_date, datetime.min.time()) if log_start_date else None
                    log_end_date = datetime.combine(log_end_date, datetime.max.time()) if log_end_date else None
                    original_df = select_sql.export_log_search_data(logger)
                    original_df = original_df.set_index('編號')
                    # 檢查日期欄位並自動補齊
                    if log_start_date == None:
                        log_start_date = original_df['紀錄時間'].min()
                    if log_end_date == None:
                        log_end_date = original_df['紀錄時間'].max()

                    original_df = original_df[(original_df['紀錄時間'] >= log_start_date) & (original_df['紀錄時間'] <= log_end_date)]
                    original_df = original_df.sort_values(by='紀錄時間', ascending=False)
                    csv_data = original_df.to_csv().encode('utf-8-sig')
                    if log_start_date > log_end_date:
                        download_button = st.button("下載TXT",key='log_search_disabled_button',disabled=True,use_container_width=True)
                    else:
                        download_button = st.download_button(
                            label='下載TXT',
                            data=csv_data,
                            file_name='log.txt',
                            mime='text/plain',
                            use_container_width=True,
                            key='download_txt_button',
                            on_click=lambda: logger.info(f"[資料查詢與匯出-log紀錄] 使用者已下載 {len(original_df)} 筆資料，日期區間: {log_start_date} ~ {log_end_date}")
                        )
                    if original_df is None:
                        st.error("查無log紀錄，請確認輸入日期是否正確",icon="⚠️")
                        logger.error(f"[資料查詢與匯出-log紀錄] 查無log紀錄，請確認輸入日期是否正確")
                        return
                else:
                    download_button = st.button("下載TXT",key='log_search_disabled_button',disabled=True,use_container_width=True)
        if query_range:
            if log_start_date > log_end_date:
                        st.error("Error:起始日期不能晚於結束日期",icon="⚠️")
                        logger.error(f"[資料查詢與匯出-log紀錄] 起始日期不能晚於結束日期: {log_start_date} ~ {log_end_date}")
                        return
            st.dataframe(original_df)
            end_time = datetime.now()
            logger.info(f"[資料查詢與匯出-log紀錄] 成功查詢 {len(original_df)} 筆資料，日期: {log_start_date} ~ {log_end_date}，耗時 {end_time - start_time}")

if selected == "資料查詢與匯出":
    st.subheader('資料查詢與匯出')

    tab1, tab2 = st.tabs(["原始資料", "Log記錄"])
    export_data_tab1()
    export_data_tab2()

 
