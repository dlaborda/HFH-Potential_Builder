import json
import os

RUTA_EQUIP = "data/equipamiento.json"

# -----------------------------
# Cargar equipamiento guardado
# -----------------------------
def cargar_equipamiento():
    if not os.path.exists(RUTA_EQUIP):
        return {}

    try:
        with open(RUTA_EQUIP, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except:
        return {}

# -----------------------------
# Guardar equipamiento
# -----------------------------
def guardar_equipamiento(data):
    with open(RUTA_EQUIP, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# -----------------------------
# Equipar una pieza
# -----------------------------
def equipar_pieza(jugador, slot, pieza_id):
    data = cargar_equipamiento()

    if jugador not in data:
        data[jugador] = {}

    data[jugador][str(slot)] = pieza_id
    guardar_equipamiento(data)

# -----------------------------
# Piezas bloqueadas (ya equipadas)
# -----------------------------
def piezas_bloqueadas():
    data = cargar_equipamiento()

    # Devolver un set con todas las piezas equipadas
    bloqueadas = set()

    for jugador, slots in data.items():
        for pieza_id in slots.values():
            bloqueadas.add(pieza_id)

    return bloqueadas

# -----------------------------
# Desequipar todo
# -----------------------------
def resetear_equipamiento():
    """
    Elimina TODO el equipamiento de TODOS los jugadores.
    """
    guardar_equipamiento({})
