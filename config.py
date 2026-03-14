class GameConfig:
    # Mappings for equipment slots and types
    MAIN_STAT_FIJO_POR_SLOT = {
        "3": "Saque",
        "5": "Recepción"
    }

    MAIN_STAT_FIJO_POR_TIPO_SLOT1 = {
        "Ataque veloz": "Ataque rápido",
        "Bloque preciso": "Bloqueo",
        "Finta de colocador": "Colocación",
        "Guardia contundente": "Bloqueo",
        "Incremento de poder": "Ataque poderoso",
        "Movimiento de bloqueo": "Bloqueo",
        "Opt. de estado": "Ataque poderoso",
        "Opt. de percepción": "Ataque rápido",
        "Pase preciso": "Colocación",
        "Poder vibrante": "Ataque poderoso",
        "Potenciación de la moral": "Ataque poderoso",
        "Recepción de asistencia": "Recepción",
        "Recepción suprema": "Recepción",
        "Saque preciso": "Colocación",
        "Sentido agudo": "Ataque rápido"
    }

    # Stats that don't have a percentage version or are unique
    STATS_SOLO_UNA_VEZ = {
        "Percepción", "Fuerza", "Técnica ofensiva",
        "Técnica defensiva", "Reflejos", "Espíritu"
    }

    # Affinity lists for slots 2, 4, 6
    LISTA_SLOT2 = [
        "Saque", "Ataque rápido", "Ataque poderoso",
        "Colocación", "Percepción", "Fuerza"
    ]

    LISTA_SLOT4 = [
        "Recepción", "Recuperación", "Bloqueo",
        "Reflejos", "Espíritu"
    ]

    LISTA_SLOT6 = [
        "Ataque poderoso", "Ataque rápido", "Bloqueo", "Colocación",
        "Recepción", "Recuperación", "Saque",
        "Técnica defensiva", "Técnica ofensiva"
    ]
