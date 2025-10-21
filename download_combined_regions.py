#!/usr/bin/env python3
"""下載並合併多個地區的河流和高速公路數據"""

import requests
import json
import time

# Overpass API 端點
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# 多地區定義
REGIONS = {
    'vancouver': {
        'name': '大溫哥華地區',
        'bbox': {
            'south': 49.0,
            'west': -123.3,
            'north': 49.4,
            'east': -122.5
        }
    },
    'toronto': {
        'name': '大多倫多地區 (GTA)',
        'bbox': {
            'south': 43.4,
            'west': -79.8,
            'north': 44.0,
            'east': -79.0
        }
    }
}

def download_region_data(region_key, data_type='rivers'):
    """下載單個地區的數據"""
    region = REGIONS[region_key]
    bbox = region['bbox']

    if data_type == 'rivers':
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
        icon = "🌊"
        type_name = "河流"
    else:  # highways
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
        icon = "🛣️"
        type_name = "高速公路"

    print(f"\n{icon} 下載 {region['name']} {type_name}數據...")
    print(f"   範圍: {bbox}")

    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)

        if response.status_code == 200:
            data = response.json()
            ways_count = sum(1 for e in data['elements'] if e['type'] == 'way')
            nodes_count = sum(1 for e in data['elements'] if e['type'] == 'node')

            print(f"   ✅ 成功！")
            print(f"      節點: {nodes_count:,}")
            print(f"      線段: {ways_count:,}")

            return data
        else:
            print(f"   ❌ 失敗: HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        return None

def merge_data(datasets):
    """合併多個地區的數據"""
    merged = {
        'version': 0.6,
        'generator': 'Overpass API + Custom Merger',
        'elements': []
    }

    seen_ids = set()  # 避免重複的元素

    for dataset in datasets:
        if dataset is None:
            continue

        for element in dataset.get('elements', []):
            # 創建唯一ID（類型 + ID）
            unique_id = f"{element['type']}_{element['id']}"

            if unique_id not in seen_ids:
                merged['elements'].append(element)
                seen_ids.add(unique_id)

    return merged

def main():
    print("=" * 70)
    print("🗺️  多地區障礙物數據下載與合併工具")
    print("=" * 70)

    print("\n將下載以下地區的數據：")
    for key, region in REGIONS.items():
        bbox = region['bbox']
        print(f"  ✓ {region['name']}")
        print(f"    經緯度範圍: ({bbox['south']}, {bbox['west']}) 到 ({bbox['north']}, {bbox['east']})")

    print("\n下載內容：")
    print("  ☑️  河流數據 (rivers, streams, canals)")
    print("  ☑️  高速公路數據 (motorways, trunk roads)")

    confirm = input("\n確認下載並合併所有地區數據？ (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return

    # 下載河流數據
    print("\n" + "=" * 70)
    print("第 1 步：下載河流數據")
    print("=" * 70)

    rivers_datasets = []
    for region_key in REGIONS.keys():
        data = download_region_data(region_key, 'rivers')
        if data:
            rivers_datasets.append(data)
        time.sleep(2)  # 避免API限制

    # 合併河流數據
    if rivers_datasets:
        print("\n📦 合併河流數據...")
        merged_rivers = merge_data(rivers_datasets)
        total_elements = len(merged_rivers['elements'])
        print(f"   ✅ 合併完成！總元素數: {total_elements:,}")

        # 保存
        output_file = 'rivers_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_rivers, f, ensure_ascii=False, indent=2)

        file_size = len(json.dumps(merged_rivers)) / 1024 / 1024
        print(f"   💾 已保存到: {output_file}")
        print(f"      檔案大小: {file_size:.2f} MB")

    # 下載高速公路數據
    print("\n" + "=" * 70)
    print("第 2 步：下載高速公路數據")
    print("=" * 70)

    highways_datasets = []
    for region_key in REGIONS.keys():
        data = download_region_data(region_key, 'highways')
        if data:
            highways_datasets.append(data)
        time.sleep(2)  # 避免API限制

    # 合併高速公路數據
    if highways_datasets:
        print("\n📦 合併高速公路數據...")
        merged_highways = merge_data(highways_datasets)
        total_elements = len(merged_highways['elements'])
        print(f"   ✅ 合併完成！總元素數: {total_elements:,}")

        # 保存
        output_file = 'highways_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_highways, f, ensure_ascii=False, indent=2)

        file_size = len(json.dumps(merged_highways)) / 1024 / 1024
        print(f"   💾 已保存到: {output_file}")
        print(f"      檔案大小: {file_size:.2f} MB")

    # 完成
    print("\n" + "=" * 70)
    print("✅ 所有數據下載並合併完成！")
    print("=" * 70)

    print("\n📊 覆蓋地區：")
    for region in REGIONS.values():
        print(f"  ✓ {region['name']}")

    print("\n📝 下一步:")
    print("  1. 重啟 Flask 應用: python app.py")
    print("  2. 系統會自動載入新的合併數據")
    print("  3. 現在溫哥華和多倫多地區都可以使用幾何檢測功能了！")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
