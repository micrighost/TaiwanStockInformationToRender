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
        return True,difference
    else:
        return False,difference



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




if __name__ == "__main__":
    
    from flask import Flask, render_template, jsonify
    import threading
    import time

    # 初始化 Flask 應用
    app = Flask(__name__)

    # 全局控制變數 (多線程共享)
    stop_event = threading.Event()  # 用於控制背景任務停止
    update_progress = {  # 進度追蹤字典
        "current_batch": 0,         # 當前處理批次
        "total_batches": 5,         # 總批次數 (初始值)
        "is_running": False,        # 任務運行狀態
        "messages": []              # 操作訊息記錄
    }

    def write_db_tables():
        """
        批次寫入資料庫主邏輯
        功能分為三階段：
        1. 驗證股票代碼有效性
        2. 儲存有效代碼到 CSV
        3. 保存資料到 PostgreSQL 資料庫
        """
        try:
            # 初始化參數
            total_stocks = 10000    # 台股代碼範圍 0000-9999
            batch_size = 5          # 每批次檢查數量
            update_progress["total_batches"] = total_stocks // batch_size  # 動態計算總批次
            
            stock_codes = []        # 有效代碼暫存列表
            
            # 批次檢查代碼有效性
            for i in range(update_progress["total_batches"]):
                if stop_event.is_set():  # 檢查停止標記
                    break
                    
                # 更新進度狀態
                update_progress["current_batch"] = i + 1
                update_progress["messages"].append(f"正在處理第 {i+1} 批次")
                
                time.sleep(1)  # 模擬處理延遲
                
                # 實際處理邏輯
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                
                for num in range(start_idx, end_idx):
                    ticker = f"{num:04d}.TW"  # 格式化台股代碼
                    if is_stock_code(ticker):  # 需實作的驗證函式
                        stock_codes.append(ticker)
                
                update_progress["messages"].append(f"第 {i+1} 批次完成，已處理 {batch_size} 筆")

            # 處理未整除的最終批次
            remaining = total_stocks % batch_size
            if remaining > 0 and not stop_event.is_set():
                update_progress["messages"].append("正在處理最終批次")
                start_idx = update_progress["total_batches"] * batch_size
                for num in range(start_idx, start_idx + remaining):
                    ticker = f"{num:04d}.TW"
                    if is_stock_code(ticker):
                        stock_codes.append(ticker)
                update_progress["messages"].append("最終批次完成")

            # 儲存階段
            if not stop_event.is_set():
                # CSV 儲存
                update_progress["messages"].append("正在儲存 CSV 檔案")
                with open('valid_stock_codes.csv', 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Stock Code'])
                    writer.writerows([[code] for code in stock_codes])
                update_progress["messages"].append("CSV 儲存完成")

                # 資料庫儲存
                update_progress["messages"].append("正在儲存到資料庫")
                save_stock_codes_to_postgresql(stock_codes)  # 需實作的資料庫函式
                update_progress["messages"].append("代碼儲存完成")

                # 歷史數據抓取
                update_progress["messages"].append("開始抓取歷史資料")
                for idx, code in enumerate(stock_codes, 1):
                    if stop_event.is_set():
                        break
                        
                    update_progress["messages"].append(f"正在處理 {code} ({idx}/{len(stock_codes)})")
                    stock_data = fetch_stock_data(code)  # 需實作的數據抓取函式
                    save_stock_data_to_postgresql(stock_data, code)  # 需實作的資料庫函式
                    time.sleep(0.5)  # 避免 API 請求過快

        except Exception as e:
            update_progress["messages"].append(f"發生錯誤: {str(e)}")
            return False
        finally:
            return True  # 無論成功失敗都返回 True 以完成 Flask 響應

    def run_update_process():
        """
        更新主流程控制器
        執行順序：
        1. 刪除舊資料表
        2. 批次寫入新資料
        3. 錯誤處理與狀態更新
        """
        update_progress["is_running"] = True
        update_progress["messages"].append("開始資料庫更新流程")
        
        try:
            # 資料清理階段
            drop_db_tables.drop_all_tables()  # 需實作的資料表刪除函式
            update_progress["messages"].append("舊資料刪除完成")

            # 資料寫入階段
            write_db_tables()

            update_progress["messages"].append("資料庫更新完成")
        except Exception as e:
            update_progress["messages"].append(f"更新失敗: {str(e)}")
        finally:
            update_progress["is_running"] = False

    # 路由定義
    @app.route('/')
    def home():
        """主頁面路由"""
        return render_template('index.html')

    @app.route('/check_database', methods=['POST'])
    def check_database():
        """資料庫狀態檢查 API"""
        output = ["正在檢查資料庫..."]
        if check_database_is_null():  # 需實作的檢查函式
            output.append("資料庫是空的。")
        elif monthly_inspection():    # 需實作的檢查函式
            _, days = monthly_inspection()
            output.extend([f"距離上次更新: {days}天", "檢查完成"])
        return jsonify({"messages": output})

    @app.route('/update_database', methods=['POST'])
    def update_database():
        """啟動背景更新任務 API"""
        if update_progress["is_running"]:
            return jsonify({"status": "error", "message": "已有更新任務進行中"})
        
        # 狀態初始化
        stop_event.clear()
        update_progress.update({
            "current_batch": 0,
            "is_running": True,
            "messages": []
        })
        
        # 啟動背景執行緒
        thread = threading.Thread(target=run_update_process)
        thread.start()
        
        return jsonify({"status": "started", "message": "批次更新已啟動"})

    @app.route('/update_progress', methods=['GET'])
    def get_update_progress():
        """進度查詢 API"""
        return jsonify({
            "current": update_progress["current_batch"],
            "total": update_progress["total_batches"],
            "is_running": update_progress["is_running"],
            "messages": update_progress["messages"]
        })

    @app.route('/stop_update', methods=['POST'])
    def stop_update():
        """停止更新任務 API"""
        stop_event.set()
        return jsonify({"status": "stopped", "message": "已發送停止信號"})

    @app.route('/delete_database', methods=['POST'])
    def delete_database():
        """資料庫刪除 API"""
        drop_db_tables.drop_all_tables()
        return jsonify({"messages": ["資料庫已刪除"]})

    # 主程式入口
    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000, threaded=True)

    














