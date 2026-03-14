import streamlit as st
import pandas as pd
from data_manager import (
    load_all_into_session, 
    check_role, 
    get_all_users, 
    update_user_role, 
    delete_user
)

def main():
    # Only admins can see this page
    check_role("admin")
    load_all_into_session()

    st.title("👥 Gestión de Usuarios")

    users = get_all_users()
    
    # Create a simple table view of users
    user_list = []
    for uname, udata in users.items():
        user_list.append({
            "Usuario": uname,
            "Rol": udata.get("role", "standard")
        })
    
    df_users = pd.DataFrame(user_list)
    st.dataframe(df_users, use_container_width=True)

    st.divider()

    # --- Section: Update Role ---
    st.subheader("✏️ Modificar Rol")
    # Filter out Dalt3r from the update selection to avoid UI confusion, though backend handles it
    updatable_users = [u for u in users.keys() if u != "Dalt3r"]
    
    col1, col2 = st.columns(2)
    with col1:
        user_to_update = st.selectbox("Seleccionar usuario para cambiar rol", [""] + updatable_users)
    with col2:
        new_role = st.selectbox("Nuevo Rol", ["standard", "admin"])

    if st.button("Actualizar Rol"):
        if user_to_update:
            success, msg = update_user_role(user_to_update, new_role)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        else:
            st.warning("Selecciona un usuario.")

    st.divider()

    # --- Section: Delete User ---
    st.subheader("🗑️ Eliminar Usuario")
    # Filter out Dalt3r from the delete selection
    deletable_users = [u for u in users.keys() if u != "Dalt3r"]
    
    user_to_delete = st.selectbox("Seleccionar usuario a eliminar", [""] + deletable_users)
    
    if st.button("Eliminar permanentemente", type="primary"):
        if user_to_delete:
            # Secondary confirmation via a temporary state if desired, but here we just execute
            success, msg = delete_user(user_to_delete)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        else:
            st.warning("Selecciona un usuario.")

if __name__ == "__main__":
    main()
else:
    main()
