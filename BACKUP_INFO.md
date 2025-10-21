# Valhalla 專案備份資訊

## 最新備份

**備份文件**: `/Users/vincent/Desktop/MyDev/Valhalla_backup_20251003_155638.tar.gz`
**備份時間**: 2025-10-03 15:56:38
**備份大小**: 63 MB

## 備份內容

包含的文件：
- ✅ 所有 Python 源代碼 (.py)
- ✅ 前端文件 (HTML, CSS, JS)
- ✅ 配置文件 (.yml, .json)
- ✅ README.md 和文檔
- ✅ 河流和高速公路數據 (rivers_data.json, highways_data.json)

排除的文件：
- ❌ venv/ (虛擬環境)
- ❌ .git/ (Git 版本控制)
- ❌ __pycache__/ (Python 緩存)
- ❌ *.pyc (編譯文件)

## 恢復方法

如果需要恢復備份：

```bash
# 1. 解壓備份文件
cd /Users/vincent/Desktop/MyDev
tar -xzf Valhalla_backup_20251003_155638.tar.gz

# 2. 重新創建虛擬環境
cd Valhalla
python -m venv venv
source venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動應用
python app.py
```

## 變更記錄（此備份後的修改）

### 2025-10-21
- [ ] 準備合併溫哥華和多倫多的河流/高速公路數據
- [ ] 修改 river_detection.py 支援多地區數據

## 備份策略建議

**何時創建備份：**
- 重大功能修改前
- 修改核心算法前
- 更新數據文件前
- 部署到生產環境前

**備份命令：**
```bash
cd /Users/vincent/Desktop/MyDev
tar -czf "Valhalla_backup_$(date +%Y%m%d_%H%M%S).tar.gz" \
  --exclude='Valhalla/venv' \
  --exclude='Valhalla/.git' \
  --exclude='Valhalla/__pycache__' \
  --exclude='*.pyc' \
  Valhalla/
```

## 重要數據文件

這些文件特別重要，修改前務必備份：
- `rivers_data.json` (63 MB) - 溫哥華地區河流數據
- `highways_data.json` - 溫哥華地區高速公路數據
- `app.py` - 主要後端邏輯
- `river_detection.py` - 障礙檢測邏輯
- `static/app.js` - 前端主要邏輯

---

**最後更新**: 2025-10-21
