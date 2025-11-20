#!/usr/bin/env python3
"""完整測試：模擬前端發送的請求"""

import requests
import json

# 你的配置
config = {
    "start": {"lat": 43.734259, "lon": -79.708525},
    "order_group": "Group202511151924060106",
    "max_group_size": 5,  # 每組最多 5 個訂單
    "cluster_radius": 0.5,
    "min_samples": 3,
    "metric": "euclidean",
    "group_order_method": "greedy",
    "inner_order_method": "ortools",  # 使用 OR-Tools
    "random_state": 42,
    "n_init": 30,
    "verification": "none",
    "check_highways": True,
    "group_penalty": 2.0,
    "inner_penalty": 1.5,
    "end_point_mode": "last_order"
}

print("=" * 60)
print("測試完整配置")
print("=" * 60)
print(f"Order Group: {config['order_group']}")
print(f"Max Group Size: {config['max_group_size']} (每組最多訂單數)")
print(f"Inner Order Method: {config['inner_order_method']}")
print("=" * 60)

try:
    print("\n發送請求到 /api/route...")
    response = requests.post(
        'http://localhost:8080/api/route',
        json=config,
        timeout=120
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ 成功！")
        print(f"總訂單數: {data['total_orders']}")
        print(f"總群組數: {data['total_groups']}")
        print(f"\n前 10 個訂單:")
        for order in data['orders'][:10]:
            print(f"  {order['sequence']:3d}. {order['group_sequence']:6s} - {order['tracking_number']}")
        
        # 統計每組訂單數
        group_sizes = {}
        for order in data['orders']:
            group = order['group']
            group_sizes[group] = group_sizes.get(group, 0) + 1
        
        print(f"\n群組大小統計:")
        max_size = max(group_sizes.values())
        print(f"  最大群組大小: {max_size} (設定限制: {config['max_group_size']})")
        print(f"  群組數量: {len(group_sizes)}")
        
        if max_size <= config['max_group_size']:
            print(f"\n✓ 群組大小限制生效！所有群組 <= {config['max_group_size']}")
        else:
            print(f"\n✗ 警告：有群組超過 {config['max_group_size']} 個訂單")
        
    else:
        print(f"\n✗ 錯誤：HTTP {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n✗ 連接失敗！Flask 服務沒有運行")
    print("\n請先運行：")
    print("  cd /Users/vincent/Desktop/MyDev/Valhalla")
    print("  source venv/bin/activate")
    print("  python app.py")
    
except Exception as e:
    print(f"\n✗ 錯誤：{e}")
    import traceback
    traceback.print_exc()

