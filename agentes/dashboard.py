"""
Dashboard Central — Dental Growth
====================================
Panel de control principal de todos los agentes.

- Grid de agentes con estado en tiempo real
- Centro de comando (chat con el orquestador)
- Conexión de Instagram via Facebook OAuth
- Monitoreo de actividad de cada agente

Puerto: 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import uvicorn
import time
import threading
import json
import os
import anthropic
from urllib.parse import urlencode
from config import (
    CLICKUP_MANAGER_URL, TRANSCRIBER_URL, COPY_CONTENT_URL,
    COMMUNITY_MANAGER_PORT, ANTHROPIC_API_KEY,
    META_APP_ID, META_APP_SECRET, META_REDIRECT_URI,
    IG_APP_ID, IG_APP_SECRET
)

app = FastAPI(title="Dashboard — Dental Growth", version="2.0")

COMMUNITY_MANAGER_URL = f"http://localhost:{COMMUNITY_MANAGER_PORT}"

# Registro de actividad de agentes
agent_activity = {
    "clickup_manager": {"status": "offline", "last_action": None, "timestamp": None},
    "transcriber": {"status": "offline", "last_action": None, "timestamp": None},
    "copy_content": {"status": "offline", "last_action": None, "timestamp": None},
    "community_manager": {"status": "offline", "last_action": None, "timestamp": None},
}

# Historial de chat del comando central
chat_history = []

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Cuentas de Instagram conectadas via OAuth
IG_ACCOUNTS_FILE = os.path.join(AGENTS_DIR, "ig_accounts_oauth.json")

def _load_ig_accounts():
    if os.path.exists(IG_ACCOUNTS_FILE):
        with open(IG_ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_ig_accounts(accounts):
    with open(IG_ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)

# ============================================================
# MONITOREO DE AGENTES
# ============================================================

def _check_agent(name, url):
    try:
        r = httpx.get(f"{url}/health", timeout=3)
        if r.status_code == 200:
            agent_activity[name]["status"] = "online"
            return True
    except Exception:
        pass
    try:
        r = httpx.get(f"{url}/", timeout=3)
        if r.status_code == 200:
            agent_activity[name]["status"] = "online"
            return True
    except Exception:
        pass
    agent_activity[name]["status"] = "offline"
    return False


def _check_all_agents():
    while True:
        _check_agent("clickup_manager", CLICKUP_MANAGER_URL)
        _check_agent("transcriber", TRANSCRIBER_URL)
        _check_agent("copy_content", COPY_CONTENT_URL)
        _check_agent("community_manager", COMMUNITY_MANAGER_URL)
        time.sleep(5)


# Iniciar monitoreo en background
monitor_thread = threading.Thread(target=_check_all_agents, daemon=True)
monitor_thread.start()


# ============================================================
# CENTRO DE COMANDO (Chat con IA)
# ============================================================

SYSTEM_PROMPT = """Sos el orquestador central de Dental Growth, una agencia de marketing para profesionales de la salud en Costa Rica.

## REGLA #1: AHORRO DE CRÉDITOS
- SIEMPRE usá "api_call" para consultas simples — es GRATIS.
- Para generar copies en lote, usá "generate_copies_batch" — hace todo en paralelo (transcribir + generar + guardar).
- NUNCA uses "ask_agent" — gasta créditos innecesariamente.

## REGLA #2: PARALELISMO
- Cuando tenés que generar copies para múltiples tareas, usá generate_copies_batch — ejecuta todo en paralelo automáticamente.
- Para consultas múltiples, mandá todas las api_call al mismo tiempo.

## CÓMO BUSCAR TAREAS
- SIEMPRE: GET http://localhost:8001/buscar/{cliente} — búsqueda inteligente con match flexible.
- Params opcionales: ?mes=enero, ?mes=marzo, ?con_video=true
- Ejemplos: /buscar/dentium?mes=enero, /buscar/smile%20pro?mes=marzo&con_video=true

## ENDPOINTS API (todos via api_call a http://localhost:8001)

### Videos y Content
- GET /buscar/{cliente}?mes=X&con_video=true — buscar tareas de video (con_video=true incluye URL del video)
- GET /tarea/{task_id}/copy — obtener copy completo del campo "tema"
- GET /cliente/{nombre}/info — info del negocio
- POST /campo/set — guardar campo: {"task_id": "X", "field_id": "7dbf2727-6615-49fa-aa4c-2de3069b0000", "value": "texto"}
- PUT /tarea/status — cambiar status: {"task_id": "X", "status": "completado"}

### Administración
- GET /admin/pagos — todos los clientes con estado de pago y monto (?status=activo para filtrar)
- GET /admin/pagos/{cliente} — estado de pago de un cliente específico
- PUT /admin/pagos/status — cambiar estado de pago: {"task_id": "X", "status": "activo|pendiente de pago|atrasado|trimestral|pausado|negociación|no paga"}
- PUT /admin/pagos/monto?task_id=X&monto=1500 — actualizar monto
- GET /admin/tareas — tareas administrativas (?status=pendiente)
- POST /admin/tareas/crear — crear tarea admin: {"name": "...", "status": "pendiente"}
- GET /admin/entregas — estado de entrega de servicio por cliente
- POST /admin/nuevo-cliente — registrar nuevo cliente (crea en Pagos + Entrega de Servicio + fecha límite automática)
  Body: {"nombre": "Nombre", "monto": 2500, "fecha_inicio": "2026-04-07", "trimestral": true}
  Reglas: trimestral=true → status "trimestral" | trimestral=false → status "activo" (mensual/otro)
  SIEMPRE se pone fecha límite = inicio + 3 meses en ambas listas.
- GET /admin/resumen/{cliente} — resumen completo: pagos + tareas + entregas + info negocio

## FLUJO: GENERAR COPIES — UN SOLO PASO
- Usá generate_copies con el nombre del cliente y mes. Ejemplo: generate_copies(cliente="dentium", mes="enero")
- La herramienta AUTOMÁTICAMENTE: busca tareas sin copy → obtiene videos → transcribe → genera copies → los guarda en el campo tema de ClickUp.
- NUNCA hagas transcripciones ni copies manualmente con api_call. SIEMPRE usá generate_copies.

## FLUJO: SUBIR VIDEO A INSTAGRAM
1. api_call GET /buscar/{cliente}?con_video=true → tareas con video y copy
2. api_call GET /tarea/{task_id}/copy → copy completo
3. upload_reel_oauth → {video_url: URL de ClickUp directa, caption: el copy, username: cuenta IG}
(Las URLs de ClickUp son públicas, NO necesitás descargar el video)

## GUARDAR COPY EN CLICKUP — EJEMPLO EXACTO
```
api_call POST http://localhost:8001/campo/set
body: {"task_id": "86aerkhq2", "field_id": "7dbf2727-6615-49fa-aa4c-2de3069b0000", "value": "📍 Estamos ubicados en..."}
```
El field_id del campo tema SIEMPRE es: 7dbf2727-6615-49fa-aa4c-2de3069b0000

Respondé en español de Costa Rica (vos, usá, tenés). Sé conciso y directo."""

TOOLS = [
    {
        "name": "api_call",
        "description": "Request HTTP directo a un agente. GRATIS — usalo para todo lo simple.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                "url": {"type": "string", "description": "URL completa, ej: http://localhost:8001/tareas/901325940523"},
                "body": {"type": "object", "description": "Body para POST/PUT"}
            },
            "required": ["method", "url"]
        }
    },
    {
        "name": "generate_copies",
        "description": "Busca tareas sin copy de un cliente, transcribe sus videos, genera copies y los guarda en ClickUp. TODO AUTOMÁTICO EN PARALELO. Solo necesitás el nombre del cliente y el mes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente": {"type": "string", "description": "Nombre del cliente (ej: dentium, smile pro)"},
                "mes": {"type": "string", "description": "Mes a buscar (ej: enero, febrero, marzo, abril). Opcional."}
            },
            "required": ["cliente"]
        }
    },
    {
        "name": "get_oauth_accounts",
        "description": "Lista cuentas de Instagram conectadas via OAuth.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "upload_reel_oauth",
        "description": "Sube un Reel a Instagram usando la cuenta OAuth conectada. Pasá la URL pública del video (de ClickUp) directamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_url": {"type": "string", "description": "URL pública del video (de ClickUp o cualquier URL accesible)"},
                "caption": {"type": "string", "description": "Caption/copy del reel"},
                "username": {"type": "string", "description": "Username de Instagram (ej: isaac_hervos)"}
            },
            "required": ["video_url", "caption", "username"]
        }
    }
]

AGENT_URLS = {
    "clickup_manager": "http://localhost:8001",
    "transcriber": "http://localhost:8002",
    "copy_content": "http://localhost:8003",
    "community_manager": "http://localhost:8004",
}

AGENT_NAMES = {
    "clickup_manager": "ClickUp Manager",
    "transcriber": "Transcriber",
    "copy_content": "Copy Content",
    "community_manager": "Community Manager",
}

client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


DOWNLOAD_DIR = os.path.join(AGENTS_DIR, "_temp_videos")


def _execute_tool(name, input_data):
    """Ejecuta una herramienta y devuelve el resultado."""
    if name == "api_call":
        method = input_data["method"]
        url = input_data["url"]
        body = input_data.get("body")
        try:
            if method == "GET":
                r = httpx.get(url, timeout=30)
            elif method == "POST":
                r = httpx.post(url, json=body, timeout=120)
            elif method == "PUT":
                r = httpx.put(url, json=body, timeout=30)
            elif method == "DELETE":
                r = httpx.delete(url, json=body, timeout=30)
            else:
                return {"error": f"Método no soportado: {method}"}
            try:
                return r.json()
            except Exception:
                return {"status": r.status_code, "text": r.text[:500]}
        except httpx.ConnectError:
            return {"error": f"No se pudo conectar a {url}. ¿El agente está corriendo?"}
        except Exception as e:
            return {"error": str(e)}

    elif name == "ask_agent":
        agent = input_data["agent"]
        question = input_data["question"]
        url = AGENT_URLS.get(agent)
        if not url:
            return {"error": f"Agente desconocido: {agent}"}
        try:
            r = httpx.post(f"{url}/ask", json={"question": question}, timeout=120)
            return r.json()
        except httpx.ConnectError:
            return {"error": f"No se pudo conectar al agente {agent}. ¿Está corriendo?"}
        except Exception as e:
            return {"error": str(e)}

    elif name == "generate_copies":
        cliente = input_data["cliente"]
        mes = input_data.get("mes")
        tema_field_id = "7dbf2727-6615-49fa-aa4c-2de3069b0000"

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Paso 1: Buscar tareas con video + info del negocio en paralelo
        def fetch_tasks():
            params = f"?con_video=true"
            if mes:
                params += f"&mes={mes}"
            return httpx.get(f"http://localhost:8001/buscar/{cliente}{params}", timeout=30).json()

        def fetch_info():
            return httpx.get(f"http://localhost:8001/cliente/{cliente}/info", timeout=15).json()

        with ThreadPoolExecutor(max_workers=2) as ex:
            f_tasks = ex.submit(fetch_tasks)
            f_info = ex.submit(fetch_info)
            tasks_data = f_tasks.result()
            info_data = f_info.result()

        all_tasks = tasks_data.get("resultados", [])
        sin_copy = [t for t in all_tasks if not t.get("tiene_copy")]

        if not sin_copy:
            return {"message": f"Todas las tareas de {cliente} ya tienen copy.", "total": len(all_tasks), "sin_copy": 0}

        nombre_cliente = cliente.title()
        info_negocio = info_data.get("info", f"Cliente: {nombre_cliente}")

        # Paso 2: Para cada tarea sin copy, transcribir → generar → guardar (en paralelo)
        def process_task(task):
            task_id = task["task_id"]
            task_name = task["nombre"]
            video = task.get("video", {})
            video_url = video.get("url") if isinstance(video, dict) else None

            if not video_url:
                return {"task": task_name, "status": "error", "detail": "Sin video URL"}

            try:
                # Transcribir
                r1 = httpx.post("http://localhost:8002/transcribir",
                                json={"url": video_url, "language": "es"}, timeout=300)
                if r1.status_code != 200:
                    return {"task": task_name, "status": "error", "detail": f"Transcripción falló: {r1.status_code}"}
                transcripcion = r1.json().get("text", "")

                # Generar copy
                r2 = httpx.post("http://localhost:8003/generar",
                                json={"transcripcion": transcripcion, "nombre_cliente": nombre_cliente, "info_negocio": info_negocio},
                                timeout=60)
                if r2.status_code != 200:
                    return {"task": task_name, "status": "error", "detail": f"Generación falló: {r2.status_code}"}
                copy = r2.json().get("copy", "")

                # Guardar en ClickUp
                r3 = httpx.post("http://localhost:8001/campo/set",
                                json={"task_id": task_id, "field_id": tema_field_id, "value": copy},
                                timeout=30)
                saved = r3.status_code == 200 and r3.json().get("success", False)

                return {"task": task_name, "task_id": task_id, "status": "ok" if saved else "no guardado",
                        "copy_preview": copy[:150] + "...", "guardado": saved}

            except Exception as e:
                return {"task": task_name, "status": "error", "detail": str(e)}

        results = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(process_task, t): t for t in sin_copy}
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(key=lambda x: x.get("task", ""))
        ok_count = sum(1 for r in results if r["status"] == "ok")
        return {"total_tareas": len(all_tasks), "sin_copy": len(sin_copy), "exitosos": ok_count, "resultados": results}

    elif name == "get_oauth_accounts":
        return _load_ig_accounts()

    elif name == "download_video":
        url = input_data["url"]
        filename = input_data.get("filename", "video.mp4")
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        try:
            with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            return {"path": filepath, "size_mb": round(size_mb, 2), "filename": filename,
                    "nota": "IMPORTANTE: después de subir, eliminá el archivo con cleanup_video"}
        except Exception as e:
            return {"error": f"Error descargando: {str(e)}"}

    elif name == "upload_reel_oauth":
        video_url = input_data["video_url"]
        caption = input_data["caption"]
        username = input_data["username"]

        # Buscar cuenta OAuth por username
        accounts = _load_ig_accounts()
        account = None
        for ig_id, data in accounts.items():
            if data.get("username", "").lower() == username.lower().replace("@", ""):
                account = data
                break
        if not account:
            return {"error": f"Cuenta @{username} no encontrada en OAuth. Cuentas disponibles: {[d.get('username') for d in accounts.values()]}"}

        token = account["access_token"]
        ig_user_id = account["ig_id"]

        try:
            import time as _time

            # Paso 1: Crear contenedor de Reel con video_url pública
            r1 = httpx.post(
                f"https://graph.instagram.com/v25.0/{ig_user_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "access_token": token,
                },
                timeout=60,
            )
            if r1.status_code != 200:
                return {"error": f"Error creando contenedor: {r1.text}"}

            container_id = r1.json().get("id")
            if not container_id:
                return {"error": f"No se recibió container ID: {r1.json()}"}

            # Paso 2: Esperar a que Instagram descargue y procese el video
            status = ""
            for attempt in range(36):  # max ~6 minutos
                _time.sleep(10)
                r2 = httpx.get(
                    f"https://graph.instagram.com/v25.0/{container_id}",
                    params={"fields": "status_code,status", "access_token": token},
                    timeout=15,
                )
                if r2.status_code == 200:
                    status_data = r2.json()
                    status = status_data.get("status_code", "")
                    if status == "FINISHED":
                        break
                    elif status == "ERROR":
                        return {"error": f"Instagram rechazó el video: {status_data}"}

            if status != "FINISHED":
                return {"error": f"Timeout esperando procesamiento. Último status: {status}"}

            # Paso 3: Publicar
            r3 = httpx.post(
                f"https://graph.instagram.com/v25.0/{ig_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": token},
                timeout=60,
            )
            if r3.status_code == 200:
                return {"success": True, "media_id": r3.json().get("id"), "username": username}
            else:
                return {"error": f"Error publicando: {r3.text}"}

        except Exception as e:
            return {"error": f"Error en upload OAuth: {str(e)}"}

    elif name == "cleanup_video":
        path = input_data["path"]
        try:
            if os.path.exists(path):
                os.remove(path)
                return {"deleted": True, "path": path}
            return {"deleted": False, "reason": "Archivo no encontrado"}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Herramienta desconocida: {name}"}


class ChatMessage(BaseModel):
    message: str


def _sse_event(event_type, data):
    """Formatea un evento SSE."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _execute_tool_with_heartbeat(name, input_data):
    """Ejecuta una herramienta en un thread y devuelve resultado + heartbeats SSE."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import queue

    result_queue = queue.Queue()

    def run():
        try:
            r = _execute_tool(name, input_data)
            result_queue.put(("ok", r))
        except Exception as e:
            result_queue.put(("error", str(e)))

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(run)

    # Mandar heartbeats cada 10 segundos mientras la herramienta trabaja
    while not future.done():
        try:
            future.result(timeout=10)
        except Exception:
            pass
        if not future.done():
            yield _sse_event("heartbeat", {"text": f"⏳ Procesando {name}..."})

    executor.shutdown(wait=False)

    status, data = result_queue.get()
    if status == "error":
        yield _sse_event("agent_response", {"agent": name, "response": f"Error: {data}"})
        yield ("__RESULT__", {"error": data})
    else:
        yield ("__RESULT__", data)


def _get_tool_label(block):
    """Genera el evento SSE de notificación para una herramienta."""
    if block.name == "api_call":
        method = block.input.get("method", "")
        url = block.input.get("url", "")
        agent_label = "API"
        for aname, aurl in AGENT_URLS.items():
            if aurl in url:
                agent_label = AGENT_NAMES.get(aname, aname)
                break
        path = url.split("localhost:")[1].split("/", 1)[1] if "localhost:" in url else url
        return _sse_event("agent_call", {"agent": agent_label, "question": f"{method} /{path}"})
    elif block.name == "ask_agent":
        agent_name = AGENT_NAMES.get(block.input.get("agent", ""), block.input.get("agent", ""))
        return _sse_event("agent_call", {"agent": f"{agent_name} (IA)", "question": block.input.get("question", "")})
    elif block.name == "get_oauth_accounts":
        return _sse_event("agent_call", {"agent": "OAuth", "question": "Consultando cuentas conectadas..."})
    elif block.name == "generate_copies":
        c = block.input.get("cliente", "")
        m = block.input.get("mes", "todos los meses")
        return _sse_event("agent_call", {"agent": "Generador de Copies", "question": f"Buscando tareas de {c} ({m}), transcribiendo, generando y guardando copies en paralelo..."})
    elif block.name == "upload_reel_oauth":
        return _sse_event("agent_call", {"agent": "Instagram Upload", "question": f"Subiendo reel a @{block.input.get('username', '')}..."})
    else:
        return _sse_event("agent_call", {"agent": block.name, "question": "Procesando..."})


def _get_tool_response_event(block, result):
    """Genera el evento SSE de respuesta para una herramienta."""
    if block.name == "ask_agent":
        agent_name = AGENT_NAMES.get(block.input.get("agent", ""), "")
        response_text = result.get("response", str(result))
        if len(response_text) > 300:
            response_text = response_text[:300] + "..."
        return _sse_event("agent_response", {"agent": agent_name, "response": response_text})
    elif block.name == "api_call":
        return _sse_event("agent_response", {"agent": "API", "response": str(result)[:200]})
    elif block.name == "generate_copies":
        ok = result.get("exitosos", 0)
        sin = result.get("sin_copy", 0)
        return _sse_event("agent_response", {"agent": "Generador de Copies", "response": f"{ok}/{sin} copies generados y guardados en ClickUp"})
    elif block.name == "upload_reel_oauth":
        if result.get("success"):
            return _sse_event("agent_response", {"agent": "Instagram", "response": f"Reel publicado en @{result.get('username', '')}"})
        else:
            return _sse_event("agent_response", {"agent": "Instagram", "response": f"Error: {result.get('error', str(result))}"})
    else:
        return _sse_event("agent_response", {"agent": block.name, "response": str(result)[:200]})


def _chat_stream(message: str):
    """Generador SSE que procesa el chat con tool use."""
    chat_history.append({"role": "user", "content": message})
    messages = [{"role": m["role"], "content": m["content"]} for m in chat_history[-20:]]

    try:
        max_iterations = 10
        for _ in range(max_iterations):
            yield _sse_event("thinking", {"text": "Pensando..."})

            response = client_ai.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                timeout=600,
            )

            # Si terminó sin tool use
            if response.stop_reason == "end_of_turn":
                text_parts = [b.text for b in response.content if b.type == "text"]
                reply = "\n".join(text_parts) if text_parts else "Listo."
                chat_history.append({"role": "assistant", "content": reply})
                yield _sse_event("done", {"text": reply})
                return

            # Procesar tool use
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                # Mostrar texto intermedio del asistente si lo hay
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        yield _sse_event("thinking", {"text": block.text})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Notificar qué herramienta se está ejecutando
                        yield _get_tool_label(block)

                        # Ejecutar con heartbeat para mantener la conexión viva
                        result = None
                        for event in _execute_tool_with_heartbeat(block.name, block.input):
                            if isinstance(event, tuple) and event[0] == "__RESULT__":
                                result = event[1]
                            else:
                                yield event

                        if result is None:
                            result = {"error": "No se obtuvo resultado"}

                        # Notificar respuesta
                        yield _get_tool_response_event(block, result)

                        result_str = json.dumps(result, ensure_ascii=False, default=str)
                        if len(result_str) > 8000:
                            result_str = result_str[:8000] + "...(truncado)"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Otro stop_reason
            text_parts = [b.text for b in response.content if b.type == "text"]
            reply = "\n".join(text_parts) if text_parts else "Completado."
            chat_history.append({"role": "assistant", "content": reply})
            yield _sse_event("done", {"text": reply})
            return

        yield _sse_event("done", {"text": "Se alcanzó el límite de iteraciones."})

    except Exception as e:
        yield _sse_event("done", {"text": f"Error: {str(e)}"})


@app.post("/chat")
def chat(msg: ChatMessage):
    return StreamingResponse(
        _chat_stream(msg.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/chat/history")
def get_chat_history():
    return chat_history[-50:]


@app.delete("/chat/history")
def clear_chat_history():
    chat_history.clear()
    return {"cleared": True}


# ============================================================
# ESTADO DE AGENTES
# ============================================================

@app.get("/agents/status")
def agents_status():
    # También traer info de cuentas de Instagram si el CM está online
    ig_accounts = {}
    if agent_activity["community_manager"]["status"] == "online":
        try:
            r = httpx.get(f"{COMMUNITY_MANAGER_URL}/clientes", timeout=3)
            ig_accounts = r.json()
            r2 = httpx.get(f"{COMMUNITY_MANAGER_URL}/login/status", timeout=3)
            ig_statuses = r2.json()
            for u in ig_accounts:
                ig_accounts[u]["login_status"] = ig_statuses.get(u, "disconnected")
        except Exception:
            pass

    # Agregar cuentas conectadas via OAuth
    oauth_accounts = _load_ig_accounts()
    for ig_id, data in oauth_accounts.items():
        ig_accounts[data.get("username", ig_id)] = {
            "nombre_negocio": data.get("name", ""),
            "login_status": "connected",
            "method": "oauth",
            "ig_id": ig_id
        }

    return {
        "agents": agent_activity,
        "ig_accounts": ig_accounts
    }


# ============================================================
# OAUTH — Facebook / Instagram
# ============================================================

@app.get("/auth/login")
def auth_login():
    """Redirige al usuario a Instagram para autorizar la app."""
    params = urlencode({
        "client_id": IG_APP_ID,
        "redirect_uri": META_REDIRECT_URI,
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_comments,instagram_business_manage_insights",
    })
    return RedirectResponse(f"https://www.instagram.com/oauth/authorize?{params}")


@app.get("/auth/callback")
def auth_callback(code: str = None, error: str = None):
    """Callback de Instagram OAuth. Intercambia el code por tokens."""
    if error:
        return HTMLResponse(f"<script>window.close(); alert('Error: {error}');</script>")
    if not code:
        return HTMLResponse("<script>window.close(); alert('No se recibió código');</script>")

    # Intercambiar code por short-lived token via Instagram API
    r = httpx.post("https://api.instagram.com/oauth/access_token", data={
        "client_id": IG_APP_ID,
        "client_secret": IG_APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": META_REDIRECT_URI,
        "code": code,
    })
    if r.status_code != 200:
        return HTMLResponse(f"""<html><body style="background:#0a0a0a;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
            <div style="text-align:center;"><h2 style="color:#e74c3c;">Error obteniendo token</h2><p>{r.text}</p></div>
        </body></html>""")

    data = r.json()
    short_token = data["access_token"]
    user_id = str(data.get("user_id", ""))

    # Obtener long-lived token via Graph API
    r2 = httpx.get("https://graph.instagram.com/access_token", params={
        "grant_type": "ig_exchange_token",
        "client_secret": IG_APP_SECRET,
        "access_token": short_token,
    })
    long_token = r2.json().get("access_token", short_token) if r2.status_code == 200 else short_token

    # Obtener info del usuario de Instagram
    r3 = httpx.get(f"https://graph.instagram.com/v25.0/me", params={
        "fields": "user_id,username,name,profile_picture_url,account_type",
        "access_token": long_token,
    })

    accounts = _load_ig_accounts()
    connected = []

    if r3.status_code == 200:
        ig_data = r3.json()
        ig_id = ig_data.get("user_id", user_id)
        username = ig_data.get("username", "")
        accounts[ig_id] = {
            "ig_id": ig_id,
            "username": username,
            "name": ig_data.get("name", ""),
            "profile_pic": ig_data.get("profile_picture_url", ""),
            "account_type": ig_data.get("account_type", ""),
            "access_token": long_token,
        }
        connected.append(username or ig_data.get("name", ig_id))
    else:
        # Fallback: guardar con el user_id del token
        accounts[user_id] = {
            "ig_id": user_id,
            "username": "",
            "name": "",
            "access_token": long_token,
        }
        connected.append(user_id)

    _save_ig_accounts(accounts)

    names = ", ".join(connected) if connected else "ninguna cuenta encontrada"
    return HTMLResponse(f"""<html><body style="background:#0a0a0a;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
        <div style="text-align:center;">
            <h2 style="color:#2ecc71;">✅ Conectado exitosamente</h2>
            <p>Cuentas: <b>{names}</b></p>
            <p style="color:#888;margin-top:20px;">Podés cerrar esta ventana.</p>
            <script>setTimeout(()=>window.close(), 3000);</script>
        </div>
    </body></html>""")


@app.get("/auth/accounts")
def auth_accounts():
    """Lista cuentas de Instagram conectadas via OAuth."""
    return _load_ig_accounts()


@app.post("/auth/publish/{ig_id}")
def auth_publish(ig_id: str, caption: str, video_url: str = None, image_url: str = None):
    """Publica contenido en Instagram via Graph API."""
    accounts = _load_ig_accounts()
    if ig_id not in accounts:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    account = accounts[ig_id]
    token = account["page_token"]

    if video_url:
        # Publicar Reel
        r = httpx.post(f"https://graph.facebook.com/v21.0/{ig_id}/media", params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": token,
        }, timeout=60)
    elif image_url:
        # Publicar foto
        r = httpx.post(f"https://graph.facebook.com/v21.0/{ig_id}/media", params={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        }, timeout=60)
    else:
        raise HTTPException(status_code=400, detail="Se necesita video_url o image_url")

    if r.status_code != 200:
        return {"success": False, "error": r.json()}

    creation_id = r.json().get("id")

    # Publicar el contenedor
    r2 = httpx.post(f"https://graph.facebook.com/v21.0/{ig_id}/media_publish", params={
        "creation_id": creation_id,
        "access_token": token,
    }, timeout=60)

    return {"success": r2.status_code == 200, "result": r2.json()}


# ============================================================
# DASHBOARD HTML
# ============================================================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dental Growth — Centro de Control</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; height: 100vh; max-height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

  /* Header */
  .header { background: #111; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222; }
  .header h1 { font-size: 18px; font-weight: 700; }
  .header h1 span { background: linear-gradient(135deg, #E1306C, #F77737, #FCAF45); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .header-right { display: flex; gap: 12px; align-items: center; }
  .header-time { font-size: 12px; color: #666; }

  /* Main layout */
  .main { display: flex; flex: 1; min-height: 0; overflow: hidden; }

  /* Left: Agents grid */
  .sidebar { width: 300px; background: #111; border-right: 1px solid #222; padding: 16px; overflow-y: auto; }
  .sidebar h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 12px; }

  .agent-card { background: #1a1a1a; border-radius: 10px; padding: 14px; margin-bottom: 10px; border: 1px solid #2a2a2a; transition: all 0.3s; }
  .agent-card:hover { border-color: #444; }
  .agent-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .agent-icon { font-size: 20px; }
  .agent-name { font-weight: 600; font-size: 14px; }
  .agent-port { font-size: 11px; color: #666; }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: auto; }
  .dot-online { background: #2ecc71; box-shadow: 0 0 6px #2ecc7188; }
  .dot-offline { background: #e74c3c; }
  .agent-action { font-size: 12px; color: #888; margin-top: 4px; }

  /* IG Accounts section */
  .ig-section { margin-top: 20px; }
  .ig-account { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: #1a1a1a; border-radius: 8px; margin-bottom: 6px; border: 1px solid #2a2a2a; }
  .ig-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #E1306C, #F77737); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
  .ig-info { flex: 1; }
  .ig-user { font-size: 13px; font-weight: 600; }
  .ig-negocio { font-size: 11px; color: #888; }
  .ig-status { font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
  .ig-connected { background: #27ae6033; color: #2ecc71; }
  .ig-disconnected { background: #e74c3c33; color: #e74c3c; }
  .ig-logging { background: #f39c1233; color: #f1c40f; }

  .btn-add-ig { width: 100%; padding: 10px; border-radius: 8px; border: 1px dashed #444; background: transparent; color: #888; font-size: 13px; cursor: pointer; margin-top: 8px; transition: all 0.2s; }
  .btn-add-ig:hover { border-color: #E1306C; color: #E1306C; }

  /* Center: Chat */
  .chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .chat-messages { flex: 1; padding: 20px; overflow-y: auto; min-height: 0; }
  .chat-msg { margin-bottom: 16px; max-width: 85%; }
  .chat-msg.user { margin-left: auto; }
  .chat-msg.assistant { margin-right: auto; }
  .chat-bubble { padding: 12px 16px; border-radius: 16px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; }
  .chat-msg.user .chat-bubble { background: #E1306C; color: #fff; border-bottom-right-radius: 4px; }
  .chat-msg.assistant .chat-bubble { background: #1a1a1a; color: #e0e0e0; border: 1px solid #2a2a2a; border-bottom-left-radius: 4px; }
  .chat-label { font-size: 11px; color: #666; margin-bottom: 4px; }
  .chat-msg.user .chat-label { text-align: right; }

  .chat-input-area { padding: 16px 20px; border-top: 1px solid #222; background: #111; }
  .chat-input-wrap { display: flex; gap: 10px; }
  .chat-input-wrap input { flex: 1; padding: 12px 16px; border-radius: 12px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 14px; }
  .chat-input-wrap input:focus { outline: none; border-color: #E1306C; }
  .chat-input-wrap button { padding: 12px 24px; border-radius: 12px; border: none; background: #E1306C; color: #fff; font-weight: 600; cursor: pointer; font-size: 14px; }
  .chat-input-wrap button:hover { background: #c02060; }
  .chat-input-wrap button:disabled { background: #444; cursor: not-allowed; }

  .welcome { text-align: center; padding: 60px 40px; color: #444; }
  .welcome h2 { font-size: 24px; margin-bottom: 12px; color: #666; }
  .welcome p { font-size: 14px; line-height: 1.6; }


  /* Status updates */
  .status-bubble { padding: 12px 16px !important; }
  .status-items { display: flex; flex-direction: column; gap: 8px; }
  .status-item { font-size: 13px; padding: 6px 10px; border-radius: 8px; line-height: 1.4; }
  .st-think { color: #888; font-style: italic; }
  .st-call { background: #1e3a5f; color: #7cb3ff; border-left: 3px solid #4a9eff; }
  .st-resp { background: #1a3a2a; color: #7cdb8a; border-left: 3px solid #2ecc71; font-size: 12px; }
  .st-err { background: #3a1a1a; color: #ff7c7c; border-left: 3px solid #e74c3c; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
  <h1>🦷 <span>Dental Growth</span> — Centro de Control</h1>
  <div class="header-right">
    <span class="header-time" id="clock"></span>
  </div>
</div>

<div class="main">
  <!-- Sidebar: Agents + IG accounts -->
  <div class="sidebar">
    <h2>Agentes</h2>
    <div id="agents-grid"></div>

    <div class="ig-section">
      <h2>Cuentas de Instagram</h2>
      <div id="ig-accounts"></div>
      <button class="btn-add-ig" onclick="connectFacebook()">+ Conectar con Facebook</button>
    </div>
  </div>

  <!-- Center: Chat -->
  <div class="chat-area">
    <div class="chat-messages" id="chat-messages">
      <div class="welcome">
        <h2>Centro de Comando</h2>
        <p>Pedime lo que necesités sobre la agencia.<br>
        Puedo coordinar tareas en ClickUp, generar copies,<br>
        subir videos a Instagram, y más.</p>
      </div>
    </div>
    <div class="chat-input-area">
      <div class="chat-input-wrap">
        <input type="text" id="chat-input" placeholder="Escribí lo que necesitás..." onkeydown="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()" id="send-btn">Enviar</button>
      </div>
    </div>
  </div>
</div>


<script>
const CM_URL = 'http://localhost:8004';
const DASH_URL = '';

const AGENT_INFO = {
  clickup_manager: { icon: '🏢', name: 'ClickUp Manager', port: 8001 },
  transcriber: { icon: '🔤', name: 'Transcriber', port: 8002 },
  copy_content: { icon: '✍️', name: 'Copy Content', port: 8003 },
  community_manager: { icon: '📱', name: 'Community Manager', port: 8004 },
};

// Clock
setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('es-CR');
}, 1000);

// Refresh agents
async function refreshStatus() {
  try {
    const r = await fetch(DASH_URL + '/agents/status');
    const data = await r.json();

    // Render agents
    let html = '';
    for (const [key, info] of Object.entries(AGENT_INFO)) {
      const st = data.agents[key];
      const isOnline = st && st.status === 'online';
      const dotClass = isOnline ? 'dot-online' : 'dot-offline';
      const action = st && st.last_action ? st.last_action : (isOnline ? 'En espera' : 'Desconectado');
      html += `
        <div class="agent-card">
          <div class="agent-header">
            <span class="agent-icon">${info.icon}</span>
            <div>
              <div class="agent-name">${info.name}</div>
              <div class="agent-port">:${info.port}</div>
            </div>
            <span class="dot ${dotClass}"></span>
          </div>
          <div class="agent-action">${action}</div>
        </div>`;
    }
    document.getElementById('agents-grid').innerHTML = html;

    // Render IG accounts
    const ig = data.ig_accounts || {};
    let igHtml = '';
    for (const [u, info] of Object.entries(ig)) {
      const lst = String(info.login_status || 'disconnected');
      let statusClass = 'ig-disconnected';
      let statusText = 'Desconectado';
      if (lst === 'connected') { statusClass = 'ig-connected'; statusText = 'Conectado'; }
      else if (lst === 'logging_in') { statusClass = 'ig-logging'; statusText = 'Conectando...'; }
      else if (lst.includes('needs_code')) { statusClass = 'ig-logging'; statusText = 'Código requerido'; }
      else if (lst.includes('error')) { statusText = 'Error'; }

      const initial = u[0].toUpperCase();
      igHtml += `
        <div class="ig-account">
          <div class="ig-avatar">${initial}</div>
          <div class="ig-info">
            <div class="ig-user">@${u}</div>
            <div class="ig-negocio">${info.nombre_negocio || ''}</div>
          </div>
          <span class="ig-status ${statusClass}">${statusText}</span>
        </div>`;
    }
    document.getElementById('ig-accounts').innerHTML = igHtml || '<p style="color:#555;font-size:12px;padding:8px;">Sin cuentas registradas</p>';

  } catch(e) { console.error('Status error:', e); }
}

setInterval(refreshStatus, 3000);
refreshStatus();

// Facebook OAuth popup
function connectFacebook() {
  const w = 600, h = 700;
  const left = (screen.width - w) / 2;
  const top = (screen.height - h) / 2;
  const popup = window.open('/auth/login', 'fb_oauth', `width=${w},height=${h},left=${left},top=${top}`);
  // Poll for popup close, then refresh accounts
  const timer = setInterval(() => {
    if (popup.closed) {
      clearInterval(timer);
      refreshStatus();
    }
  }, 1000);
}

// Chat
let chatLoaded = false;

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  document.getElementById('send-btn').disabled = true;

  if (!chatLoaded) {
    document.getElementById('chat-messages').innerHTML = '';
    chatLoaded = true;
  }

  appendMsg('user', msg);

  // Crear burbuja de estado (se actualizará con eventos SSE)
  const statusId = 'status-' + Date.now();
  const container = document.getElementById('chat-messages');
  container.innerHTML += `<div class="chat-msg assistant" id="${statusId}">
    <div class="chat-label">🤖 Orquestador</div>
    <div class="chat-bubble status-bubble"><div class="status-items"></div></div>
  </div>`;
  container.scrollTop = container.scrollHeight;

  try {
    const response = await fetch(DASH_URL + '/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {stream: true});
      // SSE events are separated by double newlines
      const parts = buffer.split(String.fromCharCode(10)+String.fromCharCode(10));
      buffer = parts.pop(); // keep incomplete part

      for (const part of parts) {
        if (!part.trim()) continue;
        const lines = part.split(String.fromCharCode(10));
        let eventType = '';
        let eventData = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7);
          else if (line.startsWith('data: ')) eventData = line.slice(6);
        }
        if (eventType && eventData) {
          try {
            const data = JSON.parse(eventData);
            handleSSE(statusId, eventType, data);
          } catch(e) {}
        }
      }
    }
  } catch(e) {
    appendStatusItem(statusId, 'error', 'Error de conexión: ' + e.message);
  }

  document.getElementById('send-btn').disabled = false;
  input.focus();
}

function handleSSE(statusId, eventType, data) {
  const container = document.getElementById('chat-messages');

  if (eventType === 'thinking') {
    appendStatusItem(statusId, 'thinking', data.text);
  } else if (eventType === 'agent_call') {
    appendStatusItem(statusId, 'agent_call', `📡 Consultando a **${data.agent}**: ${data.question}`);
  } else if (eventType === 'agent_response') {
    appendStatusItem(statusId, 'agent_response', `✅ **${data.agent}** respondió: ${data.response}`);
  } else if (eventType === 'heartbeat') {
    appendStatusItem(statusId, 'thinking', data.text);
  } else if (eventType === 'done') {
    // Reemplazar la burbuja de estado con la respuesta final
    const el = document.getElementById(statusId);
    if (el) {
      el.innerHTML = `<div class="chat-label">🤖 Orquestador</div>
        <div class="chat-bubble">${formatMsg(data.text)}</div>`;
    }
  }
  container.scrollTop = container.scrollHeight;
}

function appendStatusItem(statusId, type, text) {
  const el = document.getElementById(statusId);
  if (!el) return;
  const items = el.querySelector('.status-items');
  if (!items) return;

  const cls = type === 'thinking' ? 'st-think' : type === 'agent_call' ? 'st-call' : type === 'agent_response' ? 'st-resp' : 'st-err';
  items.innerHTML += `<div class="status-item ${cls}">${formatMsg(text)}</div>`;
}

function appendMsg(role, text) {
  const container = document.getElementById('chat-messages');
  const label = role === 'user' ? 'Vos' : '🤖 Orquestador';
  container.innerHTML += `
    <div class="chat-msg ${role}">
      <div class="chat-label">${label}</div>
      <div class="chat-bubble">${formatMsg(text)}</div>
    </div>`;
  container.scrollTop = container.scrollHeight;
}

function formatMsg(text) {
  const div = document.createElement('div');
  div.textContent = text;
  let html = div.innerHTML;
  html = html.replace(new RegExp(String.fromCharCode(10), 'g'), '<br>');
  html = html.replace(/[*][*](.+?)[*][*]/g, '<strong>$1</strong>');
  return html;
}
</script>
</body>
</html>"""


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

DASHBOARD_PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    print("🦷 Dashboard Dental Growth iniciando en puerto", DASHBOARD_PORT)
    ssl_key = os.path.join(AGENTS_DIR, "ssl_key.pem")
    ssl_cert = os.path.join(AGENTS_DIR, "ssl_cert.pem")
    kwargs = {"host": "0.0.0.0", "port": DASHBOARD_PORT}
    if os.path.exists(ssl_key) and os.path.exists(ssl_cert):
        kwargs["ssl_keyfile"] = ssl_key
        kwargs["ssl_certfile"] = ssl_cert
        print("🔒 Abrí https://localhost:8000 en tu navegador")
    else:
        print("🌐 Abrí http://localhost:8000 en tu navegador")
    uvicorn.run(app, **kwargs)
