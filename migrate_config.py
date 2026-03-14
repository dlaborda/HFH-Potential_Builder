import json

file_path = r'c:\Users\David\Documents\Haikyuu Fly High\data\config_jugadores.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for player_name, player_data in data.items():
    if 'tipos_recomendados' in player_data or 'stats_recomendados' in player_data:
        builds = {
            "Base": {
                "tipos_recomendados": player_data.get('tipos_recomendados', []),
                "stats_recomendados": player_data.get('stats_recomendados', {})
            }
        }
        player_data['builds'] = builds
        
        # Remove old keys
        if 'tipos_recomendados' in player_data:
            del player_data['tipos_recomendados']
        if 'stats_recomendados' in player_data:
            del player_data['stats_recomendados']

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Migration completed successfully.")
