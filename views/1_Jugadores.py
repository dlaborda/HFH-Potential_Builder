import streamlit as st
import os
from data_manager import load_all_into_session, restore_player_config, player_service, get_current_user_id


def mostrar_foto(nombre, config, ancho=120):
    ruta = player_service.get_player_image_path(nombre, config)
    st.image(ruta, width=ancho)

def main():

    load_all_into_session()

    st.title("🏐 Jugadores")

    jugadores = st.session_state["jugadores"]
    config = st.session_state["config_jugadores"]

    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]


    # ============================================================
    # 1️⃣ EXPANDER — JUGADORES CON EQUIPAR = TRUE
    # ============================================================
    with st.expander("Jugadores a equipar", expanded=False):

        jugadores_equipar = [j for j in jugadores if config[j].get("Equipar", False)]
        
        # Sort using the same rules as the full list
        jugadores_equipar = player_service.sort_players_by_rarity(
            jugadores_equipar, 
            config, 
            st.session_state["rareza"]
        )

        if not jugadores_equipar:
            st.info("No hay jugadores con Equipar = True.")
        else:
            cols = st.columns(4)
            idx = 0
            for jugador in jugadores_equipar:
                imagen = config[jugador].get("imagen", "default.png")
                with cols[idx % 4]:
                    mostrar_foto(jugador, config)
                idx += 1

    st.divider()
    
    # ============================================================
    # CONTROL DE ESTADO
    # ============================================================
    if "modo_edicion" not in st.session_state:
        st.session_state["modo_edicion"] = False
    
    if "jugador_seleccionado" not in st.session_state:
        st.session_state["jugador_seleccionado"] = None
    
    
    # ============================================================
    # 2️⃣ LISTA COMPLETA — SOLO SI NO ESTAMOS EDITANDO
    # ============================================================
    if not st.session_state["modo_edicion"]:
    
        st.subheader("Lista de jugadores")

        escuelas = st.session_state["escuelas"]
        rareza = st.session_state["rareza"]
        roles = st.session_state["roles"]
        
        colf1, colf2, colf3 = st.columns(3)
        
        with colf1:
            filtro_escuela = st.selectbox("Escuela", ["Todas"] + escuelas)
        
        with colf2:
            filtro_rareza = st.selectbox("Rareza", ["Todas"] + rareza)
        
        with colf3:
            filtro_rol = st.selectbox("Rol", ["Todos"] + roles)
        
        jugadores_filtrados = player_service.get_filtered_players(
            config, 
            filtro_escuela, 
            filtro_rareza, 
            filtro_rol
        )
        
        jugadores_filtrados = player_service.sort_players_by_rarity(
            jugadores_filtrados, 
            config, 
            st.session_state["rareza"]
        )

        cols = st.columns(4)
        idx = 0
    
        for jugador in jugadores_filtrados:
            with cols[idx % 4]:
                mostrar_foto(jugador, config)
    
                if st.button(f"Editar {jugador}", key=f"btn_sel_{jugador}"):
                    st.session_state["jugador_seleccionado"] = jugador
                    st.session_state["modo_edicion"] = True
                    st.rerun()
    
            idx += 1
    
        st.stop()  # No mostrar nada más si no estamos editando
    
    
    # ============================================================
    # 3️⃣ MODO EDICIÓN — SOLO SI HAY JUGADOR SELECCIONADO
    # ============================================================
    jugador = st.session_state["jugador_seleccionado"]
    
    st.subheader(f"Editar jugador: {jugador}")
    
    # Mostrar imagen grande
    imagen_actual = config[jugador].get("imagen", "default.png")
    ruta_img = os.path.join("data", "imagenes_jugadores", imagen_actual)
    if not os.path.exists(ruta_img):
        ruta_img = os.path.join("data", "imagenes_jugadores", "default.png")
    
    st.image(ruta_img, width=200)
    st.write("")
    
    # ============================================================
    # EDITOR COMPLETO (tu código actual)
    # ============================================================
    
    # 1. Checkbox Equipar
    config[jugador]["Equipar"] = st.checkbox(
        "Calcular Build Recomendada",
        value=config[jugador].get("Equipar", False)
    )
    
    # 2. Tipos recomendados
    if "builds" not in config[jugador]:
        config[jugador]["builds"] = {"Base": {"tipos_recomendados": [], "stats_recomendados": {"stats": [], "puntos": []}}}
    
    build_base = config[jugador]["builds"]["Base"]
    
    tipos_actuales = [t for t in build_base.get("tipos_recomendados", []) if t in tipos]
    tipos_seleccionados = st.multiselect("Tipos prioritarios", tipos, default=tipos_actuales)
    
    # 3. Stats recomendados
    stats_actuales = build_base.get("stats_recomendados", {}).get("stats", [])
    puntos_actuales = build_base.get("stats_recomendados", {}).get("puntos", [])
    
    stats_limpios = []
    puntos_limpios = []
    for s, p in zip(stats_actuales, puntos_actuales):
        if s in stats:
            stats_limpios.append(s)
            puntos_limpios.append(p)
    
    stats_actuales = stats_limpios
    puntos_actuales = puntos_limpios
    
    stats_y_puntos = list(zip(stats_actuales, puntos_actuales))
    stats_y_puntos.sort(key=lambda x: x[1], reverse=True)
    
    stats_actuales = [s for s, p in stats_y_puntos]
    puntos_actuales = [p for s, p in stats_y_puntos]
    
    stats_seleccionados = st.multiselect("Stats recomendados", stats, default=stats_actuales)
    
    # 4. Puntos por stat
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
    
    # 5. Configuración adicional
    st.subheader("Configuración adicional")
    
    candidatos_4_actuales = [t for t in build_base.get("candidatos_4", []) if t in tipos]
    candidatos_4 = st.multiselect("Tipos candidatos para set de 4 piezas", tipos, default=candidatos_4_actuales)
    
    #slots_activos_actuales = [str(s) for s in config[jugador].get("slots_activos", [])]
    #slots_activos = st.multiselect("Slots activos", ["1", "2", "3", "4", "5", "6"], default=slots_activos_actuales)
    
    # ============================================================
    # BOTONES GUARDAR / CANCELAR / RESTABLECER
    # ============================================================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Guardar cambios"):
            config[jugador]["builds"]["Base"]["tipos_recomendados"] = tipos_seleccionados
            config[jugador]["builds"]["Base"]["stats_recomendados"] = {"stats": stats_seleccionados, "puntos": puntos}
            config[jugador]["builds"]["Base"]["candidatos_4"] = candidatos_4
    
            player_service.save_overrides(config, get_current_user_id())
    
            st.session_state["modo_edicion"] = False
            st.session_state["jugador_seleccionado"] = None
            st.success("Cambios guardados.")
            st.rerun()
    
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state["modo_edicion"] = False
            st.session_state["jugador_seleccionado"] = None
            st.rerun()

    with col3:
        if st.button("🔄 Restablecer", help="Vuelve a la configuración predeterminada"):
            restore_player_config(jugador)
            st.session_state["modo_edicion"] = False
            st.session_state["jugador_seleccionado"] = None
            st.success("Configuración restablecida.")
            st.rerun()
    
if __name__ == "__main__":
    main()
else:
    main()
