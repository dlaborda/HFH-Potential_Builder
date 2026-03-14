import streamlit as st
import pandas as pd
import io
from data_manager import save_json, ensure_data_dir


# ============================================================
# Lector robusto de CSV (detecta encoding, separador y BOM)
# ============================================================
def leer_csv_seguro(file):
    raw = file.read()

    if not raw or len(raw) < 5:
        raise ValueError("El archivo está vacío o no contiene datos válidos.")

    # Intentar varios encodings
    for enc in ["utf-8-sig", "latin1", "cp1252"]:
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue

    # Detectar separador
    sep = ";" if text.count(";") > text.count(",") else ","

    df = pd.read_csv(io.StringIO(text), sep=sep)

    if df.empty or len(df.columns) == 0:
        raise ValueError("El archivo no contiene columnas válidas.")

    return df


# ============================================================
# Página principal
# ============================================================
def main():

    st.title("📥 Migración de datos desde CSV a JSON")
    ensure_data_dir()

    # ============================================================
    # BOTÓN PARA BORRAR TODOS LOS DATOS JSON
    # ============================================================
    st.subheader("⚠️ Borrar datos actuales")

    if st.button("Borrar todos los datos JSON"):
        import os
        from data_manager import FILES, DATA_DIR

        for name, filename in FILES.items():
            path = os.path.join(DATA_DIR, filename)
            if os.path.exists(path):
                os.remove(path)

        # Regenerar estructura vacía
        save_json("jugadores", [])
        save_json("tipos", [])
        save_json("stats", [])
        save_json("tipos_recomendados", {})
        save_json("stats_recomendados", {})
        save_json("config_jugadores", {})
        save_json("inventarios", {str(i): [] for i in range(1, 7)})

        st.success("Todos los datos han sido borrados y reinicializados correctamente.")

    st.warning("Ejecuta esta herramienta solo para migrar datos. Después puedes borrar esta página.")

    # ============================================================
    # 1. Tipos recomendados
    # ============================================================
    st.header("1️⃣ Tipos recomendados (Set_recomendado.csv)")

    file_tipos = st.file_uploader("Selecciona Set_recomendado.csv", type="csv")
    tipos_rec = {}

    if file_tipos:
        df = leer_csv_seguro(file_tipos)

        columnas = {"Jugador", "Tipo de Slot", "Prioridad"}
        if not columnas.issubset(df.columns):
            st.error(f"El CSV debe contener las columnas: {', '.join(columnas)}")
            return

        df = df.sort_values(["Jugador", "Prioridad"])

        for jugador, grupo in df.groupby("Jugador"):
            tipos_rec[jugador] = grupo["Tipo de Slot"].tolist()

        st.success("Tipos recomendados cargados correctamente.")

    # ============================================================
    # 2. Stats recomendados
    # ============================================================
    st.header("2️⃣ Stats recomendados (Stats_recomendados.csv)")

    file_stats = st.file_uploader("Selecciona Stats_recomendados.csv", type="csv")
    stats_rec = {}

    if file_stats:
        df = leer_csv_seguro(file_stats)

        columnas = {"Jugador", "Puntos", "Stats"}
        if not columnas.issubset(df.columns):
            st.error(f"El CSV debe contener las columnas: {', '.join(columnas)}")
            return

        for jugador, grupo in df.groupby("Jugador"):
            stats = grupo["Stats"].tolist()
            puntos = grupo["Puntos"].astype(int).tolist()
            stats_rec[jugador] = [stats, puntos]

        st.success("Stats recomendados cargados correctamente.")

    # ============================================================
    # 3. Generar lista de jugadores válidos
    # ============================================================
    if file_tipos and file_stats:

        jugadores_validos = sorted(list(set(tipos_rec.keys()) & set(stats_rec.keys())))

        st.header("3️⃣ Jugadores válidos detectados")
        st.write(jugadores_validos)

        # Guardar jugadores y recomendados
        save_json("jugadores", jugadores_validos)
        save_json("tipos_recomendados", {j: tipos_rec[j] for j in jugadores_validos})
        save_json("stats_recomendados", {j: stats_rec[j] for j in jugadores_validos})

        # Crear configuración vacía para cada jugador
        config = {
            j: {"candidatos_4": [], "slots_activos": []}
            for j in jugadores_validos
        }
        save_json("config_jugadores", config)

        st.success("Jugadores, tipos, stats y configuración generados correctamente.")

    # ============================================================
    # 3.bis. Generar listas globales de tipos y stats
    # ============================================================
    if tipos_rec and stats_rec:

        todos_tipos = {t.strip() for lista in tipos_rec.values() for t in lista}
        todos_stats = {s.strip() for stats, _ in stats_rec.values() for s in stats}

        tipos_lista = sorted(todos_tipos)
        stats_lista = sorted(todos_stats)

        save_json("tipos", tipos_lista)
        save_json("stats", stats_lista)

        st.success("Listas globales de tipos y stats generadas correctamente.")

    # ============================================================
    # 4. Inventarios
    # ============================================================
    st.header("4️⃣ Inventarios")

    inventarios = {str(i): [] for i in range(1, 7)}

    for slot in range(1, 7):
        st.subheader(f"Inventario Slot {slot}")
        file_inv = st.file_uploader(
            f"Selecciona inventario_slot{slot}.csv",
            type="csv",
            key=f"slot{slot}"
        )

        if file_inv:
            df = leer_csv_seguro(file_inv)
            inventarios[str(slot)] = df.to_dict(orient="records")
            st.success(f"Inventario del slot {slot} migrado correctamente.")

    if st.button("Guardar inventarios"):
        save_json("inventarios", inventarios)
        st.success("Inventarios guardados correctamente.")

    # ============================================================
    # 5. Limpiar session_state para recargar datos nuevos
    # ============================================================
    if st.button("Finalizar migración y recargar sistema"):
        for key in [
            "jugadores", "tipos", "stats",
            "tipos_recomendados", "stats_recomendados",
            "config_jugadores", "inventarios"
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.success("Migración completada. Reinicia la aplicación para cargar los nuevos datos.")


if __name__ == "__main__":
    main()
else:
    main()
