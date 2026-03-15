import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

from optimizer import (
    jugadores_que_usan_tipo,
    puntuar_pieza,
    umbral_minimo_por_slot_y_afinidad,
    calcular_reservas_por_jugador,
    evaluar_pieza_para_jugador_en_slot,
    valor_clasificacion
)

from data_manager import load_all_into_session


def main():

    st.title("📊 Resumen global del equipamiento")
    load_all_into_session()

    inventarios = st.session_state["inventarios"]
    piezas_equipadas = st.session_state["equipamiento"]
    equipos_entrenamiento = st.session_state.get("equipos_entrenamiento", {})
    config = st.session_state["config_jugadores"]
    tipos = st.session_state["tipos"]
    rareza = st.session_state["rareza"]

    # ============================================================
    # RECONSTRUIR stats_recomendados Y tipos_recomendados
    # ============================================================

    stats_recomendados = {
        jugador: {
            "stats": config[jugador]["builds"]["Base"]["stats_recomendados"]["stats"],
            "puntos": dict(zip(
                config[jugador]["builds"]["Base"]["stats_recomendados"]["stats"],
                config[jugador]["builds"]["Base"]["stats_recomendados"]["puntos"]
            ))
        }
        for jugador in config if "builds" in config[jugador]
    }

    tipos_recomendados = {
        jugador: config[jugador]["builds"]["Base"]["tipos_recomendados"]
        for jugador in config if "builds" in config[jugador]
    }

    # ============================================================
    # 1. CALIDAD GLOBAL DEL EQUIPAMIENTO
    # ============================================================
    st.header("🎽 Calidad global del equipamiento")

    tabla_equipadas = []
    clasificaciones = []
    calidad_por_tipo = {}
    calidad_por_tipo_slot = {}

    for jugador, slots in piezas_equipadas.items():

        stats_rec = stats_recomendados[jugador]["stats"]
        puntos_rec = stats_recomendados[jugador]["puntos"]

        for slot, pieza_id in slots.items():
            if pieza_id in ("", None):
                continue

            pieza_id = str(pieza_id)
            piezas_slot = inventarios.get(slot, [])
            pieza = next((p for p in piezas_slot if str(p["ID"]) == pieza_id), None)
            if pieza is None:
                continue

            tipo = pieza["Tipo"]
            main_stat = pieza["Main Stat"]
            
            eval_pieza=evaluar_pieza_para_jugador_en_slot(pieza,jugador,tipo,str(slot),inventarios,config[jugador]["builds"]["Base"]["stats_recomendados"])

            valor = valor_clasificacion(eval_pieza["calidad"])
            
            clasificaciones.append(valor)

            tabla_equipadas.append({
                "Jugador": jugador,
                "ID": pieza_id,
                "Slot": slot,
                "Tipo": tipo,
                "Clasificación": eval_pieza["calidad"]
            })

    df_equipadas = pd.DataFrame(tabla_equipadas)
    if not df_equipadas.empty:
        df_equipadas["ID"] = df_equipadas["ID"].astype(str)

    orden_prioridad = st.session_state.get("orden_jugadores", [])

    if df_equipadas.empty:
        st.info("No hay piezas equipadas actualmente.")
        return

    df_equipadas["prioridad"] = df_equipadas["Jugador"].apply(lambda j: orden_prioridad.index(j))

    df_equipadas["valor_calidad"] = df_equipadas["Clasificación"].apply(valor_clasificacion)

    df_ordenada = (
        df_equipadas
        .sort_values(["valor_calidad", "prioridad", "Slot"], ascending=[True, True, True])
        .drop(columns=["prioridad", "valor_calidad"])
    )

    st.dataframe(df_ordenada, use_container_width=True, hide_index=True)

    # ============================================================
    # 1B. DISTRIBUCIÓN GLOBAL
    # ============================================================
    st.subheader("📈 Distribución de calidad")

    total = len(clasificaciones)
    num_perfectos = sum(v == 1.0 for v in clasificaciones)
    num_excelentes = sum(v == 0.85 for v in clasificaciones)
    num_buenos = sum(v == 0.7 for v in clasificaciones)
    num_aceptables = sum(v == 0.5 for v in clasificaciones)
    num_malos = sum(v == 0.0 for v in clasificaciones)

    pct_perfectos = num_perfectos / total * 100
    pct_excelentes = num_excelentes / total * 100
    pct_buenos = num_buenos / total * 100
    pct_aceptables = num_aceptables / total * 100
    pct_malos = num_malos / total * 100

    df_pie_global = pd.DataFrame({
        "Clasificación": ["Perfectos", "Excelentes", "Buenos", "Aceptables", "Malos"],
        "Porcentaje": [pct_perfectos, pct_excelentes, pct_buenos, pct_aceptables, pct_malos],
        "Cantidad": [num_perfectos, num_excelentes, num_buenos, num_aceptables, num_malos]
    })

    fig_global = px.pie(
        df_pie_global,
        names="Clasificación",
        values="Porcentaje",
        color="Clasificación",
        color_discrete_map={
            "Perfectos": "#8E44AD",
            "Excelentes": "#2980B9",
            "Buenos": "#27AE60",
            "Aceptables": "#F1C40F",
            "Malos": "#C0392B"
        },
        title="Distribución global",
        custom_data="Cantidad"
    )

    fig_global.update_traces(
        hovertemplate="<b>%{label}</b><br>Porcentaje: %{value:.1f}%<br>Cantidad: %{customdata[0]}"
    )

    # ============================================================
    # TITULARES
    # ============================================================
    max_jugadores = len(orden_prioridad)
    num_titulares = st.slider("Nº Titulares", 1, max_jugadores, min(11, max_jugadores))
    titulares = orden_prioridad[:num_titulares]

    clasif_titulares = [
        valor_clasificacion(row["Clasificación"])
        for _, row in df_equipadas.iterrows()
        if row["Jugador"] in titulares
    ]
    
    total_t = len(clasif_titulares)
    num_perfectos_t = sum(v == 1.0 for v in clasif_titulares)
    num_excelentes_t = sum(v == 0.85 for v in clasif_titulares)
    num_buenos_t = sum(v == 0.7 for v in clasif_titulares)
    num_aceptables_t = sum(v == 0.5 for v in clasif_titulares)
    num_malos_t = sum(v == 0.0 for v in clasif_titulares)
    
    if clasif_titulares:
        pct_perfectos_t = num_perfectos_t / total_t * 100
        pct_excelentes_t = num_excelentes_t / total_t * 100
        pct_buenos_t = num_buenos_t / total_t * 100
        pct_aceptables_t = num_aceptables_t / total_t * 100
        pct_malos_t = num_malos_t / total_t * 100
    else:
        pct_buenos_t = pct_aceptables_t = pct_malos_t = 0

    df_pie_titulares = pd.DataFrame({
        "Clasificación": ["Perfectos", "Excelentes", "Buenos", "Aceptables", "Malos"],
        "Porcentaje": [pct_perfectos_t, pct_excelentes_t, pct_buenos_t, pct_aceptables_t, pct_malos_t],
        "Cantidad": [num_perfectos_t, num_excelentes_t, num_buenos_t, num_aceptables_t, num_malos_t]
    })

    fig_titulares = px.pie(
        df_pie_titulares,
        names="Clasificación",
        values="Porcentaje",
        color="Clasificación",
        color_discrete_map={
            "Perfectos": "#8E44AD",
            "Excelentes": "#2980B9",
            "Buenos": "#27AE60",
            "Aceptables": "#F1C40F",
            "Malos": "#C0392B"
        },
        title="Distribución titulares",
        custom_data="Cantidad"
    )

    fig_titulares.update_traces(
        hovertemplate="<b>%{label}</b><br>Porcentaje: %{value:.1f}%<br>Cantidad: %{customdata}"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_global, use_container_width=True)
    with col2:
        st.plotly_chart(fig_titulares, use_container_width=True)

    st.divider()

    # ============================================================
    # 📊 ESTADO DEL INVENTARIO — SOLO PIEZAS RESERVADAS
    # ============================================================
    
    st.header("📊 Estado del inventario")
    
    reservas = calcular_reservas_por_jugador(
        inventarios=inventarios,
        config_jugadores=config,
        stats_recomendados=stats_recomendados,
        tipos_recomendados=tipos_recomendados,
        piezas_equipadas=piezas_equipadas,
        lista_jugadores_prioridad=orden_prioridad,
        rareza_lista=rareza,
        modo="equipar"
    )
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    tipo_sel = col1.selectbox("Tipo", ["Todos"] + tipos)
    slot_sel = col2.selectbox("Slot", ["Todos", "1", "2", "3", "4", "5", "6"])
    
    jugadores_filtrados = set(orden_prioridad[:num_titulares])
    
    rows = []
    
    # Recorremos SOLO las piezas reservadas
    for jugador, slots_j in reservas.items():
        if jugador not in jugadores_filtrados:
            continue
            
        for slot, tipos_j in slots_j.items():
            if slot_sel != "Todos" and slot != slot_sel:
                continue
    
            for tipo, info in tipos_j.items():
                if tipo_sel != "Todos" and tipo != tipo_sel:
                    continue
    
                rows.append({
                    "Jugador": jugador,
                    "Tipo": tipo,
                    "Slot": slot,
                    "Evaluación": info["calidad"]
                })
    
    df_eval = pd.DataFrame(rows)
    
    if df_eval.empty:
        st.info("No hay piezas que coincidan con los filtros.")
    else:
        # -------------------------
        # Gráfico de barras
        # -------------------------
        df_counts = df_eval.groupby(["Tipo", "Evaluación"]).size().reset_index(name="Cantidad")
    
        chart = alt.Chart(df_counts).mark_bar().encode(
            x=alt.X("Tipo:N", title="Tipo", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Cantidad:Q", title="Cantidad"),
            color=alt.Color("Evaluación:N", scale=alt.Scale(
            domain=["Perfecto", "Excelente", "Bueno", "Aceptable", "Malo", "Falta"],
            range=["#8E44AD","#2980B9","#27AE60","#F1C40F","#C0392B","#999999"]
            )),
            xOffset="Evaluación:N"
        ).properties(width=600, height=400)
    
        st.altair_chart(chart, use_container_width=True)
    
        # -------------------------
        # Tabla detallada
        # -------------------------
        with st.expander("📋 Detalle de calidades"):
            df_detalle = df_eval.groupby(["Tipo", "Slot", "Evaluación"]).size().reset_index(name="Cantidad")
    
            orden_eval = {"Malo": 0, "Aceptable": 1, "Bueno": 2}
            df_detalle["orden_eval"] = df_detalle["Evaluación"].map(orden_eval)
    
            df_detalle = df_detalle.sort_values(
                by=["orden_eval", "Cantidad"],
                ascending=[True, False]
            ).drop(columns=["orden_eval"])
    
            st.dataframe(df_detalle, use_container_width=True)

    # ============================================================
    # 🏐 ¿Con qué equipo deberías entrenar? — NUEVO FORMATO (SOLO RESERVAS)
    # ============================================================
    
    st.subheader("🏐 ¿Con qué equipo deberías entrenar?")
    
    filas = []
    
    for equipo, tipos_equipo in equipos_entrenamiento.items():
    
        # Contadores titulares
        t_falta = t_malo = t_acep = t_bueno = t_excelente = t_perfecto = 0
        # Contadores resto
        r_falta = r_malo = r_acep = r_bueno = r_excelente = r_perfecto = 0
    
        # Recorremos SOLO reservas
        for jugador, slots_j in reservas.items():
            es_titular = jugador in titulares
    
            for slot, tipos_j in slots_j.items():
                for tipo, info in tipos_j.items():
                        
                    if tipo not in tipos_equipo:
                        continue
                       
                    clas = info["calidad"]
    
                    if clas == "Falta":
                        if es_titular:
                            t_falta += 1
                        else:
                            r_falta += 1
    
                    elif clas == "Malo":
                        if es_titular:
                            t_malo += 1
                        else:
                            r_malo += 1
    
                    elif clas == "Aceptable":
                        if es_titular:
                            t_acep += 1
                        else:
                            r_acep += 1
    
                    elif clas == "Bueno":
                        if es_titular:
                            t_bueno += 1
                        else:
                            r_bueno += 1
                    
                    elif clas == "Excelente":
                        if es_titular:
                            t_excelente += 1
                        else:
                            r_excelente += 1
                            
                    elif clas == "Perfectoe":
                        if es_titular:
                            t_perfecto += 1
                        else:
                            r_perfecto += 1
    
        # Añadir fila titulares
        filas.append({
            "Equipo": equipo,
            "Grupo": "Titulares",
            "Faltan": t_falta,
            "Malos": t_malo,
            "Aceptables": t_acep,
            "Buenos": t_bueno,
            "Excelentes": t_excelente,
            "Perfectos": t_perfecto
        })
    
        # Añadir fila resto
        filas.append({
            "Equipo": equipo,
            "Grupo": "Resto",
            "Faltan": r_falta,
            "Malos": r_malo,
            "Aceptables": r_acep,
            "Buenos": r_bueno,
            "Excelentes": r_excelente,
            "Perfectos": r_perfecto
        })
    
    df_rec = pd.DataFrame(filas)
    
    # ============================================================
    # ORDENAR POR PRIORIDAD (con peso extra para titulares)
    # ============================================================
    
    def peso_fila(row):
        # Titulares pesan más
        factor_titular = 5 if row["Grupo"] == "Titulares" else 1
    
        malos_tot = (row["Faltan"] + row["Malos"]) * factor_titular * 3
        aceptables_tot = row["Aceptables"] * factor_titular * 2
        buenos_tot = row["Buenos"] * factor_titular * 1.5
        excelentes_tot = row["Excelentes"] * factor_titular
    
        return (malos_tot, aceptables_tot, buenos_tot, excelentes_tot)
    
    def peso_equipo(df_e):
        malos_total = 0
        aceptables_total = 0
        buenos_total = 0
        excelentes_total = 0
          
        for _, r in df_e.iterrows():
            malos, aceptables, buenos, excelentes = peso_fila(r)
            malos_total += malos
            aceptables_total += aceptables
            buenos_total += buenos
            excelentes_total += excelentes
    
        return (malos_total, aceptables_total, buenos_total, excelentes_total)
    
    pesos_equipo = {
        equipo: peso_equipo(df_rec[df_rec["Equipo"] == equipo])
        for equipo in df_rec["Equipo"].unique()
    }
    
    # Ordenar del PEOR al MEJOR
    df_rec["orden"] = df_rec["Equipo"].map(pesos_equipo)
    
    # Orden descendente: primero el equipo más necesitado de entrenamiento
    df_rec = df_rec.sort_values("orden", ascending=False).drop(columns=["orden"])
    
    # Mostrar tabla final
    st.dataframe(df_rec, use_container_width=True, hide_index=True)
    
    # Mejor equipo
    mejor_equipo = df_rec.iloc[0]["Equipo"]
    st.success(f"🏆 **Deberías entrenar con {mejor_equipo}**")
    
if __name__ == "__main__":
    main()
else:
    main()
