# 多地區數據合併使用指南

## 📋 總覽

此指南說明如何下載並合併多個地區的河流和高速公路數據，讓幾何檢測功能支援更多城市。

---

## ✅ 已完成的備份

**備份文件**: `/Users/vincent/Desktop/MyDev/Valhalla_backup_20251003_155638.tar.gz`
**備份大小**: 63 MB
**備份時間**: 2025-10-03 15:56:38

包含：
- ✅ 所有源代碼
- ✅ 原始溫哥華地區數據
- ✅ 前端文件
- ✅ 配置文件

---

## 🚀 快速開始：下載合併數據

### 方法 1：自動合併（推薦）

```bash
# 下載溫哥華 + 多倫多合併數據
python download_combined_regions.py
```

**執行流程：**
1. 顯示將下載的地區列表
2. 詢問確認
3. 下載溫哥華河流數據（約 1-2 分鐘）
4. 下載多倫多河流數據（約 1-2 分鐘）
5. 合併並保存到 `rivers_data.json`
6. 下載溫哥華高速公路數據
7. 下載多倫多高速公路數據
8. 合併並保存到 `highways_data.json`

**預期輸出：**
```
✅ 所有數據下載並合併完成！

📊 覆蓋地區：
  ✓ 大溫哥華地區
  ✓ 大多倫多地區 (GTA)

📝 下一步:
  1. 重啟 Flask 應用: python app.py
  2. 系統會自動載入新的合併數據
  3. 現在溫哥華和多倫多地區都可以使用幾何檢測功能了！
```

---

### 方法 2：分別下載後手動合併

```bash
# 下載多倫多數據
python download_toronto_rivers.py
python download_toronto_highways.py

# 手動合併（需要自己寫腳本）
# 或直接覆蓋：
mv rivers_data_toronto.json rivers_data.json
mv highways_data_toronto.json highways_data.json
```

---

### 方法 3：互動式選擇單一地區

```bash
python download_obstacles_auto.py
```

選項：
1. 大溫哥華地區
2. 大多倫多地區
3. 自訂範圍

---

## 🌍 添加新地區

### 步驟 1：編輯腳本

打開 `download_combined_regions.py`，找到 `REGIONS` 字典（約第 10 行）：

```python
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
    },
    # 添加新地區：
    'london_uk': {
        'name': '倫敦地區',
        'bbox': {
            'south': 51.3,
            'west': -0.5,
            'north': 51.7,
            'east': 0.3
        }
    }
}
```

### 步驟 2：如何確定邊界範圍 (BBOX)

**方法 A：使用 Google Maps**
1. 打開 Google Maps
2. 右鍵點擊地圖 → 「這是哪裡？」
3. 查看座標（例如：43.6532, -79.3832）
4. 找出你要覆蓋區域的四個角：
   - 左下角 (south, west)
   - 右上角 (north, east)

**方法 B：使用 OpenStreetMap**
1. 訪問 https://www.openstreetmap.org/
2. 縮放到目標區域
3. 點擊右側「分享」圖標
4. 查看 URL 中的 bbox 參數

**方法 C：城市範圍參考**
```python
# 主要城市建議範圍（±0.3-0.5 度）

# 加拿大
'montreal': {'south': 45.3, 'west': -73.8, 'north': 45.7, 'east': -73.4}
'ottawa': {'south': 45.2, 'west': -75.9, 'north': 45.6, 'east': -75.5}
'calgary': {'south': 50.8, 'west': -114.3, 'north': 51.2, 'east': -113.9}

# 美國
'new_york': {'south': 40.5, 'west': -74.3, 'north': 40.9, 'east': -73.7}
'los_angeles': {'south': 33.7, 'west': -118.7, 'north': 34.3, 'east': -118.1}

# 英國
'london': {'south': 51.3, 'west': -0.5, 'north': 51.7, 'east': 0.3}

# 澳洲
'sydney': {'south': -34.0, 'west': 150.9, 'north': -33.7, 'east': 151.3}
```

### 步驟 3：執行下載

```bash
python download_combined_regions.py
```

---

## 📊 數據大小估算

| 地區 | 河流數據 | 高速公路數據 | 合計 |
|------|---------|-------------|------|
| 溫哥華 | ~63 MB | ~3 MB | ~66 MB |
| 多倫多 | ~15 MB | ~5 MB | ~20 MB |
| **合併** | **~78 MB** | **~8 MB** | **~86 MB** |

**Note**: 實際大小取決於該地區的河流和公路密度

---

## ⚙️ 系統要求

- Python 3.8+
- 網絡連接
- 硬碟空間：每個地區約 20-70 MB
- Overpass API 限制：
  - 超時時間：300 秒（5 分鐘）
  - 建議在請求之間等待 2-3 秒

---

## 🔧 故障排除

### 問題 1：下載超時

```
❌ 請求超時，請稍後再試
```

**解決方法：**
- 減小 BBOX 範圍（縮小覆蓋區域）
- 等待幾分鐘後重試
- 或使用方法 2 分別下載

### 問題 2：數據為空

```
✅ 合併完成！總元素數: 0
```

**可能原因：**
- BBOX 範圍內沒有河流/高速公路
- 座標順序錯誤（south > north 或 west > east）
- Overpass API 暫時故障

**檢查：**
```python
# 確保：
south < north  # 例如：43.4 < 44.0 ✓
west < east    # 例如：-79.8 < -79.0 ✓
```

### 問題 3：合併後應用仍不工作

**檢查清單：**
1. ✅ 確認 `rivers_data.json` 和 `highways_data.json` 已更新
2. ✅ 檢查檔案大小（應該比原來大）
3. ✅ 重啟 Flask 應用
4. ✅ 清除瀏覽器緩存
5. ✅ 查看後端日誌是否有載入錯誤

---

## 📝 驗證數據

下載完成後，驗證數據是否正確：

```bash
# 檢查檔案大小
ls -lh rivers_data.json highways_data.json

# 檢查元素數量（應該看到多個地區的數據）
python -c "import json; data=json.load(open('rivers_data.json')); print(f'河流元素: {len(data[\"elements\"]):,}')"
python -c "import json; data=json.load(open('highways_data.json')); print(f'高速公路元素: {len(data[\"elements\"]):,}')"
```

預期輸出：
```
河流元素: 25,000+
高速公路元素: 3,000+
```

---

## 🔄 恢復原始數據

如果需要回退到溫哥華地區數據：

```bash
# 方法 1：從備份恢復
cd /Users/vincent/Desktop/MyDev
tar -xzf Valhalla_backup_20251003_155638.tar.gz Valhalla/rivers_data.json
tar -xzf Valhalla_backup_20251003_155638.tar.gz Valhalla/highways_data.json

# 方法 2：重新下載溫哥華數據
python download_obstacles_auto.py
# 選擇選項 1 (大溫哥華地區)
```

---

## 🎯 測試新地區

下載合併數據後：

1. **重啟應用**
   ```bash
   python app.py
   ```

2. **測試多倫多訂單**
   - 輸入多倫多地區的 Order Group
   - 設定起點在多倫多（例如：43.6532, -79.3832）
   - 選擇「幾何數據檢測」
   - 點擊「計算路徑」

3. **檢查後端日誌**
   應該看到：
   ```
   [INFO] 啟用組內跨河優化（幾何檢測），懲罰係數: 1.5
   [INFO] 載入河流數據: 25000+ 條
   [INFO] 載入高速公路數據: 3000+ 條
   ```

4. **驗證結果**
   - 地圖上應顯示跨越 Don River 或 Humber River 的訂單
   - 有 🌊 圖標的訂單表示跨河

---

## 📞 需要幫助？

如果遇到問題：
1. 查看 `BACKUP_INFO.md` 了解備份位置
2. 檢查後端日誌輸出
3. 確認網絡連接正常
4. 嘗試減小 BBOX 範圍重新下載

---

**最後更新**: 2025-10-21
**版本**: v3.9+
