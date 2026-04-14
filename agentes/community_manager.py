"""
Community Manager — Dental Growth
===================================
Agente IA + Servicio API para gestionar cuentas de Instagram de los clientes.

- Panel web en /panel para agregar cuentas, meter códigos, ver estado
- API REST para que otros agentes suban videos, eliminen posts, etc.
- Todo visual, sin necesidad de escribir código

Puerto: 8004
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from instagrapi import Client
from pathlib import Path
import json
import os
import time
import threading
import uvicorn

app = FastAPI(title="Community Manager — Dental Growth", version="2.0")

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
SESIONES_DIR = os.path.join(AGENTS_DIR, "sesiones_ig")
CLIENTES_FILE = os.path.join(AGENTS_DIR, "clientes_ig.json")
os.makedirs(SESIONES_DIR, exist_ok=True)

# Códigos de verificación pendientes
pending_codes = {}
# Clientes de Instagram activos (username → instagrapi.Client)
active_clients = {}
# Estado de login en progreso
login_status = {}


# ============================================================
# GESTIÓN DE CLIENTES
# ============================================================

def _load_clientes():
    if os.path.exists(CLIENTES_FILE):
        with open(CLIENTES_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_clientes(clientes):
    with open(CLIENTES_FILE, "w") as f:
        json.dump(clientes, f, indent=2, ensure_ascii=False)


def _session_path(username):
    return os.path.join(SESIONES_DIR, f"{username}.json")


def _challenge_handler(username, choice):
    choice_name = "email" if choice == 1 else "SMS"
    pending_codes[username] = {
        "choice": choice_name,
        "code": None,
        "timestamp": time.time()
    }
    login_status[username] = f"needs_code_{choice_name}"

    for _ in range(60):
        if pending_codes[username]["code"]:
            code = pending_codes[username]["code"]
            del pending_codes[username]
            return code
        time.sleep(5)

    del pending_codes[username]
    raise Exception(f"Timeout esperando código para {username}")


def _login_in_background(username, password):
    """Ejecuta el login en un thread separado para no bloquear el panel."""
    login_status[username] = "logging_in"
    cl = Client()
    cl.delay_range = [1, 3]
    cl.challenge_code_handler = _challenge_handler

    session = Path(_session_path(username))
    try:
        if session.exists():
            cl.load_settings(session)
            cl.login(username, password)
            cl.account_info()
        else:
            cl.login(username, password)
        cl.dump_settings(session)
        active_clients[username] = cl
        login_status[username] = "connected"
    except Exception as e:
        try:
            cl.login(username, password, relogin=True)
            cl.dump_settings(session)
            active_clients[username] = cl
            login_status[username] = "connected"
        except Exception as e2:
            login_status[username] = f"error: {str(e2)[:100]}"


def _get_client(username: str) -> Client:
    if username in active_clients:
        return active_clients[username]

    clientes = _load_clientes()
    if username not in clientes:
        raise HTTPException(status_code=404, detail=f"Cliente '{username}' no registrado.")

    password = clientes[username]["password"]
    cl = Client()
    cl.delay_range = [1, 3]
    cl.challenge_code_handler = _challenge_handler

    session = Path(_session_path(username))
    try:
        if session.exists():
            cl.load_settings(session)
            cl.login(username, password)
            cl.account_info()
        else:
            cl.login(username, password)
        cl.dump_settings(session)
    except Exception:
        try:
            cl.login(username, password, relogin=True)
            cl.dump_settings(session)
        except Exception as e2:
            raise HTTPException(status_code=401, detail=str(e2)[:200])

    active_clients[username] = cl
    return cl


# ============================================================
# PANEL WEB
# ============================================================

PANEL_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Community Manager — Dental Growth</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 800px; margin: 0 auto; padding: 20px; }
  h1 { text-align: center; margin: 20px 0; font-size: 24px; }
  h1 span { color: #E1306C; }
  .card { background: #1a1a1a; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #333; }
  .card h2 { font-size: 18px; margin-bottom: 16px; color: #fff; }
  label { display: block; margin-bottom: 4px; font-size: 13px; color: #999; }
  input, select { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 14px; margin-bottom: 12px; }
  input:focus { outline: none; border-color: #E1306C; }
  button { padding: 10px 20px; border-radius: 8px; border: none; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .btn-primary { background: #E1306C; color: #fff; width: 100%; }
  .btn-primary:hover { background: #c02060; }
  .btn-small { padding: 6px 14px; font-size: 12px; background: #333; color: #ddd; margin-left: 8px; }
  .btn-small:hover { background: #444; }
  .btn-danger { background: #c0392b; color: #fff; }
  .btn-connect { background: #27ae60; color: #fff; }
  .status { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .status-connected { background: #27ae6033; color: #2ecc71; }
  .status-disconnected { background: #e74c3c33; color: #e74c3c; }
  .status-logging { background: #f39c1233; color: #f1c40f; }
  .status-code { background: #9b59b633; color: #bb6bd9; }
  .client-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2a2a2a; }
  .client-row:last-child { border-bottom: none; }
  .client-info { flex: 1; }
  .client-name { font-weight: 600; color: #fff; }
  .client-user { font-size: 13px; color: #888; }
  .actions { display: flex; gap: 6px; align-items: center; }
  .msg { padding: 10px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; }
  .msg-success { background: #27ae6022; color: #2ecc71; border: 1px solid #27ae6044; }
  .msg-error { background: #e74c3c22; color: #e74c3c; border: 1px solid #e74c3c44; }
  .msg-info { background: #3498db22; color: #3498db; border: 1px solid #3498db44; }
  .code-section { display: none; margin-top: 12px; padding-top: 12px; border-top: 1px solid #333; }
  .code-section.active { display: block; }
  #refreshing { font-size: 12px; color: #666; text-align: center; margin-top: 10px; }
</style>
</head>
<body>
<div class="container">
  <h1>📱 <span>Community Manager</span> — Dental Growth</h1>

  <!-- Mensajes -->
  <div id="messages"></div>

  <!-- Agregar cuenta -->
  <div class="card">
    <h2>➕ Agregar cuenta de Instagram</h2>
    <label>Usuario de Instagram</label>
    <input type="text" id="new-username" placeholder="@usuario (sin el @)">
    <label>Contraseña</label>
    <input type="password" id="new-password" placeholder="Contraseña de Instagram">
    <label>Nombre del negocio (opcional)</label>
    <input type="text" id="new-negocio" placeholder="Ej: Smile Pro, Dentium...">
    <button class="btn-primary" onclick="agregarCuenta()">Agregar e iniciar sesión</button>
  </div>

  <!-- Código de verificación -->
  <div class="card" id="code-card" style="display:none;">
    <h2>🔐 Código de verificación requerido</h2>
    <div id="code-info" class="msg msg-info"></div>
    <label>Código de verificación</label>
    <input type="text" id="verify-code" placeholder="Ingresá el código que recibiste">
    <input type="hidden" id="verify-username">
    <button class="btn-primary" onclick="enviarCodigo()">Enviar código</button>
  </div>

  <!-- Cuentas conectadas -->
  <div class="card">
    <h2>📋 Cuentas registradas</h2>
    <div id="clients-list">Cargando...</div>
  </div>

  <div id="refreshing">Se actualiza automáticamente cada 3 segundos</div>
</div>

<script>
const API = '';

function showMsg(text, type='success') {
  const el = document.getElementById('messages');
  el.innerHTML = `<div class="msg msg-${type}">${text}</div>`;
  setTimeout(() => el.innerHTML = '', 5000);
}

async function agregarCuenta() {
  const username = document.getElementById('new-username').value.trim().replace('@','');
  const password = document.getElementById('new-password').value;
  const negocio = document.getElementById('new-negocio').value.trim();

  if (!username || !password) { showMsg('Completá usuario y contraseña', 'error'); return; }

  try {
    const r = await fetch(API + '/cliente/agregar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, password, nombre_negocio: negocio || username})
    });
    const data = await r.json();
    if (data.success) {
      showMsg(`Cuenta @${username} agregada. Iniciando sesión...`, 'info');
      document.getElementById('new-username').value = '';
      document.getElementById('new-password').value = '';
      document.getElementById('new-negocio').value = '';
      // Iniciar login
      await fetch(API + '/login/async', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username})
      });
      refreshClients();
    }
  } catch(e) { showMsg('Error: ' + e.message, 'error'); }
}

async function enviarCodigo() {
  const username = document.getElementById('verify-username').value;
  const code = document.getElementById('verify-code').value.trim();
  if (!code) { showMsg('Ingresá el código', 'error'); return; }

  try {
    const r = await fetch(API + '/challenge/codigo', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, code})
    });
    const data = await r.json();
    showMsg(`Código enviado para @${username}. Verificando...`, 'info');
    document.getElementById('code-card').style.display = 'none';
    document.getElementById('verify-code').value = '';
  } catch(e) { showMsg('Error enviando código: ' + e.message, 'error'); }
}

async function conectar(username) {
  try {
    await fetch(API + '/login/async', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username})
    });
    showMsg(`Conectando @${username}...`, 'info');
  } catch(e) { showMsg('Error: ' + e.message, 'error'); }
}

async function eliminar(username) {
  if (!confirm(`¿Eliminar la cuenta @${username}?`)) return;
  try {
    await fetch(API + `/cliente/${username}`, {method: 'DELETE'});
    showMsg(`@${username} eliminada`, 'success');
    refreshClients();
  } catch(e) { showMsg('Error: ' + e.message, 'error'); }
}

async function refreshClients() {
  try {
    const [clientsR, statusR, challengeR] = await Promise.all([
      fetch(API + '/clientes'),
      fetch(API + '/login/status'),
      fetch(API + '/challenge/pendiente')
    ]);
    const clients = await clientsR.json();
    const statuses = await statusR.json();
    const challenges = await challengeR.json();

    const list = document.getElementById('clients-list');
    const usernames = Object.keys(clients);

    if (usernames.length === 0) {
      list.innerHTML = '<p style="color:#666;text-align:center;padding:20px;">No hay cuentas registradas. Agregá una arriba.</p>';
      return;
    }

    let html = '';
    for (const u of usernames) {
      const c = clients[u];
      const st = statuses[u] || 'disconnected';
      let statusHtml, actionsHtml;

      if (st === 'connected') {
        statusHtml = '<span class="status status-connected">Conectado</span>';
        actionsHtml = `<button class="btn-small btn-danger" onclick="eliminar('${u}')">Eliminar</button>`;
      } else if (st === 'logging_in') {
        statusHtml = '<span class="status status-logging">Conectando...</span>';
        actionsHtml = '';
      } else if (st.startsWith('needs_code')) {
        statusHtml = '<span class="status status-code">Necesita código</span>';
        actionsHtml = `<button class="btn-small btn-danger" onclick="eliminar('${u}')">Eliminar</button>`;
        // Mostrar sección de código
        const ch = challenges[u];
        if (ch) {
          document.getElementById('code-card').style.display = 'block';
          document.getElementById('code-info').textContent =
            `Instagram envió un código por ${ch.choice} a la cuenta @${u}. Ingresalo abajo.`;
          document.getElementById('verify-username').value = u;
        }
      } else if (st.startsWith('error')) {
        statusHtml = `<span class="status status-disconnected" title="${st}">Error</span>`;
        actionsHtml = `<button class="btn-small btn-connect" onclick="conectar('${u}')">Reintentar</button>
                       <button class="btn-small btn-danger" onclick="eliminar('${u}')">Eliminar</button>`;
      } else {
        statusHtml = '<span class="status status-disconnected">Desconectado</span>';
        actionsHtml = `<button class="btn-small btn-connect" onclick="conectar('${u}')">Conectar</button>
                       <button class="btn-small btn-danger" onclick="eliminar('${u}')">Eliminar</button>`;
      }

      html += `
        <div class="client-row">
          <div class="client-info">
            <div class="client-name">${c.nombre_negocio || u}</div>
            <div class="client-user">@${u} ${statusHtml}</div>
          </div>
          <div class="actions">${actionsHtml}</div>
        </div>`;
    }
    list.innerHTML = html;

    // Ocultar código si no hay challenges
    if (Object.keys(challenges).length === 0) {
      document.getElementById('code-card').style.display = 'none';
    }

  } catch(e) { console.error('Error refreshing:', e); }
}

// Auto-refresh
setInterval(refreshClients, 3000);
refreshClients();
</script>
</body>
</html>"""


@app.get("/panel", response_class=HTMLResponse)
def panel():
    """Panel web para gestionar cuentas de Instagram."""
    return PANEL_HTML


@app.get("/login/status")
def login_statuses():
    """Estado de login de todas las cuentas."""
    clientes = _load_clientes()
    result = {}
    for username in clientes:
        if username in active_clients:
            result[username] = "connected"
        elif username in login_status:
            result[username] = login_status[username]
        else:
            result[username] = "disconnected"
    return result


class LoginAsyncRequest(BaseModel):
    username: str

@app.post("/login/async")
def login_async(req: LoginAsyncRequest):
    """Inicia login en background (no bloquea). Verificar estado con /login/status."""
    clientes = _load_clientes()
    if req.username not in clientes:
        raise HTTPException(status_code=404, detail="Cliente no registrado")

    password = clientes[req.username]["password"]
    thread = threading.Thread(target=_login_in_background, args=(req.username, password))
    thread.start()
    return {"success": True, "message": f"Login iniciado para @{req.username}"}


# ============================================================
# MODELOS
# ============================================================

class AgregarClienteRequest(BaseModel):
    username: str
    password: str
    nombre_negocio: Optional[str] = None

class LoginRequest(BaseModel):
    username: str

class VerificationCodeRequest(BaseModel):
    username: str
    code: str

class SubirReelRequest(BaseModel):
    username: str
    video_path: str
    caption: str
    thumbnail_path: Optional[str] = None

class SubirFotoRequest(BaseModel):
    username: str
    photo_path: str
    caption: str

class SubirCarruselRequest(BaseModel):
    username: str
    paths: List[str]
    caption: str

class EditarCaptionRequest(BaseModel):
    username: str
    media_pk: str
    caption: str

class EliminarPostRequest(BaseModel):
    username: str
    media_pk: str


# ============================================================
# ENDPOINTS — GESTIÓN DE CLIENTES
# ============================================================

@app.get("/")
def root():
    return {"agent": "Community Manager", "status": "running", "panel": "http://localhost:8004/panel"}


@app.get("/clientes")
def listar_clientes():
    clientes = _load_clientes()
    return {
        username: {
            "nombre_negocio": data.get("nombre_negocio", ""),
            "sesion_activa": username in active_clients
        }
        for username, data in clientes.items()
    }


@app.post("/cliente/agregar")
def agregar_cliente(req: AgregarClienteRequest):
    clientes = _load_clientes()
    clientes[req.username] = {
        "password": req.password,
        "nombre_negocio": req.nombre_negocio or req.username
    }
    _save_clientes(clientes)
    return {"success": True, "message": f"Cliente '{req.username}' agregado."}


@app.delete("/cliente/{username}")
def eliminar_cliente(username: str):
    clientes = _load_clientes()
    if username not in clientes:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    del clientes[username]
    _save_clientes(clientes)

    session = _session_path(username)
    if os.path.exists(session):
        os.remove(session)
    if username in active_clients:
        del active_clients[username]
    if username in login_status:
        del login_status[username]

    return {"success": True, "message": f"Cliente '{username}' eliminado."}


# ============================================================
# ENDPOINTS — LOGIN Y VERIFICACIÓN
# ============================================================

@app.post("/login")
def login(req: LoginRequest):
    cl = _get_client(req.username)
    account = cl.account_info()
    login_status[req.username] = "connected"
    return {
        "success": True,
        "username": account.username,
        "full_name": account.full_name,
        "is_private": account.is_private
    }


@app.get("/challenge/pendiente")
def challenges_pendientes():
    return {
        username: {
            "choice": data["choice"],
            "esperando_desde": round(time.time() - data["timestamp"])
        }
        for username, data in pending_codes.items()
        if data["code"] is None
    }


@app.post("/challenge/codigo")
def enviar_codigo(req: VerificationCodeRequest):
    if req.username not in pending_codes:
        raise HTTPException(status_code=404, detail="No hay challenge pendiente")
    pending_codes[req.username]["code"] = req.code
    return {"success": True, "message": f"Código enviado para {req.username}."}


# ============================================================
# ENDPOINTS — PUBLICACIONES
# ============================================================

@app.post("/subir/reel")
def subir_reel(req: SubirReelRequest):
    cl = _get_client(req.username)
    kwargs = {"path": Path(req.video_path), "caption": req.caption}
    if req.thumbnail_path:
        kwargs["thumbnail"] = Path(req.thumbnail_path)
    media = cl.clip_upload(**kwargs)
    cl.dump_settings(Path(_session_path(req.username)))
    return {
        "success": True, "media_pk": str(media.pk),
        "code": media.code, "url": f"https://www.instagram.com/reel/{media.code}/"
    }


@app.post("/subir/foto")
def subir_foto(req: SubirFotoRequest):
    cl = _get_client(req.username)
    media = cl.photo_upload(path=Path(req.photo_path), caption=req.caption)
    cl.dump_settings(Path(_session_path(req.username)))
    return {
        "success": True, "media_pk": str(media.pk),
        "code": media.code, "url": f"https://www.instagram.com/p/{media.code}/"
    }


@app.post("/subir/carrusel")
def subir_carrusel(req: SubirCarruselRequest):
    cl = _get_client(req.username)
    paths = [Path(p) for p in req.paths]
    media = cl.album_upload(paths=paths, caption=req.caption)
    cl.dump_settings(Path(_session_path(req.username)))
    return {
        "success": True, "media_pk": str(media.pk),
        "code": media.code, "url": f"https://www.instagram.com/p/{media.code}/"
    }


# ============================================================
# ENDPOINTS — GESTIÓN DE POSTS
# ============================================================

@app.get("/posts/{username}")
def listar_posts(username: str, cantidad: int = 20):
    cl = _get_client(username)
    medias = cl.user_medias(cl.user_id, amount=cantidad)
    return [
        {
            "media_pk": str(m.pk), "code": m.code, "type": m.media_type,
            "caption": m.caption_text[:200] if m.caption_text else "",
            "likes": m.like_count, "comments": m.comment_count,
            "url": f"https://www.instagram.com/p/{m.code}/",
            "fecha": str(m.taken_at)
        }
        for m in medias
    ]


@app.get("/post/{username}/{media_pk}")
def info_post(username: str, media_pk: str):
    cl = _get_client(username)
    m = cl.media_info(media_pk)
    return {
        "media_pk": str(m.pk), "code": m.code, "type": m.media_type,
        "caption": m.caption_text, "likes": m.like_count, "comments": m.comment_count,
        "url": f"https://www.instagram.com/p/{m.code}/",
        "fecha": str(m.taken_at),
        "thumbnail_url": str(m.thumbnail_url) if m.thumbnail_url else None
    }


@app.put("/post/editar")
def editar_caption(req: EditarCaptionRequest):
    cl = _get_client(req.username)
    result = cl.media_edit(req.media_pk, req.caption)
    return {"success": True, "result": result}


@app.delete("/post/eliminar")
def eliminar_post(req: EliminarPostRequest):
    cl = _get_client(req.username)
    result = cl.media_delete(req.media_pk)
    return {"success": result, "message": "Post eliminado" if result else "Error"}


# ============================================================
# ENDPOINTS — INFO DE CUENTA
# ============================================================

@app.get("/cuenta/{username}")
def info_cuenta(username: str):
    cl = _get_client(username)
    account = cl.account_info()
    return {
        "username": account.username, "full_name": account.full_name,
        "biography": account.biography, "is_private": account.is_private,
        "profile_pic_url": str(account.profile_pic_url) if account.profile_pic_url else None
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "clientes_registrados": len(_load_clientes()),
        "sesiones_activas": len(active_clients)
    }


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

COMMUNITY_MANAGER_PORT = 8004

# ============================================================
# IA — ENDPOINT /ask (lenguaje natural)
# ============================================================

from agent_brain import ask_agent

CM_BRAIN_PROMPT = """Sos el Community Manager de Dental Growth. Gestionás cuentas de Instagram.

Podés subir reels, fotos, carruseles, ver posts, eliminar posts, y gestionar cuentas.
Usá las herramientas disponibles para ejecutar las acciones.
Respondé en español de Costa Rica. Sé conciso."""

CM_TOOLS = [
    {
        "name": "list_accounts",
        "description": "Lista las cuentas de Instagram registradas.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "upload_reel",
        "description": "Sube un reel (video) a Instagram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "video_path": {"type": "string", "description": "Ruta local o URL del video"},
                "caption": {"type": "string"}
            },
            "required": ["username", "video_path", "caption"]
        }
    },
    {
        "name": "upload_photo",
        "description": "Sube una foto a Instagram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "image_path": {"type": "string"},
                "caption": {"type": "string"}
            },
            "required": ["username", "image_path", "caption"]
        }
    },
    {
        "name": "list_posts",
        "description": "Lista los posts recientes de una cuenta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"}
            },
            "required": ["username"]
        }
    },
    {
        "name": "delete_post",
        "description": "Elimina un post de Instagram.",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "media_pk": {"type": "string"}
            },
            "required": ["username", "media_pk"]
        }
    }
]


def _cm_tool_executor(name, input_data):
    import httpx
    base = f"http://localhost:{COMMUNITY_MANAGER_PORT}"
    if name == "list_accounts":
        r = httpx.get(f"{base}/clientes", timeout=10)
        return r.json()
    elif name == "upload_reel":
        r = httpx.post(f"{base}/subir/reel", json=input_data, timeout=120)
        return r.json()
    elif name == "upload_photo":
        r = httpx.post(f"{base}/subir/foto", json=input_data, timeout=60)
        return r.json()
    elif name == "list_posts":
        r = httpx.get(f"{base}/posts/{input_data['username']}", timeout=15)
        return r.json()
    elif name == "delete_post":
        r = httpx.delete(f"{base}/post/eliminar", json=input_data, timeout=15)
        return r.json()
    return {"error": f"Herramienta desconocida: {name}"}


class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    try:
        response = ask_agent(req.question, CM_BRAIN_PROMPT, CM_TOOLS, _cm_tool_executor)
        return {"response": response}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


if __name__ == "__main__":
    print("📱 Community Manager iniciando en puerto", COMMUNITY_MANAGER_PORT)
    print("🌐 Panel web: http://localhost:8004/panel")
    uvicorn.run(app, host="0.0.0.0", port=COMMUNITY_MANAGER_PORT)
