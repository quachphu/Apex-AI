#!/bin/bash
# ─── Apex Tunnel Helper ─────────────────────────────────────────────
# Starts a public HTTPS tunnel to localhost:8000 and updates .env
# Usage: ./tunnel.sh [ngrok|lt]  (default: tries ngrok, falls back to lt)

APEX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$APEX_DIR/.env"
METHOD="${1:-auto}"

update_env() {
  local url="$1"
  if grep -q "^WEBHOOK_URL=" "$ENV_FILE"; then
    sed -i.bak "s|^WEBHOOK_URL=.*|WEBHOOK_URL=$url|" "$ENV_FILE"
  else
    echo "WEBHOOK_URL=$url" >> "$ENV_FILE"
  fi
  echo "✅ WEBHOOK_URL set to: $url"
  echo "   (saved to .env)"
}

start_localtunnel() {
  echo "Starting localtunnel on port 8000..."
  echo "Note: First visit to the URL requires clicking 'Continue' once."
  echo ""
  LT_URL=$(npx localtunnel --port 8000 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
  if [ -n "$LT_URL" ]; then
    update_env "$LT_URL"
  else
    # Start in foreground and parse output
    npx localtunnel --port 8000 &
    sleep 3
    LT_URL=$(curl -s http://localhost:4040/api/ 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('url',''))" 2>/dev/null)
    [ -n "$LT_URL" ] && update_env "$LT_URL"
  fi
}

start_ngrok() {
  echo "Starting ngrok on port 8000..."
  ngrok http 8000 > /dev/null 2>&1 &
  sleep 3
  NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels', []):
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
except: pass
" 2>/dev/null)
  if [ -n "$NGROK_URL" ]; then
    update_env "$NGROK_URL"
    echo ""
    echo "ngrok dashboard: http://localhost:4040"
  else
    echo "❌ ngrok failed. If you see an auth error, fix it:"
    echo "   1. Go to: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "   2. Run:   ngrok config add-authtoken YOUR_NEW_TOKEN"
    echo "   3. Re-run this script"
    echo ""
    echo "Falling back to localtunnel..."
    start_localtunnel
  fi
}

echo ""
echo "  ⬡ APEX Tunnel Helper"
echo ""

if [ "$METHOD" = "lt" ] || [ "$METHOD" = "localtunnel" ]; then
  start_localtunnel
elif [ "$METHOD" = "ngrok" ]; then
  start_ngrok
else
  # Auto: try ngrok first, fall back to lt
  if command -v ngrok &> /dev/null; then
    start_ngrok
    if [ -z "$NGROK_URL" ]; then
      start_localtunnel
    fi
  elif command -v npx &> /dev/null; then
    start_localtunnel
  else
    echo "❌ Neither ngrok nor npx found."
    echo "   Install either: https://ngrok.com/download OR npm install -g localtunnel"
    exit 1
  fi
fi
