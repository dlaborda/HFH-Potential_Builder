import streamlit as st
from data_manager import load_all_into_session, save_json


def main():

    load_all_into_session()

    st.title("👤 Gestionar Jugadores")

    jugadores = st.session_state["jugadores"]
    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    tipos_rec = st.session_state["tipos_recomendados"]
    stats_rec = st.session_state["stats_recomendados"]
    config = st.session_state["config_jugadores"]

    modo = st.radio("Modo", ["Añadir", "Editar"])

    # ============================================================
    # MODO EDITAR
    # ============================================================
    if modo == "Editar":

        jugador_sel = st.selectbox("Selecciona jugador", jugadores)

        # Datos actuales
        tipos_actuales = tipos_rec.get(jugador_sel, [])
        stats_actuales, puntos_actuales = stats_rec.get(jugador_sel, [[], []])
        conf_actual = config.get(jugador_sel, {"candidatos_4": [], "slots_activos": []})

        # Nombre editable
        nombre = st.text_input("Nombre del jugador", jugador_sel)

        # Tipos recomendados
        tipos_seleccionados = st.multiselect(
            "Tipos prioritarios",
            tipos,
            default=tipos_actuales
        )

        # Stats recomendados
        stats_seleccionados = st.multiselect(
            "Stats recomendados",
            stats,
            default=stats_actuales
        )

        # Puntos por stat
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
                    key=f"puntos_{jugador_sel}_{stat}"
                )
            )

        # ============================================================
        # CONFIGURACIÓN DE JUGADOR (candidatos_4 y slots_activos)
        # ============================================================

        st.subheader("Configuración adicional")

        # Cargar configuración actual correctamente
        config_actual = config.get(jugador_sel, {"candidatos_4": [], "slots_activos": []})

        candidatos_4_actuales = config_actual.get("candidatos_4", [])

        # Normalizar slots a str para que coincidan con las opciones del multiselect
        slots_activos_actuales_raw = config_actual.get("slots_activos", [])
        slots_activos_actuales = [str(s) for s in slots_activos_actuales_raw]

        # Tipos disponibles en tu juego
        opciones_tipos = tipos
        opciones_slots = ["1", "2", "3", "4", "5", "6"]

        candidatos_4 = st.multiselect(
            "Tipos candidatos para set de 4 piezas",
            opciones_tipos,
            default=candidatos_4_actuales,
            key=f"candidatos_4_editor_{jugador_sel}"
        )

        slots_activos = st.multiselect(
            "Slots activos",
            opciones_slots,
            default=slots_activos_actuales,
            key=f"slots_activos_editor_{jugador_sel}"
        )

        # Botón para guardar cambios
        if st.button("Guardar cambios"):

            # Actualizar datos
            tipos_rec[jugador_sel] = tipos_seleccionados
            stats_rec[jugador_sel] = [stats_seleccionados, puntos]

            # Guardamos slots como lista de strings (coherente con el resto de la app)
            config[jugador_sel] = {
                "candidatos_4": candidatos_4,
                "slots_activos": slots_activos
            }

            # Guardar en JSON
            save_json("tipos_recomendados", tipos_rec)
            save_json("stats_recomendados", stats_rec)
            save_json("config_jugadores", config)

            st.success(f"Jugador '{jugador_sel}' actualizado correctamente.")

    # ============================================================
    # MODO AÑADIR
    # ============================================================
    else:

        nombre = st.text_input("Nombre del jugador")

        tipos_seleccionados = st.multiselect("Tipos prioritarios", tipos)
        stats_seleccionados = st.multiselect("Stats recomendados", stats)

        if stats_seleccionados:
            st.subheader("Puntos por stat")
            puntos = []

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
            tipos_rec[nombre] = tipos_seleccionados
            stats_rec[nombre] = [stats_seleccionados, puntos]

            # Guardamos slots como strings desde el principio
            config[nombre] = {
                "candidatos_4": candidatos_4,
                "slots_activos": slots_activos
            }

            save_json("jugadores", jugadores)
            save_json("tipos_recomendados", tipos_rec)
            save_json("stats_recomendados", stats_rec)
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
            tipos_rec.pop(jugador_del, None)
            stats_rec.pop(jugador_del, None)
            config.pop(jugador_del, None)

            save_json("jugadores", jugadores)
            save_json("tipos_recomendados", tipos_rec)
            save_json("stats_recomendados", stats_rec)
            save_json("config_jugadores", config)

            st.success(f"Jugador '{jugador_del}' eliminado correctamente.")


if __name__ == "__main__":
    main()
