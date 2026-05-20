#!/bin/bash
set -e
cd /app/agentes

# Levantar agentes en background
python3 clickup_manager.py &
python3 transcriber.py &
python3 copy_content.py &
python3 community_manager.py &

# Esperar a que los agentes inicien
sleep 5

# Verificar que estén corriendo
echo "=== Estado de agentes ==="
curl -sf http://localhost:8001/ && echo " OK"
curl -sf http://localhost:8002/ && echo " OK"
curl -sf http://localhost:8003/ && echo " OK"
curl -sf http://localhost:8004/ && echo " OK"
echo "========================="

# Dashboard en foreground (proceso principal)
exec python3 dashboard.py
