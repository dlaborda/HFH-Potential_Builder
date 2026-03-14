---
description: Repository Information Overview
alwaysApply: true
---

# Haikyuu Fly High Information

## Summary
**Haikyuu Fly High** is a multi-user Streamlit-based optimization tool for the mobile game of the same name. It enables users to manage player stats, track equipment inventory ("potenciales"), and calculate optimal equipment configurations using a custom optimization engine. The application follows **SOLID principles**, featuring a repository pattern for data persistence and a role-based access control system (Admin vs. Standard).

## Structure
- **Root**: Contains the main entry point (`Home.py`), core business logic (`optimizer.py`), data persistence layer (`data_manager.py`), game configuration (`config.py`), and ETL processes (`etl.py`).
- **views/**: Contains individual page modules loaded via `st.navigation`. Standard views include player management, inventory, and optimization. Admin-only views handle global game settings and user management.
- **data/**: Central data store.
    - `user_data/`: Isolated directories per user containing personal inventory, equipment assignments, and player configuration overrides.
    - Root JSON files: Global game data (stats, types, rarities, roles) and encrypted user credentials.
- **backup/**: Legacy or point-in-time snapshots of core modules.
- **Datos originales/**: Source Excel and CSV files for data initialization.

## Language & Runtime
**Language**: Python  
**Version**: 3.12 (as indicated by pycache and venv)  
**Framework**: Streamlit  
**Package Manager**: Conda / Anaconda (referenced in `ini.bat`)

## Dependencies
**Main Dependencies**:
- `streamlit`: UI framework and navigation.
- `pandas`: Data manipulation for players and inventory.
- `numpy`: Mathematical operations for the optimization engine.
- `openpyxl`: Excel processing for ETL.
- `hashlib`: SHA-256 password encryption.

## Build & Installation
The project is a script-based application and does not require a formal build process.

```bash
# To start the application (Windows)
./ini.bat
```

The `ini.bat` script handles environment activation and launches the Streamlit server:
```bash
streamlit run Home.py
```

## Main Files & Resources
- **Entry Point**: `Home.py` (Handles session hydration, auth routing, and navigation).
- **Data Manager**: `data_manager.py` (Implements `JSONStorage` and repository patterns for user-isolated data).
- **Optimizer**: `optimizer.py` (The core scoring engine for calculating equipment efficiency).
- **Configuration**: `config.py` (Hardcoded game-specific stat mappings and slot rules).
- **User Management**: `views/9_Gestion_de_Usuarios.py` (Admin tool for role updates and user deletion).

## Testing & Validation
- **Testing Framework**: No formal unit testing framework (e.g., pytest) is implemented.
- **Validation**: Business logic validation is integrated into `optimizer.py` and exposed via the `5_Validar.py` view to ensure equipment configurations meet game requirements.

## Multi-User Data Isolation
The application uses a specific directory structure to ensure data privacy:
- **Global Config**: `data/*.json`
- **User Isolated**: `data/user_data/{username}/`
    - `inventarios.json`
    - `equipamiento.json`
    - `orden_jugadores.json`
    - `config_jugadores_overrides.json` (Stores user-specific modifications to global player stats).
