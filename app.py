# 導入必要庫
import yfinance as yf  # 用於從 Yahoo Finance 獲取金融數據
import pandas as pd  # 用於數據處理和分析
import psycopg2  # PostgreSQL 數據庫適配器
from datetime import datetime, timedelta  # 處理日期和時間
import csv  # 讀寫 CSV 文件
import os  # 操作系統功能
from flask import Flask, render_template, jsonify, request  # Web 框架及相關工具
import threading  # 多線程支持
import time  # 時間相關功能

# 導入自定義模塊
import drop_db_tables  # 刪除數據庫表的工具
from dotenv import load_dotenv  # 從 .env 文件加載環境變量

# 加載環境變量
load_dotenv()  # 從項目根目錄的 .env 文件加載敏感信息

def is_stock_code(ticker):
    """檢查是否為有效的台股股票代號
    
    Args:
        ticker (str): 股票代號
        
    Returns:
        bool: 是否為有效代號
    """
    try:
        stock_info = yf.Ticker(ticker)  # 創建股票對象
        
        # 檢查是否存在市場價格數據
        if stock_info.info['regularMarketPrice'] is not None:
            return True
        return False
    
    except KeyError:
        print(f"錯誤：無法找到股票代號 {ticker} 的市場價格資訊。")
        return False
    except ValueError:
        print(f"錯誤：股票代號 {ticker} 格式不正確。")
        return False
    except Exception as e:
        print(f"發生未知錯誤：{e}")
        return False

def fetch_stock_data(ticker):
    """抓取指定股票近6個月歷史數據
    
    Args:
        ticker (str): 股票代號
        
    Returns:
        pd.DataFrame: 包含 OHLCV 數據的 DataFrame
    """
    end_date = datetime.now()  # 當前日期
    start_date = end_date - timedelta(days=180)  # 180天前日期
    data = yf.download(ticker, start=start_date, end=end_date)  # 下載歷史數據
    return data

def save_stock_codes_to_postgresql(stock_codes):
    """將股票代號批量存入 PostgreSQL 數據庫
    
    Args:
        stock_codes (list): 股票代號列表
        
    工作流程：
    1. 建立數據庫連接
    2. 創建 stock_codes 表 (如果不存在)
    3. 批量插入數據，忽略重複值
    4. 提交事務並關閉連接
    """
    try:
        # 建立數據庫連接
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        cursor = conn.cursor()

        # 創建股票代碼表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_codes (
            id SERIAL PRIMARY KEY,  -- 自增主鍵
            ticker VARCHAR(10) UNIQUE  -- 唯一股票代號
        )
        """)

        # 批量插入數據
        for code in stock_codes:
            cursor.execute("""
            INSERT INTO stock_codes (ticker)
            VALUES (%s)
            ON CONFLICT (ticker) DO NOTHING
            """, (code,))

        conn.commit()  # 提交事務
        print("股票代號存儲成功")
        
    except Exception as e:
        print(f"數據庫操作異常: {e}")
    finally:
        cursor.close()
        conn.close()

def save_stock_data_to_postgresql(data, ticker):
    """存儲單個股票歷史數據到數據庫
    
    Args:
        data (pd.DataFrame): 包含 OHLCV 的股票數據
        ticker (str): 股票代號
        
    注意事項：
    - 數據表 stock_data 包含外鍵約束
    - 使用批量插入提高性能
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        cursor = conn.cursor()

        # 創建股票數據表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            id SERIAL PRIMARY KEY,
            date DATE,  -- 交易日期
            open FLOAT,  -- 開盤價
            high FLOAT,  -- 最高價
            low FLOAT,  -- 最低價
            close FLOAT,  -- 收盤價
            volume INT,  -- 成交量
            ticker VARCHAR(10) REFERENCES stock_codes(ticker)  -- 外鍵約束
        )
        """)

        # 插入每行數據
        for index, row in data.iterrows():
            cursor.execute("""
            INSERT INTO stock_data (date, open, high, low, close, volume, ticker)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                index.date(), 
                float(row['Open'].iloc[0]),
                float(row['High'].iloc[0]),
                float(row['Low'].iloc[0]),
                float(row['Close'].iloc[0]),
                int(row['Volume'].iloc[0]),
                ticker
            ))

        conn.commit()
        print(f"{ticker} 數據存儲成功")
        
    except Exception as e:
        print(f"數據存儲異常: {e}")
    finally:
        cursor.close()
        conn.close()

def check_database_is_null():
    """檢查數據庫初始化狀態
    
    Returns:
        bool: True 表示數據庫為空需要初始化
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        cursor = conn.cursor()

        # 檢查公共模式下的表數量
        cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]

        if table_count == 0:
            return True

        # 檢查 stock_codes 表存在性
        cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'stock_codes'
        )
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            return True

        # 檢查表是否為空
        cursor.execute("SELECT COUNT(*) FROM stock_codes")
        count = cursor.fetchone()[0]
        return count == 0
        
    except Exception as e:
        print(f"數據庫檢查異常: {e}")
        return True
    finally:
        cursor.close()
        conn.close()



def get_last_updated_stock():
    """取得 stock_data 表中最後加入的股票代號及日期，並計算距今天數
    
    Returns:
        dict: 包含股票代號(code)、最後更新日期(date)和距今天數(days)的字典
        None: 查詢失敗時返回
    """
    try:
        # 導入依賴（通常應放在文件頂部，此處為保持函數獨立性）
        import psycopg2
        from datetime import datetime
        
        # 建立數據庫連接
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),  # 從環境變量獲取數據庫名
            user=os.getenv('DB_USER'),    # 數據庫用戶名
            password=os.getenv('DB_PASSWORD'),  # 數據庫密碼
            host=os.getenv('DB_HOST'),    # 數據庫主機地址
            port=os.getenv('DB_PORT')     # 數據庫端口號
        )
        
        # 使用上下文管理器自動管理游標
        with conn.cursor() as cur:
            # 查詢最新數據（按主鍵ID降序）
            cur.execute("""
                SELECT ticker, date
                FROM stock_data
                ORDER BY id DESC  -- 按插入順序倒排
                LIMIT 1           -- 只取最新一條
            """)
            result = cur.fetchone()  # 獲取單條結果
            
            if result:
                stock_code, last_date = result
                # 計算日期差（使用date()過濾時間部分）
                days_diff = (datetime.now().date() - last_date).days
                return {
                    "code": stock_code,
                    "date": last_date,
                    "days": days_diff
                }
    except Exception as e:
        # 使用Flask應用日誌記錄錯誤（需確保app實例存在）
        app.logger.error(f"查詢最後加入股票資料失敗: {str(e)}")
    return None  # 發生異常時返回空值

# 全局控制變數 (多線程共享)
stop_event = threading.Event()  # 線程安全事件對象，用於跨線程停止信號
update_progress = {
    "current_batch": 0,         # 當前處理的批次序號（從0開始）
    "total_batches": 5,         # 總批次數（初始值可被覆蓋）
    "is_running": False,        # 流程運行狀態標誌位
    "messages": [],             # 操作日誌隊列（需注意線程安全）
    "start_idx": 0              # 新增：批次處理起始索引
}

def write_db_tables(total_stocks):
    """批量處理股票數據寫入流程
    
    Args:
        total_stocks (int): 需要處理的股票總數
        
    Returns:
        bool: True=成功完成且未中斷, False=被中斷或失敗
    """
    try:
        batch_size = 5 # 每批處理的數量
        start_idx = update_progress["start_idx"] # 從進度字典獲取起始索引
        stock_codes = [] # 初始化空列表，用於儲存當前批次的股票代碼
        


        # 主批次處理循環
        for i in range(update_progress["total_batches"]): # 歷遍所有批次
            if stop_event.is_set(): # 用.is_set()檢查標誌是否為 True
                update_progress["messages"].append("用戶中斷: 批次處理階段")
                return False  # 立即返回中斷狀態

            # 迴圈的迭代索引（從 0 開始），i + 1 轉換為人類可讀的批次編號（從 1 開始）
            update_progress["current_batch"] = i + 1 # 更新當前批次編號
            update_progress["messages"].append(f"正在處理第 {i+1} 批次") # 添加處理日誌
            
            time.sleep(1)
            
            current_start = start_idx + i * batch_size # 計算批次起始索引，範例start_idx=10, i=2, batch_size=5 → 10 + 2*5 = 20
            # 計算批次結束位置，取小的防止最後一批次超出總數據量
            # 範例current_start=20, batch_size=5, start_idx + total_stocks=23 → min(25,23)=23
            current_end = min(current_start + batch_size, start_idx + total_stocks)  
            
            for num in range(current_start, current_end): # 遍歷當前批次範圍
                ticker = f"{num:04d}.TW" # 將數字補零至 4 位，並加上台灣股票市場後綴.TW
                if is_stock_code(ticker): # 自定義函數，檢查股票代號是否存在
                    stock_codes.append(ticker) # 保留有效代碼到 stock_codes 列表中
            
            update_progress["messages"].append(f"第 {i+1} 批次完成")



        # 最終保存階段
        if not stop_event.is_set(): # 如果沒有收到停止訊號
            # 將有效的股票代碼列表寫入 CSV 檔案
            with open('valid_stock_codes.csv', 'w', newline='') as csvfile: # 開啟檔案
                writer = csv.writer(csvfile) # 建立寫入器
                writer.writerow(['Stock Code']) # 寫入標題列
                writer.writerows([[code] for code in stock_codes])  # 寫入所有代碼
            
            # 傳入有效的股票代碼，將有效的股票代碼列表保存至 PostgreSQL 資料庫
            save_stock_codes_to_postgresql(stock_codes)
            
            # 歷史數據抓取
            # 使用 enumerate 函數逐一取出 stock_codes 的元素，生成 (編號, 股票代碼) 元組
            # 參數 1 表示編號從 1 開始（預設為 0）
            for idx, code in enumerate(stock_codes, 1):
                if stop_event.is_set(): # 如果有收到停止訊號
                    update_progress["messages"].append("用戶中斷: 歷史數據抓取階段")
                    update_progress["messages"].append(f"第 {idx} 支股票 {code} 處理失敗")
                    return False
                
                stock_data = fetch_stock_data(code) # 抓取單一股票歷史數據（包含開/高/低/收等欄位）
                save_stock_data_to_postgresql(stock_data, code) # 將股票數據存入 PostgreSQL 資料庫
                time.sleep(0.5)

            return True  # 只有完整執行到這裡才返回成功
        
        else: # # 如果有收到停止訊號
            update_progress["messages"].append("用戶中斷: 最終保存前")
            return False

    except Exception as e:
        update_progress["messages"].append(f"處理失敗: {str(e)}")

        raise # 重新拋出異常，將原始異常傳遞給上層調用者

def run_update_process(total_stocks):
    """更新主流程控制器
    
    Args:
        total_stocks (int): 要處理的股票總數
    """
    update_progress["is_running"] = True  # 設置運行標誌
    update_progress["messages"].append("開始資料庫更新流程")
    
    try:            
        if write_db_tables(total_stocks):  # 執行核心處理邏輯，返回True則顯示資料庫更新完成
            update_progress["messages"].append("資料庫更新完成")
        else:
            update_progress["messages"].append(f"資料庫更新未完成") # 返回False則顯示資料庫更新未完成

    except Exception as e:
        update_progress["messages"].append(f"更新失敗: {str(e)}")
    finally:
        update_progress["is_running"] = False  # 重置狀態標誌




# 初始化 Flask 應用
app = Flask(__name__)  # 創建 Flask 應用實例

@app.route('/')
def home():
    """主頁面路由
    
    Returns:
        str: 渲染後的 HTML 模板
    """
    return render_template('index.html')  # 返回 templates 目錄下的 index.html

@app.route('/update_database', methods=['POST'])
def update_database():
    """啟動資料庫更新流程的 API 端點
    
    Returns:
        Response: JSON 格式的回應，包含操作狀態
    """
    # 檢查是否已有任務在執行
    # 當檢測到 update_progress 字典中的 is_running 為 True 時，立即返回錯誤響應，阻止新任務啟動
    if update_progress["is_running"]:
        return jsonify({"status": "error", "message": "已有更新任務進行中"})
    
    # 解析用戶輸入範圍 (格式: '起始-結束')
    # 前端使用user_input: $('#newInput').val()傳遞參數user_input到後段，這裡用request.form.get取值
    user_input = request.form.get('user_input', '0-20')  # 默認範圍 0-20
    
    try:
        # in 是一個成員運算符（membership operator），用來判斷某個元素是否存在於一個「序列」或「集合」中
        if '-' in user_input: # 檢查輸入是否包含連字符
            start, end = map(int, user_input.split('-'))  # 將輸入按照'-'拆分為兩個數字
            total_stocks = end - start  # 計算總股票數
        else:
            start, end = 0, int(user_input)  # 如果只有一個數字，就假定從零開始到輸入的數字
            total_stocks = end - start # 計算總股票數
    except ValueError:  # 格式錯誤處理
        start, end = 0, 20  # 使用默認值
        total_stocks = end - start
    
    # 初始化全局狀態變數
    stop_event.clear()  # 重置停止標誌，將標誌設為 False
    update_progress.update({
        # 如果 user_input 包含 -（如 0-20），則使用 start 變數的值，否則預設為 0
        "start_idx": start if '-' in user_input else 0,  # 設置起始索引
        "current_batch": 0,  # 重置當前批次，固定設為 0，表示從第 0 批開始執行
        # 範例total_stocks = 23 → (23 + 5 - 1) // 5 = 27 // 5 = 5 批次
        "total_batches": (total_stocks + 5 - 1) // 5,  # 計算總批次數(每批5個)(向上取整)
        "is_running": True,  # 設置運行標誌，設為 True，表示任務啟動
        "messages": []  # 清空消息隊列
    })

    # 啟動後台更新線程
    thread = threading.Thread(
        target=run_update_process,  # 指定執行緒要跑的函數
        args=(total_stocks,)  # 傳入參數（注意單參數需加逗號 ,）避免被當成數學計算的括號，而不是元組
    )
    # thread.start() 會讓 run_update_process 函數在獨立執行緒中運行，不阻塞主程式
    thread.start()  # 啟動線程
    
    return jsonify({
        "status": "started",
        "message": "批次更新已啟動"
    })

@app.route('/check_database', methods=['POST'])
def check_database():
    """資料庫狀態檢查 API
    
    Returns:
        Response: 包含檢查結果的 JSON 回應
    """
    output = ["正在檢查資料庫..."]  # 初始化輸出消息
    
    if check_database_is_null():  # 調用數據庫檢查函數
        output.append("資料庫是空的。")
    else:
        last_stock = get_last_updated_stock()  # 獲取最後更新記錄
        if last_stock:
            output.extend([
                f"最後加入股票代號: {last_stock['code']}",
                f"最後資料日期: {last_stock['date'].strftime('%Y-%m-%d')}",  # 格式化日期
                f"距今天數: {last_stock['days']} 天",
                "檢查完成"
            ])
        else:
            output.append("無法取得最後加入的股票資料")

    return jsonify({"messages": output})

@app.route('/update_progress', methods=['GET'])
def get_update_progress():
    """進度查詢 API
    
    Returns:
        Response: 包含當前進度信息的 JSON 回應
    """
    return jsonify({
        "current": update_progress["current_batch"],  # 當前批次序號
        "total": update_progress["total_batches"],  # 總批次數
        "is_running": update_progress["is_running"],  # 運行狀態
        "messages": update_progress["messages"]  # 操作日誌
    })

@app.route('/stop_update', methods=['POST'])
def stop_update():
    """停止更新 API
    
    Returns:
        Response: 操作結果 JSON 回應
    """
    stop_event.set()  # 設置全局停止標誌，將標誌設為 True
    return jsonify({
        "status": "stopped",
        "message": "已發送停止信號"
    })

@app.route('/delete_database', methods=['POST'])
def delete_database():
    """資料庫刪除 API
    
    Returns:
        Response: 操作結果 JSON 回應
    """
    drop_db_tables.drop_all_tables()  # 調用刪除表函數
    return jsonify({"messages": ["資料庫已刪除"]})

if __name__ == "__main__":
    # 啟動 Flask 開發服務器
    app.run(
        host='0.0.0.0',  # 監聽所有網絡接口
        port=5000,  # 使用 5000 端口
        threaded=True  # 啟用多線程模式
    )