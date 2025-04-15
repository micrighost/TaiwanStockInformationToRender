import yfinance as yf  # 引入 yfinance 庫，用於獲取股票數據
import pandas as pd  # 引入 pandas 庫，用於數據處理
import psycopg2  # 引入 psycopg2 庫，用於連接 PostgreSQL 資料庫
from datetime import datetime, timedelta  # 引入 datetime 和 timedelta 用於日期處理
import csv  # 引入 csv 庫，用於讀寫 CSV 檔案
import os

# 引入讀取db_tables的方法
import read_db_tables
# 引入刪除db_tables的方法
import drop_db_tables


from dotenv import load_dotenv
# 加載 .env 文件中的環境變數
load_dotenv()



def is_stock_code(ticker):
    """檢查是否為有效的台股股票代號"""

    try:
        stock_info = yf.Ticker(ticker)  # 使用 yfinance 獲取股票資訊
        # 檢查是否有市場價格，若有則為有效代號
        if stock_info.info['regularMarketPrice'] is not None: # 如果不是空，判定有這股票返回 True
            return True
        else:
            return False

    # 根據錯誤類型返回異常
    except KeyError:
        print(f"錯誤：無法找到股票代號 {ticker} 的市場價格資訊。")
        return False  # 若無法找到市場價格，返回 False
    except ValueError:
        print(f"錯誤：股票代號 {ticker} 格式不正確。")
        return False  # 若格式不正確，返回 False
    except Exception as e:
        print(f"發生錯誤：{e}")  # 捕捉其他異常並輸出錯誤訊息
        return False  # 若發生其他錯誤，返回 False

def fetch_stock_data(ticker):
    """抓取指定股票代號的近三個月交易資料"""
    end_date = datetime.now()  # 獲取當前日期
    start_date = end_date - timedelta(days=180)  # 計算三個月前的日期
    data = yf.download(ticker, start=start_date, end=end_date)  # 使用 yfinance 下載指定日期範圍內的股票數據
    return data  # 返回抓取到的數據

def save_stock_codes_to_postgresql(stock_codes):
    """將股票代號儲存到 PostgreSQL 資料庫"""
    try:
        # 連接到 PostgreSQL 資料庫
        conn = psycopg2.connect(
            dbname = os.getenv('DB_NAME'), # 資料庫名稱
            user = os.getenv('DB_USER'), # 使用者名稱
            password = os.getenv('DB_PASSWORD'), # 密碼
            host = os.getenv('DB_HOST'), # 主機地址
            port = os.getenv('DB_PORT') # 端口號
        )
        cursor = conn.cursor()  # 創建游標以執行 SQL 語句

        # 創建股票代號資料表（如果不存在）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_codes (
            id SERIAL PRIMARY KEY,  -- 自增主鍵
            ticker VARCHAR(10) UNIQUE  -- 股票代號
        )
        """)

        for code in stock_codes:
            cursor.execute("""
            INSERT INTO stock_codes (ticker)
            VALUES (%s)
            ON CONFLICT (ticker) DO NOTHING
            """, (code,))

        conn.commit()  # 提交事務
        cursor.close()  # 關閉游標
        conn.close()  # 關閉連接
        print("成功將股票代號儲存到 PostgreSQL 資料庫。")
    except Exception as e:
        print(f"儲存股票代號時發生錯誤: {e}")

def save_stock_data_to_postgresql(data, ticker):
    """將股票資料儲存到 PostgreSQL 資料庫"""
    try:
        # 連接到 PostgreSQL 資料庫
        conn = psycopg2.connect(
            dbname = os.getenv('DB_NAME'), # 資料庫名稱
            user = os.getenv('DB_USER'), # 使用者名稱
            password = os.getenv('DB_PASSWORD'), # 密碼
            host = os.getenv('DB_HOST'), # 主機地址
            port = os.getenv('DB_PORT') # 端口號
        )
        cursor = conn.cursor()  # 創建游標以執行 SQL 語句

        # 創建交易資料表（如果不存在）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            id SERIAL PRIMARY KEY,  -- 自增主鍵
            date DATE,  -- 日期
            open FLOAT,  -- 開盤價
            high FLOAT,  -- 最高價
            low FLOAT,  -- 最低價
            close FLOAT,  -- 收盤價
            volume INT,  -- 交易量
            ticker VARCHAR(10) REFERENCES stock_codes(ticker)  -- 股票代號，外鍵參考 stock_codes
        )
        """)

        for index, row in data.iterrows():
            cursor.execute("""
            INSERT INTO stock_data (date, open, high, low, close, volume, ticker)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (index.date(), float(row['Open'].iloc[0]), float(row['High'].iloc[0]), float(row['Low'].iloc[0]), float(row['Close'].iloc[0]), int(row['Volume'].iloc[0]), ticker))



        conn.commit()  # 提交事務
        cursor.close()  # 關閉游標
        conn.close()  # 關閉連接
        print(f"成功將 {ticker} 的資料儲存到 PostgreSQL 資料庫。")
    except Exception as e:
        print(f"儲存資料時發生錯誤: {e}")


def monthly_inspection():
    """這方法會比對資料庫裡的2330的最後一筆資料的日期，如果比今天的日期還要少一個月以上，就回傳True"""
    # 以護國神山為基礎來查詢日期，如果它沒了我看台灣也沉了
    ticker = '2330.TW'
    df = read_db_tables.fetch_stock_data(ticker)
    # 確保日期列是日期時間格式
    df['date'] = pd.to_datetime(df['date'])

    # 獲取最新的日期
    latest_date = df['date'].max()
    print("最新的日期是:", latest_date)


    from datetime import date
    # 取得今天的日期
    today = date.today()
    # 確保日期列是日期時間格式
    today = pd.to_datetime(today)
    # 輸出今天的日期
    print("今天的日期是:", today)

    # 計算日期差異
    difference = today - latest_date

    # 輸出結果
    print("日期差異是:", difference.days, "天")
    
    # 日期差30天以上，就回傳真
    if difference.days > 30:
        return True
    else:
        return False



def check_database_is_null():
    """這方法會搜尋資料庫是否有資料，如果沒有就寫入資料，如果有資料就不動"""
    try:

        # 連接到 PostgreSQL 資料庫
        conn = psycopg2.connect(
            dbname = os.getenv('DB_NAME'), # 資料庫名稱
            user = os.getenv('DB_USER'), # 使用者名稱
            password = os.getenv('DB_PASSWORD'), # 密碼
            host = os.getenv('DB_HOST'), # 主機地址
            port = os.getenv('DB_PORT') # 端口號
        )
        cursor = conn.cursor()

        # 查詢資料庫中的表格數量
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]

        if table_count == 0:
            print("資料庫是空的。")
            return True
        else:
            print("資料庫中已有表格，無需異動。")
            return False
    
    except Exception as e:
        print(f"發生錯誤: {e}")

    finally:
        # 確保游標和連接在結束時被關閉
        if cursor:
            cursor.close()  # 關閉游標
        if conn:
            conn.close()  # 關閉資料庫連接




def write_db_tables():
    stock_codes = []  # 初始化有效股票代號列表
    
    # 檢查從 0 到 9999 的數字
    for i in range(0, 10000):
        ticker = f"{i:04d}.TW"  # 格式化為四位數字並加上 .TW
        if is_stock_code(ticker):  # 檢查是否為有效的股票代號
            stock_codes.append(ticker)  # 若有效，則加入列表

    # 將有效的股票代號存成 CSV 檔案
    with open('valid_stock_codes.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)  # 創建 CSV 寫入器
        writer.writerow(['Stock Code'])  # 寫入表頭
        for code in stock_codes:  # 遍歷有效的股票代號
            writer.writerow([code])  # 寫入每個代號

    print("有效的台股股票代號已儲存到 valid_stock_codes.csv")  # 打印成功消息

    # 儲存股票代號到資料庫
    save_stock_codes_to_postgresql(stock_codes)

    # 抓取並儲存每個有效股票的交易資料
    for code in stock_codes:
        stock_data = fetch_stock_data(code)  # 抓取股票的交易資料
        save_stock_data_to_postgresql(stock_data, code)  # 儲存資料到 PostgreSQL


if __name__ == "__main__":

    # 把更新資料庫包成api，想要更新就打這api就可以了
    from flask import Flask
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def home():
        print("即將要開始幫你檢查資料庫")

        # 先確定資料庫是否為空，如果是空的就先填充
        if check_database_is_null():
            print("資料庫是空的，開始寫入資料庫。")
            write_db_tables()

        # 檢查上次更新日期，超過一個月就更新資料
        if monthly_inspection():
            # 刪除所有資料
            drop_db_tables.drop_all_tables()

            # 建立資料庫
            write_db_tables()
       
        return "即將要開始幫你檢查資料庫"

    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)




    


    
















