"""
App interativa: crescimento de dourada e robalo em aquacultura.

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
Quem usa a app pode pôr os dados do seu cultivo (número e peso dos juvenis,
data de entrada, temperaturas e pesagens) para comparar com o modelo.
"""

import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.growth import (PARAMETROS, CENARIOS_ALIMENTACAO, TEMPERATURA_MAXIMA_VALIDA, PESO_INICIAL_G,
                        perfil_temperatura, simular_ciclo, dias_ate_peso)
from src.regimes import (TEMPERATURA_TANQUE, DENSIDADE_SEM_EFEITO, DENSIDADE_MAXIMA,
                         fator_crescimento_densidade, FATOR_FCR_IMTA)

N_DIAS = 1400      # chega para todos os cenários possíveis com os controlos
N_PEIXES = 1000    # peixes simulados; os resultados são depois escalados ao nº de juvenis
CORES = {"dourada": "#C9971C", "robalo": "#2F6690"}
NOMES = {"dourada": "Dourada", "robalo": "Robalo"}
CIENTIFICOS = {"dourada": "Sparus aurata", "robalo": "Dicentrarchus labrax"}
COR_TEMPERATURA = "#0E7490"
COR_PESAGENS = "#0F2A36"
URL_GITHUB = "https://github.com/dinistcosta/aquaculture-growth-model"

# Ficheiros de exemplo que a pessoa pode descarregar e preencher
MODELO_TEMPERATURAS = "data,temperatura_c\n2024-04-01,16.5\n2024-04-08,17.0\n2024-04-15,17.2\n"
MODELO_PESAGENS = "data,peso_medio_g\n2024-05-01,9.8\n2024-06-01,24.5\n2024-07-01,48.0\n"

st.set_page_config(page_title="Modelo de crescimento de dourada e robalo",
                   page_icon=":material/show_chart:", layout="wide")


MESES = ["jan.", "fev.", "mar.", "abr.", "maio", "jun.",
         "jul.", "ago.", "set.", "out.", "nov.", "dez."]


def virgula(numero, casas=1):
    """Escreve um número com vírgula decimal (ex.: 14,1)."""
    return f"{numero:.{casas}f}".replace(".", ",")


def milhares(numero):
    """Escreve um número inteiro com espaço nos milhares (ex.: 25 000)."""
    return f"{numero:,.0f}".replace(",", " ")


def mes_e_ano(data):
    """Escreve uma data como mês e ano em português (ex.: out. 2025)."""
    return f"{MESES[data.month - 1]} {data.year}"


def ler_csv(ficheiro, coluna):
    """Lê um CSV com as colunas 'data' e `coluna` (aceita ; ou , e vírgula decimal).

    Devolve uma tabela com as colunas data e valor, ordenada por data.
    """
    tabela = pd.read_csv(ficheiro, sep=None, engine="python", dtype=str)
    tabela.columns = tabela.columns.str.strip().str.lower()
    if "data" not in tabela.columns or coluna not in tabela.columns:
        raise ValueError(f"O ficheiro tem de ter as colunas 'data' e '{coluna}'.")
    # Datas no formato 2024-04-01 ou 01/04/2024 (dia primeiro, como em Portugal)
    data = pd.to_datetime(tabela["data"], format="ISO8601", errors="coerce")
    data = data.fillna(pd.to_datetime(tabela["data"], format="%d/%m/%Y", errors="coerce"))
    tabela = pd.DataFrame({
        "data": data,
        "valor": pd.to_numeric(tabela[coluna].str.replace(",", "."), errors="coerce"),
    }).dropna()
    if tabela.empty:
        raise ValueError("Não encontrei linhas com data e valor válidos.")
    return tabela.sort_values("data")


def temperatura_dos_dados(tabela, datas, reserva):
    """Temperatura diária do ciclo a partir das medições da pessoa.

    1) As medições são interpoladas para ter um valor por dia.
    2) Dias do ciclo sem medição: média do mesmo dia do ano nas medições.
    3) Se ainda faltar algum dia, usa a curva `reserva` (curva sazonal).
    Devolve a temperatura e o número de dias do ciclo cobertos pelas medições.
    """
    diaria = tabela.groupby("data")["valor"].mean().resample("D").mean().interpolate()
    temperatura = diaria.reindex(datas).to_numpy(dtype=float, copy=True)
    dias_medidos = int((~np.isnan(temperatura)).sum())

    media_dia_do_ano = diaria.groupby(diaria.index.day_of_year).mean()
    falta = np.isnan(temperatura)
    temperatura[falta] = datas.day_of_year[falta].map(media_dia_do_ano).to_numpy(dtype=float)

    falta = np.isnan(temperatura)
    temperatura[falta] = reserva[falta]
    return temperatura, dias_medidos


# ---------------------------------------------------------------------------
# 1. Escolhas do utilizador (barra lateral)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Cenário")

    escolha = st.segmented_control("Espécie", ["Dourada", "Robalo", "Ambas"],
                                   default="Ambas", required=True)
    especies = {"Dourada": ["dourada"], "Robalo": ["robalo"], "Ambas": ["dourada", "robalo"]}[escolha]

    sistema = st.segmented_control(
        "Sistema de cultivo", ["Jaula no mar", "Tanque / RAS"], default="Jaula no mar", required=True,
        help="**Jaula no mar:** a temperatura é a do mar e varia ± 4 °C ao longo do ano "
             "(mínimo em fevereiro, máximo em agosto).  \n"
             "**Tanque / RAS:** tanque em terra com temperatura controlada (constante).")
    densidade = None
    imta = False
    if sistema == "Jaula no mar":
        media = st.slider("Temperatura média anual do mar (°C)", 15.0, 21.0, 19.0, 0.5)
        if "robalo" in especies:
            imta = st.toggle(
                "IMTA (robalo)",
                help="Robalo cultivado com mexilhões, ostras e pepinos-do-mar: FCR × "
                     f"{virgula(FATOR_FCR_IMTA, 2)}, crescimento igual (Cotou et al., 2024; ensaio piloto de 90 dias).")
    else:
        temperatura_tanque = st.slider(
            "Temperatura do tanque (°C)", 14.0, TEMPERATURA_MAXIMA_VALIDA, TEMPERATURA_TANQUE, 0.5,
            help=f"{virgula(TEMPERATURA_TANQUE, 0)} °C é o meio do intervalo 18–26 °C indicado pela FAO (2009). "
                 f"O modelo não é válido acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C.")
        densidade = st.slider(
            "Densidade (kg/m³)", 10, DENSIDADE_MAXIMA, 40, 5,
            help=f"No robalo, até {DENSIDADE_SEM_EFEITO} kg/m³ não há efeito no crescimento; "
                 f"a {DENSIDADE_MAXIMA} kg/m³ a SGR desce 14 % (Sammouth et al., 2009). "
                 "Na dourada não encontrámos dados, por isso a densidade só serve para calcular o volume de tanque.")

    alimentacao = st.segmented_control(
        "Alimentação", ["saciedade", "restrita"], default="saciedade", required=True,
        format_func=lambda a: "Até à saciedade" if a == "saciedade" else "Restrita",
        help="**Restrita:** 80 % da saciedade na dourada (Bonaldo et al., 2010) e "
             "75 % no robalo (Türkmen et al., 2012).")

    peso_comercial = st.slider("Tamanho comercial (g)", 250, 600, 400, 25)

    st.header("Dados da exploração")
    st.caption("Opcional. Os ficheiros são lidos apenas no browser e não são enviados para nenhum servidor.")
    n_juvenis = st.number_input("Número de juvenis", 100, 5_000_000, N_PEIXES, 1000)
    peso_inicial = st.number_input("Peso dos juvenis à entrada (g)", 1.0, 50.0, PESO_INICIAL_G, 0.5,
                                   help="O modelo foi feito para juvenis de 2–4 g; acima de 50 g não é fiável.")
    data_entrada = st.date_input("Data de entrada", datetime.date(2024, 4, 1), format="DD/MM/YYYY")

    with st.expander("Carregar medições (CSV)"):
        st.markdown("Um ficheiro por tipo de medição, com uma linha por medição. "
                    "Pode ser exportado do Excel (separador `;` ou `,`).")
        ficheiro_temp = st.file_uploader("Temperaturas da água", type="csv",
                                         help="Colunas: data, temperatura_c. Substituem a temperatura acima.")
        st.download_button("Exemplo de temperaturas", MODELO_TEMPERATURAS, "exemplo_temperaturas.csv",
                           "text/csv", icon=":material/download:")
        ficheiro_pesos = st.file_uploader("Pesagens (peso médio da amostra)", type="csv",
                                          help="Colunas: data, peso_medio_g. Aparecem no gráfico do peso.")
        st.download_button("Exemplo de pesagens", MODELO_PESAGENS, "exemplo_pesagens.csv",
                           "text/csv", icon=":material/download:")

    st.divider()
    st.caption(f"Dados simulados · [Código e notebooks no GitHub]({URL_GITHUB})")


# ---------------------------------------------------------------------------
# 2. Temperatura e dados carregados
# ---------------------------------------------------------------------------
datas, curva_sazonal = perfil_temperatura(N_DIAS, data_inicio=str(data_entrada),
                                          media=media if sistema == "Jaula no mar" else 19.0)
if sistema == "Jaula no mar":
    temperatura = curva_sazonal
else:
    temperatura = np.full(N_DIAS, temperatura_tanque)

avisos = []
if ficheiro_temp is not None:
    try:
        temperatura, dias_medidos = temperatura_dos_dados(ler_csv(ficheiro_temp, "temperatura_c"),
                                                          datas, temperatura)
        avisos.append(f"Temperatura: medições da exploração ({dias_medidos} dias do ciclo "
                      "com medições; os restantes são completados com a média do mesmo dia do ano).")
        if temperatura.max() > TEMPERATURA_MAXIMA_VALIDA:
            avisos.append(f":material/warning: Há temperaturas acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C. "
                          "O modelo não é válido aí, por isso foram limitadas a esse valor.")
            temperatura = np.minimum(temperatura, TEMPERATURA_MAXIMA_VALIDA)
    except Exception as erro:
        st.sidebar.error(f"Não consegui ler as temperaturas: {erro}")

pesagens = None
if ficheiro_pesos is not None:
    try:
        pesagens = ler_csv(ficheiro_pesos, "peso_medio_g")
        pesagens["dia"] = (pesagens["data"] - pd.Timestamp(data_entrada)).dt.days
        pesagens = pesagens[(pesagens["dia"] >= 0) & (pesagens["dia"] < N_DIAS)]
        if pesagens.empty:
            st.sidebar.error("Nenhuma pesagem é posterior à data de entrada.")
            pesagens = None
    except Exception as erro:
        st.sidebar.error(f"Não consegui ler as pesagens: {erro}")


# ---------------------------------------------------------------------------
# 3. Simulação
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def simular(especie, temperatura, fator_crescimento, fcr, peso_inicial, data_entrada):
    """Corre a simulação (o resultado fica guardado para não repetir contas)."""
    return simular_ciclo(especie, n_dias=N_DIAS, n_peixes=N_PEIXES, temperatura=temperatura,
                         data_inicio=str(data_entrada), peso_inicial_g=peso_inicial,
                         fator_crescimento=fator_crescimento, fcr=fcr, semente=42)


def simular_especie(especie):
    """Junta os efeitos do cenário escolhido e escala o resultado ao nº de juvenis."""
    cenario = CENARIOS_ALIMENTACAO[especie][alimentacao]
    fator_crescimento = cenario["fator_crescimento"]
    fcr = PARAMETROS[especie]["fcr"] * cenario["fator_fcr"]
    if especie == "robalo" and densidade is not None:
        fator_crescimento *= fator_crescimento_densidade(densidade)
    if especie == "robalo" and imta:
        fcr *= FATOR_FCR_IMTA
    sim = simular(especie, temperatura, fator_crescimento, fcr, peso_inicial, data_entrada)

    # Simulamos 1 000 peixes; para outro número de juvenis, os totais crescem na mesma proporção
    escala = n_juvenis / N_PEIXES
    return sim.assign(n_peixes=(sim["n_peixes"] * escala).round().astype(int),
                      biomassa_kg=sim["biomassa_kg"] * escala,
                      racao_kg=sim["racao_kg"] * escala,
                      mortos=(sim["mortos"] * escala).round().astype(int))


with st.spinner("A simular..."):
    simulacoes = {e: simular_especie(e) for e in especies}
dias_alvo = {e: dias_ate_peso(s, peso_comercial) for e, s in simulacoes.items()}


# ---------------------------------------------------------------------------
# 4. Cabeçalho
# ---------------------------------------------------------------------------
st.title("Modelo de crescimento de dourada e robalo")
st.markdown("Simulação do ciclo de engorda em aquacultura: tempo até ao tamanho comercial, biomassa e "
            "consumo de ração, consoante a espécie, o sistema de cultivo e a alimentação. "
            "Os parâmetros do cenário e os dados da exploração definem-se na barra lateral.")
st.caption("Resultados **simulados** com parâmetros da literatura científica; "
           "não são dados de nenhuma exploração.")
for aviso in avisos:
    st.caption(aviso)


# ---------------------------------------------------------------------------
# 5. Números principais (um cartão por espécie)
# ---------------------------------------------------------------------------
colunas = st.columns(len(especies), gap="medium")
for coluna, especie in zip(colunas, especies):
    sim = simulacoes[especie]
    dia = dias_alvo[especie]
    with coluna.container(border=True):
        # Quadrado com a cor da espécie nos gráficos
        marca = (f'<span style="display:inline-block;width:0.7em;height:0.7em;border-radius:2px;'
                 f'background:{CORES[especie]};margin-right:0.4em"></span>')
        st.markdown(f"#### {marca}{NOMES[especie]} &nbsp;*:gray[{CIENTIFICOS[especie]}]*",
                    unsafe_allow_html=True)
        if dia is None:
            st.error(f"Não chega aos {peso_comercial} g em {N_DIAS} dias.")
            continue
        ate_peso = sim.loc[:dia]
        ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - n_juvenis * peso_inicial / 1000
        fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Dias até {peso_comercial} g", dia)
        c1.caption(f"≈ {virgula(dia / 30.4)} meses")
        c2.metric("FCR económico", virgula(fcr, 2),
                  help="kg de ração por kg de peixe produzido, incluindo a ração comida pelos peixes que morreram.")
        c3.metric("Sobrevivência", f"{sim.loc[dia, 'n_peixes'] / n_juvenis:.0%}")
        st.caption(f"Despesca prevista: {mes_e_ano(sim.loc[dia, 'data'])}")

# Frase-resumo quando se comparam as duas espécies
if len(especies) == 2 and None not in dias_alvo.values():
    diferenca = dias_alvo["robalo"] - dias_alvo["dourada"]
    if diferenca >= 0:
        frase = "a **dourada** chega {} antes do **robalo**"
    else:
        frase = "o **robalo** chega {} antes da **dourada**"
    tempo = f"aos {peso_comercial} g **{abs(diferenca)} dias** (≈ {virgula(abs(diferenca) / 30.4)} meses)"
    st.markdown("Neste cenário, " + frase.format(tempo) + ".")


# ---------------------------------------------------------------------------
# 6. Gráficos
# ---------------------------------------------------------------------------
aba_crescimento, aba_biomassa, aba_dados, aba_modelo = st.tabs(
    ["Crescimento", "Biomassa e ração", "Dados", "Sobre o modelo"])

with aba_crescimento:
    dia_maximo = min(N_DIAS, int(max(d or N_DIAS for d in dias_alvo.values()) * 1.15))
    if pesagens is not None:
        dia_maximo = max(dia_maximo, min(N_DIAS, int(pesagens["dia"].max()) + 10))
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
    eixo_x = alt.X("dia:Q", scale=escala_x,
                   title=f"Dias desde a entrada dos juvenis ({virgula(peso_inicial, 1).replace(',0', '')} g)")

    faixa = alt.Chart(dados).mark_area(opacity=0.15).encode(
        x=eixo_x, y="minimo:Q", y2="maximo:Q", color=cor)
    linha = alt.Chart(dados).mark_line(strokeWidth=2.5).encode(
        x=eixo_x,
        y=alt.Y("peso_medio_g:Q", title="Peso médio (g)", axis=alt.Axis(format="d")),
        color=cor,
        tooltip=[alt.Tooltip("nome:N", title="Espécie"), alt.Tooltip("dia:Q", title="Dia"),
                 alt.Tooltip("data:T", title="Data", format="%d/%m/%Y"),
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

    camadas = faixa + linha + alvo + alvo_texto + pontos
    subtitulo = "Linha: média da jaula · sombra: ± 1 desvio-padrão entre peixes"
    if pesagens is not None:
        # As pesagens da exploração, como losangos escuros por cima das curvas do modelo
        camadas += alt.Chart(pesagens).mark_point(shape="diamond", filled=True, size=90,
                                                  color=COR_PESAGENS, opacity=0.9).encode(
            x=alt.X("dia:Q", scale=escala_x), y="valor:Q",
            tooltip=[alt.Tooltip("data:T", title="Pesagem", format="%d/%m/%Y"),
                     alt.Tooltip("dia:Q", title="Dia"),
                     alt.Tooltip("valor:Q", title="Peso médio medido (g)", format=".1f")])
        subtitulo += " · ◆ pesagens da exploração"

    grafico_peso = camadas.properties(
        height=380, title=alt.Title("Peso médio dos peixes", subtitle=subtitulo))
    st.altair_chart(grafico_peso, width="stretch")

    # Comparação das pesagens com o modelo, no mesmo dia
    if pesagens is not None:
        comparacao = pesagens.rename(columns={"valor": "Medido (g)"})
        comparacao["Data"] = comparacao["data"].dt.strftime("%d/%m/%Y")
        for e, s in simulacoes.items():
            comparacao[f"{NOMES[e]}: modelo (g)"] = s.loc[comparacao["dia"], "peso_medio_g"].round(1).to_numpy()
        st.markdown("**Pesagens da exploração vs. modelo**")
        st.dataframe(comparacao.drop(columns="data").rename(columns={"dia": "Dia"})
                     [["Data", "Dia", "Medido (g)"] + [f"{NOMES[e]}: modelo (g)" for e in especies]],
                     hide_index=True)
        st.caption("Se as pesagens ficam sistematicamente abaixo (ou acima) da curva, o cultivo cresce "
                   "mais devagar (ou mais depressa) do que os estudos usados no modelo.")

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
# 7. Biomassa e ração gasta (até ao tamanho comercial)
# ---------------------------------------------------------------------------
with aba_biomassa:
    st.markdown(f"**{milhares(n_juvenis)} juvenis** de {virgula(peso_inicial).replace(',0', '')} g. "
                "A biomassa é o peso total dos peixes vivos; a ração é a soma da ração dada desde o início.")

    # Uma linha por espécie e por dia, com a ração acumulada
    dados_bio = pd.concat([
        s.iloc[:dia_maximo:2].assign(nome=NOMES[e], racao_acumulada=s["racao_kg"].cumsum().iloc[:dia_maximo:2])
        for e, s in simulacoes.items()])

    grafico_biomassa = alt.Chart(dados_bio).mark_line(strokeWidth=2.5).encode(
        x=eixo_x, y=alt.Y("biomassa_kg:Q", title="Biomassa (kg)"), color=cor,
        tooltip=[alt.Tooltip("nome:N", title="Espécie"), alt.Tooltip("dia:Q", title="Dia"),
                 alt.Tooltip("biomassa_kg:Q", title="Biomassa (kg)", format=",.0f"),
                 alt.Tooltip("n_peixes:Q", title="Peixes vivos", format=",")]
    ).properties(height=260, title=alt.Title("Biomassa"))
    grafico_racao = alt.Chart(dados_bio).mark_line(strokeWidth=2.5, strokeDash=[6, 3]).encode(
        x=eixo_x, y=alt.Y("racao_acumulada:Q", title="Ração (kg)"), color=cor,
        tooltip=[alt.Tooltip("nome:N", title="Espécie"), alt.Tooltip("dia:Q", title="Dia"),
                 alt.Tooltip("racao_acumulada:Q", title="Ração acumulada (kg)", format=",.0f")]
    ).properties(height=260, title=alt.Title("Ração acumulada"))

    col_bio, col_racao = st.columns(2, gap="medium")
    col_bio.altair_chart(grafico_biomassa, width="stretch")
    col_racao.altair_chart(grafico_racao, width="stretch")

    # Resumo no dia em que cada espécie chega ao tamanho comercial
    linhas = []
    for e, d in dias_alvo.items():
        if d is None:
            continue
        linha = {"Espécie": NOMES[e], "Dias": d,
                 "Peixes vivos": milhares(simulacoes[e].loc[d, "n_peixes"]),
                 "Biomassa (kg)": milhares(simulacoes[e].loc[d, "biomassa_kg"]),
                 "Ração gasta (kg)": milhares(simulacoes[e].loc[:d, "racao_kg"].sum())}
        if densidade is not None:
            linha["Volume de tanque (m³)"] = virgula(simulacoes[e].loc[d, "biomassa_kg"] / densidade)
        linhas.append(linha)
    if linhas:
        st.markdown(f"**No dia em que chega aos {peso_comercial} g**")
        st.dataframe(pd.DataFrame(linhas), hide_index=True)
        if densidade is not None:
            st.caption(f"Volume de tanque necessário para ter essa biomassa a {densidade} kg/m³.")


# ---------------------------------------------------------------------------
# 8. Tabela com os dados simulados (para descarregar)
# ---------------------------------------------------------------------------
with aba_dados:
    st.markdown("Valores diários da simulação, até ao fim do gráfico. **Dados simulados.**")
    colunas_tabela = ["especie", "dia", "data", "temperatura_c", "n_peixes",
                      "peso_medio_g", "peso_dp_g", "biomassa_kg", "racao_kg", "mortos"]
    tabela = pd.concat([s.iloc[:dia_maximo][colunas_tabela] for s in simulacoes.values()])
    tabela = tabela.round({"peso_medio_g": 1, "peso_dp_g": 1, "biomassa_kg": 1, "racao_kg": 2})
    st.dataframe(tabela, hide_index=True, height=320)
    st.download_button("Descarregar CSV", tabela.to_csv(index=False).encode("utf-8"),
                       file_name="simulacao_crescimento.csv", mime="text/csv",
                       icon=":material/download:")


# ---------------------------------------------------------------------------
# 9. Explicação do modelo
# ---------------------------------------------------------------------------
with aba_modelo:
    st.markdown(r"""
Cada peixe cresce, dia a dia, segundo

$$\frac{dW}{dt} = a \cdot W^{\,b} \cdot e^{\,c \cdot T}$$

com $W$ o peso (g) e $T$ a temperatura (°C). Simulamos 1 000 juvenis, com variação individual
no crescimento e mortalidade diária; para outro número de juvenis, os totais (biomassa, ração,
peixes vivos) crescem na mesma proporção.

| | Dourada | Robalo |
|---|---|---|
| a · b · c | 0,024 · 0,514 · 0,060 (Hernández et al., 2003) | 0,010 · 0,68 · 0,05 (Lanari et al., 2002) × 1,14 (calibração) |
| Sobrevivência no ciclo | 80 % (Muniesa et al., 2020) | 85 % (Muniesa et al., 2020) |
| FCR | 2,1 (Kallitsis & Avramidis, 2025) | 2,2 (Kallitsis & Avramidis, 2025) |
| Ração restrita | 80 %: crescimento × 0,92, FCR × 0,83 (Bonaldo et al., 2010) | 75 %: crescimento × 0,88, FCR igual (Türkmen et al., 2012) |
| Densidade em tanque / RAS | sem dados | até 70 kg/m³ sem efeito; 100 kg/m³: crescimento × 0,86 (Sammouth et al., 2009) |
| IMTA | sem dados | FCR × 0,89 (Cotou et al., 2024) |

**Sistemas de cultivo:** na jaula a temperatura segue uma curva sazonal (pressuposto, ± 4 °C);
no tanque / RAS é constante, por defeito 22 °C (meio do intervalo 18–26 °C da FAO, 2009).

**Dados da exploração:** as temperaturas são interpoladas para ter um valor por dia; os dias do ciclo
sem medição usam a média do mesmo dia do ano nas medições. As pesagens não mudam a simulação:
servem para verificar se o cultivo cresce como o modelo prevê.

**Limitações:** o modelo não tem temperatura ótima (por isso a temperatura está limitada a 25 °C),
a mortalidade é constante e os efeitos da ração, da densidade e do IMTA vêm de ensaios curtos.
""")
    st.link_button("Ver o código, os notebooks e as referências no GitHub", URL_GITHUB,
                   icon=":material/code:")
