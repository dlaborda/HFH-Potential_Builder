import json
import os
import streamlit as st

DATA_DIR = "data"

FILES = {
    "jugadores": "jugadores.json",
    "tipos": "tipos.json",
    "stats": "stats.json",
    "tipos_recomendados": "tipos_recomendados.json",
    "stats_recomendados": "stats_recomendados.json",
    "inventarios": "inventarios.json",
    "config_jugadores": "config_jugadores.json",
    "equipos_entrenamiento": "equipos_entrenamiento.json",
    "equipamiento": "equipamiento.json",
    "orden_jugadores": "orden_jugadores.json" # ⭐ AÑADIDO
}

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_json(name, default):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, FILES[name])
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    ensure_data_dir()
    path = os.path.join(DATA_DIR, FILES[name])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================================
# TIPOS
# ============================================================
def load_tipos():
    return load_json("tipos", [])

def save_tipos(tipos):
    save_json("tipos", tipos)


# ============================================================
# EQUIPOS DE ENTRENAMIENTO (NUEVO)
# ============================================================
def load_equipos_entrenamiento():
    """
    Carga los equipos de entrenamiento desde JSON.
    Si no existe, devuelve {}.
    """
    return load_json("equipos_entrenamiento", {})


def save_equipos_entrenamiento(data):
    """
    Guarda los equipos de entrenamiento en JSON.
    """
    save_json("equipos_entrenamiento", data)

# ============================================================
# EQUIPAMIENTO (integrado desde equip_state.py)
# ============================================================
def load_equipamiento():
    return load_json("equipamiento", {})

def save_equipamiento(data):
    """
    Guarda el equipamiento en equipamiento.json.
    """
    save_json("equipamiento", data)


def equipar_pieza(jugador, slot, pieza_id):
    """
    Asigna una pieza a un jugador en un slot concreto.
    """
    data = load_equipamiento()

    if jugador not in data:
        data[jugador] = {}

    data[jugador][str(slot)] = pieza_id
    save_equipamiento(data)
    
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
    
def resetear_equipamiento():
    """
    Elimina TODO el equipamiento de TODOS los jugadores.
    """
    save_equipamiento({})

# ============================================================
# CONFIGURACIÓN DE JUGADORES (integrado desde Equipar.py)
# ============================================================

def load_config_jugadores():
    """
    Carga config_jugadores.json y normaliza los slots a string.
    """
    raw = load_json("config_jugadores", {})
    config_normalizado = {}

    for jugador, conf in raw.items():
        candidatos = conf.get("candidatos_4", [])
        slots = conf.get("slots_activos", [])
        slots = [str(s) for s in slots]  # normalización

        config_normalizado[jugador] = {
            "candidatos_4": candidatos,
            "slots_activos": slots
        }

    return config_normalizado


def save_config_jugadores(config):
    """
    Guarda config_jugadores.json.
    """
    save_json("config_jugadores", config)

def save_orden_jugadores(orden):
    """Guarda el orden de jugadores en un JSON."""
    save_json("orden_jugadores", orden)


def load_orden_jugadores():
    """Carga el orden de jugadores desde JSON. Si no existe, devuelve []."""
    return load_json("orden_jugadores", [])

# ============================================================
# CARGA GLOBAL
# ============================================================
def load_all_into_session():

    st.session_state["jugadores"] = load_json("jugadores", [])
    st.session_state["tipos"] = load_json("tipos", [])
    st.session_state["stats"] = load_json("stats", [])
    st.session_state["tipos_recomendados"] = load_json("tipos_recomendados", {})
    st.session_state["stats_recomendados"] = load_json("stats_recomendados", {})
    st.session_state["equipamiento"] = load_json("equipamiento", {})
    st.session_state["config_jugadores"] = load_config_jugadores()
    st.session_state["equipos_entrenamiento"] = load_equipos_entrenamiento()
    st.session_state["orden_jugadores"] = load_orden_jugadores()

    # Inventarios
    st.session_state["inventarios"] = load_json(
        "inventarios",
        {str(i): [] for i in range(1, 7)}
    )