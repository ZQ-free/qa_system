.PHONY: help install install-venv run stop status logs clean image-build

PROJECT_ROOT := $(shell pwd)
BACKEND_DIR := $(PROJECT_ROOT)/qa_system
FRONTEND_DIR := $(PROJECT_ROOT)/chat-web
BACKEND_PID_FILE := $(PROJECT_ROOT)/.backend.pid
FRONTEND_PID_FILE := $(PROJECT_ROOT)/.frontend.pid
VENV_DIR := $(BACKEND_DIR)/.venv
IMAGE_NAME := qa-backend
IMAGE_TAG := latest
SOURCE_DIR := $(PROJECT_ROOT)/source

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies (use existing venv or system pip)"
	@echo "  make install-venv   - Create venv and install dependencies"
	@echo "  make run            - Start both backend and frontend"
	@echo "  make stop           - Stop backend and frontend"
	@echo "  make status         - Show running status"
	@echo "  make logs           - Show recent logs"
	@echo "  make clean          - Clean up cache files"
	@echo "  make image-build    - Build Docker image and export to source/"

install:
	@echo "Installing backend dependencies..."
	@cd $(BACKEND_DIR) && pip install -r requirements.txt --break-system-packages -q 2>/dev/null || pip install -r requirements.txt -q
	@echo "Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && npm install -q
	@echo "Install complete."

install-venv:
	@echo "Creating virtual environment..."
	@cd $(BACKEND_DIR) && python3 -m venv .venv
	@echo "Installing backend dependencies..."
	@$(VENV_DIR)/bin/pip install -r $(BACKEND_DIR)/requirements.txt -q
	@echo "Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && npm install -q
	@echo "Install complete. Use 'make run' to start services."

run: stop
	@echo "Starting backend (port 8000)..."
	@if [ -d "$(VENV_DIR)" ]; then \
		cd $(BACKEND_DIR) && nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > $(PROJECT_ROOT)/.backend.log 2>&1 & \
		echo $$! > $(BACKEND_PID_FILE); \
	else \
		cd $(BACKEND_DIR) && nohup uvicorn main:app --host 0.0.0.0 --port 8000 > $(PROJECT_ROOT)/.backend.log 2>&1 & \
		echo $$! > $(BACKEND_PID_FILE); \
	fi
	@echo "Starting frontend (port 5173)..."
	@cd $(FRONTEND_DIR) && nohup npm run dev -- --port 5173 --host 0.0.0.0 > $(PROJECT_ROOT)/.frontend.log 2>&1 &
	@echo $$! > $(FRONTEND_PID_FILE)
	@sleep 4
	@echo "Services started."
	@echo "  Backend: http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"

stop:
	@echo "Stopping services..."
	@if [ -f $(BACKEND_PID_FILE) ]; then \
		kill $$(cat $(BACKEND_PID_FILE)) 2>/dev/null || true; \
		rm -f $(BACKEND_PID_FILE); \
	fi
	@ps aux | grep -E "node.*vite|uvicorn.*main" | grep -v grep | awk '{print $$2}' | xargs kill 2>/dev/null || true
	@echo "Services stopped."

status:
	@echo "=== Service Status ==="
	@echo ""
	@echo "Backend (port 8000):"
	@if ps aux | grep -E "uvicorn.*main:app" | grep -v grep | grep -q .; then \
		echo "  Status: RUNNING"; \
		echo "  PID: $$(ps aux | grep 'uvicorn.*main:app' | grep -v grep | awk '{print $$2}' | head -1)"; \
	else \
		echo "  Status: STOPPED"; \
	fi
	@echo ""
	@echo "Frontend (port 5173):"
	@if ps aux | grep -E "node.*vite" | grep -v grep | grep -q .; then \
		echo "  Status: RUNNING"; \
		echo "  PID: $$(ps aux | grep 'node.*vite' | grep -v grep | awk '{print $$2}' | head -1)"; \
	else \
		echo "  Status: STOPPED"; \
	fi
	@echo ""
	@echo "URLs:"
	@echo "  Backend API: http://localhost:8000"
	@echo "  Frontend:    http://localhost:5173"

logs:
	@echo "=== Backend Log (last 20 lines) ==="
	@tail -n 20 $(PROJECT_ROOT)/.backend.log 2>/dev/null || echo "(no log)"
	@echo ""
	@echo "=== Frontend Log (last 20 lines) ==="
	@tail -n 20 $(PROJECT_ROOT)/.frontend.log 2>/dev/null || echo "(no log)"

clean:
	@echo "Cleaning cache files..."
	@rm -f $(BACKEND_PID_FILE) $(FRONTEND_PID_FILE)
	@rm -f $(PROJECT_ROOT)/.backend.log $(PROJECT_ROOT)/.frontend.log
	@cd $(BACKEND_DIR) && rm -rf __pycache__ .pytest_cache .ruff_cache .venv 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."

image-build:
	@echo "Building Docker image..."
	@mkdir -p $(SOURCE_DIR)
	@cd $(PROJECT_ROOT) && docker build -t $(IMAGE_NAME):$(IMAGE_TAG) -f $(BACKEND_DIR)/Dockerfile $(BACKEND_DIR)
	@echo "Exporting image to $(SOURCE_DIR)/$(IMAGE_NAME)-$(IMAGE_TAG).tar..."
	@docker save $(IMAGE_NAME):$(IMAGE_TAG) -o $(SOURCE_DIR)/$(IMAGE_NAME)-$(IMAGE_TAG).tar
	@echo "Image saved: $(SOURCE_DIR)/$(IMAGE_NAME)-$(IMAGE_TAG).tar"
	@echo "Image size: $$(du -h $(SOURCE_DIR)/$(IMAGE_NAME)-$(IMAGE_TAG).tar | cut -f1)"