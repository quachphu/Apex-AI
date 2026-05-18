#!/bin/bash
set -e

APEX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APEX_DIR"

echo ""
echo "  ⬡ APEX — AI Sales Agent"
echo "  YC Call My Agent Hackathon · May 17, 2026"
echo ""

# Check if ngrok is running
if ! curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
  echo "  Starting ngrok tunnel on port 8000..."
  ngrok http 8000 > /tmp/ngrok.log 2>&1 &
  echo "  Waiting for ngrok to start..."
  sleep 4
fi

# Extract ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    for t in tunnels:
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
    else:
        if tunnels:
            print(tunnels[0]['public_url'])
except:
    print('')
" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
  echo "  ⚠️  Could not get ngrok URL. Set WEBHOOK_URL manually in .env"
  echo "     Run: ngrok http 8000"
else
  echo "  ✅ Webhook URL: $NGROK_URL"
  # Update .env with the ngrok URL
  if grep -q "WEBHOOK_URL=" "$APEX_DIR/.env"; then
    sed -i.bak "s|WEBHOOK_URL=.*|WEBHOOK_URL=$NGROK_URL|" "$APEX_DIR/.env"
  else
    echo "WEBHOOK_URL=$NGROK_URL" >> "$APEX_DIR/.env"
  fi
fi

echo ""
echo "  Starting Apex backend on http://localhost:8000 ..."
echo "  Starting Apex frontend on http://localhost:5173 ..."
echo ""

# Start backend in background
cd "$APEX_DIR/backend" && python -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$APEX_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

echo "  ✅ Backend PID: $BACKEND_PID"
echo "  ✅ Frontend PID: $FRONTEND_PID"
echo ""
echo "  🌐 Dashboard: http://localhost:5173"
echo "  🔌 API:       http://localhost:8000"
echo "  📊 Health:    http://localhost:8000/health"
echo ""
echo "  Press Ctrl+C to stop all processes"

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
