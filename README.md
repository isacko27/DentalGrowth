# DentalGrowth

Multi-agent AI dashboard for Dental Growth marketing agency.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 8000 | Central control panel + chat orchestrator |
| ClickUp Manager | 8001 | ClickUp workspace management |
| Transcriber | 8002 | Video transcription (AssemblyAI) |
| Copy Content | 8003 | Instagram copy generation |
| Community Manager | 8004 | Community management |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env
```

## Run

```bash
cd agentes
python3 dashboard.py
python3 clickup_manager.py
python3 transcriber.py
python3 copy_content.py
python3 community_manager.py
```
