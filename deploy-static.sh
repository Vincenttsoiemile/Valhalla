#!/bin/bash

# 部署靜態文件並重啟服務

echo "🚀 開始部署更新..."

# 1. 檢查靜態文件是否存在
if [ ! -f "static/index.html" ]; then
    echo "❌ 錯誤: static/index.html 不存在"
    exit 1
fi

if [ ! -f "static/app.js" ]; then
    echo "❌ 錯誤: static/app.js 不存在"
    exit 1
fi

if [ ! -f "static/style.css" ]; then
    echo "❌ 錯誤: static/style.css 不存在"
    exit 1
fi

echo "✅ 靜態文件檢查完成"

# 2. 提交到 Git（如果需要）
if [ "$1" == "--git" ]; then
    echo "📦 提交到 Git..."
    git add static/
    git add app.py
    git commit -m "更新靜態文件和進度條顯示"
    git push
    echo "✅ Git 推送完成"
fi

# 3. 重啟 Flask 應用
echo "🔄 重啟 Flask 應用..."
./stop.sh
sleep 2
./start.sh

echo ""
echo "✅ 部署完成！"
echo "💡 提示："
echo "   - 已在 app.py 中禁用靜態文件緩存"
echo "   - 瀏覽器訪問時按 Ctrl+Shift+R (Windows/Linux) 或 Cmd+Shift+R (Mac) 強制刷新"
echo "   - 如果仍然看不到更新，清除瀏覽器緩存或使用無痕模式"
echo ""
echo "🌐 本地測試: http://localhost:8080"
echo "🌐 部署網址: https://your-domain.com (記得也要在伺服器上執行此腳本)"

