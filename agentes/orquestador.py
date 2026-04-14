"""
Orquestador — Dental Growth
=============================
Levanta los 3 agentes en paralelo y coordina el flujo completo:
1. Pide a ClickUp Manager las tareas pendientes de copy
2. Para cada tarea, en paralelo:
   a. Pide el video a ClickUp Manager
   b. Envía el video al Transcriber
   c. Pide la info del negocio a ClickUp Manager
   d. Envía transcripción + info al Copy Content
   e. Guarda el copy via ClickUp Manager
"""

import subprocess
import sys
import time
import requests
import asyncio
import httpx
import os
import signal
from config import (
    CLICKUP_MANAGER_URL, TRANSCRIBER_URL, COPY_CONTENT_URL,
    CLICKUP_MANAGER_PORT, TRANSCRIBER_PORT, COPY_CONTENT_PORT
)

# Directorio de los agentes
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

processes = []


def iniciar_agentes():
    """Levanta los 3 agentes como subprocesos."""
    agentes = [
        ("ClickUp Manager", "clickup_manager.py", CLICKUP_MANAGER_PORT),
        ("Transcriber", "transcriber.py", TRANSCRIBER_PORT),
        ("Copy Content", "copy_content.py", COPY_CONTENT_PORT),
    ]

    for nombre, archivo, puerto in agentes:
        ruta = os.path.join(AGENTS_DIR, archivo)
        python = "/usr/local/bin/python3.12"
        proc = subprocess.Popen(
            [python, ruta],
            cwd=AGENTS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append(proc)
        print(f"   🟢 {nombre} (PID {proc.pid}) → puerto {puerto}")

    # Esperar a que todos estén listos
    print("\n⏳ Esperando que los agentes estén listos...")
    for nombre, _, puerto in agentes:
        url = f"http://localhost:{puerto}/"
        for intento in range(30):
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    print(f"   ✅ {nombre} listo")
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            print(f"   ❌ {nombre} no respondió después de 30s")
            detener_agentes()
            sys.exit(1)

    print()


def detener_agentes():
    """Detiene todos los subprocesos."""
    for proc in processes:
        proc.terminate()
    for proc in processes:
        proc.wait(timeout=5)


async def procesar_tarea(client: httpx.AsyncClient, tarea: dict, campo_tema_id: str):
    """Procesa una tarea completa: video → transcripción → copy → guardar."""
    task_id = tarea["task_id"]
    nombre_tarea = tarea["nombre_tarea"]
    nombre_cliente = tarea["nombre_cliente"]

    print(f"\n{'='*60}")
    print(f"🎬 {nombre_tarea}")
    print(f"   Cliente: {nombre_cliente} | Task: {task_id}")

    # 1. Obtener video del editor
    try:
        r = await client.get(f"{CLICKUP_MANAGER_URL}/video/{task_id}", timeout=30)
        if r.status_code == 404:
            print(f"   ⚠️  Sin video del editor. Saltando...")
            return {"status": "skipped", "reason": "no_video"}
        r.raise_for_status()
        video = r.json()
    except Exception as e:
        print(f"   ❌ Error obteniendo video: {e}")
        return {"status": "error", "reason": str(e)}

    print(f"   🎥 Video: {video['nombre']} (por {video['autor']})")

    # 2. Transcribir video + buscar info del negocio EN PARALELO
    print(f"   🔄 Transcribiendo + buscando info del negocio en paralelo...")

    async def transcribir():
        r = await client.post(
            f"{TRANSCRIBER_URL}/transcribir",
            json={"url": video["url"]},
            timeout=300
        )
        r.raise_for_status()
        return r.json()

    async def buscar_info():
        try:
            r = await client.get(
                f"{CLICKUP_MANAGER_URL}/cliente/{nombre_cliente}/info",
                timeout=30
            )
            if r.status_code == 200:
                return r.json().get("info")
        except Exception:
            pass
        return None

    try:
        transcripcion_result, info_negocio = await asyncio.gather(
            transcribir(),
            buscar_info()
        )
    except Exception as e:
        print(f"   ❌ Error en transcripción: {e}")
        return {"status": "error", "reason": str(e)}

    transcripcion = transcripcion_result["text"]
    print(f"   ✅ Transcripción: {transcripcion[:80]}...")
    print(f"   {'✅' if info_negocio else '⚠️'} Info negocio: {'encontrada' if info_negocio else 'no encontrada'}")

    # 3. Generar copy
    print(f"   ✍️  Generando copy...")
    try:
        r = await client.post(
            f"{COPY_CONTENT_URL}/generar",
            json={
                "transcripcion": transcripcion,
                "info_negocio": info_negocio,
                "nombre_cliente": nombre_cliente
            },
            timeout=60
        )
        r.raise_for_status()
        copy_result = r.json()
    except Exception as e:
        print(f"   ❌ Error generando copy: {e}")
        return {"status": "error", "reason": str(e)}

    copy = copy_result["copy"]
    print(f"\n   📝 COPY ({copy_result['palabras']} palabras):")
    print(f"   {'-'*40}")
    for linea in copy.split("\n"):
        print(f"   {linea}")
    print(f"   {'-'*40}")

    # 4. Guardar en ClickUp
    print(f"   💾 Guardando en campo 'tema'...")
    try:
        r = await client.post(
            f"{CLICKUP_MANAGER_URL}/campo/set",
            json={
                "task_id": task_id,
                "field_id": campo_tema_id,
                "value": copy
            },
            timeout=30
        )
        result = r.json()
        if result.get("success"):
            print(f"   ✅ Copy guardado exitosamente.")
            return {"status": "ok"}
        else:
            print(f"   ❌ Error guardando: {result}")
            return {"status": "error", "reason": "save_failed"}
    except Exception as e:
        print(f"   ❌ Error guardando: {e}")
        return {"status": "error", "reason": str(e)}


async def correr_pipeline(list_id: str, limite: int = None):
    """Ejecuta el pipeline completo para una lista de videos."""

    async with httpx.AsyncClient() as client:
        # 1. Obtener field_id de "tema"
        print("🔍 Obteniendo campo 'tema'...")
        r = await client.get(f"{CLICKUP_MANAGER_URL}/campos/{list_id}", timeout=30)
        campos = r.json()
        campo_tema_id = None
        for campo in campos:
            if campo.get("name", "").lower().strip() == "tema":
                campo_tema_id = campo["id"]
                break

        if not campo_tema_id:
            print("❌ Campo 'tema' no encontrado. Abortando.")
            return

        print(f"✅ Campo 'tema': {campo_tema_id}\n")

        # 2. Obtener tareas pendientes de copy
        print("📋 Buscando tareas COMPLETADAS sin copy...")
        r = await client.get(
            f"{CLICKUP_MANAGER_URL}/tareas-para-copy/{list_id}",
            timeout=30
        )
        tareas = r.json()

        if not tareas:
            print("✅ Todas las tareas ya tienen copy.")
            return

        if limite:
            tareas = tareas[:limite]

        print(f"📊 {len(tareas)} tareas para procesar.\n")

        # 3. Procesar tareas (secuencial por ahora para no saturar APIs)
        ok = 0
        skipped = 0
        errors = 0

        for tarea in tareas:
            result = await procesar_tarea(client, tarea, campo_tema_id)
            if result["status"] == "ok":
                ok += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                errors += 1

        # Resumen
        print(f"\n{'='*60}")
        print(f"🎉 Pipeline finalizado.")
        print(f"   ✅ Procesadas: {ok}")
        print(f"   ⏭️  Saltadas: {skipped}")
        print(f"   ❌ Errores: {errors}")
        print(f"   📊 Total: {len(tareas)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Orquestador Dental Growth")
    parser.add_argument("--list-id", default="901325940523", help="ID de la lista de ClickUp")
    parser.add_argument("--limite", type=int, default=None, help="Limitar a N tareas")
    args = parser.parse_args()

    print("🚀 Orquestador Dental Growth")
    print("="*60)
    print("\n📡 Levantando agentes...")

    iniciar_agentes()

    try:
        print("🔄 Iniciando pipeline...")
        print(f"📅 Lista: {args.list_id}")
        if args.limite:
            print(f"🔧 Límite: {args.limite} tareas")
        print()

        asyncio.run(correr_pipeline(args.list_id, args.limite))

    except KeyboardInterrupt:
        print("\n\n⛔ Interrumpido por el usuario.")
    finally:
        print("\n🛑 Deteniendo agentes...")
        detener_agentes()
        print("✅ Agentes detenidos.")


if __name__ == "__main__":
    main()
