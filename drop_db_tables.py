import psycopg2

import os
from dotenv import load_dotenv
# 加載 .env 文件中的環境變數
load_dotenv()

def drop_all_tables():
    """刪除 PostgreSQL 資料庫中的所有資料表。

    此函數連接到指定的 PostgreSQL 資料庫，獲取所有資料表名稱，並逐一刪除它們。
    """
    try:
        # 連接到 PostgreSQL 資料庫
        conn = psycopg2.connect(
            dbname = os.getenv('DB_NAME'), # 資料庫名稱
            user = os.getenv('DB_USER'), # 使用者名稱
            password = os.getenv('DB_PASSWORD'), # 密碼
            host = os.getenv('DB_HOST'), # 主機地址
            port = os.getenv('DB_PORT') # 端口號
        )
        
        # 創建一個游標對象，用於執行 SQL 查詢
        cursor = conn.cursor()

        # 獲取所有資料表名稱
        cursor.execute("""
            SELECT tablename FROM pg_tables --pg_tables包含了資料庫中所有資料表
            WHERE schemaname = 'public';  -- 只查詢 public 的資料表
        """)
        tables = cursor.fetchall()  # 獲取所有資料表名稱的列表

        # 刪除所有資料表
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]} CASCADE;")  # 刪除資料表，若存在則刪除
            print(f"已刪除資料表: {table[0]}")  # 輸出已刪除的資料表名稱

        # 提交變更，確保所有刪除操作生效
        conn.commit()

        # 確認資料表已被刪除
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public';  -- 再次查詢以確認是否還有資料表存在
        """)
        remaining_tables = cursor.fetchall()  # 獲取剩餘的資料表名稱

        # 檢查是否還有資料表存在
        if not remaining_tables:
            print("所有資料表已成功刪除。")  # 如果沒有剩餘資料表，則輸出成功訊息
        else:
            print("仍有資料表存在：")  # 如果還有資料表，則輸出剩餘資料表名稱
            for remaining in remaining_tables:
                print(remaining[0])  # 輸出每個剩餘的資料表名稱

    except (Exception, psycopg2.DatabaseError) as error:
        print("發生錯誤：", error)  # 捕捉並輸出任何錯誤訊息
    finally:
        # 確保游標和連接在結束時被關閉
        if cursor:
            cursor.close()  # 關閉游標
        if conn:
            conn.close()  # 關閉資料庫連接

