import os

class PlayerService:
    """
    Service for managing player-related business logic (SRP).
    """
    def __init__(self, repo):
        self.repo = repo
        self.img_dir = "data/imagenes_jugadores"

    def get_filtered_players(self, config, escuela="Todas", rareza="Todas", rol="Todos"):
        filtered = []
        for j, data in config.items():
            if not data.get("activo", True):
                continue
            if escuela != "Todas" and data.get("escuela") != escuela:
                continue
            if rareza != "Todas" and data.get("rareza") != rareza:
                continue
            if rol != "Todos" and data.get("rol") != rol:
                continue
            filtered.append(j)
        return filtered

    def sort_players_by_rarity(self, player_list, config, rareza_list):
        rareza_index = {r: i for i, r in enumerate(reversed(rareza_list))}
        player_list.sort(
            key=lambda j: (
                rareza_index.get(config[j].get("rareza", ""), 999),
                config[j].get("escuela", "").lower(),
                j.lower()
            )
        )
        return player_list

    def get_player_image_path(self, jugador_name, config):
        imagen = config.get(jugador_name, {}).get("imagen", "default.png")
        ruta = os.path.join(self.img_dir, imagen)
        if not os.path.exists(ruta):
            ruta = os.path.join(self.img_dir, "default.png")
        return ruta

    def save_overrides(self, config, user_id):
        """
        Calculates and saves only the differences between user config and base config.
        """
        if not user_id: return
        
        base_config = self.repo.storage.load("config_jugadores", {})
        overrides = {}
        
        keys_to_track = ["Equipar", "tipos_recomendados", "stats_recomendados", "candidatos_4"]
        
        for j, merged_conf in config.items():
            if j in base_config:
                user_changes = {
                    k: merged_conf[k] for k in keys_to_track 
                    if k in merged_conf and merged_conf[k] != base_config[j].get(k)
                }
                if user_changes:
                    overrides[j] = user_changes
        
        self.repo.storage.save("config_jugadores_overrides", overrides, user_id)
