from os import error
import streamlit as st
import pandas as pd

from optimizer import (
    puntuar_pieza,
    jugadores_que_usan_tipo,
    puntajes_por_jugador_para_pieza,
    mainstat_por_defecto,
    formatear_stat,
    calcular_reservas_por_jugador,      
    clasificar_potencial
)


from data_manager import load_all_into_session, inventory_service, get_current_user_id
from config import GameConfig


def get_available_substats(idx, all_stats, used_stats=None):
    if used_stats is None:
        return sorted(list(set([""] + all_stats)), key=lambda x: (x != "", x))
    
    stats_used_by_others = {}
    for stat_dict in used_stats:
        for other_idx, stat_info in stat_dict.items():
            if other_idx != idx and stat_info:
                stat_value = stat_info[0]
                stats_used_by_others[stat_value] = stats_used_by_others.get(stat_value, 0) + 1
    
    available = [""]
    for stat in all_stats:
        if stat in GameConfig.STATS_SOLO_UNA_VEZ:
            if stat not in stats_used_by_others:
                available.append(stat)
        else:
            if stats_used_by_others.get(stat, 0) < 2:
                available.append(stat)
    
    return sorted(list(set(available)), key=lambda x: (x != "", x))

def get_available_tm(idx,stat, used_stats=None):
    if not stat:
        return []
    
    if stat in GameConfig.STATS_SOLO_UNA_VEZ:
        return ["Porcentaje"]
    
    if used_stats is None:
        return ["Porcentaje", "Plano"]
    
    used_tm_for_stat = []
    for stat_dict in used_stats:
        for other_idx, stat_info in stat_dict.items():
            if other_idx != idx and stat_info and stat_info[0] == stat:
                used_tm_for_stat.append(stat_info[1])
    
    available = []
    if used_tm_for_stat.count("Porcentaje") == 0:
        available.append("Porcentaje")
    if used_tm_for_stat.count("Plano") == 0:
        available.append("Plano")
    
    return available





# ============================================================
# 1. MODAL OFICIAL (VERSIÓN REFACTORIZADA Y COMPACTA)
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
        tipo_mej = pieza.get(f"Tipo_Mejora_Sub{i}", "")
        if valor:
            substats_formateados.append(formatear_stat(valor, tipo_mej))

    st.write("**Substats:** " + (" / ".join(substats_formateados) if substats_formateados else "—"))

    # ============================================================
    # 🧠 EVALUACIÓN DEL POTENCIAL (SECCIÓN PRINCIPAL)
    # ============================================================
    st.markdown("## 🧠 Evaluación del Potencial")

    estado = detalle_global.get("estado")
    motivo = detalle_global.get("motivo", "")

    # Mensaje principal según estado
    if estado == "mejora":
        st.success("✅ Esta pieza mejora al menos un potencial reservado.")
    if estado == "potencial":
        st.success("✅ Esta pieza tiene potencial para ser mejor que la actual.")
    elif estado == "warning":
        st.warning("⚠️ Pieza de buena calidad, pero no mejora los potenciales reservados.")
    elif estado == "rellena_hueco":
        st.info("🧩 Esta pieza cubre una necesidad en el inventario (faltan piezas para algún jugador).")
    elif estado == "desechable":
        st.error("🗑️ Esta pieza es considerada desechable según las reservas actuales.")
    elif estado == "sin_uso":
        st.warning("🚫 Ningún jugador usa potenciales de este tipo.")

    # ============================================================
    # 🧩 DETALLE (solo si la pieza es útil para alguien)
    # ============================================================
    jugadores_beneficiados = []

    if detalle_por_jugador:
        for jugador, info in detalle_por_jugador.items():
            # Jugadores que se benefician:
            # - supera su reservada
            # - o no tienen reservada y esta pieza cubre hueco
            if info.get("supera") or info.get("rellena_hueco") or info.get("potencial"):
                jugadores_beneficiados.append(jugador)

    if jugadores_beneficiados:
        st.markdown("### 📌 Detalle")
        lista = ", ".join(jugadores_beneficiados)
        st.write(f"El potencial será útil para los siguientes jugadores: **{lista}**")

    # ============================================================
    # BOTONES
    # ============================================================
    col1, col2, col3 = st.columns(3)

    uid = get_current_user_id()

    with col1:
        if st.button("Insertar"):
            inventory_service.add_piece(slot, pieza, uid)
            st.session_state["modal_result"] = "confirmar"
            st.rerun()

    with col2:
        if st.button("Modificar"):
            st.session_state["modal_result"] = "modificar"
            st.session_state["restore_form"] = True
            st.rerun()
            
    with col3:
        if st.button("Desechar"):
            st.session_state["modal_result"] = "desechar"
            st.rerun()


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
    calidades = ["", "Épico", "Legendario"]
    
    reservas_activas = inventory_service.get_active_reservations(
        inventarios, config, st.session_state
    )

    st.session_state["reservas_activas"] = reservas_activas
    
    piezas_equipadas = st.session_state["equipamiento"]
    lista_jugadores_prioridad = st.session_state.get("orden_jugadores", [])

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
    
        df_inv = inventory_service.prepare_inventory_dataframe(
            piezas, 
            slot=slot, 
            equipamiento=piezas_equipadas,
            reservations=reservas_activas,
            config=config,
            inventarios=inventarios
        )
    
        # -------------------------
        # Filtro por tipo
        # -------------------------
        if df_inv.empty:
            st.info("No hay piezas en este inventario.")
            tipos_disp = []
        else:
            tipos_disp = sorted(df_inv["Tipo"].unique())
            
        tipo_filtro = st.selectbox(
            "Filtrar por tipo:",
            ["Todos"] + tipos_disp,
            index=(["Todos"] + tipos_disp).index(st.session_state["filtro_tipo_inventario"]),
            key="filtro_inventario_completo"
        )
    
        st.session_state["filtro_tipo_inventario"] = tipo_filtro
        
        #Ordenar por calidad->ID
        if not df_inv.empty:
            # Asegurar ID numérico para sort correcto
            df_inv["ID"] = pd.to_numeric(df_inv["ID"], errors='coerce')
            df_ordenado = df_inv.sort_values(["Calidad", "ID"], ascending=[True, True])
            
            # Convertir ID a string para evitar formato numérico (comas) en el editor y para comparaciones uniformes
            df_ordenado["ID"] = df_ordenado["ID"].astype(str).replace(r'\.0$', '', regex=True)
        else:
            df_ordenado = df_inv.copy()
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
        # Editor interactivo
        # -------------------------
        column_config = {
            "Editar": st.column_config.CheckboxColumn("Editar", help="Editar esta pieza"),
        }
        
        if "Equipado" in df_filtrado.columns:
            column_config["Equipado"] = st.column_config.TextColumn("Equipado", help="Jugador que tiene esta pieza equipada")
        
        if "Evaluación" in df_filtrado.columns:
            column_config["Evaluación"] = st.column_config.TextColumn("Evaluación", help="Calidad del jugador con la pieza o del jugador con más puntaje")
        
        if "Potencial" in df_filtrado.columns:
            column_config["Potencial"] = st.column_config.TextColumn("Potencial", help="Calidad simulada si es Bueno/Excelente/Perfecto")
        
        df_editable = st.data_editor(
            df_filtrado,
            hide_index=True,
            use_container_width=True,
            key="editor_inventario_completo",
            column_config=column_config
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

        # Container instead of form to allow interactive selectboxes
        edit_container = st.container()
        with edit_container:
    
            # Fila 1: ID y Tipo
            st.text_input("ID de la pieza", value=str(pieza_id_a_editar), disabled=True)
            tipo_actual = pieza_sel.get("Tipo", tipos[0]) or tipos[0]
            idx_tipo = tipos.index(tipo_actual) if tipo_actual in tipos else 0
            tipo_edit = st.selectbox("Tipo", tipos, index=idx_tipo, key="tipo_edit_piece")

            # Fila 2: Calidad
            calidad_actual = pieza_sel.get("Calidad", calidades[0]) or calidades[0]
            idx_calidad = calidades.index(calidad_actual) if calidad_actual in calidades else 0
            calidad_edit = st.selectbox("Calidad", calidades, index=idx_calidad, key="calidad_edit_piece")
             

            # Fila 3: Main Stat y su Tipo de Mejora
            r3c1, r3c2 = st.columns(2)
            with r3c1:
                main_actual = pieza_sel.get("Main Stat", "") or ""
                idx_main = stats.index(main_actual) if main_actual in stats else 0
                main_edit = st.selectbox("Main Stat", stats, index=idx_main, key="main_edit_piece")
            with r3c2:
                tipo_mejora_main_edit = pieza_sel.get("Tipo_Mejora_Main", "") or ""
                mainstat_default, tm_main_default = mainstat_por_defecto(slot, tipo_edit)
                if tipo_mejora_main_edit != tm_main_default:
                    tipo_mejora_main_edit = tm_main_default
                
                if main_edit != "":
                    st.text_input("Tipo de mejora (Main Stat)", value=str(tipo_mejora_main_edit), disabled=True, key="idx_tm_main_edit")
                else:
                    tipo_mejora_main_edit = ""

            used_stats = []
            # --- SUBSTATS ---
            def row_substat_edit(nombre, valor_actual, tipo_actual, idx_num, pieza_id, used_stats):
                current_val = st.session_state.get(f"edit_stat_{nombre}_{pieza_id}", valor_actual)
                
                c1, c2 = st.columns(2)
                with c1:
                    opts = get_available_substats(idx_num,stats, used_stats)
                    idx_stat = opts.index(current_val) if current_val in opts else 0
                    sub = st.selectbox(nombre, opts, index=idx_stat, key=f"edit_stat_{nombre}_{pieza_id}")
                with c2:
                    opciones_tm = get_available_tm(idx_num, sub, used_stats)
                    curr_tm = st.session_state.get(f"edit_tm_{nombre}_{pieza_id}", tipo_actual)
                    
                    if len(opciones_tm) == 1:
                        if curr_tm != opciones_tm[0]:
                            st.session_state[f"edit_tm_{nombre}_{pieza_id}"] = opciones_tm[0]
                        tm_sel = st.selectbox(f"Tipo de mejora {nombre}", opciones_tm, index=0, disabled=True, key=f"edit_tm_{nombre}_{pieza_id}")
                    else:
                        if curr_tm not in opciones_tm and curr_tm != "":
                            st.session_state[f"edit_tm_{nombre}_{pieza_id}"] = ""
                        tm_sel = st.selectbox(f"Tipo de mejora {nombre}", [""] + opciones_tm, key=f"edit_tm_{nombre}_{pieza_id}")
                  
                if idx_num not in used_stats and sub != "":
                    used_stats.append({idx_num: [sub, tm_sel]})
                else:
                    for stat_dict in used_stats:
                        if idx_num in stat_dict:
                            stat_dict[idx_num] = [sub, tm_sel]
                            break
                return sub, tm_sel, used_stats

            sub1_edit, tipo_mejora_sub1_edit, used_stats = row_substat_edit("Substat 1", pieza_sel.get("Substat1", ""), pieza_sel.get("Tipo_Mejora_Sub1", ""), 1, pieza_id_a_editar, used_stats)
            sub2_edit, tipo_mejora_sub2_edit, used_stats = row_substat_edit("Substat 2", pieza_sel.get("Substat2", ""), pieza_sel.get("Tipo_Mejora_Sub2", ""), 2, pieza_id_a_editar, used_stats)
            sub3_edit, tipo_mejora_sub3_edit, used_stats = row_substat_edit("Substat 3", pieza_sel.get("Substat3", ""), pieza_sel.get("Tipo_Mejora_Sub3", ""), 3, pieza_id_a_editar, used_stats)
            sub4_edit, tipo_mejora_sub4_edit, used_stats = row_substat_edit("Substat 4", pieza_sel.get("Substat4", ""), pieza_sel.get("Tipo_Mejora_Sub4", ""), 4, pieza_id_a_editar, used_stats)
    
            col_g, col_b, col_c = st.columns(3)
            with col_g:
                guardar = st.button("💾 Guardar cambios")
            with col_b:
                borrar = st.button("🗑️ Borrar pieza")
            with col_c:
                cancelar = st.button("❌ Cancelar edición")
    
        # -------------------------
        # LÓGICA DE LOS BOTONES
        # -------------------------
        uid = get_current_user_id()

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
            substats_edit = [s for s in [sub1_edit, sub2_edit, sub3_edit, sub4_edit] if s]
            
            for s in set(substats_edit):
                if s in GameConfig.STATS_SOLO_UNA_VEZ and substats_edit.count(s) > 1:
                    errores.append(f"El substat {s} no puede repetirse.")
                elif s not in GameConfig.STATS_SOLO_UNA_VEZ and substats_edit.count(s) > 2:
                    errores.append(f"El substat {s} no puede repetirse más de 2 veces.")
            
            # Verificar inconsistencias de tipo de mejora en substats repetidos
            substats_dict = {}
            for i, s in enumerate([sub1_edit, sub2_edit, sub3_edit, sub4_edit]):
                if s:
                    if s not in substats_dict:
                        substats_dict[s] = []
                    substats_dict[s].append(i)
            for s, indices in substats_dict.items():
                if len(indices) > 1:
                    tm_list = [tipo_mejora_sub1_edit if indices[0] == 0 else tipo_mejora_sub2_edit if indices[0] == 1 else tipo_mejora_sub3_edit if indices[0] == 2 else tipo_mejora_sub4_edit]
                    tm_list.extend([tipo_mejora_sub1_edit if i == 0 else tipo_mejora_sub2_edit if i == 1 else tipo_mejora_sub3_edit if i == 2 else tipo_mejora_sub4_edit for i in indices[1:]])
                    tipos_mejora = set(tm_list)
                    if len(tipos_mejora) == 1 and s not in GameConfig.STATS_SOLO_UNA_VEZ:
                        errores.append(f"El substat {s} no puede tener 2 veces el mismo tipo de mejora.")
    
            if errores:
                for e in errores:
                    st.error(e)
            else:
                updated_data = {
                    "Tipo": tipo_edit,
                    "Calidad": calidad_edit,
                    "Main Stat": main_edit,
                    "Tipo_Mejora_Main": tipo_mejora_main_edit,
                    "Substat1": sub1_edit,
                    "Tipo_Mejora_Sub1": tipo_mejora_sub1_edit,
                    "Substat2": sub2_edit,
                    "Tipo_Mejora_Sub2": tipo_mejora_sub2_edit,
                    "Substat3": sub3_edit,
                    "Tipo_Mejora_Sub3": tipo_mejora_sub3_edit,
                    "Substat4": sub4_edit,
                    "Tipo_Mejora_Sub4": tipo_mejora_sub4_edit
                }
                inventory_service.update_piece(slot, pieza_id_a_editar, updated_data, uid)
                st.success(f"Pieza {pieza_id_a_editar} actualizada correctamente.")
                st.rerun()
    
        elif borrar:
            inventory_service.delete_piece(slot, pieza_id_a_editar, uid)
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
    if "add_expander_open" not in st.session_state:
        st.session_state["add_expander_open"] = False

    # --- GESTIÓN DE ACCIONES TRAS MODAL (SOLID: fuera del expander para mayor estabilidad) ---
    modal_result = st.session_state.get("modal_result")
    if modal_result in ["confirmar", "desechar"]:
        # Resetear valores de forma explícita (más fiable que del)
        st.session_state["add_tipo"] = ""
        st.session_state["add_calidad"] = ""
        st.session_state["add_main"] = ""
        for i in range(1, 5):
            st.session_state[f"add_sub{i}"] = ""
            st.session_state[f"add_tm{i}"] = ""
        
        if "form_backup" in st.session_state:
            del st.session_state["form_backup"]
        
        # Feedback
        if modal_result == "confirmar":
            st.toast("✅ Pieza insertada correctamente", icon="📥")
        else:
            st.toast("ℹ️ Pieza desechada", icon="🗑️")

        st.session_state["modal_result"] = None
        st.session_state["add_expander_open"] = True 
        st.rerun()

    elif modal_result == "modificar":
        st.session_state["restore_form"] = True
        st.session_state["modal_result"] = None
        st.session_state["add_expander_open"] = True
        st.rerun()

    with st.expander("➕ Añadir nuevo potencial", expanded=st.session_state["add_expander_open"]):

        # --- RESTAURACIÓN ---
        if st.session_state.get("restore_form"):
            backup = st.session_state.get("form_backup", {})
            if backup:
                st.session_state["add_tipo"] = backup.get("tipo", "")
                st.session_state["add_calidad"] = backup.get("calidad", "")
                st.session_state["add_main"] = backup.get("main", "")
                for i in range(1, 5):
                    st.session_state[f"add_sub{i}"] = backup.get(f"sub{i}", "")
                    st.session_state[f"add_tm{i}"] = backup.get(f"tm_sub{i}", "")
            st.session_state["restore_form"] = False

        # --- FORMULARIO ---
        tipo = st.selectbox("Tipo", [""] + tipos, key="add_tipo")
        
        ids_existentes = [int(p["ID"]) for p in piezas if str(p["ID"]).isdigit()]
        nuevo_id = max(ids_existentes) + 1 if ids_existentes else 1
        st.text_input("ID de la pieza (automático)", value=str(nuevo_id), disabled=True)

        calidad = st.selectbox("Calidad", ["","Épico", "Legendario"], key="add_calidad") 

        mainstat_default, tm_main_default = mainstat_por_defecto(slot, tipo)
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            if int(slot) in (1, 3, 5):
                st.session_state["add_main"] = mainstat_default
                main_stat = st.selectbox("Main Stat", [""] + stats, disabled=True, key="add_main")
            else:
                main_stat = st.selectbox("Main Stat", [""] + mainstat_default, key="add_main")
        with r1c2:
            st.text_input("Tipo de mejora (Main Stat)", value=str(tm_main_default), disabled=True)
            tipo_mejora_main = tm_main_default

        used_stats = []
        
        # Substats
        def sub_field(idx,used_stats):
            c1, c2 = st.columns(2)
            with c1:
                s = st.selectbox(
                    f"Substat {idx}", 
                    get_available_substats(idx, stats, used_stats), 
                    key=f"add_sub{idx}"
                )

            with c2:
                tm_opts = get_available_tm(idx, s, used_stats)
                
                curr_tm = st.session_state.get(f"add_tm{idx}", "")
                if len(tm_opts) == 1:
                    if curr_tm != tm_opts[0]:
                        st.session_state[f"add_tm{idx}"] = tm_opts[0]
                    tm = st.selectbox("Tipo de mejora", tm_opts, index=0, disabled=True, key=f"add_tm{idx}")
                else:
                    if curr_tm not in tm_opts and curr_tm != "":
                        st.session_state[f"add_tm{idx}"] = ""
                    tm = st.selectbox(
                        f"Tipo de mejora Substat {idx}", 
                        [""] + tm_opts, 
                        key=f"add_tm{idx}"
                    )
            if idx not in used_stats and s:
                used_stats.append({idx: [s, tm]})
            else:
                for stat_dict in used_stats:
                    if idx in stat_dict:
                        stat_dict[idx] = [s, tm]
                        break
            return s, tm, used_stats

        sub1, tm1, used_stats = sub_field(1, used_stats)
        sub2, tm2, used_stats = sub_field(2, used_stats)
        sub3, tm3, used_stats = sub_field(3, used_stats)
        sub4, tm4, used_stats = sub_field(4, used_stats)

        if st.button("Añadir pieza"):
            st.session_state["add_expander_open"] = True
            st.session_state["form_backup"] = {
                "tipo": tipo, "calidad": calidad, "main": main_stat,
                "sub1": sub1, "tm_sub1": tm1, "sub2": sub2, "tm_sub2": tm2,
                "sub3": sub3, "tm_sub3": tm3, "sub4": sub4, "tm_sub4": tm4
            }
            errores = []
            if not tipo: errores.append("Falta Tipo")
            if not calidad: errores.append("Falta Calidad")
            if main_stat == "" and int(slot) not in (1, 3, 5): errores.append("Falta Main Stat")
            if sub1 and not tm1: errores.append("Falta Tipo de mejora para Substat 1")
            if sub2 and not tm2: errores.append("Falta Tipo de mejora para Substat 2")
            if sub3 and not tm3: errores.append("Falta Tipo de mejora para Substat 3")
            if sub4 and not tm4: errores.append("Falta Tipo de mejora para Substat 4")
            substats = [s for s in [sub1, sub2, sub3, sub4] if s]

            for s in set(substats):
                if s in GameConfig.STATS_SOLO_UNA_VEZ and substats.count(s) > 1:
                    errores.append(f"El substat {s} no puede repetirse.")
                elif s not in GameConfig.STATS_SOLO_UNA_VEZ and substats.count(s) > 2:
                    errores.append(f"El substat {s} no puede repetirse más de 2 veces.")
            
            # Verificar inconsistencias de tipo de mejora en substats repetidos
            substats_dict = {}
            for i, s in enumerate([sub1, sub2, sub3, sub4]):
                if s:
                    if s not in substats_dict:
                        substats_dict[s] = []
                    substats_dict[s].append(i)
            for s, indices in substats_dict.items():
                if len(indices) > 1:
                    tm_list = [tm1 if indices[0] == 0 else tm2 if indices[0] == 1 else tm3 if indices[0] == 2 else tm4]
                    tm_list.extend([tm1 if i == 0 else tm2 if i == 1 else tm3 if i == 2 else tm4 for i in indices[1:]])
                    tipos_mejora = set(tm_list)
                    if len(tipos_mejora) == 1:
                        errores.append(f"El substat {s} no puede tener 2 veces el mismo tipo de mejora.")

            
            if errores:
                for e in errores: st.error(e)
            else:
                pieza_temp = {
                    "ID": str(nuevo_id), "Tipo": tipo, "Calidad": calidad,
                    "Main Stat": main_stat, "Tipo_Mejora_Main": tipo_mejora_main,
                    "Substat1": sub1, "Tipo_Mejora_Sub1": tm1,
                    "Substat2": sub2, "Tipo_Mejora_Sub2": tm2,
                    "Substat3": sub3, "Tipo_Mejora_Sub3": tm3,
                    "Substat4": sub4, "Tipo_Mejora_Sub4": tm4
                }
                resultado = clasificar_potencial(pieza_temp, slot, st.session_state["reservas_activas"], config, inventarios)
                st.session_state["pieza_por_confirmar"] = pieza_temp
                st.session_state["confirm_detalle_global"] = {"motivo": resultado["motivo"], "estado": resultado["estado"]}
                st.session_state["confirm_detalle_por_jugador"] = resultado["evaluaciones"]
                modal_confirmacion(pieza_temp, st.session_state["confirm_detalle_global"], 
                                   st.session_state["confirm_detalle_por_jugador"], slot, inventarios)

    # ============================================================
    # 5. Potenciales desechables (EXPANDER)
    # ============================================================
    with st.expander("🗑️ Potenciales desechables", expanded=False):
    
        desechables = inventory_service.get_disposable_pieces(
            slot, inventarios, config, piezas_equipadas, reservas_activas
        )
    
        if len(desechables) > 0:
            df_des = pd.DataFrame(desechables)
            st.session_state["piezas_desechables"] = desechables
    
            # ============================================================
            # 5) Filtros y tabla
            # ============================================================
            st.subheader("🔍 Filtros")

            tipos_disp = sorted(df_des["Tipo"].unique())
            tipo_sel = st.multiselect(
                "Mostrar solo tipos:",
                tipos_disp,
                default=tipos_disp
            )
            
            incluir_sin_uso = st.checkbox(
                "Incluir potenciales cuyo tipo no es usado por ningún jugador",
                value=False
            )
  
            df_filtrado = df_des[df_des["Tipo"].isin(tipo_sel)]

            if not incluir_sin_uso:
                df_filtrado = df_filtrado[df_filtrado["Motivo"] != "Ningún jugador usa este tipo."]
    
            edited_df = st.data_editor(
                df_filtrado,
                use_container_width=True,
                hide_index=True,
                key="editor_desechables",
                column_order=["Seleccionar", "Slot", "ID", "Tipo", "Calidad", "Main Stat", "Substat1", "Substat2", "Substat3", "Substat4", "Motivo"]
            )
    
            # ============================================================
            # 6) Eliminación
            # ============================================================
            if st.button("Eliminar seleccionados"):
                seleccionados = edited_df[edited_df["Seleccionar"] == True]["ID"].tolist()
    
                if len(seleccionados) == 0:
                    st.warning("No has seleccionado ninguna pieza para eliminar.")
                else:
                    # Guardamos clave primaria completa
                    st.session_state["confirmar_eliminacion_ids"] = [
                        (str(slot), str(pid)) for pid in seleccionados
                    ]
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
                        uid = get_current_user_id()
                        inventory_service.delete_pieces(ids_a_eliminar, uid)
    
                        st.success(f"Eliminadas {len(ids_a_eliminar)} piezas.")
                        st.session_state["mostrar_confirmacion_eliminar"] = False
                        st.session_state["confirmar_eliminacion_ids"] = []
                        st.rerun()
    
        else:
            st.info("No hay piezas desechables en este inventario.")
    
if __name__ == "__main__":
    main()
else:
    main()