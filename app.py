"""
App interativa: crescimento de dourada e robalo em aquacultura.

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
Quem usa a app pode pôr os dados do seu cultivo (número e peso dos juvenis,
data de entrada, temperaturas e pesagens) para comparar com o modelo.

A app está em português e em inglês: o botão PT / EN ao lado do título muda a
língua, e o link com ?lang=en abre logo em inglês.
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
CIENTIFICOS = {"dourada": "Sparus aurata", "robalo": "Dicentrarchus labrax"}
COR_TEMPERATURA = "#0E7490"
COR_PESAGENS = "#0F2A36"
URL_GITHUB = "https://github.com/dinistcosta/aquaculture-growth-model"
URL_LINKEDIN = "https://www.linkedin.com/in/dinis-costa-a58a67380"

# Ficheiros de exemplo que a pessoa pode descarregar e preencher
MODELO_TEMPERATURAS = "data,temperatura_c\n2024-04-01,16.5\n2024-04-08,17.0\n2024-04-15,17.2\n"
MODELO_PESAGENS = "data,peso_medio_g\n2024-05-01,9.8\n2024-06-01,24.5\n2024-07-01,48.0\n"


# ---------------------------------------------------------------------------
# 0. Língua (português ou inglês)
# ---------------------------------------------------------------------------
def lingua_inicial():
    """Língua da primeira visita: ?lang= no link, senão a língua do browser, senão português."""
    pedida = st.query_params.get("lang")
    if pedida in ("pt", "en"):
        return pedida
    try:
        locale = st.context.locale or ""
    except Exception:          # versões do Streamlit sem st.context.locale
        locale = ""
    return "en" if locale and not locale.startswith("pt") else "pt"


# O botão PT / EN (no cabeçalho) guarda a escolha em st.session_state["idioma"]
idioma = st.session_state.get("idioma") or lingua_inicial()


def t(pt, en):
    """Devolve o texto na língua escolhida."""
    return pt if idioma == "pt" else en


NOMES = {"dourada": t("Dourada", "Sea bream"), "robalo": t("Robalo", "Sea bass")}
MESES = t(["jan.", "fev.", "mar.", "abr.", "maio", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."],
          ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

st.set_page_config(page_title=t("Modelo de crescimento de dourada e robalo",
                                "Sea bream and sea bass growth model"),
                   page_icon=":material/show_chart:", layout="wide")


def virgula(numero, casas=1):
    """Escreve um número com vírgula decimal em português (14,1) e ponto em inglês (14.1)."""
    texto = f"{numero:.{casas}f}"
    return texto.replace(".", ",") if idioma == "pt" else texto


def milhares(numero):
    """Escreve um número inteiro com separador de milhares (25 000 em português, 25,000 em inglês)."""
    texto = f"{numero:,.0f}"
    return texto.replace(",", " ") if idioma == "pt" else texto


def mes_e_ano(data):
    """Escreve uma data como mês e ano (ex.: out. 2025 ou Oct 2025)."""
    return f"{MESES[data.month - 1]} {data.year}"


def ler_csv(ficheiro, coluna):
    """Lê um CSV com as colunas 'data' e `coluna` (aceita ; ou , e vírgula decimal).

    Devolve uma tabela com as colunas data e valor, ordenada por data.
    """
    tabela = pd.read_csv(ficheiro, sep=None, engine="python", dtype=str)
    tabela.columns = tabela.columns.str.strip().str.lower()
    if "data" not in tabela.columns or coluna not in tabela.columns:
        raise ValueError(t(f"O ficheiro tem de ter as colunas 'data' e '{coluna}'.",
                           f"The file must have the columns 'data' and '{coluna}'."))
    # Datas no formato 2024-04-01 ou 01/04/2024 (dia primeiro, como em Portugal)
    data = pd.to_datetime(tabela["data"], format="ISO8601", errors="coerce")
    data = data.fillna(pd.to_datetime(tabela["data"], format="%d/%m/%Y", errors="coerce"))
    tabela = pd.DataFrame({
        "data": data,
        "valor": pd.to_numeric(tabela[coluna].str.replace(",", "."), errors="coerce"),
    }).dropna()
    if tabela.empty:
        raise ValueError(t("Não encontrei linhas com data e valor válidos.",
                           "No rows with a valid date and value were found."))
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
# Cada controlo tem uma `key`: assim a escolha mantém-se quando se muda de língua.
with st.sidebar:
    st.header(t("Cenário", "Scenario"))

    escolha = st.segmented_control(
        t("Espécie", "Species"), ["dourada", "robalo", "ambas"], default="ambas", required=True,
        format_func=lambda e: NOMES.get(e, t("Ambas", "Both")), key="especie")
    especies = ["dourada", "robalo"] if escolha == "ambas" else [escolha]

    sistema = st.segmented_control(
        t("Sistema de cultivo", "Farming system"), ["jaula", "tanque"], default="jaula", required=True,
        format_func=lambda s: t("Jaula no mar", "Sea cage") if s == "jaula" else t("Tanque / RAS", "Tank / RAS"),
        key="sistema",
        help=t("**Jaula no mar:** a temperatura é a do mar e varia ± 4 °C ao longo do ano "
               "(mínimo em fevereiro, máximo em agosto).  \n"
               "**Tanque / RAS:** tanque em terra com temperatura controlada (constante).",
               "**Sea cage:** water temperature follows the sea and varies by ± 4 °C over the year "
               "(lowest in February, highest in August).  \n"
               "**Tank / RAS:** land-based tank with controlled (constant) temperature."))
    densidade = None
    imta = False
    if sistema == "jaula":
        media = st.slider(t("Temperatura média anual do mar (°C)", "Mean annual sea temperature (°C)"),
                          15.0, 21.0, 19.0, 0.5, key="media")
        if "robalo" in especies:
            imta = st.toggle(
                t("IMTA (robalo)", "IMTA (sea bass)"), key="imta",
                help=t("Robalo cultivado com mexilhões, ostras e pepinos-do-mar: FCR × "
                       f"{virgula(FATOR_FCR_IMTA, 2)}, crescimento igual (Cotou et al., 2024; ensaio piloto de 90 dias).",
                       "Sea bass farmed together with mussels, oysters and sea cucumbers: FCR × "
                       f"{virgula(FATOR_FCR_IMTA, 2)}, same growth (Cotou et al., 2024; 90-day pilot trial)."))
    else:
        temperatura_tanque = st.slider(
            t("Temperatura do tanque (°C)", "Tank temperature (°C)"),
            14.0, TEMPERATURA_MAXIMA_VALIDA, TEMPERATURA_TANQUE, 0.5, key="temperatura_tanque",
            help=t(f"{virgula(TEMPERATURA_TANQUE, 0)} °C é o meio do intervalo 18–26 °C indicado pela FAO (2009). "
                   f"O modelo não é válido acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C.",
                   f"{virgula(TEMPERATURA_TANQUE, 0)} °C is the middle of the 18–26 °C range given by FAO (2009). "
                   f"The model is not valid above {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C."))
        densidade = st.slider(
            t("Densidade (kg/m³)", "Stocking density (kg/m³)"), 10, DENSIDADE_MAXIMA, 40, 5, key="densidade",
            help=t(f"No robalo, até {DENSIDADE_SEM_EFEITO} kg/m³ não há efeito no crescimento; "
                   f"a {DENSIDADE_MAXIMA} kg/m³ a SGR desce 14 % (Sammouth et al., 2009). "
                   "Na dourada não encontrámos dados, por isso a densidade só serve para calcular o volume de tanque.",
                   f"In sea bass, density has no effect on growth up to {DENSIDADE_SEM_EFEITO} kg/m³; "
                   f"at {DENSIDADE_MAXIMA} kg/m³ SGR drops by 14 % (Sammouth et al., 2009). "
                   "No data were found for sea bream, so density is only used to compute tank volume."))

    alimentacao = st.segmented_control(
        t("Alimentação", "Feeding"), ["saciedade", "restrita"], default="saciedade", required=True,
        format_func=lambda a: t("Até à saciedade", "To satiation") if a == "saciedade" else t("Restrita", "Restricted"),
        key="alimentacao",
        help=t("**Restrita:** 80 % da saciedade na dourada (Bonaldo et al., 2010) e "
               "75 % no robalo (Türkmen et al., 2012).",
               "**Restricted:** 80 % of satiation in sea bream (Bonaldo et al., 2010) and "
               "75 % in sea bass (Türkmen et al., 2012)."))

    peso_comercial = st.slider(t("Tamanho comercial (g)", "Market size (g)"), 250, 600, 400, 25,
                               key="peso_comercial")

    st.header(t("Dados da exploração", "Farm data"))
    st.caption(t("Opcional. Os ficheiros são lidos apenas no browser e não são enviados para nenhum servidor.",
                 "Optional. Files are read only in the browser and are not sent to any server."))
    n_juvenis = st.number_input(t("Número de juvenis", "Number of juveniles"), 100, 5_000_000, N_PEIXES, 1000,
                                key="n_juvenis")
    peso_inicial = st.number_input(
        t("Peso dos juvenis à entrada (g)", "Juvenile weight at stocking (g)"), 1.0, 50.0, PESO_INICIAL_G, 0.5,
        key="peso_inicial",
        help=t("O modelo foi feito para juvenis de 2–4 g; acima de 50 g não é fiável.",
               "The model was built for 2–4 g juveniles; above 50 g it is not reliable."))
    data_entrada = st.date_input(t("Data de entrada", "Stocking date"), datetime.date(2024, 4, 1),
                                 format="DD/MM/YYYY", key="data_entrada")

    with st.expander(t("Carregar medições (CSV)", "Upload measurements (CSV)")):
        st.markdown(t("Um ficheiro por tipo de medição, com uma linha por medição. "
                      "Pode ser exportado do Excel (separador `;` ou `,`).",
                      "One file per type of measurement, one row per measurement. "
                      "It can be exported from Excel (`;` or `,` separator). "
                      "Column names stay in Portuguese, as in the example files."))
        ficheiro_temp = st.file_uploader(
            t("Temperaturas da água", "Water temperatures"), type="csv", key="ficheiro_temp",
            help=t("Colunas: data, temperatura_c. Substituem a temperatura acima.",
                   "Columns: data (date), temperatura_c. They replace the temperature above."))
        st.download_button(t("Exemplo de temperaturas", "Temperature example"), MODELO_TEMPERATURAS,
                           "exemplo_temperaturas.csv", "text/csv", icon=":material/download:")
        ficheiro_pesos = st.file_uploader(
            t("Pesagens (peso médio da amostra)", "Weighings (mean sample weight)"), type="csv", key="ficheiro_pesos",
            help=t("Colunas: data, peso_medio_g. Aparecem no gráfico do peso.",
                   "Columns: data (date), peso_medio_g. They are shown on the weight chart."))
        st.download_button(t("Exemplo de pesagens", "Weighing example"), MODELO_PESAGENS,
                           "exemplo_pesagens.csv", "text/csv", icon=":material/download:")

    st.divider()
    st.caption(t("Dados simulados", "Simulated data") + f" · [GitHub]({URL_GITHUB})")
    st.caption(f"Dinis Costa · [LinkedIn]({URL_LINKEDIN})")


# ---------------------------------------------------------------------------
# 2. Temperatura e dados carregados
# ---------------------------------------------------------------------------
datas, curva_sazonal = perfil_temperatura(N_DIAS, data_inicio=str(data_entrada),
                                          media=media if sistema == "jaula" else 19.0)
if sistema == "jaula":
    temperatura = curva_sazonal
else:
    temperatura = np.full(N_DIAS, temperatura_tanque)

avisos = []
if ficheiro_temp is not None:
    try:
        temperatura, dias_medidos = temperatura_dos_dados(ler_csv(ficheiro_temp, "temperatura_c"),
                                                          datas, temperatura)
        avisos.append(t(f"Temperatura: medições da exploração ({dias_medidos} dias do ciclo "
                        "com medições; os restantes são completados com a média do mesmo dia do ano).",
                        f"Temperature: farm measurements ({dias_medidos} days of the cycle "
                        "measured; the rest are filled with the mean for the same day of the year)."))
        if temperatura.max() > TEMPERATURA_MAXIMA_VALIDA:
            avisos.append(":material/warning: " + t(
                f"Há temperaturas acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C. "
                "O modelo não é válido aí, por isso foram limitadas a esse valor.",
                f"Some temperatures are above {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C. "
                "The model is not valid there, so they were capped at that value."))
            temperatura = np.minimum(temperatura, TEMPERATURA_MAXIMA_VALIDA)
    except Exception as erro:
        st.sidebar.error(t("Não consegui ler as temperaturas: ", "Could not read the temperatures: ") + str(erro))

pesagens = None
if ficheiro_pesos is not None:
    try:
        pesagens = ler_csv(ficheiro_pesos, "peso_medio_g")
        pesagens["dia"] = (pesagens["data"] - pd.Timestamp(data_entrada)).dt.days
        pesagens = pesagens[(pesagens["dia"] >= 0) & (pesagens["dia"] < N_DIAS)]
        if pesagens.empty:
            st.sidebar.error(t("Nenhuma pesagem é posterior à data de entrada.",
                               "No weighing is later than the stocking date."))
            pesagens = None
    except Exception as erro:
        st.sidebar.error(t("Não consegui ler as pesagens: ", "Could not read the weighings: ") + str(erro))


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


with st.spinner(t("A simular...", "Simulating...")):
    simulacoes = {e: simular_especie(e) for e in especies}
dias_alvo = {e: dias_ate_peso(s, peso_comercial) for e, s in simulacoes.items()}


# ---------------------------------------------------------------------------
# 4. Cabeçalho (com o botão da língua)
# ---------------------------------------------------------------------------
col_titulo, col_lingua = st.columns([6, 1], vertical_alignment="center")
col_titulo.title(t("Modelo de crescimento de dourada e robalo", "Sea bream and sea bass growth model"))
idioma_escolhido = col_lingua.segmented_control(
    "Idioma / Language", ["pt", "en"], default=idioma, required=True, key="idioma",
    format_func=str.upper, label_visibility="collapsed")
st.query_params["lang"] = idioma_escolhido   # o link copiado abre na mesma língua

st.markdown(t("Simulação do ciclo de engorda em aquacultura: tempo até ao tamanho comercial, biomassa e "
              "consumo de ração, consoante a espécie, o sistema de cultivo e a alimentação. "
              "Os parâmetros do cenário e os dados da exploração definem-se na barra lateral.",
              "Simulation of the grow-out cycle in aquaculture: time to market size, biomass and "
              "feed use, depending on species, farming system and feeding. "
              "Scenario parameters and farm data are set in the sidebar."))
st.caption(t("Resultados **simulados** com parâmetros da literatura científica; "
             "não são dados de nenhuma exploração.",
             "**Simulated** results based on parameters from the scientific literature; "
             "they are not data from any farm."))
st.caption(t("Autor: Dinis Costa, Mestrado em Biologia Marinha Aplicada",
             "Author: Dinis Costa, MSc in Applied Marine Biology")
           + f" · [LinkedIn]({URL_LINKEDIN}) · [GitHub]({URL_GITHUB})")
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
            st.error(t(f"Não chega aos {peso_comercial} g em {N_DIAS} dias.",
                       f"Does not reach {peso_comercial} g within {N_DIAS} days."))
            continue
        ate_peso = sim.loc[:dia]
        ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - n_juvenis * peso_inicial / 1000
        fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
        c1, c2, c3 = st.columns(3)
        c1.metric(t(f"Dias até {peso_comercial} g", f"Days to {peso_comercial} g"), dia)
        c1.caption(t(f"≈ {virgula(dia / 30.4)} meses", f"≈ {virgula(dia / 30.4)} months"))
        c2.metric(t("FCR económico", "Economic FCR"), virgula(fcr, 2),
                  help=t("kg de ração por kg de peixe produzido, incluindo a ração comida pelos peixes que morreram.",
                         "kg of feed per kg of fish produced, including feed eaten by fish that died."))
        c3.metric(t("Sobrevivência", "Survival"), f"{sim.loc[dia, 'n_peixes'] / n_juvenis:.0%}")
        st.caption(t("Despesca prevista: ", "Expected harvest: ") + mes_e_ano(sim.loc[dia, "data"]))

# Frase-resumo quando se comparam as duas espécies
if len(especies) == 2 and None not in dias_alvo.values():
    diferenca = dias_alvo["robalo"] - dias_alvo["dourada"]
    rapida, lenta = ("dourada", "robalo") if diferenca >= 0 else ("robalo", "dourada")
    meses = virgula(abs(diferenca) / 30.4)
    if idioma == "pt":
        artigo = {"dourada": "a", "robalo": "o"}
        frase = (f"Neste cenário, {artigo[rapida]} **{NOMES[rapida].lower()}** chega aos {peso_comercial} g "
                 f"**{abs(diferenca)} dias** (≈ {meses} meses) antes {'da' if lenta == 'dourada' else 'do'} "
                 f"**{NOMES[lenta].lower()}**.")
    else:
        frase = (f"In this scenario, **{NOMES[rapida].lower()}** reaches {peso_comercial} g "
                 f"**{abs(diferenca)} days** (≈ {meses} months) before **{NOMES[lenta].lower()}**.")
    st.markdown(frase)


# ---------------------------------------------------------------------------
# 6. Gráficos
# ---------------------------------------------------------------------------
aba_crescimento, aba_biomassa, aba_dados, aba_modelo = st.tabs(
    t(["Crescimento", "Biomassa e ração", "Dados", "Sobre o modelo"],
      ["Growth", "Biomass and feed", "Data", "About the model"]))

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
                   title=t("Dias desde a entrada dos juvenis", "Days since stocking of juveniles")
                   + f" ({virgula(peso_inicial, 1).replace(',0', '').replace('.0', '')} g)")
    especie_tt = alt.Tooltip("nome:N", title=t("Espécie", "Species"))
    dia_tt = alt.Tooltip("dia:Q", title=t("Dia", "Day"))

    faixa = alt.Chart(dados).mark_area(opacity=0.15).encode(
        x=eixo_x, y="minimo:Q", y2="maximo:Q", color=cor)
    linha = alt.Chart(dados).mark_line(strokeWidth=2.5).encode(
        x=eixo_x,
        y=alt.Y("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), axis=alt.Axis(format="d")),
        color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("data:T", title=t("Data", "Date"), format="%d/%m/%Y"),
                 alt.Tooltip("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), format=".0f"),
                 alt.Tooltip("peso_dp_g:Q", title=t("Desvio-padrão (g)", "Standard deviation (g)"), format=".0f"),
                 alt.Tooltip("temperatura_c:Q", title=t("Temperatura (°C)", "Temperature (°C)"), format=".1f")])
    alvo = alt.Chart(pd.DataFrame({"y": [peso_comercial]})).mark_rule(
        strokeDash=[6, 4], color="#5B6F78").encode(y="y:Q")
    alvo_texto = alt.Chart(pd.DataFrame({"y": [peso_comercial], "x": [0]})).mark_text(
        align="left", dx=4, dy=-8, fontSize=12, color="#5B6F78").encode(
        x=alt.X("x:Q", scale=escala_x), y="y:Q",
        text=alt.value(t("tamanho comercial", "market size") + f" · {peso_comercial} g"))
    chegadas = pd.DataFrame([{"nome": NOMES[e], "dia": d, "peso": peso_comercial}
                             for e, d in dias_alvo.items() if d is not None])
    pontos = alt.Chart(chegadas).mark_point(filled=True, size=110, stroke="white", strokeWidth=2,
                                            opacity=1).encode(
        x=alt.X("dia:Q", scale=escala_x), y="peso:Q", color=cor,
        tooltip=[especie_tt, alt.Tooltip("dia:Q", title=t("Chega ao tamanho comercial no dia",
                                                          "Reaches market size on day"))])

    camadas = faixa + linha + alvo + alvo_texto + pontos
    subtitulo = t("Linha: média da jaula · sombra: ± 1 desvio-padrão entre peixes",
                  "Line: population mean · shading: ± 1 standard deviation between fish")
    if pesagens is not None:
        # As pesagens da exploração, como losangos escuros por cima das curvas do modelo
        camadas += alt.Chart(pesagens).mark_point(shape="diamond", filled=True, size=90,
                                                  color=COR_PESAGENS, opacity=0.9).encode(
            x=alt.X("dia:Q", scale=escala_x), y="valor:Q",
            tooltip=[alt.Tooltip("data:T", title=t("Pesagem", "Weighing"), format="%d/%m/%Y"), dia_tt,
                     alt.Tooltip("valor:Q", title=t("Peso médio medido (g)", "Measured mean weight (g)"),
                                 format=".1f")])
        subtitulo += t(" · ◆ pesagens da exploração", " · ◆ farm weighings")

    grafico_peso = camadas.properties(
        height=380, title=alt.Title(t("Peso médio dos peixes", "Mean fish weight"), subtitle=subtitulo))
    st.altair_chart(grafico_peso, width="stretch")

    # Comparação das pesagens com o modelo, no mesmo dia
    if pesagens is not None:
        medido = t("Medido (g)", "Measured (g)")
        modelo = {e: t(f"{NOMES[e]}: modelo (g)", f"{NOMES[e]}: model (g)") for e in especies}
        comparacao = pesagens.rename(columns={"valor": medido})
        comparacao[t("Data", "Date")] = comparacao["data"].dt.strftime("%d/%m/%Y")
        for e, s in simulacoes.items():
            comparacao[modelo[e]] = s.loc[comparacao["dia"], "peso_medio_g"].round(1).to_numpy()
        st.markdown(t("**Pesagens da exploração vs. modelo**", "**Farm weighings vs. model**"))
        st.dataframe(comparacao.drop(columns="data").rename(columns={"dia": t("Dia", "Day")})
                     [[t("Data", "Date"), t("Dia", "Day"), medido] + [modelo[e] for e in especies]],
                     hide_index=True)
        st.caption(t("Se as pesagens ficam sistematicamente abaixo (ou acima) da curva, o cultivo cresce "
                     "mais devagar (ou mais depressa) do que os estudos usados no modelo.",
                     "If the weighings fall consistently below (or above) the curve, the farm grows "
                     "more slowly (or faster) than the studies used in the model."))

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
        tooltip=[dia_tt, alt.Tooltip("temperatura:Q", title=t("Temperatura (°C)", "Temperature (°C)"),
                                     format=".1f")]
    ).properties(height=150, title=alt.Title(t("Temperatura da água", "Water temperature")))
    st.altair_chart(grafico_temp, width="stretch")


# ---------------------------------------------------------------------------
# 7. Biomassa e ração gasta (até ao tamanho comercial)
# ---------------------------------------------------------------------------
with aba_biomassa:
    peso_juvenis = virgula(peso_inicial).replace(",0", "").replace(".0", "")
    st.markdown(t(f"**{milhares(n_juvenis)} juvenis** de {peso_juvenis} g. "
                  "A biomassa é o peso total dos peixes vivos; a ração é a soma da ração dada desde o início.",
                  f"**{milhares(n_juvenis)} juveniles** of {peso_juvenis} g. "
                  "Biomass is the total weight of live fish; feed is the sum of feed given since stocking."))

    # Uma linha por espécie e por dia, com a ração acumulada
    dados_bio = pd.concat([
        s.iloc[:dia_maximo:2].assign(nome=NOMES[e], racao_acumulada=s["racao_kg"].cumsum().iloc[:dia_maximo:2])
        for e, s in simulacoes.items()])

    grafico_biomassa = alt.Chart(dados_bio).mark_line(strokeWidth=2.5).encode(
        x=eixo_x, y=alt.Y("biomassa_kg:Q", title=t("Biomassa (kg)", "Biomass (kg)")), color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("biomassa_kg:Q", title=t("Biomassa (kg)", "Biomass (kg)"), format=",.0f"),
                 alt.Tooltip("n_peixes:Q", title=t("Peixes vivos", "Live fish"), format=",")]
    ).properties(height=260, title=alt.Title(t("Biomassa", "Biomass")))
    grafico_racao = alt.Chart(dados_bio).mark_line(strokeWidth=2.5, strokeDash=[6, 3]).encode(
        x=eixo_x, y=alt.Y("racao_acumulada:Q", title=t("Ração (kg)", "Feed (kg)")), color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("racao_acumulada:Q", title=t("Ração acumulada (kg)", "Cumulative feed (kg)"),
                             format=",.0f")]
    ).properties(height=260, title=alt.Title(t("Ração acumulada", "Cumulative feed")))

    col_bio, col_racao = st.columns(2, gap="medium")
    col_bio.altair_chart(grafico_biomassa, width="stretch")
    col_racao.altair_chart(grafico_racao, width="stretch")

    # Resumo no dia em que cada espécie chega ao tamanho comercial
    linhas = []
    for e, d in dias_alvo.items():
        if d is None:
            continue
        linha = {t("Espécie", "Species"): NOMES[e], t("Dias", "Days"): d,
                 t("Peixes vivos", "Live fish"): milhares(simulacoes[e].loc[d, "n_peixes"]),
                 t("Biomassa (kg)", "Biomass (kg)"): milhares(simulacoes[e].loc[d, "biomassa_kg"]),
                 t("Ração gasta (kg)", "Feed used (kg)"): milhares(simulacoes[e].loc[:d, "racao_kg"].sum())}
        if densidade is not None:
            linha[t("Volume de tanque (m³)", "Tank volume (m³)")] = virgula(
                simulacoes[e].loc[d, "biomassa_kg"] / densidade)
        linhas.append(linha)
    if linhas:
        st.markdown(t(f"**No dia em que chega aos {peso_comercial} g**", f"**On the day it reaches {peso_comercial} g**"))
        st.dataframe(pd.DataFrame(linhas), hide_index=True)
        if densidade is not None:
            st.caption(t(f"Volume de tanque necessário para ter essa biomassa a {densidade} kg/m³.",
                         f"Tank volume needed to hold that biomass at {densidade} kg/m³."))


# ---------------------------------------------------------------------------
# 8. Tabela com os dados simulados (para descarregar)
# ---------------------------------------------------------------------------
with aba_dados:
    st.markdown(t("Valores diários da simulação, até ao fim do gráfico. **Dados simulados.**",
                  "Daily values from the simulation, up to the end of the chart. **Simulated data.**"))
    colunas_tabela = ["especie", "dia", "data", "temperatura_c", "n_peixes",
                      "peso_medio_g", "peso_dp_g", "biomassa_kg", "racao_kg", "mortos"]
    tabela = pd.concat([s.iloc[:dia_maximo][colunas_tabela] for s in simulacoes.values()])
    tabela = tabela.round({"peso_medio_g": 1, "peso_dp_g": 1, "biomassa_kg": 1, "racao_kg": 2})
    if idioma == "en":
        # Em inglês, a tabela e o CSV também ficam com nomes em inglês
        tabela = tabela.replace({"especie": {"dourada": "sea_bream", "robalo": "sea_bass"}}).rename(columns={
            "especie": "species", "dia": "day", "data": "date", "temperatura_c": "temperature_c",
            "n_peixes": "n_fish", "peso_medio_g": "mean_weight_g", "peso_dp_g": "weight_sd_g",
            "biomassa_kg": "biomass_kg", "racao_kg": "feed_kg", "mortos": "deaths"})
    st.dataframe(tabela, hide_index=True, height=320)
    st.download_button(t("Descarregar CSV", "Download CSV"), tabela.to_csv(index=False).encode("utf-8"),
                       file_name=t("simulacao_crescimento.csv", "growth_simulation.csv"), mime="text/csv",
                       icon=":material/download:")


# ---------------------------------------------------------------------------
# 9. Explicação do modelo
# ---------------------------------------------------------------------------
SOBRE_PT = r"""
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
"""

SOBRE_EN = r"""
Each fish grows, day by day, according to

$$\frac{dW}{dt} = a \cdot W^{\,b} \cdot e^{\,c \cdot T}$$

where $W$ is weight (g) and $T$ is temperature (°C). 1,000 juveniles are simulated, with individual
variation in growth and daily mortality; for a different number of juveniles, totals (biomass, feed,
live fish) scale in the same proportion.

| | Sea bream | Sea bass |
|---|---|---|
| a · b · c | 0.024 · 0.514 · 0.060 (Hernández et al., 2003) | 0.010 · 0.68 · 0.05 (Lanari et al., 2002) × 1.14 (calibration) |
| Survival over the cycle | 80 % (Muniesa et al., 2020) | 85 % (Muniesa et al., 2020) |
| FCR | 2.1 (Kallitsis & Avramidis, 2025) | 2.2 (Kallitsis & Avramidis, 2025) |
| Restricted feeding | 80 %: growth × 0.92, FCR × 0.83 (Bonaldo et al., 2010) | 75 %: growth × 0.88, same FCR (Türkmen et al., 2012) |
| Density in tank / RAS | no data | no effect up to 70 kg/m³; 100 kg/m³: growth × 0.86 (Sammouth et al., 2009) |
| IMTA | no data | FCR × 0.89 (Cotou et al., 2024) |

**Farming systems:** in sea cages, temperature follows a seasonal curve (assumption, ± 4 °C);
in tanks / RAS it is constant, 22 °C by default (middle of the FAO 18–26 °C range, 2009).

**Farm data:** temperatures are interpolated to one value per day; days of the cycle without
measurements use the mean for the same day of the year. Weighings do not change the simulation:
they show whether the farm grows as the model predicts.

**Limitations:** the model has no optimum temperature (so temperature is capped at 25 °C),
mortality is constant, and the effects of feeding, density and IMTA come from short trials.
"""

with aba_modelo:
    st.markdown(t(SOBRE_PT, SOBRE_EN))
    st.link_button(t("Ver o código, os notebooks e as referências no GitHub",
                     "View the code, notebooks and references on GitHub"), URL_GITHUB,
                   icon=":material/code:")
    st.caption(t("Autor: Dinis Costa", "Author: Dinis Costa")
               + f" · [LinkedIn]({URL_LINKEDIN})")
