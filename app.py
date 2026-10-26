"""
App interativa: crescimento de dourada e robalo em aquacultura.

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.growth import (PARAMETROS, CENARIOS_ALIMENTACAO, TEMPERATURA_MAXIMA_VALIDA,
                        perfil_temperatura, simular_ciclo, dias_ate_peso)

N_DIAS = 1400      # chega para todos os cenários possíveis com os controlos
N_PEIXES = 1000    # menos peixes do que nos notebooks, para a app ser rápida
CORES = {"dourada": "#C9971C", "robalo": "#2F6690"}
NOMES = {"dourada": "Dourada", "robalo": "Robalo"}
CIENTIFICOS = {"dourada": "Sparus aurata", "robalo": "Dicentrarchus labrax"}
COR_TEMPERATURA = "#0E7490"
URL_GITHUB = "https://github.com/dinistcosta/aquaculture-growth-model"

st.set_page_config(page_title="Crescimento de dourada e robalo", page_icon="🐟", layout="wide")


def virgula(numero, casas=1):
    """Escreve um número com vírgula decimal (ex.: 14,1)."""
    return f"{numero:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 1. Escolhas do utilizador (barra lateral)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Cenário")

    escolha = st.segmented_control("Espécie", ["Dourada", "Robalo", "Ambas"],
                                   default="Ambas", required=True)
    especies = {"Dourada": ["dourada"], "Robalo": ["robalo"], "Ambas": ["dourada", "robalo"]}[escolha]

    tipo_temperatura = st.segmented_control(
        "Temperatura da água", ["Constante", "Sazonal"], default="Sazonal", required=True,
        help="**Constante:** tanque ou RAS com temperatura controlada.  \n"
             "**Sazonal:** jaula no mar; a temperatura varia ± 4 °C ao longo do ano "
             "(mínimo em fevereiro, máximo em agosto). Entrada dos peixes a 1 de abril.")
    if tipo_temperatura == "Constante":
        temperatura_c = st.slider("Temperatura (°C)", 14.0, TEMPERATURA_MAXIMA_VALIDA, 20.0, 0.5)
        temperatura = np.full(N_DIAS, temperatura_c)
    else:
        media = st.slider("Temperatura média anual (°C)", 15.0, 21.0, 19.0, 0.5)
        _, temperatura = perfil_temperatura(N_DIAS, media=media)

    alimentacao = st.segmented_control(
        "Alimentação", ["saciedade", "restrita"], default="saciedade", required=True,
        format_func=lambda a: "Até à saciedade" if a == "saciedade" else "Restrita",
        help="**Restrita:** 80 % da saciedade na dourada (Bonaldo et al., 2010) e "
             "75 % no robalo (Türkmen et al., 2012).")

    peso_comercial = st.slider("Tamanho comercial (g)", 250, 600, 400, 25)

    st.divider()
    st.caption(f"Dados simulados · [Código e notebooks no GitHub]({URL_GITHUB})")


# ---------------------------------------------------------------------------
# 2. Simulação
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def simular(especie, temperatura, alimentacao):
    """Corre a simulação (o resultado fica guardado para não repetir contas)."""
    cenario = CENARIOS_ALIMENTACAO[especie][alimentacao]
    return simular_ciclo(especie, n_dias=N_DIAS, n_peixes=N_PEIXES, temperatura=temperatura,
                         fator_crescimento=cenario["fator_crescimento"],
                         fcr=PARAMETROS[especie]["fcr"] * cenario["fator_fcr"], semente=42)


with st.spinner("A simular..."):
    simulacoes = {e: simular(e, temperatura, alimentacao) for e in especies}
dias_alvo = {e: dias_ate_peso(s, peso_comercial) for e, s in simulacoes.items()}


# ---------------------------------------------------------------------------
# 3. Cabeçalho
# ---------------------------------------------------------------------------
st.title("🐟 Crescimento de dourada e robalo")
st.markdown("Quanto tempo demora um peixe de aquacultura a chegar ao tamanho comercial? "
            "Muda a **temperatura**, a **alimentação** e a **espécie** na barra lateral.")
st.caption(":material/science: Resultados **simulados** com parâmetros da literatura científica; "
           "não são dados de nenhuma exploração.")


# ---------------------------------------------------------------------------
# 4. Números principais (um cartão por espécie)
# ---------------------------------------------------------------------------
colunas = st.columns(len(especies), gap="medium")
for coluna, especie in zip(colunas, especies):
    sim = simulacoes[especie]
    dia = dias_alvo[especie]
    with coluna.container(border=True):
        cor = "orange" if especie == "dourada" else "blue"
        st.markdown(f"#### :{cor}[●] {NOMES[especie]} &nbsp;*:gray[{CIENTIFICOS[especie]}]*")
        if dia is None:
            st.error(f"Não chega aos {peso_comercial} g em {N_DIAS} dias.")
            continue
        ate_peso = sim.loc[:dia]
        ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - N_PEIXES * sim.loc[0, "peso_medio_g"] / 1000
        fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Até {peso_comercial} g", f"{dia} dias")
        c1.caption(f"≈ {virgula(dia / 30.4)} meses")
        c2.metric("FCR económico", virgula(fcr, 2),
                  help="kg de ração por kg de peixe produzido, incluindo a ração comida pelos peixes que morreram.")
        c3.metric("Sobrevivência", f"{sim.loc[dia, 'n_peixes'] / N_PEIXES:.0%}")

# Frase-resumo quando se comparam as duas espécies
if len(especies) == 2 and None not in dias_alvo.values():
    diferenca = dias_alvo["robalo"] - dias_alvo["dourada"]
    if diferenca >= 0:
        frase = "a **dourada** chega {} antes do **robalo**"
    else:
        frase = "o **robalo** chega {} antes da **dourada**"
    tempo = f"aos {peso_comercial} g **{abs(diferenca)} dias** (≈ {virgula(abs(diferenca) / 30.4)} meses)"
    st.markdown(":material/compare_arrows: Neste cenário, " + frase.format(tempo) + ".")


# ---------------------------------------------------------------------------
# 5. Gráficos
# ---------------------------------------------------------------------------
aba_crescimento, aba_modelo = st.tabs([":material/show_chart: Crescimento", ":material/info: Sobre o modelo"])

with aba_crescimento:
    dia_maximo = min(N_DIAS, int(max(d or N_DIAS for d in dias_alvo.values()) * 1.15))
    escala_x = alt.Scale(domain=[0, dia_maximo], nice=False)

    # Tabela "longa" com as duas espécies, um ponto de 2 em 2 dias (gráfico mais leve)
    dados = pd.concat([
        s.iloc[:dia_maximo:2].assign(
            nome=NOMES[e],
            minimo=lambda d: (d["peso_medio_g"] - d["peso_dp_g"]).clip(lower=0),
            maximo=lambda d: d["peso_medio_g"] + d["peso_dp_g"])
        for e, s in simulacoes.items()])
    escala_cor = alt.Scale(domain=[NOMES[e] for e in especies], range=[CORES[e] for e in especies])
    cor = alt.Color("nome:N", title=None, scale=escala_cor,
                    legend=alt.Legend(orient="top-left", direction="horizontal",
                                      symbolType="stroke", symbolStrokeWidth=3, symbolOpacity=1,
                                      labelFontSize=13))
    eixo_x = alt.X("dia:Q", scale=escala_x, title="Dias desde a entrada dos juvenis (3 g)")

    faixa = alt.Chart(dados).mark_area(opacity=0.15).encode(
        x=eixo_x, y="minimo:Q", y2="maximo:Q", color=cor)
    linha = alt.Chart(dados).mark_line(strokeWidth=2.5).encode(
        x=eixo_x,
        y=alt.Y("peso_medio_g:Q", title="Peso médio (g)", axis=alt.Axis(format="d")),
        color=cor,
        tooltip=[alt.Tooltip("nome:N", title="Espécie"), alt.Tooltip("dia:Q", title="Dia"),
                 alt.Tooltip("peso_medio_g:Q", title="Peso médio (g)", format=".0f"),
                 alt.Tooltip("peso_dp_g:Q", title="Desvio-padrão (g)", format=".0f"),
                 alt.Tooltip("temperatura_c:Q", title="Temperatura (°C)", format=".1f")])
    alvo = alt.Chart(pd.DataFrame({"y": [peso_comercial]})).mark_rule(
        strokeDash=[6, 4], color="#5B6F78").encode(y="y:Q")
    alvo_texto = alt.Chart(pd.DataFrame({"y": [peso_comercial], "x": [0]})).mark_text(
        align="left", dx=4, dy=-8, fontSize=12, color="#5B6F78").encode(
        x=alt.X("x:Q", scale=escala_x), y="y:Q", text=alt.value(f"tamanho comercial · {peso_comercial} g"))
    chegadas = pd.DataFrame([{"nome": NOMES[e], "dia": d, "peso": peso_comercial}
                             for e, d in dias_alvo.items() if d is not None])
    pontos = alt.Chart(chegadas).mark_point(filled=True, size=110, stroke="white", strokeWidth=2,
                                            opacity=1).encode(
        x=alt.X("dia:Q", scale=escala_x), y="peso:Q", color=cor,
        tooltip=[alt.Tooltip("nome:N", title="Espécie"), alt.Tooltip("dia:Q", title="Chega ao tamanho comercial no dia")])

    grafico_peso = (faixa + linha + alvo + alvo_texto + pontos).properties(
        height=380, title=alt.Title("Peso médio dos peixes",
                                    subtitle="Linha: média da jaula · sombra: ± 1 desvio-padrão entre peixes"))
    st.altair_chart(grafico_peso, width="stretch")

    dados_temp = pd.DataFrame({"dia": np.arange(dia_maximo), "temperatura": temperatura[:dia_maximo]})
    grafico_temp = alt.Chart(dados_temp).mark_area(
        line={"color": COR_TEMPERATURA, "strokeWidth": 2},
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                           stops=[alt.GradientStop(color="white", offset=0),
                                  alt.GradientStop(color=COR_TEMPERATURA, offset=1)]),
        opacity=0.35).encode(
        x=eixo_x,
        y=alt.Y("temperatura:Q", title="°C", scale=alt.Scale(domain=[10, 26])),
        y2=alt.datum(10),
        tooltip=[alt.Tooltip("dia:Q", title="Dia"), alt.Tooltip("temperatura:Q", title="Temperatura (°C)", format=".1f")]
    ).properties(height=150, title=alt.Title("Temperatura da água"))
    st.altair_chart(grafico_temp, width="stretch")


# ---------------------------------------------------------------------------
# 6. Explicação do modelo
# ---------------------------------------------------------------------------
with aba_modelo:
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
""")
    st.link_button("Ver o código, os notebooks e as referências no GitHub", URL_GITHUB,
                   icon=":material/code:")
