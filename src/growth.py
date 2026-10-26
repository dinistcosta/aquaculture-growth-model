"""
Modelo de crescimento de dourada (Sparus aurata) e robalo (Dicentrarchus labrax)
em aquacultura, e simulação de um ciclo de engorda em jaula.

ATENÇÃO: os dados gerados por este módulo são SIMULADOS. Os parâmetros vêm da
literatura científica (referências junto de cada valor); os valores marcados
como "PRESSUPOSTO" não têm referência e foram escolhidos por nós.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Parâmetros das espécies (com referências)
# ---------------------------------------------------------------------------
# Modelo de crescimento: coeficiente de crescimento térmico (TGC)
#
# O crescimento depende da temperatura ACUMULADA acima de uma temperatura base
# (temperatura efetiva). Abaixo de 12 °C a dourada não cresce (Mayer et al., 2008).
# Em cada dia, com T a temperatura da água (°C):
#
#     temperatura efetiva = T - 12   (0 se T < 12)
#     peixes < peso crítico:   W^(1/3) aumenta TGC_1/3 x temperatura efetiva
#     peixes >= peso crítico:  W^(2/3) aumenta TGC_2/3 x temperatura efetiva
#
#     W = peso do peixe (g)
#
# O peso crítico é o peso em que as duas fases crescem ao mesmo ritmo:
#     peso crítico = (TGC_2/3 / TGC_1/3)^3 / 8      (≈ 117 g na dourada)
#
# Mayer, P., Estruch, V.D. & Jover, M. (2012). A two-stage growth model for
# gilthead sea bream (Sparus aurata) based on the thermal growth coefficient.
# Aquaculture 358–359: 6–13. doi:10.1016/j.aquaculture.2012.06.016
# (20 lotes de dourada em jaulas comerciais em Valência, Espanha; peso inicial
# 6–44 g; validado com 6 lotes novos.)
#
# NOTA: até 2026 o projeto usava crescimento = 0,024 * W^0,514 * exp(0,060 * T).
# Essa equação é de Lupatsch, Kissil & Sklan (2003), e não de Hernández et al.
# (2003) como estava escrito. Aplicada às jaulas comerciais, errava o peso final
# em 16,6 %, contra cerca de 11 % dos modelos com temperatura efetiva:
# Mayer, P., Estruch, V.D., Blasco, J. & Jover, M. (2008). Predicting the growth
# of gilthead sea bream (Sparus aurata L.) farmed in marine cages under real
# production conditions using temperature- and time-dependent models.
# Aquaculture Research 39: 1046–1052. doi:10.1111/j.1365-2109.2008.01963.x

PARAMETROS = {
    "dourada": {
        "nome_cientifico": "Sparus aurata",
        # Mayer et al. (2012), Tabela 2 (20 lotes em jaulas comerciais).
        "tgc_1_3": 0.001646,
        "tgc_2_3": 0.016095,
        # Temperatura mínima para a dourada comer e crescer (Mayer et al., 2008).
        "temperatura_base": 12.0,
        # Sobrevivência num ciclo de engorda: 80 %.
        # Muniesa, A. et al. (2020). Mapping the knowledge of the main diseases
        # affecting sea bass and sea bream in Mediterranean.
        # Transboundary and Emerging Diseases 67: 1089–1100. doi:10.1111/tbed.13482
        "sobrevivencia_ciclo": 0.80,
        # Duração de referência do ciclo até 300–400 g: 14–16 meses (usamos 15).
        # Cardia, F. & Lovatelli, A. (2007). A review of cage aquaculture:
        # Mediterranean Sea. FAO Fisheries Technical Paper 498: 156–187.
        "duracao_ciclo_dias": 456,
        # Índice de conversão alimentar (FCR) médio em explorações gregas: 2,1.
        # Kallitsis, E. & Avramidis, P. (2025). Life cycle assessment of aquaculture
        # production in Greece. Cleaner Environmental Systems 16: 100261.
        # doi:10.1016/j.cesys.2025.100261
        "fcr": 2.1,
    },
    "robalo": {
        "nome_cientifico": "Dicentrarchus labrax",
        # CALIBRAÇÃO (não é um valor publicado): não encontrámos um TGC do robalo
        # medido em jaulas comerciais. Usamos o TGC clássico (só a fase W^(1/3))
        # com um valor escolhido para que, com a curva de temperatura de
        # perfil_temperatura e entrada em abril, o robalo demore mais 13 % do que
        # a dourada a ir de 3 g a 400 g. 13 % é a diferença entre os ciclos de
        # referência das duas espécies: 14–16 meses na dourada e 16–18 meses no
        # robalo (Cardia & Lovatelli, 2007). Quem tiver dados de uma exploração
        # deve substituir este valor pelo TGC medido nessa exploração.
        "tgc_1_3": 0.00129,
        "tgc_2_3": None,
        # PRESSUPOSTO: a mesma temperatura base da dourada (sem valor publicado
        # encontrado para o robalo em engorda).
        "temperatura_base": 12.0,
        # Sobrevivência num ciclo de engorda: 85 % (Muniesa et al., 2020).
        "sobrevivencia_ciclo": 0.85,
        # Duração de referência: 16–18 meses (usamos 17) (Cardia & Lovatelli, 2007).
        "duracao_ciclo_dias": 517,
        # FCR médio em explorações gregas: 2,2 (Kallitsis & Avramidis, 2025).
        "fcr": 2.2,
    },
}

# Cenários de alimentação: efeito de dar menos ração do que a saciedade.
# Os valores são RELATIVOS à alimentação até à saciedade (= simulação base):
# - fator_crescimento: quanto fica o crescimento (razão entre as SGR)
# - fator_fcr: quanto fica o FCR (razão entre os FCR)
# Nos dois estudos os peixes eram juvenis, em tanques, durante 1–3 meses;
# aplicar estes fatores a um ciclo inteiro é uma extrapolação. No modelo TGC o
# fator de crescimento multiplica o TGC (aproximação: os estudos mediram a SGR).
CENARIOS_ALIMENTACAO = {
    "dourada": {
        "saciedade": {"fator_crescimento": 1.0, "fator_fcr": 1.0},
        # Bonaldo, A., Isani, G., Fontanillas, R., Parma, L., Grilli, E. & Gatta, P.P.
        # (2010). Growth and feed utilization of gilthead sea bream (Sparus aurata,
        # L.) fed to satiation and restrictively at increasing dietary energy levels.
        # Aquaculture International 18: 909–919. doi:10.1007/s10499-009-9312-0
        # Peixes de 73 g, 81 dias, 24 °C. Médias das 3 dietas (Tabela 2):
        #   SGR (calculada do peso inicial e final): 1,50 vs 1,37 %/dia -> 0,92
        #   FCR: 1,37 vs 1,14 -> 0,83
        "restrita": {"fator_crescimento": 0.92, "fator_fcr": 0.83,
                     "descricao": "80 % da saciedade"},
    },
    "robalo": {
        "saciedade": {"fator_crescimento": 1.0, "fator_fcr": 1.0},
        # Türkmen, S., Eroldoğan, O.T., Yılmaz, H.A., Ölçülü, A., İnan, G.A.K.,
        # Erçen, Z. & Tekelioğlu, N. (2012). Compensatory growth response of
        # European sea bass (Dicentrarchus labrax L.) under cycled starvation and
        # restricted feeding rate. Aquaculture Research 43: 1643–1650.
        # doi:10.1111/j.1365-2109.2011.02970.x
        # Peixes de 10,5 g. SGR 2,5 (saciedade) vs 2,2 %/dia (alimentação 25 %
        # restrita) -> 0,88. FCR sem diferença significativa -> 1,0.
        "restrita": {"fator_crescimento": 0.88, "fator_fcr": 1.0,
                     "descricao": "75 % da saciedade"},
    },
}

# Peso dos juvenis à entrada na jaula: 2–4 g (Cardia & Lovatelli, 2007). Usamos 3 g.
PESO_INICIAL_G = 3.0

# PRESSUPOSTO (sem referência): variação individual no ritmo de crescimento.
# Cada peixe cresce a um ritmo multiplicado por um fator ~ Normal(1; 0,15).
CV_CRESCIMENTO_INDIVIDUAL = 0.15

# Limite de validade: no modelo TGC o crescimento aumenta sempre com a
# temperatura (não há temperatura ótima). Os dados de Mayer et al. (2008) iam até
# 26,5 °C, e a temperatura ótima de crescimento do robalo é cerca de 26 °C
# (Person-Le Ruyet, J., Mahé, K., Le Bayon, N. & Le Delliou, H., 2004. Effects of
# temperature on growth and metabolism in a Mediterranean population of European
# sea bass, Dicentrarchus labrax. Aquaculture 237: 269–280.
# doi:10.1016/j.aquaculture.2004.04.021), por isso não usamos o modelo acima de 25 °C.
TEMPERATURA_MAXIMA_VALIDA = 25.0


# ---------------------------------------------------------------------------
# 2. Funções do modelo
# ---------------------------------------------------------------------------

def peso_critico(parametros):
    """Peso (g) em que o crescimento passa da fase W^(1/3) para a fase W^(2/3).

    Sem TGC_2/3 (só uma fase), devolve infinito.
    """
    if not parametros.get("tgc_2_3"):
        return np.inf
    return (parametros["tgc_2_3"] / parametros["tgc_1_3"]) ** 3 / 8


def crescimento_diario(peso_g, temperatura_c, especie, parametros=None, fator=1.0):
    """Ganho de peso de um peixe num dia (g/dia), pelo modelo TGC.

    peso_g pode ser um número ou um array com o peso de vários peixes.
    parametros: dicionário que substitui os valores de PARAMETROS[especie]
    (ex.: o TGC medido numa exploração).
    fator: multiplica o crescimento (variação individual, cenários de alimentação).
    """
    p = {**PARAMETROS[especie], **(parametros or {})}
    peso = np.asarray(peso_g, dtype=float)
    efetiva = max(temperatura_c - p["temperatura_base"], 0.0) * fator
    fase_1 = peso < peso_critico(p)
    novo = np.where(fase_1,
                    (np.cbrt(peso) + p["tgc_1_3"] * efetiva) ** 3,
                    (peso ** (2 / 3) + (p["tgc_2_3"] or 0.0) * efetiva) ** 1.5)
    return novo - peso


def perfil_temperatura(n_dias, data_inicio="2024-04-01", media=19.0, amplitude=4.0,
                       dia_do_ano_minimo=45):
    """Temperatura diária da água ao longo do ciclo (curva sazonal).

    PRESSUPOSTO (ilustrativo): uma onda sinusoidal com média de 19 °C, a variar
    entre 15 °C (meados de fevereiro) e 23 °C (meados de agosto). Pode ser
    substituída por dados reais de temperatura (ex.: sonda da exploração).
    """
    datas = pd.date_range(data_inicio, periods=n_dias, freq="D")
    dia_do_ano = datas.dayofyear.to_numpy()
    temperatura = media - amplitude * np.cos(2 * np.pi * (dia_do_ano - dia_do_ano_minimo) / 365)
    return datas, temperatura


def simular_ciclo(especie, n_dias=640, n_peixes=5000, temperatura=None,
                  data_inicio="2024-04-01", peso_inicial_g=PESO_INICIAL_G,
                  fator_crescimento=1.0, fcr=None, parametros=None, semente=42):
    """Simula, dia a dia, um ciclo de engorda numa jaula.

    Devolve uma tabela (DataFrame) com uma linha por dia:
    dia, data, temperatura_c, n_peixes, peso_medio_g, peso_dp_g,
    biomassa_kg, racao_kg e mortos.

    - temperatura: array com a temperatura de cada dia (se None, usa a curva
      sazonal de perfil_temperatura).
    - fator_crescimento: multiplica o crescimento (usado nos cenários de
      alimentação; 1 = alimentação normal).
    - fcr: índice de conversão alimentar (se None, usa o valor da espécie).
    - parametros: valores que substituem os de PARAMETROS[especie] (ex.: TGC
      ou sobrevivência de uma exploração).
    """
    p = {**PARAMETROS[especie], **(parametros or {})}
    gerador = np.random.default_rng(semente)

    if temperatura is None:
        datas, temperatura = perfil_temperatura(n_dias, data_inicio)
    else:
        temperatura = np.asarray(temperatura, dtype=float)
        datas = pd.date_range(data_inicio, periods=n_dias, freq="D")
    if np.max(temperatura) > TEMPERATURA_MAXIMA_VALIDA:
        print(f"Aviso: temperaturas acima de {TEMPERATURA_MAXIMA_VALIDA} °C estão "
              "fora da validade do modelo.")
    if fcr is None:
        fcr = p["fcr"]

    # Cada peixe tem o seu próprio ritmo de crescimento (variação individual)
    ritmo = gerador.normal(1.0, CV_CRESCIMENTO_INDIVIDUAL, n_peixes).clip(0.3, None)
    pesos = np.full(n_peixes, float(peso_inicial_g))
    vivo = np.ones(n_peixes, dtype=bool)

    # Probabilidade diária de morrer, calculada para que, ao fim da duração de
    # referência do ciclo, sobreviva a fração indicada na literatura:
    #   (1 - p_dia) ^ duracao = sobrevivencia   =>   p_dia = 1 - sobrevivencia^(1/duracao)
    p_morte_dia = 1 - p["sobrevivencia_ciclo"] ** (1 / p["duracao_ciclo_dias"])

    linhas = []
    for dia in range(n_dias):
        # 1) Mortalidade do dia
        morre = vivo & (gerador.random(n_peixes) < p_morte_dia)
        vivo[morre] = False

        # 2) Crescimento dos peixes vivos
        ganho = crescimento_diario(pesos[vivo], temperatura[dia], especie, p,
                                   fator=ritmo[vivo] * fator_crescimento)
        pesos[vivo] += ganho

        # 3) Ração: o ganho de biomassa do dia vezes o FCR, com variação diária
        #    (o FCR real oscila de dia para dia; a média mantém-se no valor do FCR)
        fcr_dia = fcr * gerador.lognormal(0, 0.10) / np.exp(0.10 ** 2 / 2)
        racao_kg = ganho.sum() / 1000 * fcr_dia

        linhas.append({
            "dia": dia,
            "data": datas[dia],
            "temperatura_c": round(float(temperatura[dia]), 2),
            "n_peixes": int(vivo.sum()),
            "peso_medio_g": float(pesos[vivo].mean()),
            "peso_dp_g": float(pesos[vivo].std()),
            "biomassa_kg": float(pesos[vivo].sum() / 1000),
            "racao_kg": float(racao_kg),
            "mortos": int(morre.sum()),
        })

    tabela = pd.DataFrame(linhas)
    tabela.insert(0, "especie", especie)
    return tabela


def registos_de_exploracao(simulacao, intervalo_dias=14, n_amostra=50, semente=1):
    """Converte a simulação diária em registos como os de uma exploração real.

    Numa exploração não se pesam todos os peixes todos os dias: faz-se uma
    biometria (pesagem de uma amostra) de tempos a tempos. Esta função imita isso:
    - de 'intervalo_dias' em 'intervalo_dias', o peso médio é estimado a partir
      de uma amostra de 'n_amostra' peixes (por isso tem erro de amostragem);
    - a ração é somada entre biometrias;
    - a temperatura é a média do período.

    O resultado tem as colunas do formato de dados reais:
    especie, dia, data, peso_medio_g, temperatura_c, racao_kg, n_peixes
    """
    gerador = np.random.default_rng(semente)
    dias_biometria = list(range(0, len(simulacao), intervalo_dias))
    linhas = []
    for i, dia in enumerate(dias_biometria):
        hoje = simulacao.iloc[dia]
        # Erro de amostragem: a média de 50 peixes não é exatamente a média da jaula
        erro_padrao = hoje["peso_dp_g"] / np.sqrt(n_amostra)
        peso_estimado = hoje["peso_medio_g"] + gerador.normal(0, erro_padrao)
        inicio = dias_biometria[i - 1] if i > 0 else 0
        periodo = simulacao.iloc[inicio:dia] if dia > 0 else simulacao.iloc[0:1]
        linhas.append({
            "especie": hoje["especie"],
            "dia": int(dia),
            "data": hoje["data"].date(),
            "peso_medio_g": round(float(peso_estimado), 1),
            "temperatura_c": round(float(periodo["temperatura_c"].mean()), 1),
            "racao_kg": round(float(periodo["racao_kg"].sum()), 1) if dia > 0 else 0.0,
            "n_peixes": int(hoje["n_peixes"]),
        })
    return pd.DataFrame(linhas)


def dias_ate_peso(tabela, peso_alvo_g=400, coluna="peso_medio_g"):
    """Primeiro dia em que o peso médio atinge o peso-alvo (None se não atingir)."""
    atingiu = tabela[tabela[coluna] >= peso_alvo_g]
    return int(atingiu["dia"].iloc[0]) if len(atingiu) else None
