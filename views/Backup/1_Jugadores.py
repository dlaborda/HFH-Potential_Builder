import streamlit as st
from data_manager import load_all_into_session, save_json


def main():

    st.title("👤 Jugadores")

    # Cargar datos desde session_state
    jugadores = st.session_state["jugadores"]              # LISTA de strings
    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    config = st.session_state["config_jugadores"]

    # Ordenar jugadores alfabéticamente
    lista_jugadores = sorted(jugadores, key=lambda x: x.lower())
    jugador = st.selectbox("Selecciona jugador", lista_jugadores)

    # Asegurar que existe config para este jugador
    if jugador not in config:
        config[jugador] = {
            "Equipar": False,
            "tipos_recomendados": [],
            "stats_recomendados": {"stats": [], "puntos": []},
            "candidatos_4": [],
            "slots_activos": []
        }

    # ============================================================
    # 1. CHECKBOX EQUIPAR
    # ============================================================
    config[jugador]["Equipar"] = st.checkbox(
        "Calcular Build Recomendada",
        value=config[jugador].get("Equipar", False)
    )

    # ============================================================
    # 2. TIPOS RECOMENDADOS
    # ============================================================
    tipos_actuales = config[jugador]["tipos_recomendados"]
    tipos_actuales = [t for t in tipos_actuales if t in tipos]  # limpiar valores inválidos

    tipos_seleccionados = st.multiselect(
        "Tipos prioritarios",
        tipos,
        default=tipos_actuales
    )

    # ============================================================
    # 3. STATS RECOMENDADOS
    # ============================================================
    stats_actuales = config[jugador]["stats_recomendados"]["stats"]
    puntos_actuales = config[jugador]["stats_recomendados"]["puntos"]

    # Limpiar stats inválidos
    stats_actuales_limpios = []
    puntos_limpios = []

    for s, p in zip(stats_actuales, puntos_actuales):
        if s in stats:
            stats_actuales_limpios.append(s)
            puntos_limpios.append(p)

    stats_actuales = stats_actuales_limpios
    puntos_actuales = puntos_limpios

    # Ordenar stats por puntuación descendente
    stats_y_puntos = list(zip(stats_actuales, puntos_actuales))
    stats_y_puntos.sort(key=lambda x: x[1], reverse=True)

    stats_actuales = [s for s, p in stats_y_puntos]
    puntos_actuales = [p for s, p in stats_y_puntos]

    stats_seleccionados = st.multiselect(
        "Stats recomendados",
        stats,
        default=stats_actuales
    )

    # ============================================================
    # 4. PUNTOS POR STAT
    # ============================================================
    st.subheader("Puntos por stat")
    puntos = []

    for stat in stats_seleccionados:

        if stat in stats_actuales:
            idx = stats_actuales.index(stat)
            valor_inicial = puntos_actuales[idx]
        else:
            valor_inicial = 3  # valor por defecto

        puntos.append(
            st.number_input(
                f"Puntos para {stat}",
                min_value=1,
                max_value=10,
                value=valor_inicial,
                key=f"puntos_{jugador}_{stat}"
            )
        )

    # ============================================================
    # 5. CONFIGURACIÓN ADICIONAL
    # ============================================================
    st.subheader("Configuración adicional")

    candidatos_4_actuales = config[jugador].get("candidatos_4", [])
    candidatos_4_actuales = [t for t in candidatos_4_actuales if t in tipos]

    candidatos_4 = st.multiselect(
        "Tipos candidatos para set de 4 piezas",
        tipos,
        default=candidatos_4_actuales,
        key=f"candidatos_4_editor_{jugador}"
    )

    slots_activos_actuales = [str(s) for s in config[jugador].get("slots_activos", [])]
    opciones_slots = ["1", "2", "3", "4", "5", "6"]

    slots_activos = st.multiselect(
        "Slots activos",
        opciones_slots,
        default=slots_activos_actuales,
        key=f"slots_activos_editor_{jugador}"
    )

    # ============================================================
    # 6. GUARDAR CAMBIOS
    # ============================================================
    if st.button("Guardar cambios"):

        config[jugador]["tipos_recomendados"] = tipos_seleccionados

        config[jugador]["stats_recomendados"] = {
            "stats": stats_seleccionados,
            "puntos": puntos
        }

        config[jugador]["candidatos_4"] = candidatos_4
        config[jugador]["slots_activos"] = slots_activos

        save_json("config_jugadores", config)

        st.success(f"Jugador '{jugador}' actualizado correctamente.")


if __name__ == "__main__":
    main()
