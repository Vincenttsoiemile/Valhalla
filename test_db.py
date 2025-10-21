#!/usr/bin/env python3
import pymysql

DB_CONFIG = {
    'host': '38.14.208.188',
    'port': 3306,
    'user': 'reader',
    'password': 'Emile#5092r',
    'database': 'bonddb',
    'charset': 'utf8mb4'
}

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查詢前 10 個不同的 order_group
query = """
    SELECT DISTINCT order_group 
    FROM ordersjb 
    WHERE order_group IS NOT NULL 
    LIMIT 10
"""

cursor.execute(query)
groups = cursor.fetchall()

print("資料庫中的 order_group 範例：")
for i, row in enumerate(groups, 1):
    print(f"{i}. {row['order_group']}")

# 查詢特定 group
test_group = "Group202510010056605011"
query2 = "SELECT COUNT(*) as cnt FROM ordersjb WHERE order_group = %s"
cursor.execute(query2, (test_group,))
result = cursor.fetchone()
print(f"\n查詢 '{test_group}': {result['cnt']} 筆")

# 模糊查詢
query3 = "SELECT DISTINCT order_group FROM ordersjb WHERE order_group LIKE %s LIMIT 5"
cursor.execute(query3, (f"%202510010056605011%",))
similar = cursor.fetchall()
print(f"\n類似的 order_group:")
for row in similar:
    print(f"  - {row['order_group']}")

cursor.close()
conn.close()

