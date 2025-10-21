#!/bin/bash
# Valhalla Tunnel 啟動腳本

echo "🚀 啟動 Valhalla 路徑規劃系統..."
echo ""

# 獲取腳本所在目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 檢查 Flask 是否運行
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Flask 已在運行 (port 8080)"
else
    echo "⚠️  Flask 未運行，正在啟動..."
    source venv/bin/activate
    python app.py > flask.log 2>&1 &
    FLASK_PID=$!
    echo "✅ Flask 已啟動 (PID: $FLASK_PID)"
    sleep 2
fi

# 檢查 Cloudflare Tunnel 是否運行
if pgrep -f "cloudflared tunnel" > /dev/null ; then
    echo "✅ Cloudflare Tunnel 已在運行"
else
    echo "⚠️  Cloudflare Tunnel 未運行，正在啟動..."
    cloudflared tunnel --config cloudflared-config.yml run valhalla > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    echo "✅ Cloudflare Tunnel 已啟動 (PID: $TUNNEL_PID)"
fi

echo ""
echo "🌐 服務已啟動："
echo "   本地:  http://localhost:8080"
echo "   線上:  https://route.12141214.xyz"
echo ""
echo "📋 日誌位置："
echo "   Flask:  $DIR/flask.log"
echo "   Tunnel: $DIR/tunnel.log"
echo ""
echo "🛑 停止服務: killall python cloudflared"

