"""
App interativa: crescimento de dourada e robalo em aquacultura.

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
"""

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.growth import (PARAMETROS, CENARIOS_ALIMENTACAO, TEMPERATURA_MAXIMA_VALIDA,
                        perfil_temperatura, simular_ciclo, dias_ate_peso)

N_DIAS = 1400      # chega para todos os cenários possíveis com os sliders
N_PEIXES = 1000    # menos peixes do que nos notebooks, para a app ser rápida
CORES = {"dourada": "#c9971c", "robalo": "#3f6ea6"}
NOMES = {"dourada": "Dourada (Sparus aurata)", "robalo": "Robalo (Dicentrarchus labrax)"}

st.set_page_config(page_title="Crescimento de dourada e robalo", page_icon="🐟", layout="wide")
st.title("🐟 Crescimento de dourada e robalo em aquacultura")
st.warning("Os resultados são **simulados** com um modelo baseado em parâmetros da literatura "
           "científica. Não são dados de nenhuma exploração.")


# ---------------------------------------------------------------------------
# 1. Escolhas do utilizador (barra lateral)
# ---------------------------------------------------------------------------
st.sidebar.header("Cenário")

escolha = st.sidebar.radio("Espécie", ["Dourada", "Robalo", "Comparar as duas"])
especies = {"Dourada": ["dourada"], "Robalo": ["robalo"],
            "Comparar as duas": ["dourada", "robalo"]}[escolha]

tipo_temperatura = st.sidebar.radio(
    "Temperatura da água",
    ["Constante (tanque / RAS)", "Sazonal (jaula no mar)"],
    help="Num tanque com temperatura controlada a temperatura é sempre a mesma; "
         "numa jaula no mar varia ao longo do ano.")
if tipo_temperatura.startswith("Constante"):
    temperatura_c = st.sidebar.slider("Temperatura (°C)", 14.0, TEMPERATURA_MAXIMA_VALIDA, 20.0, 0.5)
    temperatura = np.full(N_DIAS, temperatura_c)
else:
    media = st.sidebar.slider("Temperatura média anual (°C)", 15.0, 21.0, 19.0, 0.5,
                              help="A temperatura varia ± 4 °C à volta da média: mínimo em "
                                   "fevereiro, máximo em agosto. Entrada dos peixes a 1 de abril.")
    _, temperatura = perfil_temperatura(N_DIAS, media=media)

alimentacao = st.sidebar.radio(
    "Alimentação", ["saciedade", "restrita"],
    format_func=lambda a: "Até à saciedade" if a == "saciedade" else "Restrita (75–80 % da saciedade)",
    help="Efeito da ração restrita: Bonaldo et al. (2010) para a dourada e "
         "Türkmen et al. (2012) para o robalo.")

peso_comercial = st.sidebar.slider("Tamanho comercial (g)", 250, 600, 400, 25)


# ---------------------------------------------------------------------------
# 2. Simulação
# ---------------------------------------------------------------------------
@st.cache_data
def simular(especie, temperatura, alimentacao):
    """Corre a simulação (o resultado fica guardado para não repetir contas)."""
    cenario = CENARIOS_ALIMENTACAO[especie][alimentacao]
    return simular_ciclo(especie, n_dias=N_DIAS, n_peixes=N_PEIXES, temperatura=temperatura,
                         fator_crescimento=cenario["fator_crescimento"],
                         fcr=PARAMETROS[especie]["fcr"] * cenario["fator_fcr"], semente=42)


with st.spinner("A simular..."):
    simulacoes = {e: simular(e, temperatura, alimentacao) for e in especies}


# ---------------------------------------------------------------------------
# 3. Resultados: números principais
# ---------------------------------------------------------------------------
colunas = st.columns(len(especies))
for coluna, especie in zip(colunas, especies):
    sim = simulacoes[especie]
    dia = dias_ate_peso(sim, peso_comercial)
    with coluna:
        st.subheader(NOMES[especie])
        if dia is None:
            st.error(f"Não chega aos {peso_comercial} g em {N_DIAS} dias.")
            continue
        ate_peso = sim.loc[:dia]
        ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - N_PEIXES * sim.loc[0, "peso_medio_g"] / 1000
        fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Dias até {peso_comercial} g", dia, f"≈ {dia / 30.4:.1f} meses", delta_color="off")
        c2.metric("FCR económico", f"{fcr:.2f}".replace(".", ","))
        c3.metric("Sobrevivência", f"{sim.loc[dia, 'n_peixes'] / N_PEIXES:.0%}")


# ---------------------------------------------------------------------------
# 4. Gráfico: curva de crescimento e temperatura
# ---------------------------------------------------------------------------
fig, (ax_peso, ax_temp) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True,
                                       gridspec_kw={"height_ratios": [3, 1]})
dias_alvo = [dias_ate_peso(s, peso_comercial) for s in simulacoes.values()]
dia_maximo = min(N_DIAS, int(max(d or N_DIAS for d in dias_alvo) * 1.15))

for especie, sim in simulacoes.items():
    s = sim.iloc[:dia_maximo]
    ax_peso.plot(s["dia"], s["peso_medio_g"], color=CORES[especie], linewidth=2.2, label=NOMES[especie])
    ax_peso.fill_between(s["dia"], s["peso_medio_g"] - s["peso_dp_g"], s["peso_medio_g"] + s["peso_dp_g"],
                         color=CORES[especie], alpha=0.18)
    dia = dias_ate_peso(sim, peso_comercial)
    if dia is not None:
        ax_peso.axvline(dia, color=CORES[especie], linestyle=":", linewidth=1.2)
ax_peso.axhline(peso_comercial, color="0.3", linestyle="--", linewidth=1)
ax_peso.text(5, peso_comercial * 1.03, f"tamanho comercial ({peso_comercial} g)", color="0.3", fontsize=9)
ax_peso.set_ylim(0, peso_comercial * 1.6)
ax_peso.set_ylabel("Peso médio (g)")
ax_peso.set_title("Crescimento simulado (linha: média; sombra: ± 1 desvio-padrão entre peixes)")
ax_peso.legend(loc="upper left")
ax_peso.grid(alpha=0.3)

ax_temp.plot(np.arange(dia_maximo), temperatura[:dia_maximo], color="#2a6f97", linewidth=1.8)
ax_temp.set_ylim(10, 26)
ax_temp.set_ylabel("Temperatura (°C)")
ax_temp.set_xlabel("Dias desde a entrada dos juvenis (3 g)")
ax_temp.grid(alpha=0.3)
fig.tight_layout()
st.pyplot(fig)


# ---------------------------------------------------------------------------
# 5. Explicação do modelo
# ---------------------------------------------------------------------------
with st.expander("Sobre o modelo"):
    st.markdown(r"""
Cada peixe cresce, dia a dia, segundo

$$\frac{dW}{dt} = a \cdot W^{\,b} \cdot e^{\,c \cdot T}$$

com $W$ o peso (g) e $T$ a temperatura (°C). Simulamos uma jaula de 1 000 juvenis de 3 g,
com variação individual no crescimento e mortalidade diária.

| | Dourada | Robalo |
|---|---|---|
| a · b · c | 0,024 · 0,514 · 0,060 (Hernández et al., 2003) | 0,010 · 0,68 · 0,05 (Lanari et al., 2002) × 1,14 (calibração) |
| Sobrevivência no ciclo | 80 % (Muniesa et al., 2020) | 85 % (Muniesa et al., 2020) |
| FCR | 2,1 (Kallitsis & Avramidis, 2025) | 2,2 (Kallitsis & Avramidis, 2025) |
| Ração restrita | 80 %: crescimento × 0,92, FCR × 0,83 (Bonaldo et al., 2010) | 75 %: crescimento × 0,88, FCR igual (Türkmen et al., 2012) |

**Limitações:** o modelo não tem temperatura ótima (por isso a temperatura está limitada a 25 °C),
a mortalidade é constante e os efeitos da ração vêm de ensaios curtos com juvenis.

Código, notebooks e referências completas:
[github.com/dinistcosta/aquaculture-growth-model](https://github.com/dinistcosta/aquaculture-growth-model)
""")
