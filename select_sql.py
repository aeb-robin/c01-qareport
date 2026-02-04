from sqlalchemy import create_engine ,text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
mysql_engine = create_engine(DATABASE_URL,
                            pool_recycle=3600,
                            pool_pre_ping=True
                            )
Session = sessionmaker(bind=mysql_engine)



def search_daily_results(date,logger):
    sql = text('''
        SELECT 
            `employee`,
            `new_issues`,
            `combined_done`,
            `cumulative_unfinished`,
            `important_unprocessed`,
            `external_unprocessed`,
            `under_test`
        FROM `daily_results`
        WHERE DATE(`daily_results`.`report_date`) = '{date}'
    '''.format(date=date))
    logger.info(f'[歷史統計查詢-單日統計] 執行 SQL: {sql}') 
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
        return
    df = pd.DataFrame(result)
    df.columns = ['員工','新問題','今日完成','累積未完成','重要未處理','外部未處理','待測試']
    
    return df

def search_employee_list(logger):
    sql = text('''
        SELECT DISTINCT `employee`
        FROM `daily_results`
    ''')
    logger.info(f'[查詢員工列表] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    
    if result == []:
        return
    employee_list = [i[0] for i in result if i[0] != '待測試']
    return employee_list

def search_last30days_result(logger):
    sql = text('''
        SELECT `report_date`, `employee`,
               `new_issues`, `combined_done`, `cumulative_unfinished`,
               `important_unprocessed`, `external_unprocessed`
        FROM `daily_results`
        WHERE `report_date` >= (
            SELECT MAX(`report_date`) FROM `daily_results`
        ) - INTERVAL 30 DAY
    ''')
    logger.info(f'[QA統計圖表] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
        return
    df = pd.DataFrame(result)
    df.columns = ['回報日期', '員工', '新問題', '每日完成', '累積未完成', '重要未處理', '外部未處理']
    return df

def search_range_results(start_date,end_date,logger):
    sql = text('''
        SELECT `report_date`, `employee`,
               `new_issues`, `combined_done`, `cumulative_unfinished`,
               `important_unprocessed`, `external_unprocessed`,
                `under_test`
        FROM `daily_results`
        WHERE `report_date` BETWEEN '{start_date}' AND '{end_date}'
    '''.format(start_date=start_date,end_date=end_date))
    logger.info(f'[歷史統計查詢-區間統計] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
        return
    df = pd.DataFrame(result)
    df.columns = ['回報日期', '員工', '新問題', '每日完成', '累積未完成', '重要未處理', '外部未處理','待測試']
    return df

def export_original_data(logger):
    sql = text('''SELECT  
                `case_no`,
                `project`,
                `reporter`,
                `receiver`,
                `priority`,
                `severity`,
                `frequency`,
                `version`,
                `category`,
                `report_date`,
                `os`,
                `os_version`,
                `platform_category`,
                `is_public`,
                `update_date`,
                `status`,
                `analysis`,
                `fixed_version`
            FROM `original_data`
            ORDER BY `update_date` DESC
        ''')
    logger.info(f'[資料查詢與匯出-原始資料] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
            return
    df = pd.DataFrame(result)
    df.columns = ['編號', '專案', '回報人', '分配給', '優先權', 
                '嚴重性', '出現頻率', '產品版本', '類別', '回報日期', 
                '作業系統', '作業系統版本', '平台類型', '檢視狀態', 
                '已更新', '狀態', '問題分析', '已修正版本']
    return df

def export_log_search_data(logger):
    sql = text('''SELECT `id`,
                `timestamp`,
                `levelname`,
                `message`
                FROM `logs`
                ORDER BY `id` DESC
            ''')
    logger.info(f'[資料查詢與匯出-log紀錄] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
            return
    df = pd.DataFrame(result)
    df.columns = ['編號', '紀錄時間', '等級', '訊息']
    return df

def get_team_members(logger):
    sql = text('''
        SELECT `name`
        FROM `team_members`
        WHERE `status` = TRUE
        ORDER BY `name` ASC
    ''')
    logger.info(f'[取得團隊成員列表] 執行 SQL: {sql}')
    session = Session()
    result = session.execute(sql)
    session.commit()
    result = result.fetchall()
    if result == []:
        return []
    team_members = [row[0] for row in result]
    return team_members
