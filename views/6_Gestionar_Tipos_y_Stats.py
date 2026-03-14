import streamlit as st
from data_manager import load_all_into_session, save_json, check_role


def main():
    check_role("admin")
    load_all_into_session()

    st.title("⚙️ Gestionar Tipos, Stats y Equipos de Entrenamiento")

    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    config = st.session_state["config_jugadores"]
    equipos = st.session_state.get("equipos_entrenamiento", {})

    # ============================================================
    # 1. TIPOS
    # ============================================================
    st.header("📌 Tipos")

    nuevo_tipo = st.text_input("Añadir nuevo tipo")
    if st.button("Añadir tipo"):
        if nuevo_tipo and nuevo_tipo not in tipos:
            tipos.append(nuevo_tipo)
            save_json("tipos", tipos)
            st.session_state["tipos"] = tipos
            st.success(f"Tipo '{nuevo_tipo}' añadido.")
        else:
            st.error("Tipo vacío o ya existente.")

    tipo_eliminar = st.selectbox("Eliminar tipo", [""] + tipos)
    if st.button("Eliminar tipo"):
        if tipo_eliminar:
            tipos.remove(tipo_eliminar)
            save_json("tipos", tipos)
            st.session_state["tipos"] = tipos

            # Eliminar de tipos_recomendados de cada jugador
            for jugador in config:
                lista = config[jugador]["tipos_recomendados"]
                if tipo_eliminar in lista:
                    lista.remove(tipo_eliminar)

            save_json("config_jugadores", config)
            st.success(f"Tipo '{tipo_eliminar}' eliminado.")

    st.divider()

    # ============================================================
    # 2. STATS
    # ============================================================
    st.header("📌 Stats")

    nuevo_stat = st.text_input("Añadir nuevo stat")
    if st.button("Añadir stat"):
        if nuevo_stat and nuevo_stat not in stats:
            stats.append(nuevo_stat)
            save_json("stats", stats)
            st.session_state["stats"] = stats
            st.success(f"Stat '{nuevo_stat}' añadido.")
        else:
            st.error("Stat vacío o ya existente.")

    stat_eliminar = st.selectbox("Eliminar stat", [""] + stats)
    if st.button("Eliminar stat"):
        if stat_eliminar:
            stats.remove(stat_eliminar)
            save_json("stats", stats)
            st.session_state["stats"] = stats

            # Eliminar de stats_recomendados de cada jugador
            for jugador in config:
                lista_stats = config[jugador]["stats_recomendados"]["stats"]
                lista_puntos = config[jugador]["stats_recomendados"]["puntos"]

                if stat_eliminar in lista_stats:
                    idx = lista_stats.index(stat_eliminar)
                    lista_stats.pop(idx)
                    lista_puntos.pop(idx)

            save_json("config_jugadores", config)
            st.success(f"Stat '{stat_eliminar}' eliminado.")

    st.divider()

    st.subheader("📄 Tipos actuales")
    st.write(tipos)

    st.subheader("📄 Stats actuales")
    st.write(stats)

    st.divider()

    # ============================================================
    # 3. EQUIPOS DE ENTRENAMIENTO
    # ============================================================
    st.header("🏐 Equipos de Entrenamiento")

    # -----------------------------
    # Crear equipo
    # -----------------------------
    st.subheader("➕ Crear equipo")

    nuevo_equipo = st.text_input("Nombre del nuevo equipo")
    if st.button("Añadir equipo"):
        if nuevo_equipo and nuevo_equipo not in equipos:
            equipos[nuevo_equipo] = []
            save_json("equipos_entrenamiento", equipos)
            st.session_state["equipos_entrenamiento"] = equipos
            st.success(f"Equipo '{nuevo_equipo}' creado.")
        else:
            st.error("Nombre vacío o ya existente.")

    st.divider()

    # -----------------------------
    # Editar equipo
    # -----------------------------
    st.subheader("✏️ Editar equipo")

    equipo_sel = st.selectbox("Selecciona un equipo", [""] + list(equipos.keys()))

    if equipo_sel:

        st.write(f"### Equipo: {equipo_sel}")

        # Renombrar equipo
        nuevo_nombre = st.text_input("Renombrar equipo", value=equipo_sel)
        if st.button("Guardar nombre"):
            if nuevo_nombre and nuevo_nombre not in equipos:
                equipos[nuevo_nombre] = equipos.pop(equipo_sel)
                save_json("equipos_entrenamiento", equipos)
                st.session_state["equipos_entrenamiento"] = equipos
                st.success("Nombre actualizado.")
                st.rerun()
            else:
                st.error("Nombre vacío o ya existente.")

        st.write("### Tipos del equipo")
        st.write(equipos[equipo_sel])

        # Añadir tipo al equipo
        tipo_add = st.selectbox("Añadir tipo al equipo", [""] + tipos)
        if st.button("Añadir tipo al equipo"):
            if tipo_add and tipo_add not in equipos[equipo_sel]:
                equipos[equipo_sel].append(tipo_add)
                save_json("equipos_entrenamiento", equipos)
                st.session_state["equipos_entrenamiento"] = equipos
                st.success(f"Tipo '{tipo_add}' añadido al equipo.")
            else:
                st.error("Tipo vacío o ya existente en el equipo.")

        # Quitar tipo del equipo
        tipo_del = st.selectbox("Eliminar tipo del equipo", [""] + equipos[equipo_sel])
        if st.button("Eliminar tipo del equipo"):
            if tipo_del:
                equipos[equipo_sel].remove(tipo_del)
                save_json("equipos_entrenamiento", equipos)
                st.session_state["equipos_entrenamiento"] = equipos
                st.success(f"Tipo '{tipo_del}' eliminado del equipo.")

        st.divider()

        # Eliminar equipo
        if st.button("🗑️ Eliminar equipo"):
            equipos.pop(equipo_sel)
            save_json("equipos_entrenamiento", equipos)
            st.session_state["equipos_entrenamiento"] = equipos
            st.success(f"Equipo '{equipo_sel}' eliminado.")
            st.rerun()

    st.subheader("📄 Equipos actuales")
    st.write(equipos)


if __name__ == "__main__":
    main()
else:
    main()
