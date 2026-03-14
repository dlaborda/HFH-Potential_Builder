import streamlit as st

def main():
    st.title("🏐 Haikyuu Optimizer")
    st.markdown("""
    Bienvenido al optimizador avanzado de equipamiento para Haikyuu.

    ### Pasos recomendados:
    1. Ve a **0 – Cargar Datos** y carga tus CSVs.
    2. Ve a **1 – Equipar** para ver recomendaciones y equipar piezas.
    3. Ve a **2 – Eliminar** para limpiar piezas sobrantes.
    4. Ve a **3 – Resumen** para ver el estado global del equipo.

    Todo se guarda automáticamente.
    """)

if __name__ == "__main__":
    main()
