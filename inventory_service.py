import pandas as pd
from optimizer import (
    mainstat_por_defecto,
    formatear_stat,
    calcular_reservas_por_jugador,
    clasificar_potencial
)

class InventoryService:
    """
    Handles business logic for inventory management, decoupling it from the UI.
    """
    def __init__(self, storage, config_repo, equip_repo):
        self.storage = storage
        self.config_repo = config_repo
        self.equip_repo = equip_repo

    def get_inventory(self, slot: str, user_id: str = None):
        return self.storage.load("inventarios", {str(i): [] for i in range(1, 7)}, user_id).get(slot, [])

    def save_inventory(self, inventarios, user_id: str = None):
        self.storage.save("inventarios", inventarios, user_id)

    def update_piece(self, slot, piece_id, updated_data, user_id: str = None):
        inventarios = self.storage.load("inventarios", {str(i): [] for i in range(1, 7)}, user_id)
        piezas = inventarios.get(slot, [])
        for p in piezas:
            if str(p["ID"]) == str(piece_id):
                p.update(updated_data)
                break
        self.save_inventory(inventarios, user_id)

    def delete_piece(self, slot, piece_id, user_id: str = None):
        inventarios = self.storage.load("inventarios", {str(i): [] for i in range(1, 7)}, user_id)
        inventarios[slot] = [
            p for p in inventarios.get(slot, []) if str(p["ID"]) != str(piece_id)
        ]
        self.save_inventory(inventarios, user_id)

    def delete_pieces(self, deletions: list, user_id: str = None):
        """
        Deletions is a list of tuples (slot, piece_id)
        """
        inventarios = self.storage.load("inventarios", {str(i): [] for i in range(1, 7)}, user_id)
        for slot, piece_id in deletions:
            if slot in inventarios:
                inventarios[slot] = [
                    p for p in inventarios[slot] if str(p["ID"]) != str(piece_id)
                ]
        self.save_inventory(inventarios, user_id)

    def add_piece(self, slot, piece_data, user_id: str = None):
        inventarios = self.storage.load("inventarios", {str(i): [] for i in range(1, 7)}, user_id)
        if slot not in inventarios: inventarios[slot] = []
        inventarios[slot].append(piece_data)
        self.save_inventory(inventarios, user_id)

    def prepare_inventory_dataframe(self, piezas, slot=None, equipamiento=None, reservations=None, config=None, inventarios=None):
        columns = ["ID", "Tipo", "Calidad", "Main Stat", "Substat1", "Substat2", "Substat3", "Substat4"]
        if not piezas:
            return pd.DataFrame(columns=columns)
        
        piece_lookup = {str(p.get("ID", "")).replace(".0", ""): p for p in piezas}
            
        df = pd.DataFrame(piezas)
        # Ensure essential columns exist for sorting and display
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        df = df.fillna("")
        
        df["Main Stat"] = df.apply(
            lambda row: formatear_stat(row.get("Main Stat", ""), row.get("Tipo_Mejora_Main", "")),
            axis=1
        )
        for i in range(1, 5):
            col = f"Substat{i}"
            tm_col = f"Tipo_Mejora_Sub{i}"
            df[col] = df.apply(
                lambda row: formatear_stat(row.get(col, ""), row.get(tm_col, "")),
                axis=1
            )
        
        if slot and equipamiento:
            df["Equipado"] = df["ID"].astype(str).apply(
                lambda piece_id: self._get_player_with_piece_equipped(piece_id, slot, equipamiento)
            )
        
        if slot and reservations and config and inventarios:
            df["Evaluación"] = df["ID"].astype(str).apply(
                lambda piece_id: self._get_evaluation_for_piece(piece_id, piece_lookup, slot, equipamiento, reservations, config, inventarios)
            )
            df["Potencial"] = df["ID"].astype(str).apply(
                lambda piece_id: self._check_if_potencial(piece_id, piece_lookup, slot, reservations, config, inventarios, equipamiento)
            )
        
        cols_to_drop = ["Tipo_Mejora_Main"] + [f"Tipo_Mejora_Sub1", "Tipo_Mejora_Sub2", "Tipo_Mejora_Sub3", "Tipo_Mejora_Sub4"]
        return df.drop(columns=cols_to_drop, errors="ignore")
    
    def _get_player_with_piece_equipped(self, piece_id, slot, equipamiento):
        for jugador, slots_equipados in equipamiento.items():
            if str(slots_equipados.get(slot, "")).replace(".0", "") == str(piece_id).replace(".0", ""):
                return jugador
        return ""
    
    def _get_evaluation_for_piece(self, piece_id, piece_lookup, slot, equipamiento, reservations, config, inventarios):
        from optimizer import puntuar_pieza, evaluar_pieza_para_jugador_en_slot
        
        piece_id_normalized = str(piece_id).replace(".0", "")
        pieza = piece_lookup.get(piece_id_normalized)
        
        if not pieza:
            return ""
        
        result = clasificar_potencial(pieza, slot, reservations, config, inventarios)
        evaluaciones = result.get("evaluaciones", {})
        
        slot_str = str(slot)
        tipo_p = pieza.get("Tipo", "")
        
        if not evaluaciones:
            evaluaciones = {}
            for jugador, cfg in config.items():
                if not cfg.get("activo", False):
                    continue
                
                if tipo_p not in cfg["builds"]["Base"]["tipos_recomendados"]:
                    continue
                
                if slot_str not in cfg["slots_activos"]:
                    continue
                
                stats_rec = cfg["builds"]["Base"]["stats_recomendados"]["stats"]
                puntos_rec = cfg["builds"]["Base"]["stats_recomendados"]["puntos"]
                
                puntaje_p = puntuar_pieza(pieza, stats_rec, puntos_rec)
                
                eval_pieza = evaluar_pieza_para_jugador_en_slot(
                    pieza=pieza,
                    jugador=jugador,
                    tipo=tipo_p,
                    slot=slot_str,
                    inventarios=inventarios,
                    stats_recomendados=cfg["builds"]["Base"]["stats_recomendados"]
                )
                calidad = eval_pieza["calidad"]
                
                evaluaciones[jugador] = {
                    "puntaje": puntaje_p,
                    "calidad": calidad
                }
        
        if not evaluaciones:
            return ""
        
        jugador_target = None
        
        jugador_equipado = self._get_player_with_piece_equipped(piece_id, slot, equipamiento)
        if jugador_equipado and jugador_equipado in evaluaciones:
            jugador_target = jugador_equipado
        else:
            mejor_puntaje = -1
            for jugador, eval_data in evaluaciones.items():
                puntaje = eval_data.get("puntaje", 0)
                if puntaje > mejor_puntaje:
                    mejor_puntaje = puntaje
                    jugador_target = jugador
        
        if jugador_target:
            return evaluaciones[jugador_target].get("calidad", "")
        
        return ""
    
    def _check_if_potencial(self, piece_id, piece_lookup, slot, reservations, config, inventarios, equipamiento=None):
        from optimizer import puntuar_pieza, simular_mejora_substats, evaluar_pieza_para_jugador_en_slot
        
        piece_id_normalized = str(piece_id).replace(".0", "")
        pieza = piece_lookup.get(piece_id_normalized)
        
        if not pieza:
            return ""
        
        slot_str = str(slot)
        tipo_p = pieza.get("Tipo", "")
        
        result = clasificar_potencial(pieza, slot, reservations, config, inventarios)
        evaluaciones = result.get("evaluaciones", {})
        
        if not evaluaciones:
            evaluaciones = {}
            for jugador, cfg in config.items():
                if not cfg.get("activo", False):
                    continue
                
                if tipo_p not in cfg["builds"]["Base"]["tipos_recomendados"]:
                    continue
                
                if slot_str not in cfg["slots_activos"]:
                    continue
                
                stats_rec = cfg["builds"]["Base"]["stats_recomendados"]["stats"]
                puntos_rec = cfg["builds"]["Base"]["stats_recomendados"]["puntos"]
                
                num_substats_actuales = sum(1 for i in range(1, 5) if pieza.get(f"Substat{i}", ""))
                
                puntaje_simulada = None
                calidad_simulada = None
                
                if num_substats_actuales < 4:
                    pieza_simulada = simular_mejora_substats(pieza, stats_rec, puntos_rec)
                    puntaje_simulada = puntuar_pieza(pieza_simulada, stats_rec, puntos_rec)
                    
                    eval_simulada = evaluar_pieza_para_jugador_en_slot(
                        pieza=pieza_simulada,
                        jugador=jugador,
                        tipo=tipo_p,
                        slot=slot_str,
                        inventarios=inventarios,
                        stats_recomendados=cfg["builds"]["Base"]["stats_recomendados"]
                    )
                    calidad_simulada = eval_simulada["calidad"]
                
                evaluaciones[jugador] = {
                    "calidad_simulada": calidad_simulada,
                    "puntaje_simulada": puntaje_simulada
                }
        
        jugador_target = None
        
        if equipamiento:
            jugador_equipado = self._get_player_with_piece_equipped(piece_id, slot, equipamiento)
            if jugador_equipado and jugador_equipado in evaluaciones:
                jugador_target = jugador_equipado
        
        if not jugador_target:
            mejor_puntaje_simulada = -1
            for jugador, eval_data in evaluaciones.items():
                puntaje_sim = eval_data.get("puntaje_simulada")
                if puntaje_sim is not None and puntaje_sim > mejor_puntaje_simulada:
                    mejor_puntaje_simulada = puntaje_sim
                    jugador_target = jugador
        
        if jugador_target:
            calidad_simulada = evaluaciones[jugador_target].get("calidad_simulada")
            return calidad_simulada if calidad_simulada else ""
        
        return ""

    def find_piece_by_id(self, inventarios, piece_id, slot):
        piezas_slot = inventarios.get(slot, [])
        for p in piezas_slot:
            if str(p["ID"]) == str(piece_id):
                return p
        return None

    def get_active_reservations(self, inventarios, config, session_state):
        stats_rec = {
            j: {
                "stats": config[j]["builds"]["Base"]["stats_recomendados"]["stats"],
                "puntos": dict(zip(config[j]["builds"]["Base"]["stats_recomendados"]["stats"], config[j]["builds"]["Base"]["stats_recomendados"]["puntos"]))
            } for j in config
        }
        
        tipos_rec = {j: config[j]["builds"]["Base"]["tipos_recomendados"] for j in config}
        
        return calcular_reservas_por_jugador(
            inventarios=inventarios,
            config_jugadores=config,
            stats_recomendados=stats_rec,
            tipos_recomendados=tipos_rec,
            piezas_equipadas=session_state.get("equipamiento", {}),
            lista_jugadores_prioridad=session_state.get("orden_jugadores", []),
            rareza_lista=session_state.get("rareza", []),
            modo="activo"
        )

    def get_disposable_pieces(self, slot, inventarios, config, pieces_equipped, reservations):
        piezas = inventarios.get(slot, [])
        
        # Build reserved set for fast lookup
        ids_reservados = set()
        for j_res in reservations.values():
            if slot in j_res:
                for info in j_res[slot].values():
                    if info.get("id") is not None:
                        ids_reservados.add(str(info["id"]).replace(".0", ""))

        # Build equipped set
        ids_equipados = set()
        for s_j in pieces_equipped.values():
            pid = s_j.get(slot)
            if pid: ids_equipados.add(str(pid).replace(".0", ""))

        desechables = []
        for p in piezas:
            idp = str(p["ID"]).replace(".0", "")
            if idp in ids_equipados or idp in ids_reservados:
                continue

            res = clasificar_potencial(p, slot, reservations, config, inventarios)
            estado = res["estado"]
            
            if estado == "mejora":
                motivo = "No reservada, pero mejora a alguna actual."
            if estado == "potencial":
                motivo = "No reservada, pero tiene potencial para ser mejor que la actual."
            elif estado == "warning":
                motivo = "Calidad Buena, sin hueco en reserva."
            elif estado == "rellena_hueco":
                motivo = "Cubre necesidad (faltan piezas)."
            elif estado == "sin_uso":
                motivo = "Ningún jugador usa este tipo."
            else:
                motivo = "Calidad Aceptable/Mala y sin hueco."

            p_copy = p.copy()
            p_copy["Motivo"] = motivo
            p_copy["Seleccionar"] = False
            p_copy["Slot"] = slot
            
            # Formatear stats para mostrar en la tabla de desechables
            p_copy["Main Stat"] = formatear_stat(p.get("Main Stat", ""), p.get("Tipo_Mejora_Main", ""))
            p_copy["Substat1"] = formatear_stat(p.get("Substat1", ""), p.get("Tipo_Mejora_Sub1", ""))
            p_copy["Substat2"] = formatear_stat(p.get("Substat2", ""), p.get("Tipo_Mejora_Sub2", ""))
            p_copy["Substat3"] = formatear_stat(p.get("Substat3", ""), p.get("Tipo_Mejora_Sub3", ""))
            p_copy["Substat4"] = formatear_stat(p.get("Substat4", ""), p.get("Tipo_Mejora_Sub4", ""))
            
            # Quitar columnas de tipo de mejora (ya integradas en el formato)
            for tm_col in ["Tipo_Mejora_Main", "Tipo_Mejora_Sub1", "Tipo_Mejora_Sub2", "Tipo_Mejora_Sub3", "Tipo_Mejora_Sub4"]:
                p_copy.pop(tm_col, None)

            desechables.append(p_copy)
            
        return desechables
