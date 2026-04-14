#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[INFO] .env not found, created from .env.example"
fi

docker compose up -d --build

echo
echo "[OK] Services are starting."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000/health"
echo "Neo4j:    http://localhost:7474"