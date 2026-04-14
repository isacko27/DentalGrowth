"""
Agent Brain — Motor de IA para cada agente
============================================
Cada agente usa este módulo para tener un endpoint /ask
que entiende lenguaje natural y ejecuta acciones.
"""

import anthropic
import json
import httpx
from config import ANTHROPIC_API_KEY

client_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_agent(question: str, system_prompt: str, tools: list, tool_executor, max_iterations: int = 8) -> str:
    """
    Procesa una pregunta en lenguaje natural usando Claude con tool use.

    Args:
        question: La pregunta o instrucción del orquestador
        system_prompt: El prompt de sistema que describe al agente
        tools: Lista de herramientas disponibles (formato Anthropic)
        tool_executor: Función que ejecuta herramientas: (name, input) -> result
        max_iterations: Máximo de ciclos de tool use

    Returns:
        Respuesta en texto del agente
    """
    messages = [{"role": "user", "content": question}]

    for _ in range(max_iterations):
        response = client_ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Si terminó, devolver texto
        if response.stop_reason == "end_of_turn":
            text_parts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_parts) if text_parts else "Listo."

        # Procesar tool use
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_executor(block.name, block.input)
                    except Exception as e:
                        result = {"error": str(e)}

                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    if len(result_str) > 10000:
                        result_str = result_str[:10000] + "...(truncado)"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Otro stop_reason
        text_parts = [b.text for b in response.content if b.type == "text"]
        return "\n".join(text_parts) if text_parts else "Completado."

    return "Se alcanzó el límite de iteraciones."
