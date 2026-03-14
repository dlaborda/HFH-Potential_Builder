import streamlit as st
import pandas as pd
from optimizer import asignar_todos_los_jugadores, formatear_stat, evaluar_pieza_para_jugador_en_slot
from data_manager import (
    save_equipamiento,
    equipar_pieza,
    resetear_equipamiento,
    load_all_into_session,
    save_orden_jugadores
)

def get_text_color(calidad):
    """Returns CSS for text color based on quality."""
    colors = {
        "Perfecto": "color: #8E44AD; font-weight: bold",
        "Excelente": "color: #2980B9; font-weight: bold",
        "Bueno": "color: #27AE60; font-weight: bold",
        "Aceptable": "color: #F1C40F; font-weight: bold",
        "Malo": "color: #C0392B; font-weight: bold",
        "Falta": "color: #999999; font-style: italic"
    }
    return colors.get(calidad, "color: inherit")

def main():
    st.title("⚡ Equipar jugadores")

    if "inventarios" not in st.session_state:
        st.error("Primero debes cargar los datos en la página Home.")
        return

    inventarios = st.session_state["inventarios"]
    config = st.session_state["config_jugadores"]
    piezas_equipadas = st.session_state.get("equipamiento", {})

    stats_recomendados = {
        jugador: {
            "stats": config[jugador]["stats_recomendados"]["stats"],
            "puntos": dict(zip(
                config[jugador]["stats_recomendados"]["stats"],
                config[jugador]["stats_recomendados"]["puntos"]
            ))
        }
        for jugador in config
    }

    tipos_recomendados = {
        jugador: config[jugador]["tipos_recomendados"]
        for jugador in config
    }

    # Sync player order
    if "orden_jugadores" not in st.session_state:
        st.session_state["orden_jugadores"] = []

    orden = st.session_state["orden_jugadores"]
    orden = [j for j in orden if j in config and config[j].get("Equipar", False)]
    for j in config:
        if config[j].get("Equipar", False) and j not in orden:
            orden.append(j)

    st.session_state["orden_jugadores"] = orden
    save_orden_jugadores(orden)
    jugadores = orden

    with st.expander("📋 Orden de prioridad", expanded=False):
        df_prioridad = pd.DataFrame({"Prioridad": list(range(1, len(jugadores) + 1)), "Jugador": jugadores})
        df_editado = st.data_editor(df_prioridad, hide_index=True, use_container_width=True)
        if st.button("✔️ Confirmar Prioridad"):
            nuevo_orden = df_editado.sort_values("Prioridad")["Jugador"].tolist()
            st.session_state["orden_jugadores"] = nuevo_orden
            save_orden_jugadores(nuevo_orden)
            st.rerun()

    st.subheader("Recomendaciones")
    
    # 1. Execute optimizer and calculate all data first
    resultados = asignar_todos_los_jugadores(
        lista_jugadores=jugadores,
        inventarios=inventarios,
        config_jugadores=config,
        stats_recomendados=stats_recomendados,
        tipos_recomendados=tipos_recomendados,
        piezas_equipadas=piezas_equipadas
    )
    st.session_state["resultados_optimizador"] = resultados

    # 2. Identify players with pending changes
    jugadores_con_cambios = []
    player_data_cache = {}

    # Pre-map which piece is where to detect conflicts
    mapa_equipamiento_actual = {} # {(slot, piece_id): jugador}
    for j, slots in piezas_equipadas.items():
        for s, pid in slots.items():
            if pid:
                # Normalizar ID (quitar .0 si existe)
                pid_str = str(pid).replace(".0", "")
                mapa_equipamiento_actual[(str(s), pid_str)] = j

    for jugador in jugadores:
        res = resultados[jugador]
        ids_recomendados = res["ids_por_slot"]
        equip_actual = piezas_equipadas.get(jugador, {})
        
        has_pending_changes = False
        cambios_list = []
        actual_list = []
        conflictos = []
        p_total_act = 0
        p_total_rec = 0

        for slot_idx in range(1, 7):
            s = str(slot_idx)
            # Current
            pid_act = equip_actual.get(s)
            eval_act = {"puntaje": 0, "calidad": "Falta"}
            pieza_act_data = None
            if pid_act:
                pieza_act_data = next((p for p in inventarios[s] if str(p["ID"]).replace(".0", "") == str(pid_act).replace(".0", "")), None)
                if pieza_act_data:
                    eval_act = evaluar_pieza_para_jugador_en_slot(pieza_act_data, jugador, pieza_act_data["Tipo"], s, inventarios, config[jugador]["stats_recomendados"])
            p_total_act += eval_act["puntaje"]

            # Recommended
            id_rec = ids_recomendados.get(s)
            eval_rec = {"puntaje": 0, "calidad": "Falta"}
            pieza_rec_data = None
            if id_rec:
                pieza_rec_data = next((p for p in inventarios[s] if str(p["ID"]).replace(".0", "") == str(id_rec).replace(".0", "")), None)
                if pieza_rec_data:
                    eval_rec = evaluar_pieza_para_jugador_en_slot(pieza_rec_data, jugador, pieza_rec_data["Tipo"], s, inventarios, config[jugador]["stats_recomendados"])
            p_total_rec += eval_rec["puntaje"]

            # Conflict detection: is id_rec equipped by a LESS priority player?
            if id_rec:
                id_rec_str = str(id_rec).replace(".0", "")
                poseedor = mapa_equipamiento_actual.get((s, id_rec_str))
                if poseedor and poseedor != jugador:
                    # check priority (higher priority is earlier in 'jugadores' list)
                    idx_actual = jugadores.index(jugador)
                    idx_poseedor = jugadores.index(poseedor) if poseedor in jugadores else 999
                    if idx_poseedor > idx_actual:
                        conflictos.append(f"El potencial **{id_rec_str}** (Slot {s}) está equipado por **{poseedor}**.")

            # Store actual row for table
            if pieza_act_data:
                actual_list.append({
                    "Slot": s, "ID": str(pid_act), "Tipo": pieza_act_data["Tipo"],
                    "Calidad": pieza_act_data.get("Calidad", ""),
                    "Main Stat": formatear_stat(pieza_act_data["Main Stat"], pieza_act_data.get("Tipo_Mejora_Main", "")),
                    "Sub1": formatear_stat(pieza_act_data.get("Substat1"), pieza_act_data.get("Tipo_Mejora_Sub1")),
                    "Sub2": formatear_stat(pieza_act_data.get("Substat2"), pieza_act_data.get("Tipo_Mejora_Sub2")),
                    "Sub3": formatear_stat(pieza_act_data.get("Substat3"), pieza_act_data.get("Tipo_Mejora_Sub3")),
                    "Sub4": formatear_stat(pieza_act_data.get("Substat4"), pieza_act_data.get("Tipo_Mejora_Sub4")),
                    "_calidad": eval_act["calidad"]
                })
            else:
                actual_list.append({"Slot": s, "ID": str(pid_act) if pid_act else "Vacío", "Tipo": "-", "Calidad": "", "Main Stat": "", "Sub1": "", "Sub2": "", "Sub3": "", "Sub4": "", "_calidad": "Falta"})

            # Detect and store change
            if id_rec and str(id_rec) != str(pid_act or ""):
                has_pending_changes = True
                if pieza_rec_data:
                    cambios_list.append({
                        "Slot": s, "Actual ID": str(pid_act or "Vacío"), "Nuevo ID": str(id_rec), "Tipo": pieza_rec_data["Tipo"],
                        "Calidad": pieza_rec_data.get("Calidad", ""),
                        "Main Stat": formatear_stat(pieza_rec_data["Main Stat"], pieza_rec_data.get("Tipo_Mejora_Main", "")),
                        "Sub1": formatear_stat(pieza_rec_data.get("Substat1"), pieza_rec_data.get("Tipo_Mejora_Sub1")),
                        "Sub2": formatear_stat(pieza_rec_data.get("Substat2"), pieza_rec_data.get("Tipo_Mejora_Sub2")),
                        "Sub3": formatear_stat(pieza_rec_data.get("Substat3"), pieza_rec_data.get("Tipo_Mejora_Sub3")),
                        "Sub4": formatear_stat(pieza_rec_data.get("Substat4"), pieza_rec_data.get("Tipo_Mejora_Sub4")),
                        "_calidad": eval_rec["calidad"]
                    })

        if has_pending_changes:
            jugadores_con_cambios.append(jugador)
        
        player_data_cache[jugador] = {
            "has_changes": has_pending_changes,
            "actual_table": actual_list,
            "cambios_table": cambios_list,
            "conflictos": conflictos,
            "p_act": p_total_act,
            "p_rec": p_total_rec
        }

    # 3. Display Summary Header
    st.markdown("## 🔄 Cambios recomendados sin aplicar")
    if jugadores_con_cambios:
        st.write(", ".join(jugadores_con_cambios))
    else:
        st.write("✔ No hay cambios pendientes")
    st.divider()

    # 4. Render Player Expanders
    for jugador in jugadores:
        data = player_data_cache[jugador]
        # Expanders are closed by default UNLESS the player has pending changes
        with st.expander(f"🏐 Gestión de equipamiento: {jugador}", expanded=data["has_changes"]):
            st.markdown("### 🎽 Equipamiento Actual")
            df_actual = pd.DataFrame(data["actual_table"])
            st.dataframe(
                df_actual.style.apply(lambda row: [get_text_color(row["_calidad"])] * len(row), axis=1),
                use_container_width=True, hide_index=True,
                column_order=["Slot", "ID", "Tipo", "Calidad", "Main Stat", "Sub1", "Sub2", "Sub3", "Sub4"]
            )

            if data["has_changes"]:
                st.markdown("### 🔄 Cambios Recomendados")
                diff = data["p_rec"] - data["p_act"]
                st.info(f"📈 **Mejora total del build:** {round(diff, 1)} puntos ({round(data['p_act'], 1)} → {round(data['p_rec'], 1)})")
                
                df_cambios = pd.DataFrame(data["cambios_table"])
                st.dataframe(
                    df_cambios.style.apply(lambda row: [get_text_color(row["_calidad"])] * len(row), axis=1),
                    use_container_width=True, hide_index=True,
                    column_order=["Slot", "Actual ID", "Nuevo ID", "Tipo", "Calidad", "Main Stat", "Sub1", "Sub2", "Sub3", "Sub4"]
                )

                if data["conflictos"]:
                    st.warning("⚠️ **Conflictos de prioridad:**\n\n" + "\n".join([f"- {c}" for c in data["conflictos"]]))
                
                # Permite seleccionar qué cambios aplicar
                slots_disponibles = [f"Slot {c['Slot']}" for c in data["cambios_table"]]
                slots_seleccionados_str = st.multiselect(
                    "📌 Selecciona los cambios a aplicar:",
                    options=slots_disponibles,
                    default=slots_disponibles,
                    key=f"sel_{jugador}"
                )
                
                # Mapear de nuevo a los IDs de los slots
                slots_seleccionados = [s.split(" ")[1] for s in slots_seleccionados_str]

                if st.button(f"Aplicar cambios seleccionados para {jugador}", key=f"apply_{jugador}"):
                    if not slots_seleccionados:
                        st.warning("⚠️ Debes seleccionar al menos un slot.")
                    else:
                        for c in data["cambios_table"]:
                            if c["Slot"] in slots_seleccionados:
                                equipar_pieza(jugador, c["Slot"], c["Nuevo ID"])
                        st.success(f"Equipamiento de {jugador} actualizado.")
                        load_all_into_session()
                        st.rerun()
            else:
                st.success("✨ El equipamiento actual es el óptimo.")
            
            st.divider()

    if st.button("🧹 Resetear todo el equipamiento", type="primary"):
        resetear_equipamiento()
        load_all_into_session()
        st.rerun()

if __name__ == "__main__":
    main()
else:
    main()
