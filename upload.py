# upload.py

from sqlalchemy import create_engine, text
import streamlit as st
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime

load_dotenv()

# 資料庫連線設定
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_NAME = st.secrets["DB_NAME"]
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

mysql_engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600,
    pool_pre_ping=True
)
Session = sessionmaker(bind=mysql_engine)

def daily_results(df, team_members):
    # 確保日期格式正確
    df['回報日期'] = pd.to_datetime(df['回報日期'], errors='coerce')
    df['已更新'] = pd.to_datetime(df['已更新'], errors='coerce')

    report_date = df['回報日期'].max()

    # 這裡填補空字串是為了後續統計邏輯不報錯
    df_stat = df.fillna('')
    
    fixed_keys = team_members
    people_results = {person: {} for person in fixed_keys}

    # 各項指標統計
    new_issues = df_stat[(df_stat['狀態'] == '已分配') & (df_stat['回報日期'] == report_date)]['分配給'].value_counts().to_dict()
    
    done_tested = df_stat[(df_stat['狀態'] == '已測試') & (df_stat['已更新'] == report_date)]
    done_tested_count = done_tested['回報人'].value_counts().to_dict()
    
    done_assigned = df_stat[(df_stat['狀態'] == '待測試') & (df_stat['已更新'] == report_date)]
    done_assigned_count = done_assigned['分配給'].value_counts().to_dict()
    
    combined_done = {**done_tested_count, **done_assigned_count}
    cumulative_unfinished = df_stat[df_stat['狀態'] == '已分配']['分配給'].value_counts().to_dict()
    important_unprocessed = df_stat[(df_stat['狀態'] == '已分配') & (df_stat['嚴重性'] == '重要')]['分配給'].value_counts().to_dict()
    external_unprocessed = df_stat[(df_stat['狀態'] == '已分配') & (df_stat['類別'] == 'HAPCS疾管署_愛滋追管系統')]['分配給'].value_counts().to_dict()
    
    daily_stats = {
        '新問題': new_issues,
        '每日完成': combined_done,
        '累積未完成': cumulative_unfinished,
        '重要未處理': important_unprocessed,
        '外部未處理': external_unprocessed
    }

    all_categories = list(daily_stats.keys())
    
    # 初始化與補零
    for person in fixed_keys:
        for cat in all_categories:
            people_results[person][cat] = 0

    # 寫入統計結果
    for cat, data in daily_stats.items():
        for person, count in data.items():
            if person in people_results:
                people_results[person][cat] = count

    # 待測試統計
    under_test_count = int((df['狀態'] == '待測試').sum())
    people_results['待測試'] = {'新問題': under_test_count}
    
    return people_results

def insert_original_data(data_dict, logger):
    # 【修正點】二次檢查：強制將 dictionary 內殘留的 NaN 轉為 None (對應 SQL NULL)
    clean_data = [
        {k: (None if pd.isna(v) else v) for k, v in d.items()}
        for d in data_dict
    ]
    
    sql = text("""INSERT INTO `original_data`
            (`case_no`, `project`, `reporter`, `receiver`,
            `priority`, `severity`, `frequency`, `version`,
            `category`, `report_date`, `os`, `os_version`,
            `platform_category`, `is_public`, `update_date`,
            `status`, `analysis`, `fixed_version`)
    VALUES (:case_no, :project, :reporter, :receiver, :priority, :severity, :frequency,
            :version, :category, :report_date, :os, :os_version, :platform_category, :is_public,
            :update_date, :status, :analysis, :fixed_version)
            ON DUPLICATE KEY UPDATE
            project = VALUES(project),
            reporter = VALUES(reporter),
            receiver = VALUES(receiver),
            priority = VALUES(priority),
            severity = VALUES(severity),
            frequency = VALUES(frequency),
            version = VALUES(version),
            category = VALUES(category),
            report_date = VALUES(report_date),
            os = VALUES(os),
            os_version = VALUES(os_version),
            platform_category = VALUES(platform_category),
            is_public = VALUES(is_public),
            update_date = VALUES(update_date),
            status = VALUES(status),
            analysis = VALUES(analysis),
            fixed_version = VALUES(fixed_version)
            """)
    
    session = Session()
    try:
        session.execute(sql, clean_data)  # 批次寫入
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[上傳CSV] 批次上傳失敗: {e}")
        raise
    finally:
        session.close()

def insert_daily_results_data(data_list):
    # 【修正點】改用參數化查詢，避免手動 replace('nan', 'NULL')
    sql = text('''INSERT INTO `daily_results`
            (`employee`, `report_date`, `new_issues`, `combined_done`,
            `cumulative_unfinished`, `important_unprocessed`, `external_unprocessed`, `under_test`)
            VALUES (:employee, :report_date, :new_issues, :combined_done, 
                    :cumulative_unfinished, :important_unprocessed, :external_unprocessed, :under_test)
            ON DUPLICATE KEY UPDATE
            new_issues = VALUES(new_issues),
            combined_done = VALUES(combined_done),
            cumulative_unfinished = VALUES(cumulative_unfinished),
            important_unprocessed = VALUES(important_unprocessed),
            external_unprocessed = VALUES(external_unprocessed),
            under_test = VALUES(under_test)
        ''')
    
    # 將 list 轉換為 dict 以匹配參數化 SQL
    param_dict = {
        "employee": data_list[0],
        "report_date": data_list[1],
        "new_issues": data_list[2],
        "combined_done": data_list[3],
        "cumulative_unfinished": data_list[4],
        "important_unprocessed": data_list[5],
        "external_unprocessed": data_list[6],
        "under_test": data_list[7]
    }

    session = Session()
    try:
        session.execute(sql, param_dict)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def upload(df, date, team_members, logger):
    # 移除摘要
    df = df.drop(columns="摘要", errors='ignore') 
    
    # 【修正點】將所有 NaN/NaT 徹底轉為 None，否則 MySQL 不收
    df_clean = df.where(pd.notnull(df), None)
    
    # 定義對應資料庫的欄位名稱
    keys = ["case_no", "project", "reporter", "receiver",
            "priority", "severity", "frequency", "version",
            "category", "report_date", "os", "os_version",
            "platform_category", "is_public", "update_date",
            "status", "analysis", "fixed_version"]
    
    # 確保 DataFrame 欄位數量與順序正確後轉換為 Dict
    # 如果 df 的欄位與 keys 順序一致，可以直接轉換
    original_data_dict = [dict(zip(keys, row)) for row in df_clean.values]
    
    # 執行原始資料上傳
    insert_original_data(original_data_dict, logger)

    # 計算每日統計
    day_results = daily_results(df, team_members)
    
    for name, stats in day_results.items():
        if name == '待測試':
            daily_list = [name, date, 0, 0, 0, 0, 0, stats['新問題']]
        else:
            # 確保統計數值中沒有 NaN，若有則給 0
            vals = [stats.get(cat, 0) for cat in ['新問題', '每日完成', '累積未完成', '重要未處理', '外部未處理']]
            daily_list = [name, date] + vals + [0]
        
        insert_daily_results_data(daily_list)
    
    return

def add_team_member(member_name, logger):
    sql = text('''INSERT INTO `team_members` (`name`, `status`)
                VALUES (:name, TRUE)
                ON DUPLICATE KEY UPDATE status = VALUES(status)''')

    session = Session()
    try:
        session.execute(sql, {"name": member_name})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[新增團隊成員] 新增失敗: {e}")
        raise
    finally:
        session.close()

def delete_team_member(member_name, logger):
    sql = text('''UPDATE `team_members` SET `status` = FALSE WHERE `name` = :name''')

    session = Session()
    try:
        session.execute(sql, {"name": member_name})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[刪除團隊成員] 刪除失敗: {e}")
        raise
    finally:
        session.close()
