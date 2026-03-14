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
    mainstat_por_defecto,
    formatear_stat
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

    # --- MAIN STAT ---
    main_valor = pieza.get("Main Stat", "")
    main_tipo = pieza.get("Tipo_Mejora_Main", "")
    main_formateado = formatear_stat(main_valor, main_tipo)
    
    st.write(f"**Main Stat:** {main_formateado}")
    
    # --- SUBSTATS ---
    substats_formateados = []
    for i in range(1, 5):
        valor = pieza.get(f"Substat{i}", "")
        tipo = pieza.get(f"Tipo_Mejora_Sub{i}", "")
        if valor:
            substats_formateados.append(formatear_stat(valor, tipo))
    
    st.write("**Substats:** " + (" / ".join(substats_formateados) if substats_formateados else "—"))


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


# ============================================================
# 3. PÁGINA PRINCIPAL
# ============================================================
def main():

    st.title("📦 Inventario de Potenciales")
    load_all_into_session()

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

    config = st.session_state["config_jugadores"]

    stats_recomendados = {}

    for jugador, datos in config.items():
        stats = datos["stats_recomendados"]["stats"]
        puntos = datos["stats_recomendados"]["puntos"]
    
        # reconstruir diccionario requerido por el optimizador
        puntos_dict = dict(zip(stats, puntos))
    
        stats_recomendados[jugador] = {
            "stats": stats,
            "puntos": puntos_dict
        }

    tipos_recomendados = {
        jugador: config[jugador]["tipos_recomendados"]
        for jugador in config
    }

    tipos = st.session_state["tipos"]
    stats = st.session_state["stats"]

    piezas_equipadas = st.session_state["equipamiento"]
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
    
    # Mantener filtro por tipo entre slots
    if "filtro_tipo_inventario" not in st.session_state:
        st.session_state["filtro_tipo_inventario"] = "Todos"
    
    # Mantener la pieza seleccionada entre renders
    if "pieza_seleccionada" not in st.session_state:
        st.session_state["pieza_seleccionada"] = None
    
    with st.expander("🔎 Inventario completo", expanded=True):
    
        df_inv = pd.DataFrame(piezas).fillna("")
    
        # -------------------------
        # Filtro por tipo
        # -------------------------
        tipos_disp = sorted(df_inv["Tipo"].unique())
            
        tipo_filtro = st.selectbox(
            "Filtrar por tipo:",
            ["Todos"] + tipos_disp,
            index=(["Todos"] + tipos_disp).index(st.session_state["filtro_tipo_inventario"]),
            key="filtro_inventario_completo"
        )
    
        st.session_state["filtro_tipo_inventario"] = tipo_filtro
        
        #Ordenar por calidad->ID
        df_ordenado = df_inv.sort_values(["Calidad", "ID"], ascending=[True, True])
        # Aplicar filtro
        if tipo_filtro == "Todos":
            df_filtrado = df_ordenado.copy()
        else:
            df_filtrado = df_ordenado[df_ordenado["Tipo"] == tipo_filtro].copy()

        # -------------------------
        # Columna Editar (checkbox)
        # -------------------------
        df_filtrado.insert(0, "Editar", False)
    
        # Estado inicial de la columna según la pieza seleccionada
        if st.session_state["pieza_seleccionada"] is not None:
            df_filtrado["Editar"] = df_filtrado["ID"].astype(str) == str(
                st.session_state["pieza_seleccionada"]
            )
        
        # -------------------------
        # Formatear stats
        # -------------------------
        df_filtrado["Main Stat"] = df_filtrado.apply(
            lambda row: formatear_stat(row["Main Stat"], row.get("Tipo_Mejora_Main", "")),
            axis=1
        )
        df_filtrado["Substat1"] = df_filtrado.apply(
            lambda row: formatear_stat(row["Substat1"], row.get("Tipo_Mejora_Sub1", "")),
            axis=1
        )
        df_filtrado["Substat2"] = df_filtrado.apply(
            lambda row: formatear_stat(row["Substat2"], row.get("Tipo_Mejora_Sub2", "")),
            axis=1
        )
        df_filtrado["Substat3"] = df_filtrado.apply(
            lambda row: formatear_stat(row["Substat3"], row.get("Tipo_Mejora_Sub3", "")),
            axis=1
        )
        df_filtrado["Substat4"] = df_filtrado.apply(
            lambda row: formatear_stat(row["Substat4"], row.get("Tipo_Mejora_Sub4", "")),
            axis=1
        )
    
        # -------------------------
        # Ocultar columnas internas
        # -------------------------
        df_filtrado = df_filtrado.drop(columns=[
            "Tipo_Mejora_Main",
            "Tipo_Mejora_Sub1",
            "Tipo_Mejora_Sub2",
            "Tipo_Mejora_Sub3",
            "Tipo_Mejora_Sub4"
        ], errors="ignore")
    
        # -------------------------
        # Editor interactivo
        # -------------------------
        df_editable = st.data_editor(
            df_filtrado,
            hide_index=True,
            use_container_width=True,
            key="editor_inventario_completo",
            column_config={
                "Editar": st.column_config.CheckboxColumn("Editar", help="Editar esta pieza"),
            }
        )
    
        # -------------------------
        # Detectar selección nueva (forzar selección única)
        # -------------------------
        seleccionadas = df_editable[df_editable["Editar"] == True]
    
        if len(seleccionadas) >= 1:
            # Si hay varias marcadas, nos quedamos con la última (fila más baja)
            nueva = seleccionadas.iloc[-1]["ID"]
            if str(nueva) != str(st.session_state["pieza_seleccionada"]):
                st.session_state["pieza_seleccionada"] = str(nueva)
                st.rerun()
    
        elif len(seleccionadas) == 0 and st.session_state["pieza_seleccionada"] is not None:
            # Se ha desmarcado todo
            st.session_state["pieza_seleccionada"] = None
            st.rerun()
    
    
    # ============================================================
    # FORMULARIO DE EDICIÓN DIRECTO DESDE LA TABLA
    # ============================================================
    
    pieza_id_a_editar = st.session_state.get("pieza_seleccionada", None)
    
    if pieza_id_a_editar:
    
        # Buscar la pieza en el inventario actual (slot)
        pieza_sel = next(
            p for p in piezas
            if str(p["ID"]) == str(pieza_id_a_editar)
        )
    
        # Aviso si está equipada exactamente en este slot
        jugador_que_la_tiene = None
        for jugador, slots_j in piezas_equipadas.items():
            pieza_id_j = slots_j.get(slot)
            if pieza_id_j is not None and str(pieza_id_j) == str(pieza_id_a_editar):
                jugador_que_la_tiene = jugador
                break
    
        if jugador_que_la_tiene:
            st.warning(
                f"⚠️ Esta pieza está actualmente equipada por **{jugador_que_la_tiene}**."
            )
    
        st.markdown("### ✏️ Editar pieza seleccionada")

        with st.form("form_edit_piece"):
    
            # --- CALIDAD ---
            calidad_actual = pieza_sel.get("Calidad", "Raro") or "Raro"
            opciones_calidad = ["Raro", "Épico", "Legendario"]
            idx_calidad = opciones_calidad.index(calidad_actual) if calidad_actual in opciones_calidad else 0
    
            calidad_edit = st.selectbox(
                "Calidad",
                opciones_calidad,
                index=idx_calidad
            )
    
            # --- TIPO ---
            tipo_actual = pieza_sel.get("Tipo", tipos[0]) or tipos[0]
            idx_tipo = tipos.index(tipo_actual) if tipo_actual in tipos else 0
    
            tipo_edit = st.selectbox(
                "Tipo",
                tipos,
                index=idx_tipo
            )
            
            opciones_tipo_mejora = ["", "Porcentaje", "Plano"]
            
            # --- MAIN STAT ---
            main_actual = pieza_sel.get("Main Stat", "") or ""
            idx_main = stats.index(main_actual) if main_actual in stats else 0
            
            main_edit = st.selectbox(
                "Main Stat",
                stats,
                index=idx_main
            )
    
            tipo_mejora_main_edit = pieza_sel.get("Tipo_Mejora_Main", "") or ""
            mainstat_default, tm_main_default = mainstat_por_defecto(slot, tipo_edit)
            
            if tipo_mejora_main_edit != tm_main_default:
                tipo_mejora_main_edit = tm_main_default
            
            if main_edit != "":
                st.text_input("Tipo de mejora (Main Stat)", value=str(tipo_mejora_main_edit), disabled=True, key="idx_tm_main")
            else:
                tipo_mejora_main_edit = ""
    
            # --- SUBSTATS ---
            def editar_substat(nombre, valor_actual, tipo_actual):
                valor_actual = valor_actual or ""
                tipo_actual = tipo_actual or ""
    
                opciones_stats = [""] + stats
                idx_stat = opciones_stats.index(valor_actual) if valor_actual in opciones_stats else 0
    
                sub = st.selectbox(
                    nombre,
                    opciones_stats,
                    index=idx_stat
                )
    
                if sub != "":
                    #opciones_tipo_mejora = ["", "Porcentaje", "Plano"]
                    idx_tm = opciones_tipo_mejora.index(tipo_actual) if tipo_actual in opciones_tipo_mejora else 0
                    tipo_mejora = st.selectbox(
                        f"Tipo de mejora ({nombre})",
                        opciones_tipo_mejora,
                        index=idx_tm
                    )
                else:
                    tipo_mejora = ""
    
                return sub, tipo_mejora
    
            sub1_edit, tipo_mejora_sub1_edit = editar_substat(
                "Substat 1",
                pieza_sel.get("Substat1", ""),
                pieza_sel.get("Tipo_Mejora_Sub1", "")
            )
            sub2_edit, tipo_mejora_sub2_edit = editar_substat(
                "Substat 2",
                pieza_sel.get("Substat2", ""),
                pieza_sel.get("Tipo_Mejora_Sub2", "")
            )
            sub3_edit, tipo_mejora_sub3_edit = editar_substat(
                "Substat 3",
                pieza_sel.get("Substat3", ""),
                pieza_sel.get("Tipo_Mejora_Sub3", "")
            )
            sub4_edit, tipo_mejora_sub4_edit = editar_substat(
                "Substat 4",
                pieza_sel.get("Substat4", ""),
                pieza_sel.get("Tipo_Mejora_Sub4", "")
            )
    
            col_g, col_b, col_c = st.columns(3)
            with col_g:
                guardar = st.form_submit_button("💾 Guardar cambios")
            with col_b:
                borrar = st.form_submit_button("🗑️ Borrar pieza")
            with col_c:
                cancelar = st.form_submit_button("❌ Cancelar edición")
    
        # -------------------------
        # LÓGICA DE LOS BOTONES
        # -------------------------
    
        if guardar:
    
            errores = []
            if main_edit != "" and tipo_mejora_main_edit == "":
                errores.append("Debes indicar el tipo de mejora del Main Stat.")
            if sub1_edit != "" and tipo_mejora_sub1_edit == "":
                errores.append("Debes indicar el tipo de mejora del Substat 1.")
            if sub2_edit != "" and tipo_mejora_sub2_edit == "":
                errores.append("Debes indicar el tipo de mejora del Substat 2.")
            if sub3_edit != "" and tipo_mejora_sub3_edit == "":
                errores.append("Debes indicar el tipo de mejora del Substat 3.")
            if sub4_edit != "" and tipo_mejora_sub4_edit == "":
                errores.append("Debes indicar el tipo de mejora del Substat 4.")
    
            if errores:
                for e in errores:
                    st.error(e)
            else:
                for p in piezas:
                    if str(p["ID"]) == str(pieza_id_a_editar):
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
                st.success(f"Pieza {pieza_id_a_editar} actualizada correctamente.")
                st.rerun()
    
        elif borrar:
            inventarios[slot] = [
                p for p in piezas if str(p["ID"]) != str(pieza_id_a_editar)
            ]
            save_json("inventarios", inventarios)
            st.session_state["pieza_seleccionada"] = None
            st.success(f"Pieza {pieza_id_a_editar} eliminada del inventario.")
            st.rerun()
    
        elif cancelar:
            st.session_state["pieza_seleccionada"] = None
            st.info("Edición cancelada.")
            st.rerun()

    # ============================================================
    # 4. Añadir nuevo potencial (EXPANDER)
    # ============================================================
    with st.expander("➕ Añadir nuevo potencial", expanded=False):

        # Detectar cambio de tipo para resetear el main
        tipo_key = "tipo_add_piece"
        tipo_actual = st.session_state.get(tipo_key, "")

        # Selector de tipo FUERA del form para que dispare el rerun
        tipo = st.selectbox("Tipo", [""] + tipos, key=tipo_key)
        
        # Si el tipo ha cambiado, reseteamos el main
        if tipo != tipo_actual and "id_main" in st.session_state:
            del st.session_state["id_main"]

        with st.form("form_add_piece", clear_on_submit=True):
    
            ids_existentes = [int(p["ID"]) for p in piezas if str(p["ID"]).isdigit()]
            nuevo_id = max(ids_existentes) + 1 if ids_existentes else 1
    
            st.text_input("ID de la pieza (automático)", value=str(nuevo_id), disabled=True, key="id_auto")
    
            calidad = st.selectbox("Calidad", ["","Raro", "Épico", "Legendario"])
            #tipo = st.selectbox("Tipo", [""] + tipos)
            
            mainstat_default, tm_main_default = mainstat_por_defecto(slot, tipo)
            col1, col2 = st.columns(2)
            with col1:
                if int(slot) in (1, 3, 5):
                    main_stat = st.selectbox(
                        "Main Stat",
                        [""] + stats,
                        index=([""] + stats).index(mainstat_default) if mainstat_default in stats else 0,
                        disabled=True,
                        key="id_main",
                    )
                else:
                    main_stat = st.selectbox(
                        "Main Stat",
                        [""] + mainstat_default,
                        key="id_main",
                    )
                sub1 = st.selectbox("Substat 1", [""] + stats, key="f_sub1")
                sub2 = st.selectbox("Substat 2", [""] + stats, key="f_sub2")
                sub3 = st.selectbox("Substat 3", [""] + stats, key="f_sub3")
                sub4 = st.selectbox("Substat 4", [""] + stats, key="f_sub4")
            with col2:
                tipo_mejora_main = st.text_input("Tipo de mejora (Main Stat)", value=str(tm_main_default), disabled=True, key="id_tm_main")
                tipo_mejora_sub1 = st.selectbox("Tipo de mejora (Substat 1)", ["", "Porcentaje", "Plano"], key="f_tm_sub1")
                tipo_mejora_sub2 = st.selectbox("Tipo de mejora (Substat 2)", ["", "Porcentaje", "Plano"], key="f_tm_sub2")
                tipo_mejora_sub3 = st.selectbox("Tipo de mejora (Substat 3)", ["", "Porcentaje", "Plano"], key="f_tm_sub3")
                tipo_mejora_sub4 = st.selectbox("Tipo de mejora (Substat 4)", ["", "Porcentaje", "Plano"], key="f_tm_sub4")
    
            submit_add = st.form_submit_button("Añadir pieza")
    
        if submit_add:

            errores = []
            
            if calidad == "":
                errores.append("Debes indicar la calidad del Potencial.")
                
            if tipo == "":
                 errores.append("Debes indicar el tipo del Potencial.")
                 
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
                        stats_rec = stats_recomendados[jugador]["stats"]
                        puntos_rec = stats_recomendados[jugador]["puntos"]


        
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
                # 4.1 Procesar resultado del modal (confirmar / cancelar)
                # ============================================================
                modal_result = st.session_state.get("modal_result", None)
                
                if modal_result == "confirmar":
                    # 🔥 Limpiar formulario SOLO si se confirmó
                    for key in [
                        "id_auto",
                        "id_tm_main",
                        "f_sub1", "f_tm_sub1",
                        "f_sub2", "f_tm_sub2",
                        "f_sub3", "f_tm_sub3",
                        "f_sub4", "f_tm_sub4",
                    ]:
                        if key in st.session_state:
                            del st.session_state[key]
                
                    # Resetear estado del modal
                    st.session_state["modal_result"] = None
                    st.rerun()
                
                elif modal_result == "cancelar":
                    # No limpiar nada
                    st.session_state["modal_result"] = None
                

    # ============================================================
    # 5. Potenciales desechables (EXPANDER)
    # ============================================================
    with st.expander("🗑️ Potenciales desechables", expanded=False):

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
