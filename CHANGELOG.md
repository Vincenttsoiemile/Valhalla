# Valhalla 路徑規劃系統 - 變更日誌

## [v3.9] - 2025-10-21

### 新增功能 ✨
- **設定複製/導入功能**
  - 側邊欄右上角新增 📋 複製設定按鈕
  - 側邊欄右上角新增 📥 導入設定按鈕
  - 支援所有參數的完整複製（起點、終點、優化模式、障礙檢測等）
  - 通過剪貼板實現跨設備、跨平台分享設定

### 改進 🔧
- **用戶體驗優化**
  - 新增視覺反饋通知系統（成功/失敗提示）
  - 優雅的淡入淡出動畫效果
  - 自動消失通知（2秒後）
  - 右上角浮動通知位置

### 技術細節 💻
- **前端更新**
  - `index.html`: 新增側邊欄標題區域和按鈕容器
  - `style.css`: 新增圖標按鈕樣式和通知樣式
  - `app.js`: 實現 `getAllSettings()`, `copySettingsToClipboard()`, `importSettingsFromClipboard()`, `applySettings()`, `showNotification()` 函數
- **支援的設定參數**
  - 起點座標 (startLat, startLon)
  - 終點模式與座標 (endPointMode, endLat, endLon)
  - Order Group
  - 優化模式 (optimizationMode, globalMethod)
  - 分組參數 (maxGroupSize, clusterRadius, minSamples, metric, groupOrderMethod, innerOrderMethod, randomState, nInit)
  - 障礙檢測 (verification, checkHighways, groupPenalty, innerPenalty)
  - 序號顯示模式 (sequenceMode)
  - 路線預加載 (preloadRoutes)

### 使用方式 📖
1. **複製設定**：
   - 配置好所有參數
   - 點擊右上角 📋 按鈕
   - 設定已自動複製到剪貼板（JSON 格式）

2. **分享設定**：
   - 將剪貼板內容粘貼到任何聊天應用（WhatsApp、Telegram、Email 等）
   - 發送給團隊成員

3. **導入設定**：
   - 從聊天應用複製收到的設定內容
   - 點擊右上角 📥 按鈕
   - 所有參數自動應用到界面

### 相關文件 📁
- `/static/index.html` (line 60-66)
- `/static/style.css` (line 27-73, 1076-1107)
- `/static/app.js` (line 835-1027, 1825-1834)
- `README.md` (line 902-922)

---

## 歷史版本

詳細歷史變更請參考 [README.md](./README.md#更新記錄)
