import pandas as pd

EXCEL_PATH = "Potenciales_Haikyuu_v3.xlsx"

def load_sets():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Set recomendado")
    df.columns = ["Jugador", "TipoSlot", "Prioridad"]
    return df

def load_stats():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Stats recomendados")
    df.columns = ["Jugador", "Puntos", "Substat"]
    return df

def load_inventories():
    inv1 = pd.read_excel(EXCEL_PATH, sheet_name="Inventario1")
    inv2 = pd.read_excel(EXCEL_PATH, sheet_name="Inventario2")

    # Normalizar nombres de columnas
    inv1.columns = [c.strip().replace(" ", "_") for c in inv1.columns]
    inv2.columns = [c.strip().replace(" ", "_") for c in inv2.columns]

    return inv1, inv2


# --------------------------
# Lógica de puntuación
# --------------------------

def score_item_for_player(item, set_df, stats_df):
    score = 0

    # Ponderación por tipo de slot
    tipos_jugador = set_df.set_index("TipoSlot")["Prioridad"].to_dict()
    tipo_item = item["Tipo"]
    if tipo_item in tipos_jugador:
        score += (5 - tipos_jugador[tipo_item]) * 10  # prioridad 1 = más puntos

    # Ponderación por substats
    substats_jugador = stats_df.set_index("Substat")["Puntos"].to_dict()
    for col in ["Substat1", "Substat2", "Substat3", "Substat4"]:
        sub = item.get(col)
        if sub in substats_jugador:
            score += substats_jugador[sub]

    return score


def recommend_for_player(jugador, sets, stats, inventory, top_n=10):
    set_j = sets[sets["Jugador"] == jugador]
    stats_j = stats[stats["Jugador"] == jugador]

    inv_copy = inventory.copy()
    scores = []
    for _, row in inv_copy.iterrows():
        scores.append(score_item_for_player(row, set_j, stats_j))
    inv_copy["Score"] = scores

    inv_copy = inv_copy.sort_values("Score", ascending=False)
    return inv_copy.head(top_n)
    
    import json
import pandas as pd
import os

EQUIP_FILE = "equipado.json"

def load_equipped():
    if not os.path.exists(EQUIP_FILE):
        return []
    with open(EQUIP_FILE, "r") as f:
        return json.load(f)

def save_equipped(data):
    with open(EQUIP_FILE, "w") as f:
        json.dump(data, f, indent=4)

def filter_available(inventory, equipped):
    equipped_ids = {item["ID"] for item in equipped}
    return inventory[~inventory["ID"].isin(equipped_ids)]
