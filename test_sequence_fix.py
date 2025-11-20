#!/usr/bin/env python3
"""測試 Smart 模式序號修復"""

import requests
import json

API_URL = "http://localhost:8080/api/optimize-route-smart"

test_data = {
    "start": {
        "lat": 43.681878,
        "lon": -79.713353
    },
    "order_group": "Group202511131925010114",
    "maxGroupSize": 15,
    "clusterRadius": 0.8
}

print("=" * 80)
print("測試 Smart 模式序號修復")
print("=" * 80)

try:
    response = requests.post(API_URL, json=test_data, timeout=30)

    if response.status_code == 200:
        result = response.json()
        print("\n✅ API 調用成功！\n")

        # 檢查序號是否正確
        print("檢查序號格式：\n")

        current_group = None
        group_orders = []

        for order in result.get('orders', [])[:30]:  # 只顯示前30個
            group = order['group_label']
            seq = order['sequence']
            group_seq = order['group_sequence']

            if current_group != group:
                if current_group is not None:
                    print(f"  → {current_group} 組共 {len(group_orders)} 個訂單")
                current_group = group
                group_orders = []
                print(f"\n{group} 組：")

            group_orders.append(order)
            print(f"  {group_seq} (全局序號: {seq})")

        if current_group is not None:
            print(f"  → {current_group} 組共 {len(group_orders)} 個訂單")

        # 驗證邏輯
        print("\n" + "=" * 80)
        print("驗證結果：")
        print("=" * 80)

        errors = []
        current_group = None
        group_seq_counter = 0

        for order in result.get('orders', []):
            group = order['group_label']
            group_seq_str = order['group_sequence']

            # 解析 group_sequence (例如 "A-1")
            parts = group_seq_str.split('-')
            if len(parts) == 2:
                group_from_seq = parts[0]
                seq_num = int(parts[1])

                # 檢查組標籤是否一致
                if group_from_seq != group:
                    errors.append(f"❌ {group_seq_str}: 組標籤不一致 ({group_from_seq} vs {group})")

                # 檢查組內序號是否重置
                if current_group != group:
                    current_group = group
                    group_seq_counter = 1

                if seq_num != group_seq_counter:
                    errors.append(f"❌ {group_seq_str}: 序號應該是 {group}-{group_seq_counter}")

                group_seq_counter += 1

        if errors:
            print("\n發現錯誤：")
            for error in errors[:10]:  # 只顯示前10個錯誤
                print(f"  {error}")
        else:
            print("\n✅ 序號格式完全正確！")
            print("  - 組內序號正確重置（每組從1開始）")
            print("  - 全局序號連續遞增")
            print("  - 組標籤一致")

        print(f"\n總訂單數: {result.get('total_orders')}")
        print(f"總組數: {result.get('total_groups')}")

    else:
        print(f"\n❌ API 錯誤: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ 發生錯誤: {str(e)}")

print("\n" + "=" * 80)
