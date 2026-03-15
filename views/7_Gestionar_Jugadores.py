import streamlit as st
import os
from data_manager import load_all_into_session, save_json, rename_jugador, check_role


def main():
    check_role("admin")
    load_all_into_session()

    st.title("👤 Gestionar Jugadores")

    jugadores = st.session_state["jugadores"]              # LISTA de strings
    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]
    config = st.session_state["config_jugadores"]
    escuelas = st.session_state["escuelas"]
    rareza = st.session_state["rareza"]
    roles = st.session_state["roles"]

    modo = st.radio("Modo", ["Añadir", "Editar"])

    # ============================================================
    # MODO EDITAR
    # ============================================================
    if modo == "Editar":

        lista_jugadores = sorted(jugadores, key=lambda x: x.lower())
        jugador = st.selectbox("Selecciona jugador", lista_jugadores)
        
        # ============================================================
        # CHECKBOX ACTIVO
        # ============================================================
        config[jugador]["activo"] = st.checkbox(
            "Activar jugador",
            value=config[jugador].get("activo", False)
        )

        # ============================
        # RENOMBRAR JUGADOR
        # ============================
        with st.expander("Cambiar nombre del jugador", expanded=False):

            nuevo_nombre = st.text_input("Nuevo nombre", value=jugador)
    
            if st.button("Renombrar jugador"):
                if nuevo_nombre and nuevo_nombre != jugador:
                    ok, msg = rename_jugador(jugador, nuevo_nombre)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        st.divider()

        # Asegurar que existe config
        if jugador not in config:
            config[jugador] = {
                "Equipar": False,
                "activo": False,
                "builds": {
                    "Base": {
                        "tipos_recomendados": [],
                        "stats_recomendados": {"stats": [], "puntos": []},
                        "candidatos_4": []
                    }
                },
                "slots_activos": ["1", "2", "3", "4", "5", "6"],
                "imagen": "default.png",
                "escuela": "",
                "rareza": "",
                "rol": ""
            }

        # ============================================================
        # IMAGEN DEL JUGADOR
        # ============================================================
        st.subheader("📸 Imagen del jugador")

        imagen_actual = config[jugador].get("imagen", "default.png")
        ruta_img = os.path.join("data", "imagenes_jugadores", imagen_actual)

        if os.path.exists(ruta_img):
            st.image(ruta_img, width=150)
        else:
            st.warning(f"No se encontró la imagen '{imagen_actual}'. Usando default.png.")
            st.image("data/imagenes_jugadores/default.png", width=150)

        # Clave dinámica para evitar bucles
        reset_key = f"reset_uploader_{jugador}"
        if reset_key not in st.session_state:
            st.session_state[reset_key] = 0

        uploader_key = f"uploader_img_{jugador}_{st.session_state[reset_key]}"

        archivo_imagen = st.file_uploader(
            "Subir nueva imagen",
            type=["png", "jpg", "jpeg"],
            key=uploader_key
        )

        if archivo_imagen is not None:

            ruta = "data/imagenes_jugadores"
            os.makedirs(ruta, exist_ok=True)

            nombre_archivo = f"{jugador}.png"
            ruta_completa = os.path.join(ruta, nombre_archivo)

            with open(ruta_completa, "wb") as f:
                f.write(archivo_imagen.getbuffer())

            config[jugador]["imagen"] = nombre_archivo
            save_json("config_jugadores", config)

            st.success("Imagen actualizada correctamente.")

            st.session_state[reset_key] += 1
            st.rerun()

        # -----------------------------
        # ATRIBUTOS FILTRABLES
        # -----------------------------
        st.subheader("Atributos filtrables")

        escuela_actual = config[jugador].get("escuela", "")
        rareza_actual = config[jugador].get("rareza", "")
        rol_actual = config[jugador].get("rol", "")

        escuela_sel = st.selectbox(
            "Escuela",
            [""] + escuelas,
            index=escuelas.index(escuela_actual)+1 if escuela_actual in escuelas else 0
        )

        rareza_sel = st.selectbox(
            "Rareza",
            [""] + rareza,
            index=rareza.index(rareza_actual)+1 if rareza_actual in rareza else 0
        )

        rol_sel = st.selectbox(
            "Rol",
            [""] + roles,
            index=roles.index(rol_actual)+1 if rol_actual in roles else 0
        )

        # -----------------------------
        # TIPOS RECOMENDADOS
        # -----------------------------
        if "builds" not in config[jugador]:
            config[jugador]["builds"] = {"Base": {}}
        if "Base" not in config[jugador]["builds"]:
            config[jugador]["builds"]["Base"] = {}
            
        build = config[jugador]["builds"]["Base"]
        tipos_actuales = [t for t in build.get("tipos_recomendados", []) if t in tipos]

        tipos_seleccionados = st.multiselect(
            "Tipos prioritarios",
            tipos,
            default=tipos_actuales
        )

        # -----------------------------
        # STATS RECOMENDADOS
        # -----------------------------
        stats_actuales = build.get("stats_recomendados", {}).get("stats", [])
        puntos_actuales = build.get("stats_recomendados", {}).get("puntos", [])

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

        candidatos_4_actuales = build.get("candidatos_4", [])
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

            config[jugador]["builds"]["Base"]["tipos_recomendados"] = tipos_seleccionados
            config[jugador]["builds"]["Base"]["stats_recomendados"] = {
                "stats": stats_seleccionados,
                "puntos": puntos
            }
            config[jugador]["builds"]["Base"]["candidatos_4"] = candidatos_4
            config[jugador]["slots_activos"] = slots_activos
            config[jugador]["escuela"] = escuela_sel
            config[jugador]["rareza"] = rareza_sel
            config[jugador]["rol"] = rol_sel

            save_json("config_jugadores", config)

            st.success(f"Jugador '{jugador}' actualizado correctamente.")
            st.rerun()

    # ============================================================
    # MODO AÑADIR
    # ============================================================
    else:
        st.subheader("📸 Datos básicos")
        
        nombre = st.text_input("Nombre del jugador")
        
        # ============================================================
        # CHECKBOX ACTIVO
        # ============================================================
        activo_sel = st.checkbox(
            "Activar jugador",
            value = False
        )
        
        rareza_sel = st.selectbox("Rareza",[""] + rareza)
        rol_sel = st.selectbox("Rol",[""] + roles)
        
        escuela_sel = st.selectbox("Escuela",[""] + escuelas)

        # ============================================================
        # IMAGEN DEL NUEVO JUGADOR
        # ============================================================
        st.subheader("📸 Imagen del jugador (opcional)")

        archivo_imagen_nuevo = st.file_uploader(
            "Subir imagen",
            type=["png", "jpg", "jpeg"],
            key="imagen_nueva"
        )

        nombre_archivo_nuevo = ""

        if archivo_imagen_nuevo:
            ruta = "data/imagenes_jugadores"
            os.makedirs(ruta, exist_ok=True)

            nombre_archivo_nuevo = f"{nombre}.png"
            ruta_completa = os.path.join(ruta, nombre_archivo_nuevo)

            with open(ruta_completa, "wb") as f:
                f.write(archivo_imagen_nuevo.getbuffer())
        
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
            
            if not rareza_sel:
                st.error("La rareza tiene que estar informada.")
                return
            
            if not rol_sel:
                st.error("El rol tiene que estar informado.")
                return

            config[nombre] = {
                "Equipar": False,
                "activo": activo_sel,
                "builds": {
                    "Base": {
                        "tipos_recomendados": tipos_seleccionados,
                        "stats_recomendados": {
                            "stats": stats_seleccionados,
                            "puntos": puntos
                        },
                        "candidatos_4": candidatos_4
                    }
                },
                "slots_activos": slots_activos,
                "imagen": nombre_archivo_nuevo or "default.png",
                "escuela": escuela_sel,
                "rareza": rareza_sel,
                "rol": rol_sel
            }


            save_json("config_jugadores", config)

            st.success(f"Jugador '{nombre}' añadido correctamente.")
            st.rerun()

    st.divider()

    # ============================================================
    # ELIMINAR JUGADOR
    # ============================================================
    st.header("🗑️ Eliminar jugador")

    jugador_del = st.selectbox("Selecciona jugador a eliminar", [""] + jugadores)

    if st.button("Eliminar jugador"):
        if jugador_del:

            config.pop(jugador_del, None)

            save_json("config_jugadores", config)

            st.success(f"Jugador '{jugador_del}' eliminado correctamente.")
            st.rerun()


if __name__ == "__main__":
    main()
else:
    main()
