"""
Regimes de cultivo de dourada e robalo: valores da literatura e efeitos
usados nas simulações do notebook 05.

Só simulamos os efeitos para os quais encontrámos uma fonte. O resto fica
apenas na tabela descritiva (TABELA_REGIMES).
"""

import pandas as pd


# ---------------------------------------------------------------------------
# 1. Tabela descritiva dos regimes (dourada)
# ---------------------------------------------------------------------------
# Fonte principal: FAO (2009). Sparus aurata. Cultured aquatic species fact
# sheets. Texto de Colloca, F. & Cerasi, S. Editado por Crespi, V. & New, M.
# None = sem dados fiáveis encontrados.
TABELA_REGIMES = pd.DataFrame([
    {"regime": "Extensivo (lagoas)",
     "alimentação": "alimento natural",
     "densidade (kg/m³)": "≤ 0,0025",
     "produção (kg/ha/ano)": "15–30",
     "tempo até ao tamanho comercial": "20 meses até 350 g (juvenis de 2–3 g)",
     "FCR": "— (sem ração)",
     "controlo da temperatura": "não"},
    {"regime": "Semi-intensivo (lagoas e tanques de terra)",
     "alimentação": "natural + ração",
     "densidade (kg/m³)": "≤ 1",
     "produção (kg/ha/ano)": "500–2 400",
     "tempo até ao tamanho comercial": None,
     "FCR": None,
     "controlo da temperatura": "não"},
    {"regime": "Intensivo: jaulas no mar",
     "alimentação": "ração",
     "densidade (kg/m³)": "10–15",
     "produção (kg/ha/ano)": None,
     "tempo até ao tamanho comercial": "≈ 16 meses até 350–400 g (juvenis de 5 g)",
     "FCR": None,
     "controlo da temperatura": "não"},
    {"regime": "Intensivo: tanques em terra",
     "alimentação": "ração",
     "densidade (kg/m³)": "15–45",
     "produção (kg/ha/ano)": None,
     "tempo até ao tamanho comercial": "≈ 12 meses até 350–400 g (juvenis de 5 g, 18–26 °C)",
     "FCR": "≈ 1,3",
     "controlo da temperatura": "sim"},
])

# Tempos de referência da FAO (2009) para a validação (dourada, juvenis de 5 g)
MESES_FAO_JAULA = 16
MESES_FAO_TANQUE = 12
MESES_FAO_EXTENSIVO = 20   # juvenis de 2–3 g, até 350 g

# PRESSUPOSTO: temperatura de um tanque em terra / RAS com temperatura
# controlada. 22 °C é o meio do intervalo 18–26 °C indicado pela FAO (2009).
TEMPERATURA_TANQUE = 22.0


# ---------------------------------------------------------------------------
# 2. Densidade em RAS (robalo)
# ---------------------------------------------------------------------------
# Sammouth, S., Roque d'Orbcastel, E., Gasset, E., Lemarié, G., Breuil, G.,
# Marino, G., Coeurdacier, J.-L., Fivelstad, S. & Blancheton, J.-P. (2009).
# The effect of density on sea bass (Dicentrarchus labrax) performance in a
# tank-based recirculating system. Aquacultural Engineering 40: 72–78.
# doi:10.1016/j.aquaeng.2008.11.004
# Robalos de 135 g, 63 dias, densidades de 10, 40, 70 e 100 kg/m³:
# - até 70 kg/m³: sem diferenças na SGR, no FCR nem na mortalidade
# - a 100 kg/m³: SGR 14 % mais baixa
DENSIDADE_SEM_EFEITO = 70     # kg/m³
DENSIDADE_MAXIMA = 100        # kg/m³ (maior densidade testada)
REDUCAO_SGR_MAXIMA = 0.14     # a 100 kg/m³


def fator_crescimento_densidade(densidade_kg_m3):
    """Fator de crescimento do robalo em RAS consoante a densidade.

    1 até 70 kg/m³ e 0,86 a 100 kg/m³ (Sammouth et al., 2009).
    PRESSUPOSTO: entre 70 e 100 kg/m³ o efeito aumenta em linha reta.
    """
    if densidade_kg_m3 > DENSIDADE_MAXIMA:
        raise ValueError("Acima de 100 kg/m³ não há dados (Sammouth et al., 2009).")
    if densidade_kg_m3 <= DENSIDADE_SEM_EFEITO:
        return 1.0
    fracao = (densidade_kg_m3 - DENSIDADE_SEM_EFEITO) / (DENSIDADE_MAXIMA - DENSIDADE_SEM_EFEITO)
    return 1.0 - REDUCAO_SGR_MAXIMA * fracao


# ---------------------------------------------------------------------------
# 3. IMTA (robalo)
# ---------------------------------------------------------------------------
# Cotou, E., Miliou, H., Chatzoglou, E., Schoina, E., Politakis, N.,
# Kogiannou, D., Fountoulaki, E., Androni, A., Konstantinopoulou, A.,
# Assimakopoulou, G. & Nathanailides, C. (2024). Growth performance and
# environmental quality indices and biomarkers in a co-culture of the European
# sea bass with filter and deposit feeders: a case study of an IMTA system.
# Fishes 9: 69. doi:10.3390/fishes9020069
# Robalos de 147 g, 90 dias, com mexilhões, ostras e pepinos-do-mar (Tabela 2):
# - FCR 1,66 (monocultura) vs 1,47 (IMTA), diferença significativa -> 0,89
# - SGR e sobrevivência sem diferença significativa -> sem alteração
FATOR_FCR_IMTA = round(1.47 / 1.66, 2)   # = 0.89
