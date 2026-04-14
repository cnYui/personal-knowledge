@echo off
setlocal

if not exist .env (
  copy .env.example .env >nul
  echo [INFO] .env not found, created from .env.example
)

docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] docker compose up failed
  exit /b 1
)

echo.
echo [OK] Services are starting.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000/health
echo Neo4j:    http://localhost:7474