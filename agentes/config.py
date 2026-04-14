"""
Configuración compartida para todos los agentes de Dental Growth.
"""
import os
from pathlib import Path

# Cargar .env desde la raíz del proyecto
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# API Keys (configurar como variables de entorno)
CLICKUP_API_KEY = os.environ.get("CLICKUP_API_KEY", "")
ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Puertos de cada agente
CLICKUP_MANAGER_PORT = int(os.environ.get("CLICKUP_MANAGER_PORT", 8001))
TRANSCRIBER_PORT = int(os.environ.get("TRANSCRIBER_PORT", 8002))
COPY_CONTENT_PORT = int(os.environ.get("COPY_CONTENT_PORT", 8003))
COMMUNITY_MANAGER_PORT = int(os.environ.get("COMMUNITY_MANAGER_PORT", 8004))

# URLs internas de los agentes
CLICKUP_MANAGER_URL = f"http://localhost:{CLICKUP_MANAGER_PORT}"
TRANSCRIBER_URL = f"http://localhost:{TRANSCRIBER_PORT}"
COPY_CONTENT_URL = f"http://localhost:{COPY_CONTENT_PORT}"
COMMUNITY_MANAGER_URL = f"http://localhost:{COMMUNITY_MANAGER_PORT}"

# Meta / Facebook OAuth
META_APP_ID = os.environ.get("META_APP_ID", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
META_REDIRECT_URI = os.environ.get("META_REDIRECT_URI", "https://localhost:8000/auth/callback")

# Instagram API (Instagram Login flow)
IG_APP_ID = os.environ.get("IG_APP_ID", "")
IG_APP_SECRET = os.environ.get("IG_APP_SECRET", "")
