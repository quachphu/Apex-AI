.PHONY: install run-backend run-frontend tunnel dev

install:
	pip install -r requirements.txt
	cd frontend && npm install

run-backend:
	cd backend && python -m uvicorn main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

tunnel:
	@echo "Starting localtunnel (no auth required)..."
	npx localtunnel --port 8000

tunnel-ngrok:
	@echo "Fix ngrok auth: ngrok config add-authtoken YOUR_TOKEN"
	@echo "Get token at: https://dashboard.ngrok.com/get-started/your-authtoken"
	ngrok http 8000

dev:
	@echo "Open 3 terminals:"
	@echo "  Terminal 1: make tunnel       (localtunnel — no auth needed)"
	@echo "  Terminal 2: make run-backend"
	@echo "  Terminal 3: make run-frontend"
	@echo ""
	@echo "Then copy the tunnel URL into .env as WEBHOOK_URL="
	@echo "Then open: http://localhost:5173"
