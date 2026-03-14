import streamlit as st
import json
import os
import pandas as pd

#from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from optimizer import asignar_todos_los_jugadores, formatear_stat
from data_manager import (
    save_equipamiento,
    equipar_pieza,
    piezas_bloqueadas,
    resetear_equipamiento,
    load_all_into_session,
    save_config_jugadores,
    save_orden_jugadores
)

def main():

    st.title("⚡ Equipar jugadores")
    #oad_all_into_session()

    # -----------------------------
    # 1. Cargar datos base
    # -----------------------------
    if "inventarios" not in st.session_state:
        st.error("Primero debes cargar los datos en la página Home.")
        return

    inventarios = st.session_state["inventarios"]
    stats_recomendados = st.session_state["stats_recomendados"]
    tipos_recomendados = st.session_state["tipos_recomendados"]

    # Equipamiento REAL cargado desde Home
    piezas_equipadas = st.session_state.get("equipamiento", {})

    # Configuración de jugadores
    config = st.session_state["config_jugadores"]

    # -----------------------------
    # 2. Sincronizar jugadores detectados con config
    # -----------------------------
    jugadores_detectados = list(stats_recomendados.keys())

    if jugadores_detectados:
        for j in jugadores_detectados:
            if j not in config:
                config[j] = {}

        save_config_jugadores(config)
        load_all_into_session()

        # Recargar config y equipamiento tras la sincronización
        config = st.session_state["config_jugadores"]
        piezas_equipadas = st.session_state["equipamiento"]

    # -----------------------------
    # 3. Orden persistente de jugadores
    # -----------------------------
    if "orden_jugadores" not in st.session_state:
        st.session_state["orden_jugadores"] = list(config.keys())

    orden = st.session_state["orden_jugadores"]

    # Añadir jugadores nuevos al orden
    for j in config.keys():
        if j not in orden:
            orden.append(j)

    # Eliminar jugadores que ya no existan
    orden = [j for j in orden if j in config]

    st.session_state["orden_jugadores"] = orden

    jugadores = orden

    # -----------------------------
    # 2. Orden de prioridad de jugadores (sin AgGrid, con expander y sin scroll)
    # -----------------------------
    with st.expander("📋 Orden de prioridad de jugadores", expanded=False):

        df_prioridad = pd.DataFrame({
            "Prioridad": list(range(1, len(jugadores) + 1)),
            "Jugador": jugadores
        })

        # Calcular altura exacta para evitar scroll
        altura = 40 + len(df_prioridad) * 35

        st.markdown("Modifica la prioridad manualmente y pulsa **Confirmar** para aplicar los cambios.")

        df_editado = st.data_editor(
            df_prioridad,
            hide_index=True,
            use_container_width=True,
            height=altura,
            column_config={
                "Prioridad": st.column_config.NumberColumn(
                    "Prioridad",
                    min_value=1,
                    max_value=len(jugadores),
                    step=1
                ),
                "Jugador": st.column_config.Column(disabled=True)
            },
            key="editor_prioridad",
        )

        if st.button("✔️ Confirmar", use_container_width=True):
            df_ordenado = df_editado.sort_values("Prioridad").reset_index(drop=True)
            nuevo_orden = df_ordenado["Jugador"].tolist()
    
            st.session_state["orden_jugadores"] = nuevo_orden
    
            nuevo_config = {j: config[j] for j in nuevo_orden}
            save_config_jugadores(nuevo_config)
            nuevo_orden = df_ordenado["Jugador"].tolist()
            save_orden_jugadores(nuevo_orden)

            load_all_into_session()
    
            st.rerun()
            st.success("Orden actualizado correctamente.")

    # -----------------------------
    # 3. Ejecutar optimizador
    # -----------------------------
    st.subheader("Recomendaciones")

    piezas_equipadas = st.session_state["equipamiento"]

    resultados = asignar_todos_los_jugadores(
        lista_jugadores=jugadores,
        inventarios=inventarios,
        config_jugadores=config,
        stats_recomendados=stats_recomendados,
        tipos_recomendados=tipos_recomendados,
        piezas_equipadas=piezas_equipadas
    )

    st.session_state["resultados_optimizador"] = resultados

    # ============================================================
    # 3.1 Lista de jugadores con cambios pendientes (elegante)
    # ============================================================
    
    jugadores_con_cambios = []
    
    for jugador in jugadores:
        res = resultados[jugador]
        ids_recomendados = res["ids_por_slot"]
        ids_actuales = piezas_equipadas.get(jugador, {})
    
        hay_cambios = False
        for slot, id_rec in ids_recomendados.items():
            id_rec_str = str(id_rec) if id_rec is not None else ""
            id_act_str = str(ids_actuales.get(str(slot), ""))
    
            if id_rec_str and id_rec_str != id_act_str:
                hay_cambios = True
                break
    
        if hay_cambios:
            jugadores_con_cambios.append(jugador)
    
    st.markdown("## 🔄 Cambios recomendados sin aplicar")
    
    if jugadores_con_cambios:
        st.write(", ".join(jugadores_con_cambios))
    else:
        st.write("✔ No hay cambios pendientes")
    
    st.divider()
    
    # ============================================================
    # 4. Mostrar resultados por jugador (expanders automáticos)
    # ============================================================
    
    for jugador in jugadores:
    
        res = resultados[jugador]
        ids_recomendados = res["ids_por_slot"]
    
        # 🔥 Se expande automáticamente si tiene cambios pendientes
        expanded = jugador in jugadores_con_cambios
    
        with st.expander(f"🏐 Recomendaciones para {jugador}", expanded=expanded):


            tabla = []

            for slot, id_rec in ids_recomendados.items():

                df_inv = inventarios[slot]

                if isinstance(df_inv, list):
                    df_inv = pd.DataFrame(df_inv).fillna("")
                else:
                    df_inv = df_inv.fillna("")

                df_inv["ID_str"] = df_inv["ID"].astype(str)
                id_rec_str = str(id_rec)

                fila = df_inv[df_inv["ID_str"] == id_rec_str]

                #if not fila.empty:
                #    tipo = fila["Tipo"].values[0]
                #    main = fila["Main Stat"].values[0]
                #    sub1 = fila["Substat1"].values[0]
                #    sub2 = fila["Substat2"].values[0]
                #    sub3 = fila["Substat3"].values[0]
                #    sub4 = fila["Substat4"].values[0]
                #    calidad = fila["Calidad"].values[0]
                if not fila.empty:
                    tipo = fila["Tipo"].values[0]
                    calidad = fila["Calidad"].values[0]
                
                    # 🔥 Recuperar tipos de mejora
                    tm_main = fila["Tipo_Mejora_Main"].values[0] if "Tipo_Mejora_Main" in fila else ""
                    tm_sub1 = fila["Tipo_Mejora_Sub1"].values[0] if "Tipo_Mejora_Sub1" in fila else ""
                    tm_sub2 = fila["Tipo_Mejora_Sub2"].values[0] if "Tipo_Mejora_Sub2" in fila else ""
                    tm_sub3 = fila["Tipo_Mejora_Sub3"].values[0] if "Tipo_Mejora_Sub3" in fila else ""
                    tm_sub4 = fila["Tipo_Mejora_Sub4"].values[0] if "Tipo_Mejora_Sub4" in fila else ""
                
                    # 🔥 Formatear stats igual que en Gestionar Inventarios
                    main = formatear_stat(fila["Main Stat"].values[0], tm_main)
                    sub1 = formatear_stat(fila["Substat1"].values[0], tm_sub1)
                    sub2 = formatear_stat(fila["Substat2"].values[0], tm_sub2)
                    sub3 = formatear_stat(fila["Substat3"].values[0], tm_sub3)
                    sub4 = formatear_stat(fila["Substat4"].values[0], tm_sub4)

                else:
                    tipo = main = sub1 = sub2 = sub3 = sub4 = calidad = ""

                id_actual = piezas_equipadas.get(jugador, {}).get(str(slot), "")
                id_actual_str = str(id_actual)

                tabla.append({
                    "Slot": slot,
                    "ID actual": id_actual_str,
                    "ID recom.": id_rec_str,
                    "Calidad": calidad,
                    "Tipo": tipo,
                    "Main Stat": main,
                    "Substat1": sub1,
                    "Substat2": sub2,
                    "Substat3": sub3,
                    "Substat4": sub4,
                })

            df_tabla = pd.DataFrame(tabla)
            df_tabla = df_tabla.sort_values("Slot").reset_index(drop=True)

            df_editado = st.data_editor(
                df_tabla,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ID actual": st.column_config.TextColumn(
                        "ID actual",
                        help="Escribe manualmente el ID que quieres equipar en este slot."
                    )
                },
                key=f"editor_{jugador}"
            )

            # -----------------------------------------
            # Aviso: ID recomendado usado por jugador de menor prioridad
            # -----------------------------------------
            conflictos = []

            idx_actual = jugadores.index(jugador)

            for idx, fila in df_tabla.iterrows():
                slot = fila["Slot"]
                id_rec = str(fila["ID recom."])

                for j2 in jugadores[idx_actual + 1:]:
                    id_j2 = piezas_equipadas.get(j2, {}).get(str(slot), "")
                    if str(id_j2) == id_rec and id_rec != "":
                        conflictos.append((slot, id_rec, j2))

            if conflictos:
                for slot, id_rec, j2 in conflictos:
                    st.markdown(
                        f"⚠️ Slot **{slot}** → ID **{id_rec}** está equipado por **{j2}** (prioridad inferior)"
                    )

            # Botón para confirmar cambios parciales
            if st.button(f"Confirmar cambios para {jugador}", key=f"confirmar_{jugador}"):
                cambios = 0
                for idx, fila in df_editado.iterrows():
                    slot = fila["Slot"]
                    nuevo_id = fila["ID actual"]
                    anterior = df_tabla.loc[idx, "ID actual"]

                    if nuevo_id != anterior:
                        equipar_pieza(jugador, slot, nuevo_id)
                        load_all_into_session()
                        piezas_equipadas = st.session_state["equipamiento"]
                        cambios += 1

                if cambios > 0:
                    st.success(f"Se actualizaron {cambios} slots para {jugador}.")
                else:
                    st.info("No se detectaron cambios.")

                st.rerun()

            # Botón para equipar todo
            if st.button(f"Equipar todo para {jugador}", key=f"equipar_{jugador}"):
            
                for slot, id_rec in ids_recomendados.items():
                    if id_rec is None or id_rec == "":
                        continue
            
                    equipar_pieza(jugador, slot, str(id_rec))
            
                load_all_into_session()
            
                st.success(f"Equipamiento actualizado para {jugador}")
                st.rerun()

            st.divider()
    
    # ---------------------------------------------------------
    # Botón para resetear TODO el equipamiento
    # ---------------------------------------------------------
    if st.button("🧹 Resetear equipamiento (vaciar todo)", type="primary"):
        resetear_equipamiento()
        load_all_into_session()
        st.success("Todo el equipamiento ha sido reseteado.")
        st.rerun()

if __name__ == "__main__":
    main()
