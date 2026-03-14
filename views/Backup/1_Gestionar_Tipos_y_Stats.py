import streamlit as st
from data_manager import load_all_into_session, save_json

def main():
    load_all_into_session()

    st.title("⚙️ Gestionar Tipos y Stats")

    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    tipos_rec = st.session_state["tipos_recomendados"]
    stats_rec = st.session_state["stats_recomendados"]

    # -----------------------------
    # TIPOS
    # -----------------------------
    st.header("📌 Tipos")

    nuevo_tipo = st.text_input("Añadir nuevo tipo")
    if st.button("Añadir tipo"):
        if nuevo_tipo and nuevo_tipo not in tipos:
            tipos.append(nuevo_tipo)

            # Guardar y sincronizar
            save_json("tipos", tipos)
            st.session_state["tipos"] = tipos

            st.success(f"Tipo '{nuevo_tipo}' añadido.")
        else:
            st.error("Tipo vacío o ya existente.")

    tipo_eliminar = st.selectbox("Eliminar tipo", [""] + tipos)
    if st.button("Eliminar tipo"):
        if tipo_eliminar:

            # Eliminar del listado de tipos
            tipos.remove(tipo_eliminar)
            save_json("tipos", tipos)
            st.session_state["tipos"] = tipos

            # Eliminar de tipos recomendados de cada jugador
            for jugador, lista in tipos_rec.items():
                if tipo_eliminar in lista:
                    lista.remove(tipo_eliminar)

            save_json("tipos_recomendados", tipos_rec)
            st.session_state["tipos_recomendados"] = tipos_rec

            st.success(f"Tipo '{tipo_eliminar}' eliminado.")

    st.divider()

    # -----------------------------
    # STATS
    # -----------------------------
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

            # Eliminar de stats recomendados de cada jugador
            for jugador, (lista_stats, lista_puntos) in stats_rec.items():
                if stat_eliminar in lista_stats:
                    idx = lista_stats.index(stat_eliminar)
                    lista_stats.pop(idx)
                    lista_puntos.pop(idx)

            save_json("stats_recomendados", stats_rec)
            st.session_state["stats_recomendados"] = stats_rec

            st.success(f"Stat '{stat_eliminar}' eliminado.")

    st.divider()

    st.subheader("📄 Tipos actuales")
    st.write(tipos)

    st.subheader("📄 Stats actuales")
    st.write(stats)


if __name__ == "__main__":
    main()
