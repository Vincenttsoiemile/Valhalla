#!/bin/bash
# Valhalla 停止腳本 - 停止所有服務

echo "🛑 停止 Valhalla 服務..."
echo ""

# 停止 Flask (port 8080)
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "停止 Flask..."
    FLASK_PIDS=$(lsof -Pi :8080 -sTCP:LISTEN -t)
    for PID in $FLASK_PIDS; do
        echo "  終止 PID: $PID"
        kill -9 $PID 2>/dev/null || true
    done
    echo "✅ Flask 已停止"
else
    echo "ℹ️  Flask 未在運行"
fi

echo ""

# 停止 Cloudflare Tunnel
if pgrep -f "cloudflared tunnel.*valhalla" > /dev/null 2>&1 ; then
    echo "停止 Cloudflare Tunnel..."
    TUNNEL_PIDS=$(pgrep -f "cloudflared tunnel.*valhalla")
    for PID in $TUNNEL_PIDS; do
        echo "  終止 PID: $PID"
        kill -9 $PID 2>/dev/null || true
    done
    echo "✅ Cloudflare Tunnel 已停止"
else
    echo "ℹ️  Cloudflare Tunnel 未在運行"
fi

echo ""
echo "════════════════════════════════════════"
echo "✅ 所有服務已停止"
echo "════════════════════════════════════════"


