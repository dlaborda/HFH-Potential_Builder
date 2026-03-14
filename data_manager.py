import json
import os
import shutil
import streamlit as st
import hashlib
from abc import ABC, abstractmethod

# Constants
DATA_DIR = "data"
USER_DATA_DIR = "data/user_data"
IMG_DIR = "data/imagenes_jugadores"

FILES = {
    "tipos": "tipos.json",
    "stats": "stats.json",
    "inventarios": "inventarios.json",
    "config_jugadores": "config_jugadores.json",
    "equipos_entrenamiento": "equipos_entrenamiento.json",
    "equipamiento": "equipamiento.json",
    "orden_jugadores": "orden_jugadores.json",
    "Escuelas": "escuelas.json",
    "Rarezas": "rarezas.json",
    "Rol": "rol.json",
    "usuarios": "usuarios.json"
}

# ============================================================
# 1. STORAGE (SRP & DIP) - Multi-User Aware
# ============================================================

class Storage(ABC):
    @abstractmethod
    def load(self, name: str, default: any, user_id: str = None) -> any: pass
    @abstractmethod
    def save(self, name: str, data: any, user_id: str = None): pass

class JSONStorage(Storage):
    def __init__(self, data_dir: str, user_data_dir: str, files_map: dict):
        self.data_dir = data_dir
        self.user_data_dir = user_data_dir
        self.files_map = files_map
        self._ensure_dir(self.data_dir)
        self._ensure_dir(self.user_data_dir)

    def _ensure_dir(self, directory: str):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _get_path(self, name: str, user_id: str = None) -> str:
        # Files that are isolated per user
        user_isolated = ["inventarios", "orden_jugadores", "equipamiento", "config_jugadores_overrides"]
        if user_id and name in user_isolated:
            user_dir = os.path.join(self.user_data_dir, user_id)
            self._ensure_dir(user_dir)
            filename = self.files_map.get(name, f"{name}.json")
            return os.path.join(user_dir, filename)
        return os.path.join(self.data_dir, self.files_map[name])

    def load(self, name: str, default: any, user_id: str = None) -> any:
        path = self._get_path(name, user_id)
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def save(self, name: str, data: any, user_id: str = None):
        path = self._get_path(name, user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

storage = JSONStorage(DATA_DIR, USER_DATA_DIR, FILES)

# ============================================================
# 2. DOMAIN REPOSITORIES (Multi-User)
# ============================================================

class UserRepository:
    def __init__(self, storage: Storage):
        self.storage = storage
        self._ensure_admin()

    def _ensure_admin(self):
        # Hardcoded admin credentials
        admin_user = "Dalt3r"
        admin_pass = "0ItLK^w*P5L8@#LH"
        
        users = self.get_all()
        if admin_user not in users:
            self.create(admin_user, admin_pass, role="admin")

    def get_all(self) -> dict:
        return self.storage.load("usuarios", {})

    def save_all(self, users: dict):
        self.storage.save("usuarios", users)

    def authenticate(self, username, password) -> dict:
        users = self.get_all()
        if username in users:
            hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if users[username]["password"] == hashed:
                # Return data including role
                data = users[username].copy()
                data["username"] = username
                return data
        return None

    def create(self, username, password, role="standard"):
        users = self.get_all()
        if username in users: return False
        users[username] = {
            "password": hashlib.sha256(password.encode("utf-8")).hexdigest(),
            "role": role
        }
        self.save_all(users)
        
        # Initialize config_jugadores_overrides with Equipar=False for active players
        base_config = self.storage.load("config_jugadores", {})
        overrides = {
            jugador: {"Equipar": False}
            for jugador, data in base_config.items()
            if data.get("activo") == True
        }
        self.storage.save("config_jugadores_overrides", overrides, username)
        
        return True

    def update_role(self, username, new_role):
        if username == "Dalt3r": return False, "No se puede cambiar el rol del administrador principal."
        users = self.get_all()
        if username in users:
            users[username]["role"] = new_role
            self.save_all(users)
            return True, f"Rol de {username} actualizado a {new_role}."
        return False, "Usuario no encontrado."

    def delete_user(self, username):
        if username == "Dalt3r": return False, "No se puede eliminar al administrador principal."
        users = self.get_all()
        if username in users:
            # Remove user data folder if it exists
            user_dir = os.path.join(self.storage.user_data_dir, username)
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)
            
            del users[username]
            self.save_all(users)
            return True, f"Usuario {username} eliminado."
        return False, "Usuario no encontrado."

class PlayerRepository:
    def __init__(self, storage: Storage):
        self.storage = storage

    def load_config(self, user_id: str = None) -> dict:
        base_config = self.storage.load("config_jugadores", {})
        if not user_id: return base_config
        
        overrides = self.storage.load("config_jugadores_overrides", {}, user_id)
        
        # Merge: base config with user overrides
        config = {}
        for jugador, base_conf in base_config.items():
            user_conf = overrides.get(jugador, {})
            merged = base_conf.copy()
            merged.update(user_conf)
            config[jugador] = merged
        return config

    def save_user_override(self, user_id: str, jugador: str, data: dict):
        overrides = self.storage.load("config_jugadores_overrides", {}, user_id)
        if jugador not in overrides: overrides[jugador] = {}
        overrides[jugador].update(data)
        self.storage.save("config_jugadores_overrides", overrides, user_id)

    def reset_user_override(self, user_id: str, jugador: str):
        overrides = self.storage.load("config_jugadores_overrides", {}, user_id)
        if jugador in overrides:
            del overrides[jugador]
            self.storage.save("config_jugadores_overrides", overrides, user_id)

    def update_base_active_status(self, jugador: str, active: bool):
        config = self.storage.load("config_jugadores", {})
        if jugador in config:
            config[jugador]["activo"] = active
            self.storage.save("config_jugadores", config)

    def load_order(self, user_id: str = None) -> list:
        return self.storage.load("orden_jugadores", [], user_id)

    def save_order(self, order: list, user_id: str = None):
        self.storage.save("orden_jugadores", order, user_id)

class EquipmentRepository:
    def __init__(self, storage: Storage):
        self.storage = storage

    def load(self, user_id: str = None) -> dict:
        return self.storage.load("equipamiento", {}, user_id)

    def save(self, data: dict, user_id: str = None):
        self.storage.save("equipamiento", data, user_id)

from inventory_service import InventoryService
from player_service import PlayerService

# Instances
user_repo = UserRepository(storage)
player_repo = PlayerRepository(storage)
equip_repo = EquipmentRepository(storage)

# Services (SOLID: Service Layer)
inventory_service = InventoryService(storage, player_repo, equip_repo)
player_service = PlayerService(player_repo)

# ============================================================
# 3. FACADE / COMPATIBILITY
# ============================================================

def get_current_user_id():
    return st.session_state.get("usuario")

def check_role(required_role):
    if "usuario" not in st.session_state:
        st.error("Debes iniciar sesión.")
        st.stop()
    user_role = st.session_state.get("user_data", {}).get("role")
    if user_role != required_role:
        st.error(f"Acceso denegado. Se requiere rol: {required_role}")
        st.stop()

def load_config_jugadores():
    return player_repo.load_config(get_current_user_id())

def save_config_jugadores(config):
    # This function is used in pages/1_Jugadores.py for overrides
    uid = get_current_user_id()
    if not uid: return
    
    # We only want to save the fields that the user modified in the UI
    # In the current UI (1_Jugadores.py), the 'config' object passed is the MERGED one.
    # We should calculate what to store in overrides.
    base_config = player_repo.storage.load("config_jugadores", {})
    overrides = {}
    
    for j, merged_conf in config.items():
        if j in base_config:
            # Detect changes against base
            user_changes = {}
            for key in ["Equipar", "tipos_recomendados", "stats_recomendados", "candidatos_4"]:
                if key in merged_conf and merged_conf[key] != base_config[j].get(key):
                    user_changes[key] = merged_conf[key]
            if user_changes:
                overrides[j] = user_changes
    
    player_repo.storage.save("config_jugadores_overrides", overrides, uid)

def save_json(name, data):
    # This is used in admin pages to save global data
    storage.save(name, data)

def restore_player_config(jugador):
    uid = get_current_user_id()
    if uid:
        player_repo.reset_user_override(uid, jugador)

def update_player_active_status(jugador, active):
    # Global admin update
    player_repo.update_base_active_status(jugador, active)

def load_orden_jugadores():
    return player_repo.load_order(get_current_user_id())

def save_orden_jugadores(orden):
    player_repo.save_order(orden, get_current_user_id())

def load_equipamiento():
    return equip_repo.load(get_current_user_id())

def save_equipamiento(data):
    equip_repo.save(data, get_current_user_id())

def equipar_pieza(jugador, slot, pieza_id):
    uid = get_current_user_id()
    data = equip_repo.load(uid)
    if jugador not in data: data[jugador] = {}
    data[jugador][str(slot)] = pieza_id
    equip_repo.save(data, uid)

def load_all_into_session():
    uid = get_current_user_id()
    config = load_config_jugadores()
    st.session_state["config_jugadores"] = config
    st.session_state["jugadores"] = list(config.keys())
    st.session_state["orden_jugadores"] = [j for j in player_repo.load_order(uid) if j in config]
    st.session_state["equipamiento"] = equip_repo.load(uid)
    st.session_state["inventarios"] = storage.load("inventarios", {str(i): [] for i in range(1, 7)}, uid)
    
    # Global data
    st.session_state["tipos"] = storage.load("tipos", [])
    st.session_state["stats"] = storage.load("stats", [])
    st.session_state["escuelas"] = storage.load("Escuelas", [])
    st.session_state["rareza"] = storage.load("Rarezas", [])
    st.session_state["roles"] = storage.load("Rol", [])
    st.session_state["equipos_entrenamiento"] = storage.load("equipos_entrenamiento", {})

def authenticate(username, password):
    return user_repo.authenticate(username, password)

def register_user(username, password, role="standard"):
    return user_repo.create(username, password, role)

def get_all_users():
    return user_repo.get_all()

def update_user_role(username, new_role):
    return user_repo.update_role(username, new_role)

def delete_user(username):
    return user_repo.delete_user(username)

def resetear_equipamiento():
    equip_repo.save({}, get_current_user_id())

def piezas_bloqueadas():
    data = equip_repo.load(get_current_user_id())
    bloqueadas = set()
    for slots in data.values():
        for pid in slots.values(): bloqueadas.add(pid)
    return bloqueadas

def rename_jugador(old, new):
    # Global admin action
    check_role("admin")
    config = storage.load("config_jugadores", {})
    order = storage.load("orden_jugadores", [])
    equipamiento = storage.load("equipamiento", {}) # Base equipamiento if any

    if old not in config: return False, f"El jugador '{old}' no existe."
    if new in config: return False, f"El jugador '{new}' ya existe."

    config[new] = config.pop(old)
    order = [new if j == old else j for j in order]
    
    if old in equipamiento: equipamiento[new] = equipamiento.pop(old)

    old_img = os.path.join(IMG_DIR, f"{old}.png")
    new_img = os.path.join(IMG_DIR, f"{new}.png")
    if os.path.exists(old_img):
        os.rename(old_img, new_img)
        config[new]["imagen"] = f"{new}.png"

    storage.save("config_jugadores", config)
    storage.save("orden_jugadores", order)
    storage.save("equipamiento", equipamiento)
    return True, f"Jugador renombrado de '{old}' a '{new}'."
