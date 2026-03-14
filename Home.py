import streamlit as st
from data_manager import (
    load_all_into_session, 
    authenticate, 
    register_user
)

# ============================================================
# PAGE CONTENT FUNCTIONS
# ============================================================

def formulario_login():
    st.subheader("Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        user_data = authenticate(username, password)
        if user_data:
            st.session_state["usuario"] = username
            st.session_state["user_data"] = user_data
            load_all_into_session()
            st.success(f"Bienvenido {username}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

def formulario_registro():
    st.subheader("Crear cuenta")
    new_user = st.text_input("Nuevo Usuario")
    new_pass = st.text_input("Nueva Contraseña", type="password")
    
    if st.button("Registrarse"):
        if register_user(new_user, new_pass, role="standard"):
            st.success("Usuario creado. Ahora puedes iniciar sesión.")
        else:
            st.error("El usuario ya existe")

def pagina_acceso():
    st.title("🏐 Haikyuu Fly High — Acceso")
    modo = st.radio("¿Qué quieres hacer?", ["Iniciar sesión", "Crear cuenta"])
    if modo == "Iniciar sesión":
        formulario_login()
    else:
        formulario_registro()

def main_home():
    st.title("🏠 Inicio")
    
    if "datos_cargados" not in st.session_state:
        load_all_into_session()
        st.session_state["datos_cargados"] = True
        st.success("Datos cargados correctamente.")
    else:
        st.info("Tus datos están listos.")

    st.write("Usa el menú lateral para navegar por las diferentes secciones.")
    
    role = st.session_state['user_data']['role']
    if role == "admin":
        st.markdown("---")
        st.subheader("Panel de Administrador")
        st.write("Tienes acceso a la gestión global de tipos, stats y jugadores.")
    else:
        st.write("Como usuario estándar, puedes gestionar tu propio inventario y optimizar tus jugadores.")

def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

# ============================================================
# NAVIGATION CONFIGURATION
# ============================================================

def run_navigation():
    st.set_page_config(layout="wide", page_title="Haikyuu Fly High - Optimizer")

    if "usuario" not in st.session_state:
        # User not logged in: only show login page
        pg = st.navigation([st.Page(pagina_acceso, title="Acceso", icon="🔐")])
        pg.run()
    else:
        # Define common pages
        common_pages = [
            st.Page(main_home, title="Inicio", icon="🏠"),
            st.Page("views/1_Jugadores.py", title="Jugadores", icon="🏐"),
            st.Page("views/2_Inventario_de_Potenciales.py", title="Inventario", icon="📦"),
            st.Page("views/3_Equipar.py", title="Equipar", icon="⚡"),
            st.Page("views/4_Resumen.py", title="Resumen", icon="📊"),
            st.Page("views/5_Validar.py", title="Validar", icon="✅"),
            st.Page("views/8_Backup_Datos.py", title="Backup", icon="💾"),
        ]

        # Define admin-only pages
        admin_pages = [
            st.Page("views/6_Gestionar_Tipos_y_Stats.py", title="Configuración Global", icon="⚙️"),
            st.Page("views/7_Gestionar_Jugadores.py", title="Gestión de Jugadores", icon="👤"),
            st.Page("views/9_Gestion_de_Usuarios.py", title="Gestión de Usuarios", icon="👥"),
        ]

        # Build final navigation based on role
        pages = {"Herramientas": common_pages}
        if st.session_state["user_data"]["role"] == "admin":
            pages["Administración"] = admin_pages

        pg = st.navigation(pages)
        
        # Add logout to sidebar
        logout_button()
        
        pg.run()

if __name__ == "__main__":
    run_navigation()
