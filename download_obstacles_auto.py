#!/usr/bin/env python3
"""自動檢測地區並下載河流和高速公路數據"""

import requests
import json
import sys

# Overpass API 端點
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 預定義地區
REGIONS = {
    'vancouver': {
        'name': '大溫哥華地區',
        'bbox': {
            'south': 49.0,
            'west': -123.3,
            'north': 49.4,
            'east': -122.5
        },
        'rivers': ['Fraser River', 'Pitt River', 'Coquitlam River']
    },
    'toronto': {
        'name': '大多倫多地區 (GTA)',
        'bbox': {
            'south': 43.4,
            'west': -79.8,
            'north': 44.0,
            'east': -79.0
        },
        'rivers': ['Humber River', 'Don River', 'Rouge River']
    },
    'custom': {
        'name': '自訂範圍',
        'bbox': None  # 需要用戶輸入
    }
}

def download_rivers(bbox, region_name):
    """下載河流數據"""
    query = f"""
    [out:json][timeout:300];
    (
      way["waterway"="river"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["waterway"="stream"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["waterway"="canal"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      relation["waterway"="river"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
    );
    out body;
    >;
    out skel qt;
    """

    print(f"\n🌊 下載 {region_name} 河流數據...")
    print(f"範圍: {bbox}")

    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)

        if response.status_code == 200:
            data = response.json()
            ways_count = sum(1 for e in data['elements'] if e['type'] == 'way')

            print(f"✅ 河流數據下載成功！")
            print(f"   河流段數: {ways_count:,}")

            output_file = 'rivers_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

            print(f"💾 已保存到: {output_file}")
            return True
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False

def download_highways(bbox, region_name):
    """下載高速公路數據"""
    query = f"""
    [out:json][timeout:300];
    (
      way["highway"="motorway"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["highway"="trunk"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
      way["highway"="motorway_link"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
    );
    out body;
    >;
    out skel qt;
    """

    print(f"\n🛣️  下載 {region_name} 高速公路數據...")
    print(f"範圍: {bbox}")

    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)

        if response.status_code == 200:
            data = response.json()
            ways_count = sum(1 for e in data['elements'] if e['type'] == 'way')

            print(f"✅ 高速公路數據下載成功！")
            print(f"   道路段數: {ways_count:,}")

            output_file = 'highways_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)

            print(f"💾 已保存到: {output_file}")
            return True
        else:
            print(f"❌ 請求失敗: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False

def main():
    print("=" * 60)
    print("🗺️  障礙物數據下載工具")
    print("=" * 60)
    print("\n請選擇地區:")
    print("1. 大溫哥華地區 (Vancouver)")
    print("2. 大多倫多地區 (Toronto / GTA)")
    print("3. 自訂範圍")

    try:
        choice = input("\n請輸入選項 (1-3): ").strip()

        if choice == '1':
            region = REGIONS['vancouver']
        elif choice == '2':
            region = REGIONS['toronto']
        elif choice == '3':
            print("\n請輸入自訂範圍（經緯度）:")
            south = float(input("  南邊界 (緯度): "))
            north = float(input("  北邊界 (緯度): "))
            west = float(input("  西邊界 (經度): "))
            east = float(input("  東邊界 (經度): "))

            region = {
                'name': '自訂範圍',
                'bbox': {
                    'south': south,
                    'west': west,
                    'north': north,
                    'east': east
                }
            }
        else:
            print("❌ 無效選項")
            return

        print(f"\n已選擇: {region['name']}")
        print("\n下載內容:")
        print("☑️  河流數據 (rivers, streams, canals)")
        print("☑️  高速公路數據 (motorways, trunk roads)")

        confirm = input("\n確認下載？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return

        # 下載數據
        rivers_ok = download_rivers(region['bbox'], region['name'])
        highways_ok = download_highways(region['bbox'], region['name'])

        print("\n" + "=" * 60)
        if rivers_ok and highways_ok:
            print("✅ 所有數據下載完成！")
            print("\n📝 下一步:")
            print("   1. 重啟 Flask 應用 (python app.py)")
            print("   2. 在網頁上選擇「幾何數據檢測」模式")
            print("   3. 系統會自動使用新下載的數據")
        else:
            print("⚠️  部分數據下載失敗，請檢查錯誤訊息")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")

if __name__ == "__main__":
    main()
