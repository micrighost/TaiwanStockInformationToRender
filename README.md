填入.env的資料庫資料，這程式會每個月幫你把render.com的postgreSQL資料庫做更新<br/>

更新資料為台股0-9999號<br/>

需要填入的資料為:<br/>
PostgreSQL 資料庫連接設定<br/>
DB_NAME=資料庫名稱<br/>
DB_USER=使用者名稱<br/>
DB_PASSWORD=密碼<br/>
DB_HOST=xxxxxxxxxxx.render.com<br/>
DB_PORT=5432<br/>


tip:<br/>
命令輸入 psql -U postgres 登入 超級管理員<br/>
超級管理員密碼 0000<br/>

pgAdmin密碼 0000<br/>


serveo.net內網穿透開啟指令:<br/>
ssh -R 5432:localhost:5432 serveo.net<br/>


-- 列出當前資料庫裡有的資料表<br/>
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';<br/>


-- -- 列出資料表stock_data<br/>
SELECT * FROM stock_data;<br/>

-- 列出資料表stock_codes<br/>
SELECT * FROM stock_codes;<br/>