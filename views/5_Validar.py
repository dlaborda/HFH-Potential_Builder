import streamlit as st
import pandas as pd
import numpy as np

from optimizer import (
    explicar_puntaje_mejor_jugador,
    puntuar_pieza,
    explicar_puntuar_pieza,
    jugadores_que_usan_tipo
)

from data_manager import load_all_into_session


def main():

    st.title("🧮 Validar puntaje base de un potencial")
    load_all_into_session()

    # -----------------------------
    # 1. Validar datos cargados
    # -----------------------------
    if "inventarios" not in st.session_state:
        st.error("Primero debes cargar los datos en la página 0.")
        return
    
    inventarios = st.session_state["inventarios"]
    config = st.session_state["config_jugadores"]

    # -----------------------------
    # 2. Reconstruir stats_recomendados y tipos_recomendados
    # -----------------------------
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

    # -----------------------------
    # 3. Seleccionar inventario
    # -----------------------------
    st.subheader("Selecciona inventario (slot)")
    slot = st.selectbox("Inventario", list(inventarios.keys()))
    
    df_inv = pd.DataFrame(inventarios[slot]).fillna("")

    # -----------------------------
    # 4. Seleccionar potencial
    # -----------------------------
    st.subheader("Selecciona potencial")
    id_sel = st.selectbox("ID de la pieza", df_inv["ID"].tolist())
    
    pieza = df_inv[df_inv["ID"] == id_sel].iloc[0].to_dict()

    # -----------------------------
    # 5. Calcular mejor jugador
    # -----------------------------
    resultado = explicar_puntaje_mejor_jugador(
        pieza,
        stats_recomendados,
        tipos_recomendados
    )

    jugador = resultado["jugador"]
    puntaje = resultado["puntaje"]
    
    st.markdown("## 🟩 Resultado del cálculo")
    
    st.write(f"**Jugador que mejor aprovecha este potencial:** {jugador}")
    st.write(f"**Puntaje final:** {puntaje:.2f}")
    
    st.markdown("### Desglose del cálculo (mejor jugador)")

    st.write(f"### 🧩 Tipo del potencial: **{resultado['tipo']}**")

    df_detalle = pd.DataFrame(
        resultado["filas"],
        columns=["Nivel", "Stat", "Tipo Mejora", "Cálculo", "Resultado"]
    )
    
    st.dataframe(df_detalle, hide_index=True, use_container_width=True)

    # -----------------------------
    # 6. Comparar con otro jugador
    # -----------------------------
    st.markdown("---")
    st.markdown("## 🎯 Comparar con otro jugador")
    
    jugador_manual = st.selectbox(
        "Selecciona un jugador para comparar:",
        list(stats_recomendados.keys()),
        key="validar_jugador_manual"
    )
    
    stats_rec_manual = stats_recomendados[jugador_manual]["stats"]
    puntos_rec_manual = stats_recomendados[jugador_manual]["puntos"]
    
    puntaje_manual, filas_manual, tipo_manual = explicar_puntuar_pieza(
        pieza, stats_rec_manual, puntos_rec_manual
    )
    
    st.write(f"### 🧩 Tipo del potencial: **{tipo_manual}**")
    
    df_detalle_manual = pd.DataFrame(
        filas_manual,
        columns=["Nivel", "Stat", "Tipo Mejora", "Cálculo", "Resultado"]
    )
    
    st.dataframe(df_detalle_manual, hide_index=True, use_container_width=True)
    
    st.write(f"### 📌 Puntaje final: {puntaje_manual:.2f}")

    # ============================================================
    # 🔍 ANÁLISIS POR TIPO E INVENTARIO
    # ============================================================

    st.header("📊 Análisis de Potenciales por Tipo e Inventario")

    jugadores_por_tipo = jugadores_que_usan_tipo(tipos_recomendados)

    slot_sel = st.selectbox("Inventario a analizar", ["1", "2", "3", "4", "5", "6"])
    tipos_disponibles = sorted({p["Tipo"] for p in inventarios[slot_sel]})
    tipo_sel = st.selectbox("Tipo a analizar", tipos_disponibles)

    df_inv = pd.DataFrame(inventarios[slot_sel]).fillna("")

    def mejor_puntaje_para_tipo(piece, tipo):
        mejor = 0
        mejor_jugador = None
        for jugador in jugadores_por_tipo.get(tipo, []):
            stats_rec = stats_recomendados[jugador]["stats"]
            puntos_rec = stats_recomendados[jugador]["puntos"]
            puntaje = puntuar_pieza(piece, stats_rec, puntos_rec)
            if puntaje > mejor:
                mejor = puntaje
                mejor_jugador = jugador
        return mejor, mejor_jugador

    puntajes_tipo = []
    detalles = []

    for _, pieza in df_inv.iterrows():
        pieza_dict = pieza.to_dict()
        if pieza_dict["Tipo"] != tipo_sel:
            continue

        puntaje, mejor_jugador = mejor_puntaje_para_tipo(pieza_dict, tipo_sel)
        puntajes_tipo.append(puntaje)

        detalles.append({
            "ID": pieza_dict["ID"],
            "Puntaje": puntaje,
            "Jugador óptimo": mejor_jugador,
            "Main Stat": pieza_dict["Main Stat"],
            "Substats": " / ".join(
                s for s in [
                    pieza_dict.get("Substat1", ""),
                    pieza_dict.get("Substat2", ""),
                    pieza_dict.get("Substat3", ""),
                    pieza_dict.get("Substat4", "")
                ] if s
            )
        })

    if len(puntajes_tipo) >= 3:
        p70 = np.percentile(puntajes_tipo, 70)
        media = np.mean(puntajes_tipo)
        std = np.std(puntajes_tipo)
        umbral = max(p70, media + 0.5 * std)
    else:
        umbral = 0

    st.subheader(f"📌 Umbral adaptativo para '{tipo_sel}' en inventario {slot_sel}: **{umbral:.2f}**")

    df_detalles = pd.DataFrame(detalles)
    if not df_detalles.empty:
        df_detalles["ID"] = df_detalles["ID"].astype(str)
    df_detalles["Diferencia"] = df_detalles["Puntaje"] - umbral
    df_detalles = df_detalles.sort_values("Puntaje", ascending=False)

    st.dataframe(df_detalles, use_container_width=True)

    # ============================================================
    # VALIDACIÓN DE COMBINACIONES
    # ============================================================

    st.header("🔍 Validación de combinaciones")

    if "resultados_optimizador" not in st.session_state:
        st.warning("Primero ejecuta el optimizador en la página Equipar.")
        return

    jugador_val = st.selectbox(
        "Selecciona un jugador para validar",
        list(st.session_state["resultados_optimizador"].keys())
    )

    res = st.session_state["resultados_optimizador"][jugador_val]
    ids_rec = res["ids_por_slot"]

    piezas_equipadas = st.session_state.get("equipamiento", {})
    equip_actual = piezas_equipadas.get(jugador_val, {})

    stats_rec = stats_recomendados[jugador_val]["stats"]
    puntos_rec = stats_recomendados[jugador_val]["puntos"]

    slots = ["1", "2", "3", "4", "5", "6"]

    def info_pieza(slot, idp):
        df = pd.DataFrame(inventarios[slot]).fillna("")
        df["ID_norm"] = df["ID"].astype(str).str.strip()
        idp_norm = str(idp).strip()

        fila = df[df["ID_norm"] == idp_norm]

        if fila.empty:
            return "", "", "", 0

        pieza = fila.iloc[0].to_dict()
        punt = puntuar_pieza(pieza, stats_rec, puntos_rec)

        return pieza["ID"], pieza.get("Calidad", ""), pieza.get("Tipo", ""), punt

    tabla_rec = []
    tabla_act = []
    suma_rec = 0
    suma_act = 0

    for slot in slots:
        id_rec = ids_rec.get(slot, "")
        id_act = equip_actual.get(slot, "")

        idr, calr, tipr, pr = info_pieza(slot, id_rec)
        ida, cala, tipa, pa = info_pieza(slot, id_act)

        suma_rec += pr
        suma_act += pa

        tabla_rec.append([slot, idr, calr, tipr, round(pr, 2)])
        tabla_act.append([slot, ida, cala, tipa, round(pa, 2)])

    tabla_rec.append(["TOTAL", "", "", "", round(suma_rec, 2)])
    tabla_act.append(["TOTAL", "", "", "", round(suma_act, 2)])

    df_rec = pd.DataFrame(tabla_rec, columns=["Slot", "ID", "Calidad", "Tipo", "Puntuación"])
    df_act = pd.DataFrame(tabla_act, columns=["Slot", "ID", "Calidad", "Tipo", "Puntuación"])
    
    df_rec["ID"] = df_rec["ID"].astype(str)
    df_act["ID"] = df_act["ID"].astype(str)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recomendado")
        st.dataframe(df_rec, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("Actual")
        st.dataframe(df_act, hide_index=True, use_container_width=True)

    st.divider()

    # ============================================================
    # SELECCIÓN MANUAL POR SLOT
    # ============================================================

    st.subheader("Selección manual por slot")

    for slot in slots:
        key_sel = f"manual_sel_{slot}"
        if key_sel not in st.session_state:
            st.session_state[key_sel] = None

    for slot in slots:
        df_inv = pd.DataFrame(inventarios[slot]).fillna("")
        df_inv = df_inv[df_inv["Tipo"].isin(tipos_recomendados[jugador_val])]

        opciones = ["Ninguno"] + [str(x) for x in df_inv["ID"].tolist()]

        st.session_state[f"manual_sel_{slot}"] = st.selectbox(
            f"Slot {slot}",
            opciones,
            key=f"selector_slot_{slot}"
        )

    st.divider()

    tabla_manual = []
    suma_manual = 0

    for slot in slots:
        sel = st.session_state[f"manual_sel_{slot}"]

        if sel == "Ninguno":
            tabla_manual.append([slot, "", 0])
            continue

        df_inv = pd.DataFrame(inventarios[slot]).fillna("")
        fila = df_inv[df_inv["ID"] == int(sel)]
        pieza = fila.iloc[0].to_dict()
        punt = puntuar_pieza(pieza, stats_rec, puntos_rec)

        tabla_manual.append([
            slot,
            f"{pieza['ID']} / {pieza['Calidad']} / {pieza['Tipo']}",
            round(punt, 2)
        ])

        suma_manual += punt

    tabla_manual.append(["TOTAL", "", round(suma_manual, 2)])

    df_manual = pd.DataFrame(tabla_manual, columns=["Slot", "Selección manual", "Puntuación"])

    st.subheader("Comparación manual")
    st.dataframe(df_manual, hide_index=True, use_container_width=True)

    st.divider()

    # ============================================================
    # POTENCIALES DISPONIBLES POR SLOT
    # ============================================================

    st.subheader("Potenciales disponibles por slot")

    slot_ver = st.selectbox("Ver potenciales del slot", slots, key="selector_ver_potenciales")

    df_inv = pd.DataFrame(inventarios[slot_ver]).fillna("")
    df_inv = df_inv[df_inv["Tipo"].isin(tipos_recomendados[jugador_val])]

    df_inv["Puntuación"] = df_inv.apply(
        lambda row: puntuar_pieza(row.to_dict(), stats_rec, puntos_rec),
        axis=1
    )
    df_inv["ID"] = df_inv["ID"].astype(str)

    st.dataframe(
        df_inv[[

            "ID", "Calidad", "Tipo", "Main Stat",
            "Substat1", "Substat2", "Substat3", "Substat4",
            "Puntuación"
        ]],
        hide_index=True,
        use_container_width=True
    )


if __name__ == "__main__":
    main()
else:
    main()
