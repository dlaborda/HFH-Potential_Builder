import pandas as pd
import streamlit as st
from itertools import combinations
import numpy as np

# ---------------------------------------------------------
# 1. Evaluación de Potenciales
# ---------------------------------------------------------
# 1.1 Puntuar un potencial para un jugador
def puntuar_pieza(pieza, stats_rec, puntos_rec):
    """
    Calcula la puntuación de una pieza para un jugador dado:

    - Solo tiene sentido llamarla si el Tipo de la pieza es compatible
      con los tipos recomendados de ese jugador (esto se filtra fuera).
    - Suma de:
        puntos_rec[stat] × peso_main/sub × peso_porcentaje/plano
    - Multiplicador final ×1.3 si la pieza es Legendario.
    """

    # Convertir puntos_rec a dict si viene como lista
    if isinstance(puntos_rec, list):
        puntos_rec = {stat: puntos_rec[i] for i, stat in enumerate(stats_rec)}

    puntaje_base = 0

    # Multiplicador por calidad
    calidad = pieza.get("Calidad", "")
    mult_calidad = 1.3 if calidad == "Legendario" else 1.0

    # -------------------------
    # MAIN STAT
    # -------------------------
    main = pieza.get("Main Stat", "") or ""
    tipo_main = pieza.get("Tipo_Mejora_Main") or ""
    peso_main = 5  # siempre 5 para el Main
    peso_tipo_main = 2 if tipo_main == "Porcentaje" else 1

    if main in stats_rec:
        base = puntos_rec[main]
        aporte = base * peso_main * peso_tipo_main
        puntaje_base += aporte

    # -------------------------
    # SUBSTATS
    # -------------------------
    for i in range(1, 5):
        sub = pieza.get(f"Substat{i}", "") or ""
        tipo_sub = pieza.get(f"Tipo_Mejora_Sub{i}") or ""
        peso_sub = 1  # substats peso base 1
        peso_tipo_sub = 2 if tipo_sub == "Porcentaje" else 1

        if sub in stats_rec:
            base = puntos_rec[sub]
            aporte = base * peso_sub * peso_tipo_sub
            puntaje_base += aporte

    # Multiplicador final por calidad
    puntaje_final = puntaje_base * mult_calidad

    return puntaje_final

# 1.2 Calcula la afinidad (la cantidad de puntos mínimos que puede obtener con las opciones de MainStat de un slot.
def calcular_afinidad(slot_str, main_stat, stats_rec, puntos_rec):
    """
    Slots 1,3,5: umbral = afinidad(MainStat) * 10
    Slots 2,4,6: casuísticas especiales según listas de afinidad
    """
    flag_main = False

    # ---------------------------------------------------------
    # SLOTS 1, 3, 5 → lógica original (NO SE TOCA)
    # ---------------------------------------------------------
    if slot_str in ["1", "3", "5"]:
        if main_stat in stats_rec:
            afinidad = puntos_rec.get(main_stat, 0)
            flag_main = True
        else:
            afinidad = 0

    # ---------------------------------------------------------
    # SLOTS 2, 4, 6 → NUEVAS CASUÍSTICAS
    # ---------------------------------------------------------

    # Listas especiales
    lista_slot2 = [
        "Saque", "Ataque rápido", "Ataque poderoso",
        "Colocación", "Percepción", "Fuerza"
    ]

    lista_slot4 = [
        "Recepción", "Recuperación", "Bloqueo",
        "Reflejos", "Espíritu"
    ]

    lista_slot6 = [
        "Ataque poderoso", "Ataque rápido", "Bloqueo", "Colocación",
        "Recepción", "Recuperación", "Saque",
        "Técnica defensiva", "Técnica ofensiva"
    ]

    # ---------------------------------------------------------
    # SLOT 2
    # ---------------------------------------------------------
    if slot_str == "2":
        candidatos = [s for s in stats_rec if s in lista_slot2]
        if candidatos:
            mejor = max(candidatos, key=lambda s: puntos_rec.get(s, 0))
            afinidad = puntos_rec[mejor]
            flag_main = True
        else:
            afinidad = 0

    # ---------------------------------------------------------
    # SLOT 4
    # ---------------------------------------------------------
    if slot_str == "4":
        candidatos = [s for s in stats_rec if s in lista_slot4]
        if candidatos:
            mejor = max(candidatos, key=lambda s: puntos_rec.get(s, 0))
            afinidad = puntos_rec[mejor]
            flag_main = True
        else:
            afinidad = 0

    # ---------------------------------------------------------
    # SLOT 6
    # ---------------------------------------------------------
    if slot_str == "6":
        candidatos = [s for s in stats_rec if s in lista_slot6]
        if candidatos:
            mejor = max(candidatos, key=lambda s: puntos_rec.get(s, 0))
            afinidad = puntos_rec[mejor]
            flag_main = True
        else:
            afinidad = 0

    # ---------------------------------------------------------
    # Se devuelve el umbral mínimo, que debería ser al menos de una pieza legendaria
    # ---------------------------------------------------------
    return flag_main, afinidad

# 1.3 Calcula el umbral mínimo de un jugador para un slot con base en su afinidad.
def umbral_minimo_por_slot_y_afinidad(slot, main_stat, stats_rec, puntos_rec):
    """
    Slots 1,3,5: umbral = afinidad(MainStat) * 10
    Slots 2,4,6: casuísticas especiales según listas de afinidad
    """

    slot_str = str(slot)
    main_flag = False
    afinidad = 0
    
    # ---------------------------------------------------------
    # NORMALIZAR puntos_rec → SIEMPRE DICCIONARIO 
    # --------------------------------------------------------- 
    if isinstance(puntos_rec, list): 
        puntos_rec = {stat: puntos_rec[i] for i, stat in enumerate(stats_rec)}
    
    mejor_stat = max(stats_rec, key=lambda s: puntos_rec.get(s, 0))
    puntos_mejor_stat = puntos_rec[mejor_stat]
    
    main_flag, afinidad = calcular_afinidad(slot_str, main_stat, stats_rec, puntos_rec)
    
    if slot_str in ["1", "3", "5"]:
        if main_flag == True:
            afinidad *= 5  # 5 (main) × 1 (Todos los valores Main son Planos)
        else:
            afinidad * 2
        if afinidad < 6: # Si no tiene afinidad, o esta es muy débil, se inicializa en 6.
            afinidad += (puntos_mejor_stat * 2) # Afinidad de su MainStat + su mejor substat porcentual

    else:
        if main_flag == True:
            afinidad *= 10  # 5 (main) × 2 (Todos los valores Main son Porcentuales)
        else:
            afinidad * 2
        if afinidad < 6: # Si no tiene afinidad, o esta es muy débil, se inicializa en 6.
            afinidad += (puntos_mejor_stat * 2) # Afinidad de su MainStat + su mejor substat porcentual

    # ---------------------------------------------------------
    # Se devuelve el umbral mínimo, que debería ser al menos de una pieza legendaria
    # ---------------------------------------------------------
    return afinidad * 1.3

# 1.4 Calcula la puntuación que tendría un Potencial Perfecto para un jugador en determinado Slot.
def calcular_potencial_perfecto(tipo,slot,inventarios,stats_rec,puntos_rec,jugador):
    """
    Umbral aspiracional teórico para un jugador, tipo y slot.

    Definición:
    - Main:
        * Su aporte base viene de umbral_minimo_por_slot_y_afinidad,
          que ya incorpora afinidad jugador–tipo–slot.
        * Para slots aleatorios, esa función devuelve 30, que equivale
          a un main perfecto: 5 (peso main) × 3 (puntos máx) × 2 (Porcentaje).
    - Substats:
        * 4 substats
        * Cada uno con el valor máximo de puntos_rec del jugador
        * Todos Porcentuales → ×2
        * Peso base de substat = 1
    - Calidad:
        * Legendario → ×1.3
    """
    slot = str(slot)

    # Convertir puntos_rec a dict si viene como lista
    if isinstance(puntos_rec, list):
        puntos_rec = {stat: puntos_rec[i] for i, stat in enumerate(stats_rec)}

    # ---------------------------------------------------------
    # 1. Aporte ideal del MAIN STAT (ya incluye peso y tipo)
    # ---------------------------------------------------------
    # Esta función ya sabe:
    # - Si el slot tiene main fijo → afinidad real (puede ser 0 si no recomendado)
    # - Si el slot es aleatorio → 30 en tu nueva versión
    main_stat_fijo_por_slot = {
        "3": "Saque",
        "5": "Recepción"
    }
    main_stat_fijo_por_tipo_slot1 = {
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
    
    if slot == "1":
        main_stat = main_stat_fijo_por_tipo_slot1[tipo]
    elif slot in ["3","5"]:
        main_stat = main_stat_fijo_por_slot[slot]
    else:
        main_stat = ""
    
    main_flag, aporte_main_base = calcular_afinidad(
        slot,
        main_stat,
        stats_rec,
        puntos_rec
    )
    
    #El valor del MainStat se multiplica por 5 siempre y por 2 en los Slots que son porcentuales.
    if slot in ["1","3","5"] :
        aporte_main_base *= 5
    else:
        aporte_main_base *= 10

    
    # ---------------------------------------------------------
    # 2. Aporte ideal de los 4 SUBSTATS (versión realista)
    # ---------------------------------------------------------
    
    stats_solo_una_vez = {
        "Percepción", "Fuerza", "Técnica ofensiva",
        "Técnica defensiva", "Reflejos", "Espíritu"
    }
    
    # Generar lista de posibles substats ideales
    posibles = []
    
    for stat in stats_rec:
        puntos = puntos_rec.get(stat, 0)
    
        # Porcentual siempre permitido
        valor_pct = puntos * 2
        posibles.append(valor_pct)
    
        # Plano solo si NO está en la lista de “solo una vez”
        if stat not in stats_solo_una_vez:
            valor_plano = puntos * 1
            posibles.append(valor_plano)
    
    # Ordenar de mayor a menor
    posibles.sort(reverse=True)
    
    # Tomar los 4 mejores
    mejores_4 = posibles[:4]
    
    # Sumar los puntos de las 4 mejores
    aporte_subs_base = sum(mejores_4)

    # ---------------------------------------------------------
    # 3. Puntaje base ideal en Potencial Legendario
    # ---------------------------------------------------------
    potencial_perfecto = (aporte_main_base + aporte_subs_base) * 1.3
    
    return potencial_perfecto
    

# 1.5 Calcula el umbral aspiracional de un jugador en un slot, es decir, el umbral a partir del cual un Potencial se considera Bueno.
def calcular_umbral_aspiracional(tipo,slot,inventarios,stats_rec,puntos_rec,jugador):

    
    potencial_perfecto = calcular_potencial_perfecto(tipo,slot,inventarios,stats_rec,puntos_rec,jugador)

    # ---------------------------------------------------------
    # 5. Umbral aspiracional = 75% del ideal
    # ---------------------------------------------------------
    umbral = potencial_perfecto * 0.75

    return umbral

# 1.5 Calcula los umbrales aspiracionales de un jugador en un slot, de forma que una pieza se pueda considerar Aceptable, Buena, Excelente o Perfecta.
def calcular_umbrales(tipo,slot,inventarios,stats_rec,puntos_rec,jugador):
    #Se añaden variedad de umbrales, de tal forma que un potencial 
    
    potencial_perfecto = calcular_potencial_perfecto(tipo,slot,inventarios,stats_rec,puntos_rec,jugador)

    umbral_bueno = potencial_perfecto * 0.70
    umbral_excelente = potencial_perfecto * 0.85

    return umbral_bueno, umbral_excelente, potencial_perfecto

# ---------------------------------------------------------
# 1.1. Explicar puntuar pieza (para Validar)
# ---------------------------------------------------------
def explicar_puntuar_pieza(pieza, stats_rec, puntos_rec):
    """
    Devuelve (puntaje_final, filas_para_tabla, tipo_potencial)

    filas: lista de filas [Nivel, Stat, Tipo mejora, Cálculo, Resultado]
    - Main Stat con peso ×5
    - Substats con peso ×1
    - Stats porcentuales ×2 frente a planos
    - Multiplicador final ×1.3 si la pieza es Legendario
    """

    # Convertir puntos_rec a dict si viene como lista
    if isinstance(puntos_rec, list):
        puntos_rec = {stat: puntos_rec[i] for i, stat in enumerate(stats_rec)}

    filas = []
    puntaje_base = 0

    tipo_pot = pieza.get("Tipo", "(sin tipo)")
    calidad = pieza.get("Calidad", "")
    mult_calidad = 1.3 if calidad == "Legendario" else 1.0

    # -------------------------
    # MAIN STAT
    # -------------------------
    main = pieza.get("Main Stat", "") or ""
    tipo_main = pieza.get("Tipo_Mejora_Main") or ""
    peso_main = 5
    peso_tipo_main = 2 if tipo_main == "Porcentaje" else 1

    if main in stats_rec:
        base = puntos_rec[main]
    else:
        base = 0

    aporte_base = base * peso_main * peso_tipo_main
    aporte_final = aporte_base * mult_calidad
    puntaje_base += aporte_base

    filas.append([
        "Main",
        main or "(vacío)",
        tipo_main or "Plano",
        f"{peso_main} × {base} × {peso_tipo_main} × {mult_calidad}",
        round(aporte_final, 2)
    ])

    # -------------------------
    # SUBSTATS
    # -------------------------
    for i in range(1, 5):
        sub = pieza.get(f"Substat{i}", "") or ""
        tipo_sub = pieza.get(f"Tipo_Mejora_Sub{i}") or ""
        peso_sub = 1
        peso_tipo_sub = 2 if tipo_sub == "Porcentaje" else 1

        if sub in stats_rec:
            base = puntos_rec[sub]
        else:
            base = 0

        aporte_base = base * peso_sub * peso_tipo_sub
        aporte_final = aporte_base * mult_calidad
        puntaje_base += aporte_base

        filas.append([
            f"Substat {i}",
            sub or "(vacío)",
            tipo_sub or "Plano",
            f"{peso_sub} × {base} × {peso_tipo_sub} × {mult_calidad}",
            round(aporte_final, 2)
        ])

    puntaje_final = puntaje_base * mult_calidad

    return puntaje_final, filas, tipo_pot

# ---------------------------------------------------------
# 1.2. Explicar puntuar pieza mejor jugador (para validar)
# ---------------------------------------------------------
def explicar_puntaje_mejor_jugador(piece, stats_recomendados, tipos_recomendados):
    """
    Devuelve el jugador que mejor aprovecha la pieza,
    filtrando por jugadores que realmente usan ese tipo de potencial.
    """

    mejor_jugador = None
    mejor_puntaje = -1
    mejor_filas = None

    tipo_pot = piece.get("Tipo", "(sin tipo)")

    for jugador, datos in stats_recomendados.items():
        stats_rec = datos["stats"]
        puntos_rec = datos["puntos"]


        # ❗ FILTRO CRÍTICO: solo jugadores que usan este tipo
        if tipo_pot not in tipos_recomendados.get(jugador, []):
            continue

        puntaje_total, filas, _ = explicar_puntuar_pieza(piece, stats_rec, puntos_rec)

        if puntaje_total > mejor_puntaje:
            mejor_puntaje = puntaje_total
            mejor_jugador = jugador
            mejor_filas = filas

    return {
        "jugador": mejor_jugador,
        "puntaje": mejor_puntaje,
        "filas": mejor_filas,
        "tipo": tipo_pot
    }


# ---------------------------------------------------------
# 3. Mejor pieza por tipo
# ---------------------------------------------------------
def mejor_pieza_por_prioridad(jugador, tipo_objetivo, inventario, stats_rec, puntos_rec, piezas_bloqueadas):

    if isinstance(inventario, list):
        inventario = pd.DataFrame(inventario)

    col_tipo = None
    for c in inventario.columns:
        if "tipo" in c.lower():
            col_tipo = c
            break

    if col_tipo is None:
        raise KeyError(f"No se encontró columna de tipo en el inventario.")

    df_tipo = inventario[inventario[col_tipo] == tipo_objetivo]

    if piezas_bloqueadas:
        df_tipo = df_tipo[~df_tipo["ID"].astype(str).isin(piezas_bloqueadas)]

    if df_tipo.empty:
        return None, 0

    df_tipo = df_tipo.copy()
    df_tipo["Puntaje"] = df_tipo.apply(
        lambda row: puntuar_pieza(row, stats_rec, puntos_rec),
        axis=1
    )

    best_row = df_tipo.sort_values("Puntaje", ascending=False).iloc[0]
    return best_row["ID"], best_row["Puntaje"]


# ---------------------------------------------------------
# 4. Evaluar combinación 4–2 correctamente
# ---------------------------------------------------------
def evaluar_combinacion(jugador, combinacion, inventarios, stats_rec, puntos_rec, piezas_bloqueadas, slots_activos):

    tipo4 = combinacion["tipo4"]
    tipo2 = combinacion["tipo2"]

    candidatos4 = []
    candidatos2 = []

    for slot in slots_activos:
        slot_str = str(slot)
        inv = inventarios[slot_str]

        id4, pts4 = mejor_pieza_por_prioridad(
            jugador, tipo4, inv, stats_rec, puntos_rec, piezas_bloqueadas
        )
        if id4 is not None:
            candidatos4.append((slot_str, id4, pts4))

        id2, pts2 = mejor_pieza_por_prioridad(
            jugador, tipo2, inv, stats_rec, puntos_rec, piezas_bloqueadas
        )
        if id2 is not None:
            candidatos2.append((slot_str, id2, pts2))

    candidatos4.sort(key=lambda x: x[2], reverse=True)
    candidatos2.sort(key=lambda x: x[2], reverse=True)

    candidatos4 = candidatos4[:6]
    candidatos2 = candidatos2[:6]

    mejores_combinaciones = []

    for comb4 in combinations(candidatos4, 4):
        slots_usados = {s for s, _, _ in comb4}
        libres2 = [c for c in candidatos2 if c[0] not in slots_usados]

        if len(libres2) < 2:
            continue

        for comb2 in combinations(libres2, 2):
            total = sum(x[2] for x in comb4) + sum(x[2] for x in comb2)
            ids = {slot: idp for slot, idp, _ in list(comb4) + list(comb2)}
            mejores_combinaciones.append((total, ids))

    if not mejores_combinaciones:
        return 0, {}

    mejores_combinaciones.sort(key=lambda x: x[0], reverse=True)
    mejores_combinaciones = mejores_combinaciones[:30]

    mejor_total, mejor_ids = mejores_combinaciones[0]
    return mejor_total, mejor_ids


# ---------------------------------------------------------
# 5. Combinaciones 4–2
# ---------------------------------------------------------
def generar_combinaciones_4_2(tipos_disponibles, candidatos_4):
    combinaciones = []
    for tipo4 in candidatos_4:
        for tipo2 in tipos_disponibles:
            if tipo2 != tipo4:
                combinaciones.append({"tipo4": tipo4, "tipo2": tipo2})
    return combinaciones


def mejor_combinacion(jugador, inventarios, tipos_disponibles, candidatos_4, stats_rec, puntos_rec, piezas_bloqueadas, slots_activos):

    combinaciones = generar_combinaciones_4_2(tipos_disponibles, candidatos_4)

    mejor = None
    mejor_ids = None
    mejor_puntaje = -1

    for comb in combinaciones:
        puntaje, ids = evaluar_combinacion(
            jugador, comb, inventarios, stats_rec, puntos_rec, piezas_bloqueadas, slots_activos
        )

        if puntaje > mejor_puntaje:
            mejor = comb
            mejor_ids = ids
            mejor_puntaje = puntaje
    return mejor, mejor_ids, mejor_puntaje


# ---------------------------------------------------------
# 6. Recomendar para un jugador
# ---------------------------------------------------------
def recomendar_para_jugador(
    jugador,
    inventarios,
    tipos_disponibles,
    candidatos_4,
    stats_rec,
    puntos_rec,
    piezas_bloqueadas,
    slots_activos
):

    mejor_comb, ids_por_slot, puntaje_total = mejor_combinacion(
        jugador=jugador,
        inventarios=inventarios,
        tipos_disponibles=tipos_disponibles,
        candidatos_4=candidatos_4,
        stats_rec=stats_rec,
        puntos_rec=puntos_rec,
        piezas_bloqueadas=piezas_bloqueadas,
        slots_activos=slots_activos
    )

    return {
        "jugador": jugador,
        "tipo4": mejor_comb["tipo4"] if mejor_comb else None,
        "tipo2": mejor_comb["tipo2"] if mejor_comb else None,
        "ids_por_slot": ids_por_slot if ids_por_slot else {},
        "puntaje_total": puntaje_total
    }


# ---------------------------------------------------------
# 7. Ejecutar recomendación para TODOS los jugadores
# ---------------------------------------------------------
def _construir_bloqueadas_para_jugador(jugador, lista_jugadores, piezas_equipadas):
    """
    Devuelve el conjunto de IDs bloqueados para 'jugador',
    considerando SOLO las piezas equipadas por jugadores de mayor prioridad.
    """
    if piezas_equipadas is None:
        return set()

    bloqueadas = set()
    if jugador not in lista_jugadores:
        return set()

    idx = lista_jugadores.index(jugador)
    jugadores_previos = lista_jugadores[:idx]

    for j in jugadores_previos:
        slots_j = piezas_equipadas.get(j, {})
        for _, id_actual in slots_j.items():
            if id_actual not in ("", None):
                bloqueadas.add(str(id_actual))

    return bloqueadas


def asignar_todos_los_jugadores(
    lista_jugadores,
    inventarios,
    config_jugadores,
    stats_recomendados,
    tipos_recomendados,
    piezas_equipadas
):
    """
    Asigna recomendaciones para todos los jugadores respetando el orden de prioridad.
    """

    resultados = {}

    for jugador in lista_jugadores:

        candidatos_4 = config_jugadores[jugador]["candidatos_4"]
        slots_activos = config_jugadores[jugador]["slots_activos"]

        stats_rec = stats_recomendados[jugador]["stats"]
        puntos_rec = stats_recomendados[jugador]["puntos"]

        tipos_disp = tipos_recomendados[jugador]

        piezas_bloqueadas = _construir_bloqueadas_para_jugador(
            jugador=jugador,
            lista_jugadores=lista_jugadores,
            piezas_equipadas=piezas_equipadas
        )

        resultado = recomendar_para_jugador(
            jugador=jugador,
            inventarios=inventarios,
            tipos_disponibles=tipos_disp,
            candidatos_4=candidatos_4,
            stats_rec=stats_rec,
            puntos_rec=puntos_rec,
            piezas_bloqueadas=piezas_bloqueadas,
            slots_activos=slots_activos
        )

        resultados[jugador] = resultado

    return resultados

# ============================================================
# 9. Jugadores que usan cada tipo
# ============================================================
def jugadores_que_usan_tipo(tipos_recomendados):
    mapping = {}
    for jugador, tipos in tipos_recomendados.items():
        for t in tipos:
            mapping.setdefault(t, []).append(jugador)
    return mapping


# ============================================================
# 10. Puntaje por jugador y puntaje equilibrado por tipo
# ============================================================
def puntajes_por_jugador_para_pieza(piece, tipo, stats_recomendados, jugadores_por_tipo):
    resultados = {}
    for jugador in jugadores_por_tipo.get(tipo, []):
        stats_rec = stats_recomendados[jugador]["stats"]
        puntos_rec = stats_recomendados[jugador]["puntos"]

        puntaje = puntuar_pieza(piece, stats_rec, puntos_rec)
        resultados[jugador] = puntaje
    return resultados


def prioridad_tipo_para_jugador(jugador, tipo, tipos_recomendados):
    if jugador not in tipos_recomendados:
        return 0
    tipos = tipos_recomendados[jugador]
    if tipo not in tipos:
        return 0
    idx = tipos.index(tipo)
    return len(tipos) - idx


# ============================================================
# 12. Umbral aspiracional basado en necesidades reales (por jugador)
# ============================================================


# ============================================================
# 15. MainStat por defecto al añadir o editar un Potencial
# ============================================================
def mainstat_por_defecto(slot, tipo=""):
    slot = int(slot)

    # Inicializamos SIEMPRE
    mainstat_default = ""
    tm_main_default = ""

    # Slots 1, 3, 5 → Plano
    if slot in (1, 3, 5):
        tm_main_default = "Plano"

        if slot == 3:
            return "Saque", tm_main_default

        if slot == 5:
            return "Recepción", tm_main_default

        # Slot 1 → depende del tipo
        if tipo != "":
            if tipo in ("Poder vibrante", "Incremento de poder", "Opt. de estado", "Potenciación de la moral"):
                mainstat_default = "Ataque poderoso"
            elif tipo in ("Ataque veloz", "Sentido agudo", "Opt. de percepción"):
                mainstat_default = "Ataque rápido"
            elif tipo in ("Saque preciso", "Pase preciso", "Finta de colocador"):
                mainstat_default = "Colocación"
            elif tipo in ("Bloque preciso", "Movimiento de bloqueo", "Guardia contundente"):
                mainstat_default = "Bloqueo"
            elif tipo in ("Recepción de asistencia", "Recepción suprema"):
                mainstat_default = "Recepción"
            else:
                mainstat_default = ""

        return mainstat_default, tm_main_default

    # Slots 2, 4, 6 → Porcentaje
    if slot in (2, 4, 6):
        tm_main_default = "Porcentaje"

        if slot == 2:
            mainstat_default = ["Ataque poderoso","Ataque rápido","Colocación","Saque","Percepción","Fuerza"]
        elif slot == 4:
            mainstat_default = ["Recepción","Bloqueo","Recuperación","Reflejos","Espíritu"]
        elif slot == 6:
            mainstat_default = ["Ataque poderoso","Ataque rápido","Colocación","Saque","Recepción","Bloqueo","Recuperación","Técnica ofensiva","Técnica defensiva"]

        return mainstat_default, tm_main_default

    return "", ""


# ============================================================
# 16. Formatear Stat
# ============================================================
def formatear_stat(stat, tipo_mejora):
    if stat == "" or stat is None:
        return ""
    if tipo_mejora == "Porcentaje":
        return f"{stat} %"
    if tipo_mejora == "Plano":
        return f"{stat} +"
    return stat

# ============================================================
# 18. Evaluar_pieza
# ============================================================   
def evaluar_pieza_para_jugador_en_slot(
    pieza,
    jugador,
    tipo,
    slot,
    inventarios,
    stats_recomendados
):
    """
    Devuelve evaluación de una pieza para un jugador/tipo/slot:
    - puntaje real
    - umbral mínimo
    - umbral aspiracional
    - clasificación: Mala / Aceptable / Buena
    """

    slot_str = str(slot)
    stats_rec = stats_recomendados["stats"]
    puntos_rec = stats_recomendados["puntos"]


    # Puntaje real
    puntaje = puntuar_pieza(pieza, stats_rec, puntos_rec)

    # Umbral mínimo (por afinidad y slot)
    main_stat = pieza.get("Main Stat", "")
    umbral_min = umbral_minimo_por_slot_y_afinidad(
        slot_str,
        main_stat,
        stats_rec,
        puntos_rec
    )

    # nuevos umbrales
    umbral_bueno, umbral_excelente, potencial_perfecto = calcular_umbrales(
        tipo=tipo,
        slot=slot_str,
        inventarios=inventarios,
        stats_rec=stats_rec,
        puntos_rec=puntos_rec,
        jugador=jugador
    )
    
    # Umbral aspiracional (según tu lógica real)
    umbral_asp = calcular_umbral_aspiracional(
        tipo=tipo,
        slot=slot_str,
        inventarios=inventarios,
        stats_rec=stats_rec,
        puntos_rec=puntos_rec,
        jugador=jugador
    )
    
    # Clasificación
    if puntaje < umbral_min:
        calidad = "Malo"
    elif puntaje < umbral_bueno:
        calidad = "Aceptable"
    elif puntaje < umbral_excelente:
        calidad = "Bueno"
    elif puntaje < potencial_perfecto:
        calidad = "Excelente"
    elif puntaje < potencial_perfecto:
        calidad = "Perfecto"
    else:
        calidad = "Error"
        st.error(f"umbral min={umbral_min}, umbral bueno={umbral_bueno}, umbral excelente={umbral_excelente}, perfecto={potencial_perfecto} y puntuación={puntaje}.")

    # Clasificación
    #if puntaje < umbral_min:
    #    calidad = "Mala"
    #elif puntaje < umbral_asp:
    #    calidad = "Aceptable"
    #else:
    #    calidad = "Buena"

    return {
        "puntaje": puntaje,
        "calidad": calidad
    }

# ============================================================
# 19. Orden_jugadores_para_reservas
# ============================================================   
def _orden_jugadores_para_reservas(
    config_jugadores,
    lista_jugadores_prioridad,
    rareza_lista,
    modo="equipar"
):
    """
    modo = "equipar" → solo jugadores con Equipar = True, en orden de prioridad.
    modo = "activo"  → mismos + jugadores activo=True & Equipar=False al final,
                       ordenados por rareza invertida + alfabético.
    """

    # Base: jugadores con Equipar=True respetando orden de prioridad
    base = [
        j for j in lista_jugadores_prioridad
        if config_jugadores.get(j, {}).get("Equipar", False)
    ]

    if modo == "equipar":
        return base

    # Extra: jugadores activos pero sin Equipar
    rareza_index = {r: i for i, r in enumerate(reversed(rareza_lista))}

    extras = []
    for j, cfg in config_jugadores.items():
        if cfg.get("activo", False) and j not in base:
            extras.append(j)

    # Ordenar extras por rareza invertida + alfabético
    extras.sort(
        key=lambda j: (
            rareza_index.get(config_jugadores[j].get("rareza", ""), 999),
            j.lower()
        )
    )

    resultado = base + extras

    # Duplicados
    if len(resultado) != len(set(resultado)):
        st.error("⚠️ HAY DUPLICADOS EN EL ORDEN DE RESERVAS")
        st.write("Duplicados:", [j for j in resultado if resultado.count(j) > 1])

    return resultado


# ============================================================
# 20. Buscar_pieza_en_inventarios
# ============================================================   
def _buscar_pieza_en_inventarios(inventarios, slot_str, pieza_id):
    for p in inventarios.get(slot_str, []):
        if str(p["ID"]) == str(pieza_id):
            return p
    return None

# ============================================================
# 21. calcular_reservas_por_jugador
# ============================================================   
def calcular_reservas_por_jugador(
    inventarios,
    config_jugadores,
    stats_recomendados,
    tipos_recomendados,
    piezas_equipadas,
    lista_jugadores_prioridad,
    rareza_lista,
    modo="equipar",
):
    """
    Devuelve:

    reservas[jugador][slot][tipo] = {
        "id": ID_pieza_o_None,
        "calidad": "Falta" | "Mala" | "Aceptable" | "Buena",
        "estado": "Equipada" | "Reservada" | "Falta",
        "puntaje": float # 
    }
    """
    reservas = {}
    reservadas_global = set()

    # 1. Orden de jugadores según prioridad / modo
    jugadores_orden = _orden_jugadores_para_reservas(
        config_jugadores=config_jugadores,
        lista_jugadores_prioridad=lista_jugadores_prioridad,
        rareza_lista=rareza_lista,
        modo=modo,
    )

    # 2. Inicializar estructura de reservas por jugador
    for j in jugadores_orden:
        reservas[j] = {}

    # 3. Registrar piezas equipadas
    if piezas_equipadas:
        for jugador, slots_j in piezas_equipadas.items():
    
            if jugador not in reservas:
                continue
    
            for slot_str, pieza_id in slots_j.items():
    
                if not pieza_id:
                    continue
    
                pieza = _buscar_pieza_en_inventarios(inventarios, str(slot_str), pieza_id)
                if pieza is None:
                    continue
    
                tipo = pieza.get("Tipo")
                if not tipo:
                    continue
    
                eval_pieza = evaluar_pieza_para_jugador_en_slot(
                    pieza=pieza,
                    jugador=jugador,
                    tipo=tipo,
                    slot=str(slot_str),
                    inventarios=inventarios,
                    stats_recomendados=config_jugadores[jugador]["stats_recomendados"]
                )
    
                reservas[jugador].setdefault(str(slot_str), {})
                reservas[jugador][str(slot_str)][tipo] = {
                    "id": pieza["ID"],
                    "calidad": eval_pieza["calidad"],
                    "estado": "Equipada",
                    "puntaje": eval_pieza["puntaje"]
                }
    
                # Clave primaria real: (slot, ID)
                reservadas_global.add((str(slot_str), str(pieza["ID"])))

    # 4. Reservas adicionales
    for jugador in jugadores_orden:

        cfg = config_jugadores[jugador]

        tipos_j = cfg.get("tipos_recomendados", [])
        slots_activos = [str(s) for s in cfg.get("slots_activos", [])]

        stats_cfg = cfg.get("stats_recomendados", {})
        stats_rec = stats_cfg.get("stats", [])
        puntos_rec = stats_cfg.get("puntos", [])

        for slot_str in slots_activos:

            piezas_slot = inventarios.get(slot_str, [])

            for tipo in tipos_j:

                # Si ya tiene una pieza equipada/reservada para ese slot/tipo, saltamos
                if (
                    slot_str in reservas[jugador]
                    and tipo in reservas[jugador][slot_str]
                ):
                    continue

    # 5. Construcción de candidatas
                candidatas = []
            
                for p in piezas_slot:
            
                    # 5.1 Tipo debe coincidir exactamente
                    if p.get("Tipo") != tipo:
                        continue
            
                    # 5.2 No puede estar reservada globalmente
                    clave_pieza = (slot_str, str(p["ID"]))
                    if clave_pieza in reservadas_global:
                        continue
            
                    # 5.3 Evaluar puntaje para ranking posterior
                    puntaje = puntuar_pieza(p, stats_rec, puntos_rec)
            
                    # 5.4 Guardar candidata
                    candidatas.append((p, puntaje))
                    
                # 6.1 Si no hay candidatas → FALTA
                if not candidatas:
                    reservas[jugador].setdefault(slot_str, {})
                    reservas[jugador][slot_str][tipo] = {
                        "id": None,
                        "calidad": "Falta",
                        "estado": "Falta",
                        "puntaje": 0
                    }
                    continue

                # 6.2 Ordenar candidatas por puntaje (descendente)
                candidatas.sort(key=lambda x: x[1], reverse=True)
                mejor_pieza, _ = candidatas[0]

                # 6.3 Evaluar calidad real de la pieza
                eval_pieza = evaluar_pieza_para_jugador_en_slot(
                    pieza=mejor_pieza,
                    jugador=jugador,
                    tipo=tipo,
                    slot=slot_str,
                    inventarios=inventarios,
                    stats_recomendados=config_jugadores[jugador]["stats_recomendados"]
                )

                # 6.4 Registrar reserva
                reservas[jugador].setdefault(slot_str, {})
                reservas[jugador][slot_str][tipo] = {
                    "id": mejor_pieza["ID"],
                    "calidad": eval_pieza["calidad"],
                    "estado": "Reservada",
                    "puntaje": eval_pieza["puntaje"]
                }

                # 6.5 Marcar pieza como reservada globalmente
                clave_pieza = (slot_str, str(mejor_pieza["ID"]))
                reservadas_global.add(clave_pieza)


    return reservas

def clasificar_potencial(pieza, slot_str, reservas, config_jugadores, inventarios):

    tipo_p = pieza["Tipo"]
    pieza_id = str(pieza["ID"])

    # ============================================================
    # 0) Si esta pieza ya está reservada para este slot/tipo → nunca desechable
    # ============================================================
    for jugador, slots_j in reservas.items():
        if slot_str in slots_j and tipo_p in slots_j[slot_str]:
            info = slots_j[slot_str][tipo_p]
            if info["id"] is not None and str(info["id"]) == pieza_id:
                return {
                    "estado": "reservada",
                    "motivo": f"Esta pieza está actualmente reservada para {jugador} en este slot/tipo.",
                    "evaluaciones": {}
                }

    # ============================================================
    # 1) Determinar qué jugadores activos usan este tipo y este slot
    # ============================================================
    jugadores_validos = []

    for jugador, cfg in config_jugadores.items():

        # A) Solo jugadores activos
        if not cfg.get("activo", False):
            continue

        # B) Deben usar este tipo
        if tipo_p not in cfg["builds"]["Base"]["tipos_recomendados"]:
            continue

        # C) Deben usar este slot
        if slot_str not in cfg["slots_activos"]:
            continue

        jugadores_validos.append(jugador)

    # ============================================================
    # 2) Si ningún jugador usa este tipo → sin uso
    # ============================================================
    if len(jugadores_validos) == 0:
        return {
            "estado": "sin_uso",
            "motivo": "Ningún jugador usa potenciales de este tipo.",
            "evaluaciones": {}
        }

    # ============================================================
    # 3) Extraer reservadas de este slot/tipo
    # ============================================================
    reservadas_slot_tipo = []
    for jugador, slots_j in reservas.items():
        if slot_str in slots_j and tipo_p in slots_j[slot_str]:
            info = slots_j[slot_str][tipo_p]
            if info["id"] is not None:
                reservadas_slot_tipo.append({
                    "jugador": jugador,
                    "puntaje": info["puntaje"],
                    "calidad": info["calidad"]
                })

    # ============================================================
    # 4) Si hay jugadores válidos pero NO hay reservas → rellena hueco
    # ============================================================
    if len(reservadas_slot_tipo) == 0:
        return {
            "estado": "rellena_hueco",
            "motivo": "Hay jugadores que usan este tipo, pero no tienen potenciales guardados.",
            "evaluaciones": {}
        }

    # ============================================================
    # 5) Evaluar pieza para todos los jugadores válidos
    # ============================================================
    evaluaciones = {}
    pieza_buena_para_alguien = False
    supera_a_alguien = False

    for jugador in jugadores_validos:

        cfg = config_jugadores[jugador]

        stats_rec = cfg["builds"]["Base"]["stats_recomendados"]["stats"]
        puntos_rec = cfg["builds"]["Base"]["stats_recomendados"]["puntos"]

        puntaje_p = puntuar_pieza(pieza, stats_rec, puntos_rec)

        # Buscar su reservada
        puntaje_reservada = None
        if jugador in reservas and slot_str in reservas[jugador] and tipo_p in reservas[jugador][slot_str]:
            puntaje_reservada = reservas[jugador][slot_str][tipo_p]["puntaje"]

        # Calidad
        eval_pieza = evaluar_pieza_para_jugador_en_slot(
            pieza=pieza,
            jugador=jugador,
            tipo=tipo_p,
            slot=slot_str,
            inventarios=inventarios,
            stats_recomendados=cfg["builds"]["Base"]["stats_recomendados"]
        )
        calidad = eval_pieza["calidad"]

        if calidad == "Buena":
            pieza_buena_para_alguien = True

        supera = False
        if puntaje_reservada is not None and puntaje_p > puntaje_reservada:
            supera = True
            supera_a_alguien = True

        evaluaciones[jugador] = {
            "puntaje": puntaje_p,
            "calidad": calidad,
            "puntaje_reservada": puntaje_reservada,
            "supera": supera,
            "rellena_hueco": puntaje_reservada is None
        }

    # ============================================================
    # 6) Valoración final
    # ============================================================

    if supera_a_alguien:
        return {
            "estado": "mejora",
            "motivo": "Esta pieza supera a una de las reservadas para este slot/tipo.",
            "evaluaciones": evaluaciones
        }

    if pieza_buena_para_alguien:
        return {
            "estado": "warning",
            "motivo": "La pieza es de buena calidad, pero no supera a ninguna reservada.",
            "evaluaciones": evaluaciones
        }

    return {
        "estado": "desechable",
        "motivo": "La pieza no supera a ninguna reservada y su calidad es Aceptable o Mala.",
        "evaluaciones": evaluaciones
    }

def valor_clasificacion(c):
    return {"Perfecto": 1.0, "Excelente": 0.85, "Bueno": 0.7, "Aceptable": 0.5}.get(c, 0.0)