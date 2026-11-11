"""Generate the CPU low-poly script with the real Brainrot storytelling call.

Run from the repository root:
    $env:PYTHONPATH="."; uv run --locked python experiments/cpu-lowpoly/write_story.py
Writes story.json beside this file. Provider claude-code, default CLI model, level 30, factual.
"""

import json
from pathlib import Path

from brainrot import script

TOPIC = "Cómo funciona un procesador (CPU) por dentro"

# Only these facts may become specifics in the narration; the skill forbids inventing others.
FACTS = """\
- Un procesador es un chip de silicio con miles de millones de transistores.
- Un transistor es un interruptor sin partes móviles: una tensión eléctrica lo deja pasar corriente (1) o lo corta (0).
- Con pocos transistores se arman compuertas lógicas (NOT, AND, OR). Combinando compuertas se construyen sumadores, y con sumadores la ALU,
  la parte que suma, resta y compara.
- Un reloj interno marca pulsos. Cada pulso deja avanzar un paso a los circuitos. Un gigahertz son mil millones de pulsos por segundo.
- Cada instrucción sigue un ciclo: buscar (se lee la instrucción de la memoria, en la dirección que marca el contador de programa),
  decodificar (la unidad de control entiende qué pide), ejecutar (la ALU hace la operación) y guardar el resultado en un registro.
  Luego el contador de programa apunta a la siguiente.
- Los registros son memoria diminuta dentro del procesador, la más rápida que existe. La RAM está fuera del chip y es mucho más lenta.
  La caché (L1, L2, L3) guarda cerca del procesador lo usado hace poco, para no esperar a la RAM.
- Un procesador moderno tiene varios núcleos; cada uno es una unidad completa que puede ejecutar su propio hilo de instrucciones.
- Pipeline: mientras una instrucción se ejecuta, la siguiente se decodifica y otra se busca, como una línea de ensamblaje.
  Ante un if el procesador adivina por qué lado seguirá (predicción de saltos); si falla, descarta el trabajo adelantado y pierde tiempo.
- Cada conmutación de un transistor gasta energía y se convierte en calor. Disipador y ventilador lo sacan; si el chip se calienta demasiado,
  baja su frecuencia para protegerse.
- No sabe qué es una foto, un juego o una letra: solo mueve y combina ceros y unos siguiendo instrucciones muy simples.
"""

story = script.write_story(
    TOPIC, provider="claude-code", brainrot_level=30, reference_context=FACTS,
)
out = Path(__file__).with_name("story.json")
out.write_text(json.dumps({
    "title": story.title,
    "script": story.script,
    "generator": "brainrot.script.write_story(provider=claude-code, BRAINROT_CLAUDE_MODEL unset = CLI default model, brainrot_level=30, factual)",
    "words": len(story.script.split()),
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(out, len(story.script.split()), "words")
