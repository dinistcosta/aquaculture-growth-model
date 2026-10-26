"""
Indicadores de produção em aquacultura, calculados a partir de registos de
biometria (simulados ou reais), com as colunas:

    dia, peso_medio_g, temperatura_c, racao_kg, n_peixes

Em racao_kg está a ração dada desde a biometria anterior.

Indicadores:
- SGR  (taxa de crescimento específica, %/dia)
- GPD  (ganho de peso diário, g/dia)
- FCR  (índice de conversão alimentar, kg de ração / kg de biomassa ganha)
- Sobrevivência (%)
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Fórmulas
# ---------------------------------------------------------------------------

def sgr(peso_inicial_g, peso_final_g, dias):
    """Taxa de crescimento específica (%/dia).

    SGR = 100 * (ln(peso final) - ln(peso inicial)) / dias
    """
    return 100 * (np.log(peso_final_g) - np.log(peso_inicial_g)) / dias


def gpd(peso_inicial_g, peso_final_g, dias):
    """Ganho de peso diário (g/dia).

    GPD = (peso final - peso inicial) / dias
    """
    return (peso_final_g - peso_inicial_g) / dias


def fcr(racao_kg, biomassa_inicial_kg, biomassa_final_kg):
    """Índice de conversão alimentar (sem unidades).

    FCR = ração dada (kg) / ganho de biomassa (kg)
    """
    return racao_kg / (biomassa_final_kg - biomassa_inicial_kg)


def sobrevivencia(n_inicial, n_final):
    """Sobrevivência (%).

    Sobrevivência = 100 * peixes vivos no fim / peixes no início
    """
    return 100 * n_final / n_inicial


# ---------------------------------------------------------------------------
# 2. Aplicar as fórmulas aos registos
# ---------------------------------------------------------------------------

def biomassa_kg(registos):
    """Biomassa da jaula em cada biometria (kg) = peso médio * nº de peixes."""
    return registos["peso_medio_g"] * registos["n_peixes"] / 1000


def agrupar_biometrias(registos, cada=4):
    """Junta biometrias seguidas para obter períodos mais longos.

    Fica uma biometria em cada 'cada' (ex.: cada=4 com biometrias de 14 em 14
    dias dá períodos de 8 semanas). A ração das biometrias que saem é somada à
    seguinte e a temperatura passa a ser a média do período mais longo.

    Serve para reduzir o erro de amostragem: em períodos curtos, o erro da
    média da amostra pode ser maior do que o crescimento real.
    """
    r = registos.sort_values("dia").reset_index(drop=True)
    # número do grupo de cada linha: a linha 0 fica sozinha (início do ciclo),
    # as linhas 1–4 formam o grupo 1, as linhas 5–8 o grupo 2, etc.
    grupo = (r.index + cada - 1) // cada
    agrupado = r.groupby(grupo).agg(
        dia=("dia", "last"),
        peso_medio_g=("peso_medio_g", "last"),
        temperatura_c=("temperatura_c", "mean"),
        racao_kg=("racao_kg", "sum"),
        n_peixes=("n_peixes", "last"),
    )
    # Um último grupo incompleto (menos de 'cada' biometrias) é removido
    if len(r) > 1 and (len(r) - 1) % cada != 0:
        agrupado = agrupado.iloc[:-1]
    return agrupado.reset_index(drop=True)


def indicadores_por_periodo(registos):
    """Calcula os indicadores entre cada par de biometrias seguidas.

    Recebe os registos de UMA espécie (ou jaula) e devolve uma tabela com uma
    linha por período: dia_inicio, dia_fim, peso_medio_g (no início),
    temperatura_c, sgr, gpd, fcr e sobrevivencia_periodo.
    """
    r = registos.sort_values("dia").reset_index(drop=True)
    biomassa = biomassa_kg(r)

    # .shift(1) vai buscar o valor da biometria anterior
    dias = r["dia"] - r["dia"].shift(1)
    tabela = pd.DataFrame({
        "dia_inicio": r["dia"].shift(1),
        "dia_fim": r["dia"],
        "peso_medio_g": r["peso_medio_g"].shift(1),
        "temperatura_c": r["temperatura_c"],
        "sgr": sgr(r["peso_medio_g"].shift(1), r["peso_medio_g"], dias),
        "gpd": gpd(r["peso_medio_g"].shift(1), r["peso_medio_g"], dias),
        "fcr": fcr(r["racao_kg"], biomassa.shift(1), biomassa),
        "sobrevivencia_periodo": sobrevivencia(r["n_peixes"].shift(1), r["n_peixes"]),
    })
    # A primeira linha não tem biometria anterior, por isso é removida
    return tabela.dropna().reset_index(drop=True)


def resumo_ciclo(registos, ate_dia=None):
    """Indicadores do ciclo inteiro (da primeira biometria até 'ate_dia').

    O FCR calculado assim é o FCR "económico": inclui a ração comida pelos
    peixes que morreram, porque essa biomassa não chega à despesca.
    """
    r = registos.sort_values("dia")
    if ate_dia is not None:
        r = r[r["dia"] <= ate_dia]
    inicio, fim = r.iloc[0], r.iloc[-1]
    dias = fim["dia"] - inicio["dia"]
    biomassa = biomassa_kg(r)
    return {
        "dias": int(dias),
        "peso_inicial_g": inicio["peso_medio_g"],
        "peso_final_g": fim["peso_medio_g"],
        "sgr": sgr(inicio["peso_medio_g"], fim["peso_medio_g"], dias),
        "gpd": gpd(inicio["peso_medio_g"], fim["peso_medio_g"], dias),
        # a ração da primeira linha é a dada antes do início, por isso não conta
        "fcr": fcr(r["racao_kg"].iloc[1:].sum(), biomassa.iloc[0], biomassa.iloc[-1]),
        "sobrevivencia": sobrevivencia(inicio["n_peixes"], fim["n_peixes"]),
    }
