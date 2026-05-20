"""
ClickUp Manager — Dental Growth
================================
Servicio API que es el experto en el ClickUp de Dental Growth.
Puede leer, modificar y proporcionar información a otros agentes.

Puerto: 8001
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import json
import uvicorn
from config import CLICKUP_API_KEY, CLICKUP_MANAGER_PORT
from agent_brain import ask_agent

app = FastAPI(title="ClickUp Manager — Dental Growth", version="1.0")

# ============================================================
# CONOCIMIENTO DEL WORKSPACE
# ============================================================

WORKSPACE = {
    "team_id": "90131110564",
    "team_name": "Dental Growth",
    "spaces": {
        "administracion": {"id": "901312256354", "name": "Administracion"},
        "clientes": {"id": "901312256247", "name": "Clientes"},
        "videos": {"id": "90134579132", "name": "Videos"},
        "grabaciones": {"id": "901313679548", "name": "Grabaciones"},
        "content": {"id": "901312257098", "name": "Content"},
        "mentoria": {"id": "901312256625", "name": "Mentoria"},
    },
    "video_lists": {
        "enero_2026": "901324463479",
        "febrero_2026": "901325190899",
        "marzo_2026": "901325940523",
        "abril_2026": "901326704541",
        "mayo_2026": "901327032239",
    },
    "video_statuses": [
        "to do", "grabado", "en edicion",
        "en revision (agencia)", "pendiente de correccion",
        "aprobado (agencia)", "en revision (cliente)",
        "completado", "subido a campanas", "pagado"
    ],
    "editores": [
        {"name": "jano kukita", "id": 106036418, "email": "janokukita@gmail.com"},
        {"name": "valentino argibay", "id": 242488604, "email": "valentinoargibay111@gmail.com"},
    ],
    "admin_lists": {
        "pagos": "901323234572",
        "tareas": "901326329261",
        "entrega_servicio": "901323251880",
    },
    "admin_statuses": {
        "pagos": ["sin iniciar", "activo", "pendiente de pago", "atrasado", "paquete unico", "trimestral", "pausado", "negociación", "no paga"],
        "tareas": ["pendiente", "en curso", "completada", "cerrada"],
    },
    "admin_fields": {
        "monto_total": "dab0d187-fc2a-44dd-80b6-71a2a1ad1e10",
        "fecha_pago": "9f6d4197-0793-4f77-a4b5-b49e8cb8b36a",
        "servicio": "4cdf7522-dd40-4b43-8249-582795b53364",
        "tareas_rel": "79dfd1d1-2932-4ccd-a148-6c1427411a32",
    },
    "custom_fields": {
        "precio": "318db772-e2d3-4f10-b43a-21a9c39d5f02",
        "tema": "7dbf2727-6615-49fa-aa4c-2de3069b0000",
        "drive": "b5debb04-ba11-44f7-b59c-3f6c95d1d35c",
    },
    "clientes": {
        "cirugia vargas scott": {"folder_id": "901315589291", "list_id": "901323234409"},
        "villaskincr": {"folder_id": "901315589289", "list_id": "901323234408"},
        "yendry": {"folder_id": "901315589282", "list_id": "901323234401"},
        "bruno - fit and tasty": {"folder_id": "901315589299", "list_id": "901323234415"},
        "pablo jimenez": {"folder_id": "901315589296", "list_id": "901323234413"},
        "verona concept": {"folder_id": "901315589272", "list_id": "901323234390"},
        "belen dental": {"folder_id": "901315589302", "list_id": "901323234419"},
        "mg ortodoncia invisible": {"folder_id": "901315589288", "list_id": "901323234407"},
        "odontoser": {"folder_id": "901315589308", "list_id": None},
        "richard leather": {"folder_id": "901315589269", "list_id": "901323234387"},
        "viluxor": {"folder_id": "901315589283", "list_id": "901323234402"},
        "ortodoncia loranca": {"folder_id": "901315589273", "list_id": "901323234392"},
        "estefania arce": {"folder_id": "901315589284", "list_id": "901323234403"},
        "chefteo barf": {"folder_id": "901315589281", "list_id": "901323234400"},
        "hero parties": {"folder_id": "901315589277", "list_id": "901323234397"},
        "newsmile": {"folder_id": "901315589306", "list_id": "901323234424"},
        "smilepro": {"folder_id": "901315589307", "list_id": "901323234425"},
        "ortho-tandem": {"folder_id": "901315589278", "list_id": "901323234399"},
        "anthony vasquez": {"folder_id": "901315589268", "list_id": "901323234386"},
        "navas medrano": {"folder_id": "901315589297", "list_id": None},
        "montero smile art": {"folder_id": "901315589293", "list_id": "901326423924"},
        "centro medico cyrman": {"folder_id": "901315589313", "list_id": "901323234430"},
        "dental legacy": {"folder_id": "901315589274", "list_id": "901323234394"},
        "bustamante dental c": {"folder_id": "901315589304", "list_id": "901323234423"},
        "dra paula chacon": {"folder_id": "901315589270", "list_id": "901323234388"},
        "duo dental": {"folder_id": "901315589311", "list_id": "901323234429"},
        "royal dental": {"folder_id": "901315589295", "list_id": "901323234412"},
        "priscila mendoza": {"folder_id": "901315589314", "list_id": "901323234431"},
        "innova dental": {"folder_id": "901315589285", "list_id": "901326423950"},
        "sabrina arguello": {"folder_id": "901315589303", "list_id": "901323234422"},
        "horizon medical": {"folder_id": "901315589298", "list_id": "901323234414"},
        "acrogym": {"folder_id": "901315589315", "list_id": "901323234432"},
        "sonrident": {"folder_id": "901315756388", "list_id": "901323488021"},
        "aura dental": {"folder_id": "901315761044", "list_id": "901323494855"},
        "prime dental": {"folder_id": "901315835584", "list_id": "901323598309"},
        "dentium": {"folder_id": "901316057629", "list_id": "901326423965"},
        "neuro learn and play": {"folder_id": "901316200279", "list_id": "901324133615"},
        "pablo montero": {"folder_id": "901316512040", "list_id": "901324578563"},
        "nova dentis": {"folder_id": "901316524889", "list_id": "901324596302"},
        "dariana vasquez": {"folder_id": "901316557594", "list_id": "901324644123"},
        "dra. maria elena": {"folder_id": "901316766491", "list_id": "901324938210"},
        "ana porras": {"folder_id": "901316883953", "list_id": "901325102770"},
        "ortho correct": {"folder_id": "901317075615", "list_id": "901325379760"},
        "numay": {"folder_id": "901317180170", "list_id": "901325530796"},
        "lienzo dental": {"folder_id": "901317261789", "list_id": "901325649866"},
        "clinica mahelet": {"folder_id": "901317323803", "list_id": "901325736425"},
        "dra laly brickler": {"folder_id": "901317691112", "list_id": "901326256336"},
    }
}

VIDEO_EXTENSIONS = [".mov", ".mp4", ".avi", ".mkv", ".webm"]

headers = {
    "Authorization": CLICKUP_API_KEY,
    "Content-Type": "application/json"
}


# ============================================================
# MODELOS DE REQUEST/RESPONSE
# ============================================================

class SetFieldRequest(BaseModel):
    task_id: str
    field_id: str
    value: str

class SetStatusRequest(BaseModel):
    task_id: str
    status: str

class CreateTaskRequest(BaseModel):
    list_id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    assignees: Optional[list] = None

class MoveTaskRequest(BaseModel):
    task_id: str
    list_id: str

class AddCommentRequest(BaseModel):
    task_id: str
    comment_text: str
    notify_all: bool = False


# ============================================================
# HELPERS INTERNOS
# ============================================================

def _clickup_get(url, params=None):
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def _clickup_post(url, body):
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()

def _clickup_put(url, body):
    response = requests.put(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()

def _buscar_cliente(nombre):
    """Busca un cliente por nombre (match flexible)."""
    nombre_lower = nombre.lower().strip()
    for key, data in WORKSPACE["clientes"].items():
        if nombre_lower in key or key in nombre_lower:
            return {**data, "key": key}
        palabras = nombre_lower.split()
        if len(palabras) >= 2 and all(p in key for p in palabras):
            return {**data, "key": key}
    return None

def _extraer_nombre_cliente(nombre_tarea):
    """'Prime Dental #1' → 'Prime Dental', 'Dentium 6' → 'Dentium'"""
    import re
    nombre = nombre_tarea.rsplit("#", 1)[0].strip()
    nombre = re.sub(r'\s+\d+$', '', nombre).strip()
    return nombre

def _buscar_video_en_comentarios(comentarios):
    """Busca el último video subido por un editor en los comentarios."""
    editores_nombres = [e["name"] for e in WORKSPACE["editores"]]

    for comentario in reversed(comentarios):
        user_data = comentario.get("user", {})
        autor = user_data.get("username", "").lower()
        nombre_autor = user_data.get("name", "").lower()

        es_editor = any(
            editor in autor or editor in nombre_autor
            for editor in editores_nombres
        )
        if not es_editor:
            continue

        comment_blocks = comentario.get("comment", [])
        if isinstance(comment_blocks, list):
            for block in comment_blocks:
                if not isinstance(block, dict):
                    continue

                url_archivo = None
                nombre_archivo = None

                # Tipo "frame" — videos via ClickUp
                frame = block.get("frame", {})
                if frame:
                    url_archivo = frame.get("url", "") or frame.get("src", "")
                    nombre_archivo = frame.get("id", "")
                    if not nombre_archivo and url_archivo:
                        from urllib.parse import urlparse, unquote
                        path = urlparse(url_archivo).path
                        nombre_archivo = unquote(path.split("/")[-1])

                # Tipo "attachment"
                attachment = block.get("attachment", {})
                if attachment:
                    url_archivo = attachment.get("url", "")
                    nombre_archivo = attachment.get("title", "") or attachment.get("name", "")

                if url_archivo and nombre_archivo:
                    if any(nombre_archivo.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        return {
                            "url": url_archivo,
                            "nombre": nombre_archivo,
                            "autor": nombre_autor or autor,
                            "fecha": comentario.get("date")
                        }

    return None


# ============================================================
# ENDPOINTS — INFORMACIÓN DEL WORKSPACE
# ============================================================

@app.get("/")
def root():
    return {"agent": "ClickUp Manager", "status": "running", "workspace": "Dental Growth"}

@app.get("/workspace")
def get_workspace():
    """Retorna la estructura completa del workspace."""
    return WORKSPACE

@app.get("/workspace/spaces")
def get_spaces():
    return WORKSPACE["spaces"]

@app.get("/workspace/clientes")
def get_clientes():
    return WORKSPACE["clientes"]

@app.get("/workspace/video-lists")
def get_video_lists():
    return WORKSPACE["video_lists"]

@app.get("/workspace/statuses")
def get_video_statuses():
    return WORKSPACE["video_statuses"]


# ============================================================
# ENDPOINTS — TAREAS
# ============================================================

@app.get("/buscar/{cliente}")
def buscar_tareas_cliente(cliente: str, mes: Optional[str] = None, con_video: bool = False):
    """Búsqueda inteligente de tareas de un cliente en las listas de videos mensuales.

    - cliente: nombre del cliente (match flexible: "dentium", "smile pro", etc.)
    - mes: "marzo", "abril", etc. Si no se indica, busca en todos.
    - con_video: si True, solo devuelve tareas que tienen video del editor.
    """
    import re
    cliente_lower = cliente.lower().strip()

    # Determinar en qué listas buscar
    listas_a_buscar = {}
    if mes:
        mes_lower = mes.lower().strip()
        for key, lid in WORKSPACE["video_lists"].items():
            if mes_lower in key:
                listas_a_buscar[key] = lid
    if not listas_a_buscar:
        # Buscar en todas, más reciente primero
        listas_a_buscar = dict(reversed(list(WORKSPACE["video_lists"].items())))

    resultados = []
    for mes_key, list_id in listas_a_buscar.items():
        try:
            data = _clickup_get(
                f"https://api.clickup.com/api/v2/list/{list_id}/task",
                params={"include_closed": "true"}
            )
        except Exception:
            continue

        for t in data.get("tasks", []):
            nombre_tarea = t["name"].lower()
            # Match flexible: el nombre del cliente aparece en el nombre de la tarea
            if cliente_lower not in nombre_tarea:
                # Intentar con palabras individuales
                palabras = cliente_lower.split()
                if not all(p in nombre_tarea for p in palabras):
                    continue

            # Extraer info del campo "tema" (copy)
            copy = None
            for cf in t.get("custom_fields", []):
                if cf.get("id") == WORKSPACE["custom_fields"]["tema"] and cf.get("value"):
                    copy = cf["value"]
                    break

            tarea_info = {
                "task_id": t["id"],
                "nombre": t["name"],
                "status": t.get("status", {}).get("status", ""),
                "mes": mes_key,
                "tiene_copy": copy is not None,
                "copy_preview": (copy[:150] + "...") if copy and len(copy) > 150 else copy,
            }

            # Si piden con video, verificar comentarios
            if con_video:
                try:
                    comentarios = _clickup_get(
                        f"https://api.clickup.com/api/v2/task/{t['id']}/comment"
                    ).get("comments", [])
                    video = _buscar_video_en_comentarios(comentarios)
                    if video:
                        tarea_info["video"] = video
                    else:
                        continue  # Saltar si no tiene video
                except Exception:
                    continue

            resultados.append(tarea_info)

    return {
        "cliente": cliente,
        "resultados": resultados,
        "total": len(resultados),
        "listas_buscadas": list(listas_a_buscar.keys()),
    }


@app.get("/tarea/{task_id}/copy")
def get_tarea_copy(task_id: str):
    """Obtiene el copy (campo tema) de una tarea específica."""
    t = _clickup_get(f"https://api.clickup.com/api/v2/task/{task_id}")
    for cf in t.get("custom_fields", []):
        if cf.get("id") == WORKSPACE["custom_fields"]["tema"] and cf.get("value"):
            return {"task_id": task_id, "nombre": t["name"], "copy": cf["value"]}
    return {"task_id": task_id, "nombre": t["name"], "copy": None, "error": "No tiene copy en campo tema"}


@app.get("/tareas/{list_id}")
def get_tareas(list_id: str, status: Optional[str] = None):
    """Obtiene tareas de una lista, opcionalmente filtradas por estado."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    params = {"include_closed": "true"}
    if status:
        params["statuses[]"] = [status]
    data = _clickup_get(url, params)
    return data.get("tasks", [])

@app.get("/tareas/{list_id}/completadas")
def get_tareas_completadas(list_id: str):
    """Obtiene tareas con estado COMPLETADO de una lista."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    params = {"statuses[]": ["COMPLETADO"], "include_closed": "true"}
    data = _clickup_get(url, params)
    return data.get("tasks", [])

@app.get("/tarea/{task_id}")
def get_tarea(task_id: str):
    """Obtiene una tarea específica por ID."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    return _clickup_get(url)

@app.post("/tarea/crear")
def crear_tarea(req: CreateTaskRequest):
    """Crea una nueva tarea en una lista."""
    url = f"https://api.clickup.com/api/v2/list/{req.list_id}/task"
    body = {"name": req.name}
    if req.description:
        body["description"] = req.description
    if req.status:
        body["status"] = req.status
    if req.assignees:
        body["assignees"] = req.assignees
    return _clickup_post(url, body)

@app.put("/tarea/mover")
def mover_tarea(req: MoveTaskRequest):
    """Mueve una tarea a otra lista."""
    url = f"https://api.clickup.com/api/v2/list/{req.list_id}/task/{req.task_id}"
    return _clickup_post(url, {})


# ============================================================
# ENDPOINTS — ESTADOS
# ============================================================

@app.put("/tarea/status")
def cambiar_status(req: SetStatusRequest):
    """Cambia el estado de una tarea."""
    url = f"https://api.clickup.com/api/v2/task/{req.task_id}"
    return _clickup_put(url, {"status": req.status})


# ============================================================
# ENDPOINTS — CAMPOS PERSONALIZADOS
# ============================================================

@app.get("/campos/{list_id}")
def get_campos(list_id: str):
    """Obtiene los campos personalizados de una lista."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}/field"
    data = _clickup_get(url)
    return data.get("fields", [])

@app.get("/campo-tema/{task_id}")
def get_campo_tema(task_id: str):
    """Obtiene el valor del campo 'tema' de una tarea."""
    tarea = get_tarea(task_id)
    for field in tarea.get("custom_fields", []):
        if field.get("name", "").lower().strip() == "tema":
            return {"field_id": field["id"], "value": field.get("value")}
    return {"field_id": None, "value": None}

@app.post("/campo/set")
def set_campo(req: SetFieldRequest):
    """Establece el valor de un campo personalizado."""
    url = f"https://api.clickup.com/api/v2/task/{req.task_id}/field/{req.field_id}"
    response = requests.post(url, headers=headers, json={"value": req.value})
    return {"success": response.status_code == 200, "status_code": response.status_code}


# ============================================================
# ENDPOINTS — COMENTARIOS Y VIDEOS
# ============================================================

@app.get("/comentarios/{task_id}")
def get_comentarios(task_id: str):
    """Obtiene los comentarios de una tarea."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
    data = _clickup_get(url)
    return data.get("comments", [])

@app.post("/comentario/crear")
def crear_comentario(req: AddCommentRequest):
    """Agrega un comentario a una tarea."""
    url = f"https://api.clickup.com/api/v2/task/{req.task_id}/comment"
    return _clickup_post(url, {
        "comment_text": req.comment_text,
        "notify_all": req.notify_all
    })

@app.get("/video/{task_id}")
def get_video_editor(task_id: str):
    """Busca el último video subido por un editor en una tarea."""
    comentarios = get_comentarios(task_id)
    video = _buscar_video_en_comentarios(comentarios)
    if not video:
        raise HTTPException(status_code=404, detail="No se encontró video del editor")
    return video


# ============================================================
# ENDPOINTS — INFO DEL NEGOCIO (CLIENTES)
# ============================================================

@app.get("/cliente/{nombre}/info")
def get_info_negocio(nombre: str):
    """
    Busca la información del negocio de un cliente.
    Intenta leer docs y tareas de la carpeta del cliente en el espacio Clientes.
    """
    cliente = _buscar_cliente(nombre)
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente '{nombre}' no encontrado")

    if not cliente.get("list_id"):
        raise HTTPException(status_code=404, detail=f"Cliente '{nombre}' no tiene lista")

    # Intentar leer tareas de la lista del cliente (la info suele estar ahí)
    url = f"https://api.clickup.com/api/v2/list/{cliente['list_id']}/task"
    try:
        data = _clickup_get(url)
        tasks = data.get("tasks", [])
        if tasks:
            info_parts = []
            for task in tasks:
                desc = task.get("description", "")
                if desc:
                    info_parts.append(f"{task['name']}: {desc}")
            if info_parts:
                return {"cliente": cliente["key"], "info": "\n\n".join(info_parts)}
    except Exception:
        pass

    return {"cliente": cliente["key"], "info": None}


# ============================================================
# ENDPOINTS — UTILIDADES
# ============================================================

@app.get("/extraer-cliente/{nombre_tarea}")
def extraer_cliente(nombre_tarea: str):
    """Extrae el nombre del cliente del nombre de la tarea."""
    return {"cliente": _extraer_nombre_cliente(nombre_tarea)}

@app.get("/tareas-para-copy/{list_id}")
def get_tareas_para_copy(list_id: str):
    """
    Endpoint especial: retorna tareas COMPLETADAS que NO tienen copy en 'tema'.
    Incluye el video del editor y el nombre del cliente extraído.
    Ideal para que el orquestador sepa qué procesar.
    """
    tareas = get_tareas_completadas(list_id)
    resultado = []

    for tarea in tareas:
        # Verificar si ya tiene copy
        tiene_copy = False
        for field in tarea.get("custom_fields", []):
            if field.get("name", "").lower().strip() == "tema":
                valor = field.get("value")
                if valor and str(valor).strip():
                    tiene_copy = True
                break

        if tiene_copy:
            continue

        nombre_cliente = _extraer_nombre_cliente(tarea["name"])

        resultado.append({
            "task_id": tarea["id"],
            "nombre_tarea": tarea["name"],
            "nombre_cliente": nombre_cliente,
        })

    return resultado


# ============================================================
# ENDPOINTS — ADMINISTRACIÓN (Pagos, Tareas Admin, Entrega)
# ============================================================

@app.get("/admin/pagos")
def get_pagos(status: Optional[str] = None):
    """Lista todos los clientes de la lista de Pagos con su estado y monto."""
    list_id = WORKSPACE["admin_lists"]["pagos"]
    params = {"include_closed": "true"}
    if status:
        params["statuses[]"] = status
    data = _clickup_get(f"https://api.clickup.com/api/v2/list/{list_id}/task", params=params)
    resultado = []
    for t in data.get("tasks", []):
        info = {
            "task_id": t["id"],
            "cliente": t["name"],
            "status": t.get("status", {}).get("status", ""),
        }
        for cf in t.get("custom_fields", []):
            if cf["id"] == WORKSPACE["admin_fields"]["monto_total"] and cf.get("value") is not None:
                info["monto"] = cf["value"]
            elif cf["id"] == WORKSPACE["admin_fields"]["fecha_pago"] and cf.get("value") is not None:
                info["fecha_pago"] = cf["value"]
            elif cf["id"] == WORKSPACE["admin_fields"]["servicio"] and cf.get("value") is not None:
                # dropdown — extraer la opción seleccionada
                opciones = cf.get("type_config", {}).get("options", [])
                for opt in opciones:
                    if opt.get("orderindex") == cf["value"]:
                        info["servicio"] = opt.get("name", cf["value"])
                        break
                else:
                    info["servicio"] = cf["value"]
        resultado.append(info)
    return {"pagos": resultado, "total": len(resultado)}


@app.get("/admin/pagos/{cliente}")
def get_pagos_cliente(cliente: str):
    """Busca el estado de pago de un cliente específico."""
    all_pagos = get_pagos()
    nombre_lower = cliente.lower().strip()
    matches = []
    for p in all_pagos["pagos"]:
        if nombre_lower in p["cliente"].lower() or p["cliente"].lower() in nombre_lower:
            matches.append(p)
    if not matches:
        # Buscar palabra por palabra
        palabras = nombre_lower.split()
        for p in all_pagos["pagos"]:
            cl = p["cliente"].lower()
            if any(w in cl for w in palabras):
                matches.append(p)
    if not matches:
        raise HTTPException(status_code=404, detail=f"Cliente '{cliente}' no encontrado en pagos")
    return {"cliente": cliente, "resultados": matches}


@app.put("/admin/pagos/status")
def set_pago_status(req: SetStatusRequest):
    """Cambia el estado de pago de un cliente."""
    valid = WORKSPACE["admin_statuses"]["pagos"]
    if req.status.lower() not in valid:
        raise HTTPException(status_code=400, detail=f"Status inválido. Opciones: {valid}")
    url = f"https://api.clickup.com/api/v2/task/{req.task_id}"
    response = requests.put(url, headers=headers, json={"status": req.status.lower()})
    return {"success": response.status_code == 200, "status_code": response.status_code}


@app.put("/admin/pagos/monto")
def set_pago_monto(task_id: str, monto: float):
    """Actualiza el monto de un cliente."""
    field_id = WORKSPACE["admin_fields"]["monto_total"]
    url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}"
    response = requests.post(url, headers=headers, json={"value": monto})
    return {"success": response.status_code == 200}


@app.get("/admin/tareas")
def get_tareas_admin(status: Optional[str] = None):
    """Lista tareas del espacio de Administración."""
    list_id = WORKSPACE["admin_lists"]["tareas"]
    params = {"include_closed": "true"}
    if status:
        params["statuses[]"] = status
    data = _clickup_get(f"https://api.clickup.com/api/v2/list/{list_id}/task", params=params)
    resultado = []
    for t in data.get("tasks", []):
        resultado.append({
            "task_id": t["id"],
            "nombre": t["name"],
            "status": t.get("status", {}).get("status", ""),
            "assignees": [a.get("username", "") for a in t.get("assignees", [])],
        })
    return {"tareas": resultado, "total": len(resultado)}


@app.post("/admin/tareas/crear")
def crear_tarea_admin(req: CreateTaskRequest):
    """Crea una tarea en la lista de Tareas Admin."""
    req.list_id = WORKSPACE["admin_lists"]["tareas"]
    return crear_tarea(req)


@app.get("/admin/entregas")
def get_entregas(status: Optional[str] = None):
    """Lista el estado de entrega de servicio por cliente."""
    list_id = WORKSPACE["admin_lists"]["entrega_servicio"]
    params = {"include_closed": "true"}
    if status:
        params["statuses[]"] = status
    data = _clickup_get(f"https://api.clickup.com/api/v2/list/{list_id}/task", params=params)
    resultado = []
    for t in data.get("tasks", []):
        resultado.append({
            "task_id": t["id"],
            "cliente": t["name"],
            "status": t.get("status", {}).get("status", ""),
        })
    return {"entregas": resultado, "total": len(resultado)}


class NuevoClienteRequest(BaseModel):
    nombre: str
    monto: float
    fecha_inicio: Optional[str] = None  # ISO format "2026-04-07", default=hoy
    trimestral: bool = False  # True = trimestral, False = activo (mensual u otro)
    status_entrega: str = "onboarding"


@app.post("/admin/nuevo-cliente")
def crear_nuevo_cliente(req: NuevoClienteRequest):
    """Registra un nuevo cliente: crea tarea en Pagos y en Entrega de Servicio."""
    from datetime import datetime

    # Calcular timestamp de fecha inicio
    if req.fecha_inicio:
        dt = datetime.strptime(req.fecha_inicio, "%Y-%m-%d")
    else:
        dt = datetime.now()
    ts = int(dt.timestamp() * 1000)

    resultados = {}

    # Calcular fecha límite = inicio + 3 meses
    from dateutil.relativedelta import relativedelta
    fecha_fin_trimestre = dt + relativedelta(months=3)
    ts_fin = int(fecha_fin_trimestre.timestamp() * 1000)

    # 1. Crear en Pagos
    status_pago = "trimestral" if req.trimestral else "activo"
    pagos_body = {
        "name": req.nombre,
        "status": status_pago,
        "start_date": ts,
        "due_date": ts_fin,
        "custom_fields": [
            {"id": WORKSPACE["admin_fields"]["monto_total"], "value": req.monto},
            {"id": WORKSPACE["admin_fields"]["fecha_pago"], "value": ts},
        ]
    }
    pagos_resp = _clickup_post(
        f"https://api.clickup.com/api/v2/list/{WORKSPACE['admin_lists']['pagos']}/task",
        pagos_body
    )
    resultados["pagos"] = {
        "task_id": pagos_resp.get("id"),
        "nombre": pagos_resp.get("name"),
        "status": pagos_resp.get("status", {}).get("status"),
        "url": pagos_resp.get("url"),
    }

    # 2. Crear en Entrega de Servicio con fecha límite = inicio + 3 meses
    from dateutil.relativedelta import relativedelta
    fecha_fin_trimestre = dt + relativedelta(months=3)
    ts_fin = int(fecha_fin_trimestre.timestamp() * 1000)

    entrega_body = {
        "name": req.nombre,
        "status": req.status_entrega,
        "custom_fields": [
            {"id": "8a2da0e5-f2dc-44df-bed1-5f82453d8590", "value": ts_fin},
        ]
    }
    entrega_resp = _clickup_post(
        f"https://api.clickup.com/api/v2/list/{WORKSPACE['admin_lists']['entrega_servicio']}/task",
        entrega_body
    )
    resultados["entrega_servicio"] = {
        "task_id": entrega_resp.get("id"),
        "nombre": entrega_resp.get("name"),
        "status": entrega_resp.get("status", {}).get("status"),
        "url": entrega_resp.get("url"),
    }

    return {"success": True, "cliente": req.nombre, "resultados": resultados}


@app.get("/admin/resumen/{cliente}")
def resumen_cliente(cliente: str):
    """Resumen completo de un cliente: pagos, tareas admin, entregas y videos."""
    resultado = {"cliente": cliente}

    # Pagos
    try:
        pagos = get_pagos_cliente(cliente)
        resultado["pagos"] = pagos["resultados"]
    except Exception:
        resultado["pagos"] = []

    # Tareas admin que contengan el nombre
    try:
        tareas = get_tareas_admin()
        nombre_lower = cliente.lower()
        resultado["tareas_admin"] = [t for t in tareas["tareas"] if nombre_lower in t["nombre"].lower()]
    except Exception:
        resultado["tareas_admin"] = []

    # Entregas
    try:
        entregas = get_entregas()
        nombre_lower = cliente.lower()
        resultado["entregas"] = [e for e in entregas["entregas"] if nombre_lower in e["cliente"].lower()]
    except Exception:
        resultado["entregas"] = []

    # Info del negocio
    try:
        info = get_info_negocio(cliente)
        resultado["info_negocio"] = info.get("info")
    except Exception:
        resultado["info_negocio"] = None

    return resultado


# ============================================================
# IA — ENDPOINT /ask (lenguaje natural)
# ============================================================

CLICKUP_BRAIN_PROMPT = f"""Sos el ClickUp Manager de Dental Growth. Sos un experto en el workspace de ClickUp de la agencia.

Tenés herramientas para consultar y modificar el ClickUp. Usá las herramientas para responder lo que te pidan.

## Info del workspace
- Listas de videos mensuales: {json.dumps(WORKSPACE['video_lists'])}
- Clientes: {json.dumps(list(WORKSPACE['clientes'].keys()))}
- Custom fields: tema={WORKSPACE['custom_fields']['tema']}, precio={WORKSPACE['custom_fields']['precio']}
- Las tareas de video tienen formato "Cliente | Título" o "Cliente #N"
- Los videos de los editores están en los COMENTARIOS de cada tarea (usá get_video)

## Registrar nuevo cliente (herramienta: nuevo_cliente)
Cuando te pidan agregar un cliente nuevo, usá la herramienta "nuevo_cliente". Reglas:
- SIEMPRE preguntá: nombre, monto y si paga trimestral o mensual.
- Si paga trimestral → trimestral: true (status "trimestral" en Pagos)
- Si paga mensual u otro método → trimestral: false (status "activo" en Pagos)
- La fecha límite se calcula SIEMPRE automáticamente como fecha_inicio + 3 meses. Se pone tanto en Pagos (due_date) como en Entrega de Servicio (campo Fecha limite).
- Se crea la tarea en Pagos Y en Entrega de Servicio (status "onboarding") automáticamente.

Respondé en español de Costa Rica. Sé conciso y directo. Siempre usá las herramientas — no inventés datos."""

CLICKUP_TOOLS = [
    {
        "name": "get_tasks",
        "description": "Obtiene tareas de una lista. Podés filtrar por estado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ID de la lista"},
                "status": {"type": "string", "description": "Filtrar por estado (opcional)"}
            },
            "required": ["list_id"]
        }
    },
    {
        "name": "get_completed_tasks",
        "description": "Obtiene tareas completadas de una lista.",
        "input_schema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ID de la lista"}
            },
            "required": ["list_id"]
        }
    },
    {
        "name": "get_task",
        "description": "Obtiene detalle de una tarea específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID de la tarea"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_video",
        "description": "Encuentra el video del editor en los comentarios de una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ID de la tarea"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_client_info",
        "description": "Obtiene info del negocio de un cliente (ubicación, servicios, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del cliente"}
            },
            "required": ["nombre"]
        }
    },
    {
        "name": "get_tasks_for_copy",
        "description": "Obtiene tareas completadas que todavía no tienen copy generado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ID de la lista"}
            },
            "required": ["list_id"]
        }
    },
    {
        "name": "set_field",
        "description": "Establece un campo personalizado en una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "field_id": {"type": "string"},
                "value": {"type": "string"}
            },
            "required": ["task_id", "field_id", "value"]
        }
    },
    {
        "name": "set_status",
        "description": "Cambia el estado de una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["task_id", "status"]
        }
    },
    {
        "name": "add_comment",
        "description": "Agrega un comentario a una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "text": {"type": "string"}
            },
            "required": ["task_id", "text"]
        }
    },
    {
        "name": "get_comments",
        "description": "Obtiene los comentarios de una tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "nuevo_cliente",
        "description": "Registra un nuevo cliente en Pagos y Entrega de Servicio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del cliente"},
                "monto": {"type": "number", "description": "Monto en dólares"},
                "fecha_inicio": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD), default=hoy"},
                "trimestral": {"type": "boolean", "description": "True si paga trimestral, False si es mensual/otro (default: false)"},
                "status_entrega": {"type": "string", "description": "Status en entrega (default: onboarding)"}
            },
            "required": ["nombre", "monto"]
        }
    }
]


def _clickup_tool_executor(name, input_data):
    """Ejecuta las herramientas del ClickUp Manager."""
    base = "https://api.clickup.com/api/v2"

    if name == "get_tasks":
        list_id = input_data["list_id"]
        params = {"include_closed": "true"}
        if "status" in input_data and input_data["status"]:
            params["statuses[]"] = input_data["status"]
        data = _clickup_get(f"{base}/list/{list_id}/task", params=params)
        # Simplificar respuesta
        tasks = []
        for t in data.get("tasks", []):
            tasks.append({
                "id": t["id"],
                "name": t["name"],
                "status": t.get("status", {}).get("status", ""),
                "assignees": [a.get("username", "") for a in t.get("assignees", [])],
            })
        return {"tasks": tasks, "count": len(tasks)}

    elif name == "get_completed_tasks":
        list_id = input_data["list_id"]
        data = _clickup_get(f"{base}/list/{list_id}/task", params={
            "include_closed": "true",
            "statuses[]": "completado"
        })
        tasks = [{"id": t["id"], "name": t["name"]} for t in data.get("tasks", [])]
        return {"tasks": tasks, "count": len(tasks)}

    elif name == "get_task":
        task_id = input_data["task_id"]
        t = _clickup_get(f"{base}/task/{task_id}")
        return {
            "id": t["id"], "name": t["name"],
            "status": t.get("status", {}).get("status", ""),
            "description": (t.get("description") or "")[:500],
            "custom_fields": [{
                "name": cf.get("name"), "value": cf.get("value")
            } for cf in t.get("custom_fields", []) if cf.get("value")]
        }

    elif name == "get_video":
        task_id = input_data["task_id"]
        data = _clickup_get(f"{base}/task/{task_id}/comment")
        comments = data.get("comments", [])
        result = _buscar_video_en_comentarios(comments)
        if result:
            return result
        return {"error": "No se encontró video en los comentarios"}

    elif name == "get_client_info":
        nombre = input_data["nombre"]
        cliente = _buscar_cliente(nombre)
        if not cliente:
            return {"error": f"Cliente '{nombre}' no encontrado"}
        folder_id = cliente["folder_id"]
        data = _clickup_get(f"{base}/folder/{folder_id}/list")
        for lst in data.get("lists", []):
            task_data = _clickup_get(f"{base}/list/{lst['id']}/task")
            for t in task_data.get("tasks", []):
                if t.get("description"):
                    return {"cliente": cliente["key"], "info": t["description"][:1000]}
        return {"cliente": cliente["key"], "info": "Sin información de negocio"}

    elif name == "get_tasks_for_copy":
        list_id = input_data["list_id"]
        # Reusar endpoint existente
        import httpx
        r = httpx.get(f"http://localhost:{CLICKUP_MANAGER_PORT}/tareas-para-copy/{list_id}", timeout=30)
        return r.json()

    elif name == "set_field":
        task_id = input_data["task_id"]
        field_id = input_data["field_id"]
        value = input_data["value"]
        result = _clickup_post(f"{base}/task/{task_id}/field/{field_id}", {"value": value})
        return {"success": True}

    elif name == "set_status":
        task_id = input_data["task_id"]
        status = input_data["status"]
        _clickup_put(f"{base}/task/{task_id}", {"status": status})
        return {"success": True}

    elif name == "add_comment":
        task_id = input_data["task_id"]
        text = input_data["text"]
        _clickup_post(f"{base}/task/{task_id}/comment", {"comment_text": text})
        return {"success": True}

    elif name == "get_comments":
        task_id = input_data["task_id"]
        data = _clickup_get(f"{base}/task/{task_id}/comment")
        comments = []
        for c in data.get("comments", [])[-10:]:
            comments.append({
                "author": c.get("user", {}).get("name", ""),
                "text": c.get("comment_text", "")[:200],
                "date": c.get("date", ""),
            })
        return {"comments": comments}

    elif name == "nuevo_cliente":
        import httpx
        body = {
            "nombre": input_data["nombre"],
            "monto": input_data["monto"],
        }
        if "fecha_inicio" in input_data:
            body["fecha_inicio"] = input_data["fecha_inicio"]
        if "trimestral" in input_data:
            body["trimestral"] = input_data["trimestral"]
        if "status_entrega" in input_data:
            body["status_entrega"] = input_data["status_entrega"]
        r = httpx.post(f"http://localhost:{CLICKUP_MANAGER_PORT}/admin/nuevo-cliente", json=body, timeout=30)
        return r.json()

    return {"error": f"Herramienta desconocida: {name}"}


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(req: AskRequest):
    """Endpoint de IA — recibe una pregunta en lenguaje natural y la resuelve."""
    try:
        response = ask_agent(
            question=req.question,
            system_prompt=CLICKUP_BRAIN_PROMPT,
            tools=CLICKUP_TOOLS,
            tool_executor=_clickup_tool_executor,
        )
        return {"response": response}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    print("🏢 ClickUp Manager iniciando en puerto", CLICKUP_MANAGER_PORT)
    uvicorn.run(app, host="0.0.0.0", port=CLICKUP_MANAGER_PORT)
