"""
Copy Content — Dental Growth
==============================
Servicio API que genera copies para Instagram usando Claude.
Recibe la transcripción del video + info del negocio y devuelve el copy listo.

Puerto: 8003
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import anthropic
import uvicorn
from config import ANTHROPIC_API_KEY, COPY_CONTENT_PORT

app = FastAPI(title="Copy Content — Dental Growth", version="1.0")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


class CopyRequest(BaseModel):
    transcripcion: str
    info_negocio: Optional[str] = None
    nombre_cliente: str


class CopyResponse(BaseModel):
    copy: str
    palabras: int


PROMPT_TEMPLATE = """Sos un experto en marketing digital para profesionales de la salud y negocios en Costa Rica.

Tu tarea es generar un copy para Instagram basado en un video de un cliente.

IMPORTANTE: No todos los clientes son clínicas dentales. Adaptá el copy al tipo de negocio/servicio que ofrece el cliente según la información proporcionada y el contenido del video. Puede ser odontología, ginecología, fisioterapia, estética, fitness, o cualquier otro rubro.

INFORMACIÓN DEL CLIENTE:
{info_negocio}

TRANSCRIPCIÓN DEL VIDEO:
{transcripcion}

INSTRUCCIONES PARA EL COPY:
1. Empezá con el emoji 📍 seguido de la ubicación del negocio (buscala en la información del cliente)
2. Agregá una línea que introduzca el tema del video de forma atractiva (usá un emoji relevante al rubro: 🦷 dental, 🌸 ginecología, 💪 fitness, ✨ estética, etc.)
3. Si el video menciona varios servicios o beneficios, listá los más importantes con el emoji 🔹
4. Cerrá con una línea que mencione el nombre del negocio/clínica y cómo pueden ayudar
5. El CTA al final debe ser lo que se dijo al final del video (usá 🗓 como emoji)
6. Usá español de Costa Rica: vos, usá, tenés, hacé, etc.
7. NO uses hashtags
8. Máximo 80 palabras. Sé conciso y directo.
9. NUNCA uses asteriscos ni formato bold (**texto**). Instagram no renderiza markdown, así que el texto debe ser plano sin ningún tipo de formato especial.
10. En el CTA, la palabra clave o frase que el usuario debe enviar debe ir entre comillas. Ejemplo: Envianos la palabra "alinear" para agendar tu cita.

FORMATO ESPERADO:
📍 Estamos ubicados en [Ubicación] – [emoji relevante] [Intro del tema del video]
🔹 [Servicio o beneficio 1]
🔹 [Servicio o beneficio 2]
En [Nombre Negocio/Clínica] te ayudamos a [propuesta de valor].
🗓 [CTA con palabra clave entre comillas]

Generá SOLO el copy, sin explicaciones adicionales. Texto plano, sin asteriscos ni markdown."""


@app.get("/")
def root():
    return {"agent": "Copy Content", "status": "running"}


@app.post("/generar", response_model=CopyResponse)
def generar_copy(req: CopyRequest):
    """Genera un copy para Instagram basado en la transcripción y la info del negocio."""
    info = req.info_negocio if req.info_negocio else f"Cliente: {req.nombre_cliente}. No se encontró información adicional del negocio."

    prompt = PROMPT_TEMPLATE.format(
        info_negocio=info,
        transcripcion=req.transcripcion
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    copy = message.content[0].text
    palabras = len(copy.split())

    return CopyResponse(copy=copy, palabras=palabras)


@app.get("/health")
def health():
    return {"status": "ok", "api_key_set": bool(ANTHROPIC_API_KEY)}


# ============================================================
# IA — ENDPOINT /ask (lenguaje natural)
# ============================================================

from agent_brain import ask_agent

COPY_BRAIN_PROMPT = """Sos el agente Copy Content de Dental Growth. Generás copies para Instagram.

Cuando te pidan generar un copy, usá la herramienta generate_copy.
Necesitás: la transcripción del video, la info del negocio, y el nombre del cliente.
Respondé en español de Costa Rica. Sé conciso."""

COPY_TOOLS = [{
    "name": "generate_copy",
    "description": "Genera un copy para Instagram basado en la transcripción y la info del negocio.",
    "input_schema": {
        "type": "object",
        "properties": {
            "transcripcion": {"type": "string", "description": "Transcripción del video"},
            "info_negocio": {"type": "string", "description": "Info del negocio/clínica"},
            "nombre_cliente": {"type": "string", "description": "Nombre del cliente"}
        },
        "required": ["transcripcion", "info_negocio", "nombre_cliente"]
    }
}]


def _copy_tool_executor(name, input_data):
    if name == "generate_copy":
        import httpx
        r = httpx.post(f"http://localhost:{COPY_CONTENT_PORT}/generar",
                       json=input_data, timeout=60)
        return r.json()
    return {"error": f"Herramienta desconocida: {name}"}


class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    try:
        response = ask_agent(req.question, COPY_BRAIN_PROMPT, COPY_TOOLS, _copy_tool_executor)
        return {"response": response}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


if __name__ == "__main__":
    print("✍️  Copy Content iniciando en puerto", COPY_CONTENT_PORT)
    uvicorn.run(app, host="0.0.0.0", port=COPY_CONTENT_PORT)
