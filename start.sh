#!/bin/bash
# Valhalla 啟動腳本 - 啟動所有必要服務

set -e  # 遇到錯誤立即退出

echo "🚀 啟動 Valhalla 路徑規劃系統..."
echo ""

# 獲取腳本所在目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# ==================== 檢查依賴 ====================
if [ ! -d "venv" ]; then
    echo "❌ 錯誤: venv 目錄不存在"
    echo "請先執行: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

if ! command -v cloudflared &> /dev/null; then
    echo "❌ 錯誤: cloudflared 未安裝"
    echo "請先執行: brew install cloudflare/cloudflare/cloudflared"
    exit 1
fi

# ==================== 啟動 Flask ====================
echo "📡 檢查 Flask 狀態..."
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    FLASK_PID=$(lsof -Pi :8080 -sTCP:LISTEN -t | head -1)
    echo "✅ Flask 已在運行 (PID: $FLASK_PID)"
else
    echo "⚠️  Flask 未運行，正在啟動..."
    source venv/bin/activate
    nohup python app.py > flask.log 2>&1 &
    FLASK_PID=$!
    
    # 等待 Flask 啟動
    echo "   等待 Flask 啟動..."
    sleep 3
    
    # 驗證是否成功啟動
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "✅ Flask 已成功啟動 (PID: $FLASK_PID)"
    else
        echo "❌ Flask 啟動失敗，請查看 flask.log"
        tail -20 flask.log
        exit 1
    fi
fi

# ==================== 啟動 Cloudflare Tunnel ====================
echo ""
echo "🌐 檢查 Cloudflare Tunnel 狀態..."
if pgrep -f "cloudflared tunnel.*valhalla" > /dev/null 2>&1 ; then
    TUNNEL_PID=$(pgrep -f "cloudflared tunnel.*valhalla" | head -1)
    echo "✅ Cloudflare Tunnel 已在運行 (PID: $TUNNEL_PID)"
else
    echo "⚠️  Cloudflare Tunnel 未運行，正在啟動..."
    nohup cloudflared tunnel --config cloudflared-config.yml run valhalla > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    # 等待 Tunnel 連接
    echo "   等待 Tunnel 連接..."
    sleep 5
    
    # 驗證是否成功啟動
    if pgrep -f "cloudflared tunnel.*valhalla" > /dev/null 2>&1 ; then
        echo "✅ Cloudflare Tunnel 已成功啟動 (PID: $TUNNEL_PID)"
    else
        echo "❌ Tunnel 啟動失敗，請查看 tunnel.log"
        tail -20 tunnel.log
        exit 1
    fi
fi

# ==================== 顯示狀態 ====================
echo ""
echo "════════════════════════════════════════"
echo "✅ 所有服務已成功啟動"
echo "════════════════════════════════════════"
echo ""
echo "🌐 訪問網址："
echo "   本地:  http://localhost:8080"
echo "   線上:  https://route.12141214.xyz"
echo ""
echo "📋 日誌位置："
echo "   Flask:  $DIR/flask.log"
echo "   Tunnel: $DIR/tunnel.log"
echo ""
echo "📊 進程狀態："
lsof -Pi :8080 -sTCP:LISTEN 2>/dev/null | grep -v COMMAND || echo "   Flask: 無"
pgrep -f "cloudflared tunnel.*valhalla" -l 2>/dev/null || echo "   Tunnel: 無"
echo ""
echo "🛑 停止服務："
echo "   ./stop.sh"
echo "   或手動: killall python cloudflared"
echo ""
echo "💡 提示: 進程使用 nohup 啟動，關閉終端不會停止服務"
echo "════════════════════════════════════════"


