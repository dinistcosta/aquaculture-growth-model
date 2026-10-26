"""
Curva de crescimento de von Bertalanffy, em peso, e ajuste aos registos.

    W(t) = W∞ * (1 - exp(-k * (t - t0)))^3

    W∞ = peso assintótico (g): o peso máximo que o peixe atingiria
    k  = coeficiente de crescimento (por dia): a rapidez com que se aproxima de W∞
    t0 = "idade" teórica (dias) em que o peso seria zero (um parâmetro de ajuste,
         sem significado biológico direto)

O expoente 3 vem de o peso ser proporcional ao comprimento ao cubo
(crescimento isométrico).
"""

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit


def vb_peso(t, w_inf, k, t0):
    """Peso (g) no dia t segundo a curva de von Bertalanffy."""
    return w_inf * (1 - np.exp(-k * (t - t0))) ** 3


def r_quadrado(observado, previsto):
    """Coeficiente de determinação: fração da variação explicada pelo modelo."""
    residuos = observado - previsto
    return 1 - np.sum(residuos ** 2) / np.sum((observado - np.mean(observado)) ** 2)


def ajustar_vb(dias, pesos, w_inf_fixo=None, w_inf_maximo=100_000):
    """Ajusta a curva de von Bertalanffy com scipy.optimize.curve_fit.

    - Se w_inf_fixo for None, estima W∞, k e t0.
    - Se w_inf_fixo for um número (g), W∞ fica fixo e só se estimam k e t0.

    w_inf_maximo (g) é um limite superior para W∞ no ajuste livre, para o
    algoritmo não andar até ao infinito quando os dados não chegam para
    estimar W∞.

    Devolve um dicionário com os parâmetros, os erros-padrão, os intervalos
    de confiança a 95 %, o R² e os resíduos.
    """
    dias = np.asarray(dias, dtype=float)
    pesos = np.asarray(pesos, dtype=float)

    if w_inf_fixo is None:
        nomes = ["w_inf", "k", "t0"]
        funcao = vb_peso
        inicio = [2000, 0.002, -50]                      # valores iniciais
        limites = ([0, 0, -1000], [w_inf_maximo, 1, dias.min()])
    else:
        nomes = ["k", "t0"]
        funcao = lambda t, k, t0: vb_peso(t, w_inf_fixo, k, t0)
        inicio = [0.002, -50]
        limites = ([0, -1000], [1, dias.min()])

    estimativas, covariancia = curve_fit(funcao, dias, pesos, p0=inicio,
                                         bounds=limites, maxfev=20000)
    erros_padrao = np.sqrt(np.diag(covariancia))

    # Intervalo de confiança a 95 %: estimativa ± t * erro-padrão,
    # com t da distribuição t de Student (graus de liberdade = n - nº de parâmetros)
    graus_liberdade = len(dias) - len(estimativas)
    t_critico = stats.t.ppf(0.975, graus_liberdade)

    previsto = funcao(dias, *estimativas)
    resultado = {
        "parametros": dict(zip(nomes, estimativas)),
        "erros_padrao": dict(zip(nomes, erros_padrao)),
        "ic95": {n: (e - t_critico * s, e + t_critico * s)
                 for n, e, s in zip(nomes, estimativas, erros_padrao)},
        "r2": r_quadrado(pesos, previsto),
        "residuos": pesos - previsto,
        "previsto": previsto,
    }
    # Para ser mais fácil desenhar a curva depois, guardamos sempre os 3 parâmetros
    curva = dict(resultado["parametros"])
    if w_inf_fixo is not None:
        curva["w_inf"] = w_inf_fixo
    resultado["curva"] = curva
    return resultado
