"""
Leitura de registos de produção (simulados ou reais).

Para usar dados reais em vez dos simulados, basta ter um CSV com estas colunas
(uma linha por biometria) e passar o caminho a ler_registos():

    dia, peso_medio_g, temperatura_c, racao_kg, n_peixes

Colunas opcionais: especie, data.
"""

import pandas as pd

COLUNAS_OBRIGATORIAS = ["dia", "peso_medio_g", "temperatura_c", "racao_kg", "n_peixes"]


def ler_registos(caminho):
    """Lê um CSV de registos e confirma que tem as colunas necessárias."""
    registos = pd.read_csv(caminho)
    em_falta = [c for c in COLUNAS_OBRIGATORIAS if c not in registos.columns]
    if em_falta:
        raise ValueError(f"Faltam colunas no ficheiro {caminho}: {em_falta}")
    if "data" in registos.columns:
        registos["data"] = pd.to_datetime(registos["data"])
    return registos.sort_values(["especie", "dia"] if "especie" in registos.columns else "dia")
