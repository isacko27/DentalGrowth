#!/bin/bash
cd /app/agentes
python3 clickup_manager.py &
python3 transcriber.py &
python3 copy_content.py &
python3 community_manager.py &
python3 dashboard.py
