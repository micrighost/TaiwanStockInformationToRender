import psycopg2
import pandas as pd

import os
from dotenv import load_dotenv
# 加載 .env 文件中的環境變數
load_dotenv()



def fetch_stock_data(ticker):
    """根據股票代碼從 PostgreSQL 資料庫中獲取股票數據。

    參數:
    ticker (str): 股票代碼，例如 '2308.TW'

    返回:
    pd.DataFrame: 包含股票數據的 DataFrame
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

        # 創建一個游標對象
        cursor = conn.cursor()

        # 定義查詢語句
        query = "SELECT * FROM stock_data WHERE ticker = %s;"

        # 執行查詢
        cursor.execute(query, (ticker,))

        # 獲取查詢結果
        rows = cursor.fetchall()

        # 獲取欄位名稱
        colnames = [desc[0] for desc in cursor.description]

        # 將結果轉換為 Pandas DataFrame
        df = pd.DataFrame(rows, columns=colnames)

    except psycopg2.DatabaseError as e:
        print("資料庫錯誤：", e)
        df = pd.DataFrame()  # 返回空的 DataFrame

    except Exception as e:
        print("發生錯誤：", e)
        df = pd.DataFrame()  # 返回空的 DataFrame

    finally:
        # 確保游標和連接在結束時被關閉
        if cursor:
            cursor.close()  # 關閉游標
        if conn:
            conn.close()  # 關閉資料庫連接

    return df



