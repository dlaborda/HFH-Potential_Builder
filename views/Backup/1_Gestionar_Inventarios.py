import streamlit as st
import pandas as pd

from optimizer import (
    puntuar_pieza,
    jugadores_que_usan_tipo,
    puntajes_por_jugador_para_pieza,
    prioridad_tipo_para_jugador,
    puntaje_equilibrado,
    calcular_puntajes_equilibrados_globales,
    es_desechable_consistente,
)

from data_manager import load_all_into_session, save_json


# ============================================================
# 1. MODAL OFICIAL (CON DETALLE POR JUGADOR)
# ============================================================
@st.dialog("📥 Confirmación de inserción")
def modal_confirmacion(pieza, detalle_global, detalle_por_jugador, slot, inventarios):

    tipo = pieza["Tipo"]

    st.write(f"**Tipo:** {tipo}")
    st.write(f"**Slot:** {slot}")
    st.write(f"**Calidad:** {pieza['Calidad']}")

    substats = [pieza.get(f"Substat{i}", "") for i in range(1, 5)]
    substats = [s for s in substats if s]
    st.write(f"**Main Stat:** {pieza['Main Stat']}")
    st.write("**Substats:** " + (" / ".join(substats) if substats else "—"))

    st.markdown("### 🧠 Motivo de clasificación")
    st.write(detalle_global.get("motivo", ""))

    jugadores_que_usan = detalle_global.get("jugadores_que_usan", [])

    if len(jugadores_que_usan) == 0:
        st.info(
            "Actualmente **ningún jugador utiliza este tipo**. "
            "La pieza se conservará hasta que exista al menos un jugador que lo use."
        )
    else:
        st.markdown("### 🧩 Posición de la pieza por jugador")

        for jugador, info in detalle_por_jugador.items():
            puesto = info["puesto_pieza"]
            total = info["total_candidatas"]
            puntaje_pieza = info["puntaje_pieza"]
            posiciones_reservadas = info["posiciones_reservadas"]
            puntaje_peor_en_top = info["puntaje_peor_en_top"]
            entra_en_top = info["entra_en_top"]

            if puesto is None:
                st.write(f"- **{jugador}**: la pieza no entra en el ranking.")
                continue

            if entra_en_top:
                st.success(
                    f"{jugador}: puesto **{puesto} de {total}**, "
                    f"con **{puntaje_pieza:.2f} puntos**, "
                    f"dentro de las **{posiciones_reservadas} posiciones reservadas**."
                )
            else:
                if puntaje_peor_en_top is not None:
                    st.error(
                        f"{jugador}: puesto **{puesto} de {total}**, "
                        f"con **{puntaje_pieza:.2f} puntos**. "
                        f"La peor pieza que entra en el TOP tiene **{puntaje_peor_en_top:.2f} puntos**."
                    )
                else:
                    st.warning(
                        f"{jugador}: puesto **{puesto} de {total}**, "
                        f"con **{puntaje_pieza:.2f} puntos**, "
                        f"pero aún no hay suficientes piezas para llenar el TOP."
                    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Confirmar inserción"):
            inventarios[slot].append(pieza)
            save_json("inventarios", inventarios)
            st.session_state["modal_result"] = "confirmar"
            st.rerun()

    with col2:
        if st.button("Cancelar"):
            st.session_state["modal_result"] = "cancelar"
            st.rerun()


# ============================================================
# 2. HELPERS
# ============================================================
def encontrar_pieza_por_id(inventarios, pieza_id, slot):
    piezas_slot = inventarios.get(slot, [])
    for p in piezas_slot:
        if str(p["ID"]) == str(pieza_id):
            return p
    return None


def piezas_mismo_tipo_y_slot(tipo, slot_i, inventarios, piezas_equipadas):
    piezas_slot = inventarios.get(slot_i, [])
    resultado = [p for p in piezas_slot if p["Tipo"] == tipo]

    ids_ya = {str(p["ID"]) for p in resultado}

    for jugador_equipo, slots_equipo in piezas_equipadas.items():
        pieza_id_equipada = slots_equipo.get(slot_i)
        if pieza_id_equipada is None:
            continue
        if str(pieza_id_equipada) in ids_ya:
            continue
        pieza = encontrar_pieza_por_id(inventarios, pieza_id_equipada, slot_i)
        if pieza and pieza["Tipo"] == tipo:
            resultado.append(pieza)
            ids_ya.add(str(pieza["ID"]))

    return resultado

def formatear_stat(stat, tipo_mejora):
    if stat == "" or stat is None:
        return ""
    if tipo_mejora == "Porcentaje":
        return f"{stat} %"
    if tipo_mejora == "Plano":
        return f"{stat} +"
    return stat


# ============================================================
# 3. PÁGINA PRINCIPAL
# ============================================================
def main():

    load_all_into_session()

    st.title("📦 Gestionar Inventarios")

    inventarios = st.session_state["inventarios"]
    # ============================================================
    # Compatibilidad: añadir campos Tipo_Mejora si no existen
    # ============================================================
    for slot_i, lista in inventarios.items():
        for p in lista:
            p.setdefault("Tipo_Mejora_Main", "")
            p.setdefault("Tipo_Mejora_Sub1", "")
            p.setdefault("Tipo_Mejora_Sub2", "")
            p.setdefault("Tipo_Mejora_Sub3", "")
            p.setdefault("Tipo_Mejora_Sub4", "")

    stats_recomendados = st.session_state["stats_recomendados"]
    tipos_recomendados = st.session_state["tipos_recomendados"]
    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]

    piezas_equipadas = st.session_state.get("piezas_equipadas", {})
    lista_jugadores_prioridad = st.session_state.get("orden_jugadores", [])

    jugadores_por_tipo = jugadores_que_usan_tipo(tipos_recomendados)

    # ============================================================
    # 0. Puntajes equilibrados globales (para compatibilidad)
    # ============================================================
    puntajes_eq, mejores_jugadores, detalle_por_pieza = calcular_puntajes_equilibrados_globales(
        inventarios, stats_recomendados, jugadores_por_tipo, tipos_recomendados
    )

    st.session_state["puntajes_equilibrados"] = puntajes_eq

    # ============================================================
    # 1. Selector global de inventario (compartido por toda la página)
    # ============================================================
    slot = st.selectbox("📁 Inventario (slot)", ["1", "2", "3", "4", "5", "6"])
    piezas = inventarios.get(slot, [])

    # ============================================================
    # 2. Inventario completo (EXPANDER)
    # ============================================================
    with st.expander("🔎 Inventario completo", expanded=False):

        df_inv = pd.DataFrame(piezas).fillna("")
        # -------------------------
        # Filtro por tipo
        # -------------------------
        tipos_disp = sorted(df_inv["Tipo"].unique())
        tipo_filtro = st.selectbox(
            "Filtrar por tipo:",
            ["Todos"] + tipos_disp,
            index=0
        )
        
        if tipo_filtro != "Todos":
            df_inv = df_inv[df_inv["Tipo"] == tipo_filtro]
   
        # Aplicar formato a cada stat
        df_inv["Main Stat"] = df_inv.apply(
            lambda row: formatear_stat(row["Main Stat"], row.get("Tipo_Mejora_Main", "")),
            axis=1
        )
        df_inv["Substat1"] = df_inv.apply(
            lambda row: formatear_stat(row["Substat1"], row.get("Tipo_Mejora_Sub1", "")),
            axis=1
        )
        df_inv["Substat2"] = df_inv.apply(
            lambda row: formatear_stat(row["Substat2"], row.get("Tipo_Mejora_Sub2", "")),
            axis=1
        )
        df_inv["Substat3"] = df_inv.apply(
            lambda row: formatear_stat(row["Substat3"], row.get("Tipo_Mejora_Sub3", "")),
            axis=1
        )
        df_inv["Substat4"] = df_inv.apply(
            lambda row: formatear_stat(row["Substat4"], row.get("Tipo_Mejora_Sub4", "")),
            axis=1
        )
    
        # Eliminar columnas de tipo de mejora
        df_inv = df_inv.drop(columns=[
            "Tipo_Mejora_Main",
            "Tipo_Mejora_Sub1",
            "Tipo_Mejora_Sub2",
            "Tipo_Mejora_Sub3",
            "Tipo_Mejora_Sub4"
        ], errors="ignore")
    
        st.dataframe(df_inv, use_container_width=True, hide_index=True)

    # ============================================================
    # 3. Editar potencial existente (EXPANDER)
    # ============================================================
    with st.expander("✏️ Editar potencial existente", expanded=False):

        df_edit = pd.DataFrame(piezas).fillna("")
        # -------------------------
        # Filtro por tipo
        # -------------------------
        tipos_disp_edit = sorted(df_edit["Tipo"].unique())
        tipo_filtro_edit = st.selectbox(
            "Filtrar por tipo:",
            ["Todos"] + tipos_disp_edit,
            index=0,
            key="filtro_editar_tipo"
        )

        df_edit_filtrado = df_edit.copy()
        if tipo_filtro_edit != "Todos":
            df_edit_filtrado = df_edit[df_edit["Tipo"] == tipo_filtro_edit]

        if len(df_edit) == 0:
            st.info("No hay piezas en este inventario para editar.")
        else:
            id_editar = st.selectbox(
            "Selecciona la pieza a editar",
            df_edit_filtrado["ID"].tolist(),
            key="selector_editar_pieza"
        )
    
            pieza_sel = df_edit_filtrado[df_edit_filtrado["ID"] == id_editar].iloc[0].to_dict()
    
            # ============================================================
            # Aviso si la pieza está equipada exactamente en este slot
            # ============================================================
            jugador_que_la_tiene = None
            
            for jugador, slots_j in piezas_equipadas.items():
                pieza_id_j = slots_j.get(slot)  # slot actual del inventario
                if pieza_id_j is not None and str(pieza_id_j) == str(id_editar):
                    jugador_que_la_tiene = jugador
                    break
            
            if jugador_que_la_tiene:
                st.warning(
                    f"⚠️ Esta pieza está actualmente equipada por **{jugador_que_la_tiene}**. "
                )
    
            with st.form("form_edit_piece"):
    
                st.write(f"### Editando pieza ID {id_editar}")
    
                calidad_edit = st.selectbox(
                    "Calidad",
                    ["Raro", "Épico", "Legendario"],
                    index=["Raro", "Épico", "Legendario"].index(pieza_sel["Calidad"])
                )
                tipo_edit = st.selectbox("Tipo", tipos, index=tipos.index(pieza_sel["Tipo"]))
    
                # --- MAIN STAT ---
                main_edit = st.selectbox("Main Stat", stats, index=stats.index(pieza_sel["Main Stat"]))
                tipo_mejora_main_edit = pieza_sel.get("Tipo_Mejora_Main", "")
                if main_edit != "":
                    tipo_mejora_main_edit = st.selectbox(
                        "Tipo de mejora (Main Stat)",
                        ["", "Porcentaje", "Plano"],
                        index=["", "Porcentaje", "Plano"].index(tipo_mejora_main_edit)
                        if tipo_mejora_main_edit in ["Porcentaje", "Plano"] else 0
                    )
                else:
                    tipo_mejora_main_edit = ""
    
                # --- SUBSTATS ---
                def editar_substat(nombre, valor_actual, tipo_actual):
                    sub = st.selectbox(nombre, [""] + stats, index=([""] + stats).index(valor_actual))
                    tipo_mejora = tipo_actual
                    if sub != "":
                        tipo_mejora = st.selectbox(
                            f"Tipo de mejora ({nombre})",
                            ["", "Porcentaje", "Plano"],
                            index=["", "Porcentaje", "Plano"].index(tipo_actual)
                            if tipo_actual in ["", "Porcentaje", "Plano"] else 0
                        )
                    else:
                        tipo_mejora = ""
                    return sub, tipo_mejora
    
                sub1_edit, tipo_mejora_sub1_edit = editar_substat("Substat 1", pieza_sel["Substat1"], pieza_sel.get("Tipo_Mejora_Sub1", ""))
                sub2_edit, tipo_mejora_sub2_edit = editar_substat("Substat 2", pieza_sel["Substat2"], pieza_sel.get("Tipo_Mejora_Sub2", ""))
                sub3_edit, tipo_mejora_sub3_edit = editar_substat("Substat 3", pieza_sel["Substat3"], pieza_sel.get("Tipo_Mejora_Sub3", ""))
                sub4_edit, tipo_mejora_sub4_edit = editar_substat("Substat 4", pieza_sel["Substat4"], pieza_sel.get("Tipo_Mejora_Sub4", ""))
    
                submit_edit = st.form_submit_button("Guardar cambios")
    
            if submit_edit:
                errores = []
        
                # Validación MAIN STAT
                if main_edit != "" and tipo_mejora_main_edit == "":
                    errores.append("Debes indicar el tipo de mejora del Main Stat.")
            
                # Validación SUBSTATS
                if sub1_edit != "" and tipo_mejora_sub1_edit == "":
                    errores.append("Debes indicar el tipo de mejora del Substat 1.")
            
                if sub2_edit != "" and tipo_mejora_sub2_edit == "":
                    errores.append("Debes indicar el tipo de mejora del Substat 2.")
            
                if sub3_edit != "" and tipo_mejora_sub3_edit == "":
                    errores.append("Debes indicar el tipo de mejora del Substat 3.")
            
                if sub4_edit != "" and tipo_mejora_sub4_edit == "":
                    errores.append("Debes indicar el tipo de mejora del Substat 4.")
            
                # Si hay errores → no permitir añadir
                if errores:
                    for e in errores:
                        st.error(e)
                
                else:
                    for p in piezas:
                        if p["ID"] == id_editar:
                            p["Tipo"] = tipo_edit
                            p["Calidad"] = calidad_edit
        
                            p["Main Stat"] = main_edit
                            p["Tipo_Mejora_Main"] = tipo_mejora_main_edit
        
                            p["Substat1"] = sub1_edit
                            p["Tipo_Mejora_Sub1"] = tipo_mejora_sub1_edit
        
                            p["Substat2"] = sub2_edit
                            p["Tipo_Mejora_Sub2"] = tipo_mejora_sub2_edit
        
                            p["Substat3"] = sub3_edit
                            p["Tipo_Mejora_Sub3"] = tipo_mejora_sub3_edit
        
                            p["Substat4"] = sub4_edit
                            p["Tipo_Mejora_Sub4"] = tipo_mejora_sub4_edit
                            break
        
                    save_json("inventarios", inventarios)
                    st.success(f"Pieza {id_editar} actualizada correctamente.")
                    st.rerun()

    # ============================================================
    # 4. Añadir nuevo potencial (EXPANDER)
    # ============================================================
    with st.expander("➕ Añadir nuevo potencial", expanded=False):

        with st.form("form_add_piece"):
    
            ids_existentes = [int(p["ID"]) for p in piezas if str(p["ID"]).isdigit()]
            nuevo_id = max(ids_existentes) + 1 if ids_existentes else 1
    
            st.text_input("ID de la pieza (automático)", value=str(nuevo_id), disabled=True, key="id_auto")
    
            calidad = st.selectbox("Calidad", ["Raro", "Épico", "Legendario"])
            tipo = st.selectbox("Tipo", tipos)
    
            # --- MAIN STAT ---
            main_stat = st.selectbox("Main Stat", stats)
            tipo_mejora_main = ""
            if main_stat != "":
                tipo_mejora_main = st.selectbox(
                    "Tipo de mejora (Main Stat)",
                    ["", "Porcentaje", "Plano"]
                )
    
            # --- SUBSTATS ---
            sub1 = st.selectbox("Substat 1", [""] + stats)
            tipo_mejora_sub1 = st.selectbox("Tipo de mejora (Substat 1)", ["", "Porcentaje", "Plano"])
    
            sub2 = st.selectbox("Substat 2", [""] + stats)
            tipo_mejora_sub2 = st.selectbox("Tipo de mejora (Substat 2)", ["", "Porcentaje", "Plano"])
    
            sub3 = st.selectbox("Substat 3", [""] + stats)
            tipo_mejora_sub3 = st.selectbox("Tipo de mejora (Substat 3)", ["", "Porcentaje", "Plano"])
    
            sub4 = st.selectbox("Substat 4", [""] + stats)
            tipo_mejora_sub4 = st.selectbox("Tipo de mejora (Substat 4)", ["", "Porcentaje", "Plano"])
    
            submit_add = st.form_submit_button("Añadir pieza")
    
        if submit_add:

            errores = []
        
            # Validación MAIN STAT
            if main_stat != "" and tipo_mejora_main == "":
                errores.append("Debes indicar el tipo de mejora del Main Stat.")
        
            # Validación SUBSTATS
            if sub1 != "" and tipo_mejora_sub1 == "":
                errores.append("Debes indicar el tipo de mejora del Substat 1.")
        
            if sub2 != "" and tipo_mejora_sub2 == "":
                errores.append("Debes indicar el tipo de mejora del Substat 2.")
        
            if sub3 != "" and tipo_mejora_sub3 == "":
                errores.append("Debes indicar el tipo de mejora del Substat 3.")
        
            if sub4 != "" and tipo_mejora_sub4 == "":
                errores.append("Debes indicar el tipo de mejora del Substat 4.")
        
            # Si hay errores → no permitir añadir
            if errores:
                for e in errores:
                    st.error(e)
               
            else:
                # Si no hay errores → construir la pieza
                pieza_temp = {
                    "ID": str(nuevo_id),
                    "Tipo": tipo,
                    "Calidad": calidad,
            
                    "Main Stat": main_stat,
                    "Tipo_Mejora_Main": tipo_mejora_main,
            
                    "Substat1": sub1,
                    "Tipo_Mejora_Sub1": tipo_mejora_sub1,
            
                    "Substat2": sub2,
                    "Tipo_Mejora_Sub2": tipo_mejora_sub2,
            
                    "Substat3": sub3,
                    "Tipo_Mejora_Sub3": tipo_mejora_sub3,
            
                    "Substat4": sub4,
                    "Tipo_Mejora_Sub4": tipo_mejora_sub4
                }
        
                # --- SIMULACIÓN DE TOP POR JUGADOR (nuevo sistema) ---
                jugadores_que_usan = jugadores_por_tipo.get(tipo, [])
        
                detalle_global = {}
                detalle_por_jugador = {}
                es_desechable_simulado = True
        
                if len(jugadores_que_usan) == 0:
                    detalle_global["motivo"] = (
                        "Actualmente ningún jugador utiliza este tipo. "
                        "La pieza se conservará hasta que exista al menos un jugador que lo use."
                    )
                    detalle_global["jugadores_que_usan"] = []
                else:
                    detalle_global["jugadores_que_usan"] = jugadores_que_usan
                    detalle_global["motivo"] = (
                        "Se ha evaluado si esta pieza entraría en el TOP reservado de cada jugador."
                    )
        
                    piezas_slot = inventarios.get(slot, [])
        
                    for jugador in jugadores_que_usan:
                        stats_rec, puntos_rec = stats_recomendados[jugador]
        
                        candidatas = []
                        for p in piezas_slot:
                            if p["Tipo"] != tipo:
                                continue
                            puntaje_real = puntuar_pieza(p, stats_rec, puntos_rec)
                            candidatas.append((p["ID"], puntaje_real))
        
                        puntaje_nueva = puntuar_pieza(pieza_temp, stats_rec, puntos_rec)
                        candidatas.append((pieza_temp["ID"], puntaje_nueva))
        
                        candidatas.sort(key=lambda x: x[1], reverse=True)
        
                        posiciones_reservadas = 2
                        total = len(candidatas)
        
                        puesto = next((i + 1 for i, (pid, _) in enumerate(candidatas)
                                    if str(pid) == str(pieza_temp["ID"])), None)
        
                        if total >= posiciones_reservadas:
                            peor_en_top = candidatas[posiciones_reservadas - 1][1]
                        else:
                            peor_en_top = None
        
                        entra_en_top = puesto is not None and puesto <= posiciones_reservadas
        
                        if entra_en_top:
                            es_desechable_simulado = False
        
                        detalle_por_jugador[jugador] = {
                            "puesto_pieza": puesto,
                            "total_candidatas": total,
                            "puntaje_pieza": puntaje_nueva,
                            "posiciones_reservadas": posiciones_reservadas,
                            "puntaje_peor_en_top": peor_en_top,
                            "entra_en_top": entra_en_top
                        }
        
                    if es_desechable_simulado:
                        detalle_global["motivo"] += (
                            " La pieza quedaría fuera del TOP reservado de todos los jugadores, "
                            "por lo que, si se mantiene esta configuración, será desechable."
                        )
                    else:
                        detalle_global["motivo"] += (
                            " La pieza entra en el TOP reservado de al menos un jugador, "
                            "por lo que no será desechable mientras se mantenga esa situación."
                        )
        
                st.session_state["pieza_por_confirmar"] = pieza_temp
                st.session_state["confirm_detalle_global"] = detalle_global
                st.session_state["confirm_detalle_por_jugador"] = detalle_por_jugador
                st.session_state["modal_result"] = None
        
                modal_confirmacion(
                    pieza_temp,
                    detalle_global,
                    detalle_por_jugador,
                    slot,
                    inventarios
                )

    # ============================================================
    # 5. Potenciales desechables (EXPANDER)
    # ============================================================
    with st.expander("🗑️ Potenciales desechables", expanded=True):

        desechables = []
        df_piezas_slot = pd.DataFrame(piezas).fillna("")

        for _, pieza in df_piezas_slot.iterrows():
            pieza_dict = pieza.to_dict()
            idp = pieza_dict["ID"]
            tipo_p = pieza_dict["Tipo"]

            # A. Si está equipada → nunca desechable
            if any(str(idp) == str(pid) for slots in piezas_equipadas.values() for pid in slots.values()):
                continue

            # B. Si ningún jugador usa este tipo → no desechable
            jugadores_que_usan = jugadores_por_tipo.get(tipo_p, [])
            if len(jugadores_que_usan) == 0:
                continue

            # C. Puntaje equilibrado global (solo para compatibilidad)
            clave = (slot, idp)
            puntaje_eq = puntajes_eq.get(clave, 0.0)

            # D. Llamar a la lógica unificada de desechables
            es_des, detalle_global, detalle_por_jugador = es_desechable_consistente(
                pieza_id=idp,
                puntaje_eq=puntaje_eq,
                tipo=tipo_p,
                slot=slot,
                inventarios=inventarios,
                jugadores_por_tipo=jugadores_por_tipo,
                stats_recomendados=stats_recomendados,
                puntajes_eq_global=puntajes_eq,
                piezas_equipadas=piezas_equipadas,
                lista_jugadores_prioridad=lista_jugadores_prioridad,
                umbral_minimo_global=15
            )

            if not es_des:
                continue

            motivo = detalle_global.get("motivo", "Fuera del TOP reservado para todos los jugadores que usan este tipo/slot.")

            desechables.append({
                "Seleccionar": False,
                "Slot": slot,
                "ID": idp,
                "Tipo": tipo_p,
                "Calidad": pieza_dict.get("Calidad", ""),
                "Main Stat": pieza_dict.get("Main Stat", ""),
                "Substat1": pieza_dict.get("Substat1", ""),
                "Substat2": pieza_dict.get("Substat2", ""),
                "Substat3": pieza_dict.get("Substat3", ""),
                "Substat4": pieza_dict.get("Substat4", ""),
                "Motivo": motivo
            })

        df_des = pd.DataFrame(desechables)
        
        # ============================================================
        # Formatear stats con su tipo de mejora en la tabla de desechables
        # ============================================================
        
        # Necesitamos acceder al inventario original para recuperar el tipo de mejora
        def obtener_tipo_mejora(pieza_id, inventarios, slot):
            for p in inventarios.get(slot, []):
                if str(p["ID"]) == str(pieza_id):
                    return {
                        "Main": p.get("Tipo_Mejora_Main", ""),
                        "Sub1": p.get("Tipo_Mejora_Sub1", ""),
                        "Sub2": p.get("Tipo_Mejora_Sub2", ""),
                        "Sub3": p.get("Tipo_Mejora_Sub3", ""),
                        "Sub4": p.get("Tipo_Mejora_Sub4", "")
                    }
            return {"Main": "", "Sub1": "", "Sub2": "", "Sub3": "", "Sub4": ""}
        
        # Aplicar formato a cada fila
        for idx, row in df_des.iterrows():
            tipos = obtener_tipo_mejora(row["ID"], inventarios, row["Slot"])
        
            df_des.at[idx, "Main Stat"] = formatear_stat(row["Main Stat"], tipos["Main"])
            df_des.at[idx, "Substat1"] = formatear_stat(row["Substat1"], tipos["Sub1"])
            df_des.at[idx, "Substat2"] = formatear_stat(row["Substat2"], tipos["Sub2"])
            df_des.at[idx, "Substat3"] = formatear_stat(row["Substat3"], tipos["Sub3"])
            df_des.at[idx, "Substat4"] = formatear_stat(row["Substat4"], tipos["Sub4"])
        
        st.session_state["piezas_desechables"] = desechables

        if len(df_des) > 0:

            st.subheader("🔍 Filtros")

            slots_disp = sorted(df_des["Slot"].unique())

            tipos_disp = sorted(df_des["Tipo"].unique())
            tipo_sel = st.multiselect(
                "Mostrar solo tipos:",
                tipos_disp,
                default=tipos_disp
            )

            df_filtrado = df_des[
                df_des["Slot"].isin(slots_disp) &
                df_des["Tipo"].isin(tipo_sel)
            ]

            edited_df = st.data_editor(
                df_filtrado,
                use_container_width=True,
                hide_index=True,
                key="editor_desechables"
            )

            if st.button("Eliminar seleccionados"):
                seleccionados = edited_df[edited_df["Seleccionar"] == True]["ID"].tolist()

                if len(seleccionados) == 0:
                    st.warning("No has seleccionado ninguna pieza para eliminar.")
                else:
                    st.session_state["confirmar_eliminacion_ids"] = seleccionados
                    st.session_state["mostrar_confirmacion_eliminar"] = True
                    st.rerun()

            if st.session_state.get("mostrar_confirmacion_eliminar", False):

                ids_a_eliminar = st.session_state["confirmar_eliminacion_ids"]

                st.error("⚠️ Confirmación necesaria")
                st.write(f"Vas a eliminar **{len(ids_a_eliminar)} piezas** del inventario {slot}.")
                st.write("Esta acción no se puede deshacer.")

                col_c1, col_c2 = st.columns(2)

                with col_c1:
                    if st.button("❌ Cancelar"):
                        st.session_state["mostrar_confirmacion_eliminar"] = False
                        st.session_state["confirmar_eliminacion_ids"] = []
                        st.rerun()

                with col_c2:
                    if st.button("🗑️ Confirmar eliminación"):
                        inventarios[slot] = [
                            p for p in piezas if p["ID"] not in ids_a_eliminar
                        ]
                        save_json("inventarios", inventarios)

                        st.success(f"Eliminadas {len(ids_a_eliminar)} piezas.")
                        st.session_state["mostrar_confirmacion_eliminar"] = False
                        st.session_state["confirmar_eliminacion_ids"] = []
                        st.rerun()

        else:
            st.info("No hay piezas desechables en este inventario.")


if __name__ == "__main__":
    main()
