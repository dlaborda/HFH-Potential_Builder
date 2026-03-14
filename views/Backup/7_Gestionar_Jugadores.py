import streamlit as st
from data_manager import load_all_into_session, save_json


def main():

    load_all_into_session()

    st.title("👤 Gestionar Jugadores")

    jugadores = st.session_state["jugadores"]              # LISTA de strings
    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    config = st.session_state["config_jugadores"]

    modo = st.radio("Modo", ["Añadir", "Editar"])

    # ============================================================
    # MODO EDITAR
    # ============================================================
    if modo == "Editar":

        lista_jugadores = sorted(jugadores, key=lambda x: x.lower())
        jugador = st.selectbox("Selecciona jugador", lista_jugadores)

        # Asegurar que existe config
        if jugador not in config:
            config[jugador] = {
                "Equipar": False,
                "tipos_recomendados": [],
                "stats_recomendados": {"stats": [], "puntos": []},
                "candidatos_4": [],
                "slots_activos": []
            }

        # Checkbox Equipar
        config[jugador]["Equipar"] = st.checkbox(
            "Calcular Build Recomendada",
            value=config[jugador].get("Equipar", False)
        )

        # -----------------------------
        # TIPOS RECOMENDADOS
        # -----------------------------
        tipos_actuales = config[jugador]["tipos_recomendados"]
        tipos_actuales = [t for t in tipos_actuales if t in tipos]

        tipos_seleccionados = st.multiselect(
            "Tipos prioritarios",
            tipos,
            default=tipos_actuales
        )

        # -----------------------------
        # STATS RECOMENDADOS
        # -----------------------------
        stats_actuales = config[jugador]["stats_recomendados"]["stats"]
        puntos_actuales = config[jugador]["stats_recomendados"]["puntos"]

        # Limpiar stats inválidos
        stats_limpios = []
        puntos_limpios = []
        for s, p in zip(stats_actuales, puntos_actuales):
            if s in stats:
                stats_limpios.append(s)
                puntos_limpios.append(p)

        stats_actuales = stats_limpios
        puntos_actuales = puntos_limpios

        # Ordenar por puntuación
        stats_y_puntos = list(zip(stats_actuales, puntos_actuales))
        stats_y_puntos.sort(key=lambda x: x[1], reverse=True)

        stats_actuales = [s for s, p in stats_y_puntos]
        puntos_actuales = [p for s, p in stats_y_puntos]

        stats_seleccionados = st.multiselect(
            "Stats recomendados",
            stats,
            default=stats_actuales
        )

        # -----------------------------
        # PUNTOS POR STAT
        # -----------------------------
        st.subheader("Puntos por stat")
        puntos = []

        for stat in stats_seleccionados:
            if stat in stats_actuales:
                idx = stats_actuales.index(stat)
                valor_inicial = puntos_actuales[idx]
            else:
                valor_inicial = 3

            puntos.append(
                st.number_input(
                    f"Puntos para {stat}",
                    min_value=1,
                    max_value=10,
                    value=valor_inicial,
                    key=f"puntos_{jugador}_{stat}"
                )
            )

        # -----------------------------
        # CONFIGURACIÓN ADICIONAL
        # -----------------------------
        st.subheader("Configuración adicional")

        candidatos_4_actuales = config[jugador].get("candidatos_4", [])
        slots_activos_actuales = [str(s) for s in config[jugador].get("slots_activos", [])]

        candidatos_4 = st.multiselect(
            "Tipos candidatos para set de 4 piezas",
            tipos,
            default=candidatos_4_actuales
        )

        slots_activos = st.multiselect(
            "Slots activos",
            ["1", "2", "3", "4", "5", "6"],
            default=slots_activos_actuales
        )

        # -----------------------------
        # GUARDAR CAMBIOS
        # -----------------------------
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

    # ============================================================
    # MODO AÑADIR
    # ============================================================
    else:

        nombre = st.text_input("Nombre del jugador")

        equipar_nuevo = st.checkbox("Calcular Build Recomendada", value=False)
        tipos_seleccionados = st.multiselect("Tipos prioritarios", tipos)
        stats_seleccionados = st.multiselect("Stats recomendados", stats)

        puntos = []
        if stats_seleccionados:
            st.subheader("Puntos por stat")
            for stat in stats_seleccionados:
                puntos.append(
                    st.number_input(
                        f"Puntos para {stat}",
                        min_value=1,
                        max_value=10,
                        value=3,
                        key=f"puntos_nuevo_{stat}"
                    )
                )

        st.subheader("⚙️ Configuración adicional")

        candidatos_4 = st.multiselect(
            "Tipos candidatos a 4 piezas",
            tipos_seleccionados
        )

        slots_activos = st.multiselect(
            "Slots activos",
            ["1", "2", "3", "4", "5", "6"]
        )

        if st.button("Añadir jugador"):

            if not nombre:
                st.error("El nombre no puede estar vacío.")
                return

            if nombre in jugadores:
                st.error("Ese jugador ya existe.")
                return

            jugadores.append(nombre)

            config[nombre] = {
                "Equipar": equipar_nuevo,
                "tipos_recomendados": tipos_seleccionados,
                "stats_recomendados": {
                    "stats": stats_seleccionados,
                    "puntos": puntos
                },
                "candidatos_4": candidatos_4,
                "slots_activos": slots_activos
            }

            save_json("jugadores", jugadores)
            save_json("config_jugadores", config)

            st.success(f"Jugador '{nombre}' añadido correctamente.")

    st.divider()

    # ============================================================
    # ELIMINAR JUGADOR
    # ============================================================
    st.header("🗑️ Eliminar jugador")

    jugador_del = st.selectbox("Selecciona jugador a eliminar", [""] + jugadores)

    if st.button("Eliminar jugador"):
        if jugador_del:

            jugadores.remove(jugador_del)
            config.pop(jugador_del, None)

            save_json("jugadores", jugadores)
            save_json("config_jugadores", config)

            st.success(f"Jugador '{jugador_del}' eliminado correctamente.")


if __name__ == "__main__":
    main()
