import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

from optimizer import (
    jugadores_que_usan_tipo,
    puntuar_pieza,
    calcular_umbral_aspiracional,
    umbral_minimo_por_slot_y_afinidad,
    calcular_reservas_por_jugador
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

    jugadores_por_tipo = jugadores_que_usan_tipo(tipos_recomendados)

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

            # 1) Puntaje REAL
            puntaje_real = puntuar_pieza(pieza, stats_rec, puntos_rec)

            # 2) Umbral mínimo
            umbral_min = umbral_minimo_por_slot_y_afinidad(
                slot, main_stat, stats_rec, puntos_rec
            )

            # 3) Umbral aspiracional
            umbral_asp = calcular_umbral_aspiracional(
                tipo, slot, inventarios, stats_rec, puntos_rec, jugador
            )

            # 4) Clasificación
            if puntaje_real >= umbral_asp:
                clasificacion = "Buena"
                valor = 1.0
            elif puntaje_real >= umbral_min:
                clasificacion = "Aceptable"
                valor = 0.5
            else:
                clasificacion = "Mala"
                valor = 0.0

            clasificaciones.append(valor)

            tabla_equipadas.append({
                "Jugador": jugador,
                "Slot": slot,
                "ID": pieza_id,
                "Tipo": tipo,
                "Puntaje real": round(puntaje_real, 2),
                "Umbral mínimo": round(umbral_min, 2),
                "Umbral aspiracional": round(umbral_asp, 2),
                "Clasificación": clasificacion
            })

            calidad_por_tipo.setdefault(tipo, []).append(valor)
            clave_ts = (tipo, slot)
            calidad_por_tipo_slot.setdefault(clave_ts, []).append(valor)

    df_equipadas = pd.DataFrame(tabla_equipadas)

    orden_prioridad = st.session_state.get("orden_jugadores", [])

    if df_equipadas.empty:
        st.info("No hay piezas equipadas actualmente.")
        return

    df_equipadas["prioridad"] = df_equipadas["Jugador"].apply(lambda j: orden_prioridad.index(j))

    def valor_clasificacion(c):
        return {"Buena": 1.0, "Aceptable": 0.5}.get(c, 0.0)

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
    num_buenas = sum(v == 1.0 for v in clasificaciones)
    num_aceptables = sum(v == 0.5 for v in clasificaciones)
    num_malas = sum(v == 0.0 for v in clasificaciones)

    pct_buenas = num_buenas / total * 100
    pct_aceptables = num_aceptables / total * 100
    pct_malas = num_malas / total * 100

    df_pie_global = pd.DataFrame({
        "Clasificación": ["Buenas", "Aceptables", "Malas"],
        "Porcentaje": [pct_buenas, pct_aceptables, pct_malas],
        "Cantidad": [num_buenas, num_aceptables, num_malas]
    })

    fig_global = px.pie(
        df_pie_global,
        names="Clasificación",
        values="Porcentaje",
        color="Clasificación",
        color_discrete_map={
            "Buenas": "#4CAF50",
            "Aceptables": "#FFC107",
            "Malas": "#F44336"
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
    titulares = orden_prioridad[:11]

    clasif_titulares = [
        valor_clasificacion(row["Clasificación"])
        for _, row in df_equipadas.iterrows()
        if row["Jugador"] in titulares
    ]

    if clasif_titulares:
        pct_buenas_t = sum(v == 1.0 for v in clasif_titulares) / len(clasif_titulares) * 100
        pct_aceptables_t = sum(v == 0.5 for v in clasif_titulares) / len(clasif_titulares) * 100
        pct_malas_t = sum(v == 0.0 for v in clasif_titulares) / len(clasif_titulares) * 100
    else:
        pct_buenas_t = pct_aceptables_t = pct_malas_t = 0

    df_pie_titulares = pd.DataFrame({
        "Clasificación": ["Buenas", "Aceptables", "Malas"],
        "Porcentaje": [pct_buenas_t, pct_aceptables_t, pct_malas_t],
        "Cantidad": [
            sum(v == 1.0 for v in clasif_titulares),
            sum(v == 0.5 for v in clasif_titulares),
            sum(v == 0.0 for v in clasif_titulares)
        ]
    })

    fig_titulares = px.pie(
        df_pie_titulares,
        names="Clasificación",
        values="Porcentaje",
        color="Clasificación",
        color_discrete_map={
            "Buenas": "#4CAF50",
            "Aceptables": "#FFC107",
            "Malas": "#F44336"
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
    col1, col2 = st.columns(2)
    tipo_sel = col1.selectbox("Tipo", ["Todos"] + tipos)
    slot_sel = col2.selectbox("Slot", ["Todos", "1", "2", "3", "4", "5", "6"])
    
    rows = []
    
    # Recorremos SOLO las piezas reservadas
    for jugador, slots_j in reservas.items():
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
            domain=["Mala", "Aceptable", "Buena", "Falta"],
            range=["#d9534f", "#f0ad4e", "#5cb85c", "#999999"]
            )),
            xOffset="Evaluación:N"
        ).properties(width=600, height=400)
    
        st.altair_chart(chart, use_container_width=True)
    
        # -------------------------
        # Tabla detallada
        # -------------------------
        with st.expander("📋 Detalle de calidades"):
            df_detalle = df_eval.groupby(["Tipo", "Slot", "Evaluación"]).size().reset_index(name="Cantidad")
    
            orden_eval = {"Mala": 0, "Aceptable": 1, "Buena": 2}
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

    # Titulares = primeros 11
    titulares = set(orden_prioridad[:11])
    
    filas = []
    
    for equipo, tipos_equipo in equipos_entrenamiento.items():
    
        # Contadores titulares
        t_falta = t_mala = t_acep = t_buena = 0
        # Contadores resto
        r_falta = r_mala = r_acep = r_buena = 0
    
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
    
                    elif clas == "Mala":
                        if es_titular:
                            t_mala += 1
                        else:
                            r_mala += 1
    
                    elif clas == "Aceptable":
                        if es_titular:
                            t_acep += 1
                        else:
                            r_acep += 1
    
                    elif clas == "Buena":
                        if es_titular:
                            t_buena += 1
                        else:
                            r_buena += 1
    
        # Añadir fila titulares
        filas.append({
            "Equipo": equipo,
            "Grupo": "Titulares",
            "Faltan": t_falta,
            "Malas": t_mala,
            "Aceptables": t_acep,
            "Buenas": t_buena
        })
    
        # Añadir fila resto
        filas.append({
            "Equipo": equipo,
            "Grupo": "Resto",
            "Faltan": r_falta,
            "Malas": r_mala,
            "Aceptables": r_acep,
            "Buenas": r_buena
        })
    
    df_rec = pd.DataFrame(filas)
    
    # ============================================================
    # ORDENAR POR PRIORIDAD (con peso extra para titulares)
    # ============================================================
    
    def peso_fila(row):
        # Titulares pesan más
        factor = 2 if row["Grupo"] == "Titulares" else 1
    
        malas_tot = (row["Faltan"] + row["Malas"]) * factor
        aceptables_tot = row["Aceptables"] * factor
    
        return (malas_tot, aceptables_tot)
    
    def peso_equipo(df_e):
        malas_total = 0
        aceptables_total = 0
    
        for _, r in df_e.iterrows():
            malas, aceptables = peso_fila(r)
            malas_total += malas
            aceptables_total += aceptables
    
        return (malas_total, aceptables_total)
    
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
