"""
App interativa: crescimento de dourada e robalo em aquacultura.

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
Quem usa a app pode pôr os dados de uma exploração (número e peso dos juvenis,
data de entrada, temperaturas e pesagens) para comparar com o modelo.

A página segue a ordem: cenário -> resultados -> modelo e referências.
Está em português e em inglês: o botão PT / EN ao lado do título muda a
língua, e o link com ?lang=en abre logo em inglês.
"""

import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.growth import (PARAMETROS, CENARIOS_ALIMENTACAO, TEMPERATURA_MAXIMA_VALIDA, PESO_INICIAL_G,
                        perfil_temperatura, simular_ciclo, dias_ate_peso, peso_critico)
from src.regimes import (TEMPERATURA_TANQUE, DENSIDADE_SEM_EFEITO, DENSIDADE_MAXIMA,
                         fator_crescimento_densidade, FATOR_FCR_IMTA)

N_DIAS = 1400      # chega para todos os cenários possíveis com os controlos
N_PEIXES = 1000    # peixes simulados; os resultados são depois escalados ao nº de juvenis
CORES = {"dourada": "#C9971C", "robalo": "#2F6690"}
CIENTIFICOS = {"dourada": "Sparus aurata", "robalo": "Dicentrarchus labrax"}
COR_TEMPERATURA = "#0E7490"
COR_PESAGENS = "#0F2A36"
COR_TEXTO = "#0F2A36"
COR_TEXTO_SUAVE = "#4A5E67"
URL_GITHUB = "https://github.com/dinistcosta/aquaculture-growth-model"
URL_LINKEDIN = "https://www.linkedin.com/in/dinis-costa-a58a67380"

# Ficheiros de exemplo que a pessoa pode descarregar e preencher
MODELO_TEMPERATURAS = "data,temperatura_c\n2024-04-01,16.5\n2024-04-08,17.0\n2024-04-15,17.2\n"
MODELO_PESAGENS = "data,peso_medio_g\n2024-05-01,9.8\n2024-06-01,24.5\n2024-07-01,48.0\n"

# Preços de partida (podem ser alterados na app):
# - venda à saída da exploração, Grécia, 2023: dourada 4,89 €/kg e robalo 6,45 €/kg
#   (EUMOFA, perfis de espécie "Gilthead seabream" e "European seabass");
# - juvenil: 0,20 €/unidade = 73,2 milhões de euros / 366 milhões de juvenis em 2020
#   (HAPO, Aquaculture in Greece, relatório anual de 2021; cálculo nosso);
# - ração: ≈ 1,04 €/kg, preço médio em 2020 (gráfico do mesmo relatório da HAPO).
# Segundo a HAPO (2021), a ração e os juvenis são cerca de 70 % do custo de produção.
PRECO_VENDA = {"dourada": 4.89, "robalo": 6.45}
PRECO_JUVENIL = 0.20
PRECO_RACAO = 1.04
PESO_RACAO_JUVENIS_NO_CUSTO = 0.70

# Nomes das colunas em inglês que também são aceites nos CSV
COLUNAS_EN = {"date": "data", "temperature_c": "temperatura_c", "mean_weight_g": "peso_medio_g"}

# Ajustes ao tema do Streamlit:
# - legendas e links com contraste suficiente (o Streamlit desbota-as com transparência);
# - anel de foco visível para quem usa o teclado;
# - linhas de texto com 65-75 caracteres e títulos com tamanhos em escada;
# - botões com pelo menos 44 px de altura no telemóvel.
ESTILO = """
<style>
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { opacity: 1; color: #4A5E67; }
  [data-testid="stMarkdownContainer"] a { color: #0B5468; text-underline-offset: 0.15em; }
  [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] p { max-width: 72ch; }
  [data-testid="stButtonGroup"] button[aria-checked="true"],
  [data-testid="stButtonGroup"] button[aria-checked="true"] * { color: #0B5468 !important; }
  :focus-visible { outline: 2px solid #0B5468 !important; outline-offset: 2px; }
  ::selection { background: #CFE6EC; }
  h1 { font-size: clamp(1.9rem, 1.2rem + 2.2vw, 2.75rem) !important; line-height: 1.15 !important; }
  h2 { font-size: 1.4rem !important; padding-top: 1.5rem !important; }
  h3 { font-size: 1.15rem !important; }
  [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
  @media (max-width: 640px) {
    [data-testid="stButtonGroup"] button, [data-testid="stLinkButton"] a { min-height: 44px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
  }
</style>
"""


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
st.markdown(ESTILO, unsafe_allow_html=True)


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

    Também aceita os nomes em inglês (date, temperature_c, mean_weight_g).
    Devolve uma tabela com as colunas data e valor, ordenada por data.
    """
    try:
        tabela = pd.read_csv(ficheiro, sep=None, engine="python", dtype=str)
    except Exception:
        raise ValueError(t("O ficheiro não parece ser um CSV. Exporte-o do Excel como "
                           "\"CSV (separado por vírgulas)\" e volte a carregá-lo.",
                           "The file does not look like a CSV. Export it from Excel as "
                           "\"CSV (comma delimited)\" and upload it again."))
    tabela.columns = tabela.columns.str.strip().str.lower()
    tabela = tabela.rename(columns=COLUNAS_EN)
    if "data" not in tabela.columns or coluna not in tabela.columns:
        encontradas = ", ".join(tabela.columns)
        raise ValueError(t(f"Faltam colunas: o ficheiro tem de ter 'data' e '{coluna}' "
                           f"(encontradas: {encontradas}). Use o ficheiro de exemplo como modelo.",
                           f"Missing columns: the file must have 'date' and '{coluna}' "
                           f"(found: {encontradas}). Use the example file as a template."))
    # Datas no formato 2024-04-01 ou 01/04/2024 (dia primeiro, como em Portugal)
    data = pd.to_datetime(tabela["data"], format="ISO8601", errors="coerce")
    data = data.fillna(pd.to_datetime(tabela["data"], format="%d/%m/%Y", errors="coerce"))
    tabela = pd.DataFrame({
        "data": data,
        "valor": pd.to_numeric(tabela[coluna].str.replace(",", "."), errors="coerce"),
    }).dropna()
    if tabela.empty:
        raise ValueError(t("Nenhuma linha tem uma data e um valor válidos. As datas devem estar "
                           "no formato 2024-04-01 ou 01/04/2024.",
                           "No row has a valid date and value. Dates must be in the format "
                           "2024-04-01 or 01/04/2024."))
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


def eixo_de_meses():
    """Eixo de datas com o nome do mês na língua escolhida (ex.: abr. 2024)."""
    return alt.Axis(labelExpr=f"{MESES}[month(datum.value)] + ' ' + year(datum.value)",
                    tickCount={"interval": "month", "step": 3}, grid=True, title=None)


def com_estilo(grafico):
    """Títulos dos gráficos com as cores e a letra do tema."""
    return grafico.configure_title(color=COR_TEXTO, subtitleColor=COR_TEXTO_SUAVE, fontSize=15,
                                   subtitleFontSize=12, anchor="start").configure_axis(
        labelColor=COR_TEXTO_SUAVE, titleColor=COR_TEXTO_SUAVE).configure_legend(labelColor=COR_TEXTO)


# ---------------------------------------------------------------------------
# 1. Cabeçalho (título, autor e botão da língua)
# ---------------------------------------------------------------------------
col_titulo, col_lingua = st.columns([8, 1], vertical_alignment="center")
col_titulo.title(t("Modelo de crescimento de dourada e robalo", "Sea bream and sea bass growth model"))
idioma_escolhido = col_lingua.segmented_control(
    "Idioma / Language", ["pt", "en"], default=idioma, required=True, key="idioma",
    format_func=str.upper, label_visibility="collapsed")
st.query_params["lang"] = idioma_escolhido   # o link copiado abre na mesma língua

st.markdown(t("Quanto tempo demoram a dourada e o robalo a chegar ao tamanho comercial, e quanta ração "
              "gastam pelo caminho? Simulação do ciclo de engorda com parâmetros publicados, em jaula "
              "no mar ou em tanque / RAS.",
              "How long do sea bream and sea bass take to reach market size, and how much feed do "
              "they use along the way? A grow-out simulation built on published parameters, for sea "
              "cages or tanks / RAS."))
with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    st.markdown(t("**Dinis Costa** · Mestrado em Biologia Marinha Aplicada",
                  "**Dinis Costa** · MSc in Applied Marine Biology"), width="content")
    st.link_button("LinkedIn", URL_LINKEDIN, icon=":material/person:")
    st.link_button("GitHub", URL_GITHUB, icon=":material/code:")
    st.markdown(t("[Modelo e referências](#modelo)", "[Model and references](#modelo)"), width="content")
st.caption(t("Resultados **simulados** com parâmetros da literatura científica; "
             "não são dados de nenhuma exploração.",
             "**Simulated** results based on parameters from the scientific literature; "
             "they are not data from any farm."))


# ---------------------------------------------------------------------------
# 2. Cenário (controlos à vista, por cima dos resultados)
# ---------------------------------------------------------------------------
# Cada controlo tem uma `key`: assim a escolha mantém-se quando se muda de língua.
st.header(t("Cenário", "Scenario"), anchor="cenario")
with st.container(border=True):
    c1, c2, c3 = st.columns(3, gap="medium")
    escolha = c1.segmented_control(
        t("Espécie", "Species"), ["dourada", "robalo", "ambas"], default="ambas", required=True,
        format_func=lambda e: NOMES.get(e, t("Ambas", "Both")), key="especie")
    especies = ["dourada", "robalo"] if escolha == "ambas" else [escolha]

    sistema = c2.segmented_control(
        t("Sistema de cultivo", "Farming system"), ["jaula", "tanque"], default="jaula", required=True,
        format_func=lambda s: t("Jaula no mar", "Sea cage") if s == "jaula" else t("Tanque / RAS", "Tank / RAS"),
        key="sistema",
        help=t("**Jaula no mar:** a temperatura é a do mar e varia ± 4 °C ao longo do ano "
               "(mínimo em fevereiro, máximo em agosto).  \n"
               "**Tanque / RAS:** tanque em terra com temperatura controlada (constante).",
               "**Sea cage:** water temperature follows the sea and varies by ± 4 °C over the year "
               "(lowest in February, highest in August).  \n"
               "**Tank / RAS:** land-based tank with controlled (constant) temperature."))

    alimentacao = c3.segmented_control(
        t("Alimentação", "Feeding"), ["saciedade", "restrita"], default="saciedade", required=True,
        format_func=lambda a: t("Até à saciedade", "To satiation") if a == "saciedade" else t("Restrita", "Restricted"),
        key="alimentacao",
        help=t("**Restrita:** 80 % da saciedade na dourada (Bonaldo et al., 2010) e "
               "75 % no robalo (Türkmen et al., 2012).",
               "**Restricted:** 80 % of satiation in sea bream (Bonaldo et al., 2010) and "
               "75 % in sea bass (Türkmen et al., 2012)."))

    # Com um CSV de temperaturas carregado, o slider da temperatura deixa de ser usado
    usa_csv_temperatura = st.session_state.get("ficheiro_temp") is not None
    aviso_csv = t(" · substituída pelo CSV", " · replaced by the CSV") if usa_csv_temperatura else ""

    c1, c2, c3 = st.columns(3, gap="medium")
    densidade = None
    imta = False
    if sistema == "jaula":
        media = c1.slider(t("Temperatura média anual do mar (°C)", "Mean annual sea temperature (°C)") + aviso_csv,
                          15.0, 21.0, 19.0, 0.5, format="%.1f", key="media", disabled=usa_csv_temperatura)
        if "robalo" in especies:
            with c3:
                st.space("small")
                imta = st.toggle(
                    t("IMTA (robalo)", "IMTA (sea bass)"), key="imta",
                    help=t("Robalo cultivado com mexilhões, ostras e pepinos-do-mar: FCR × "
                           f"{virgula(FATOR_FCR_IMTA, 2)}, crescimento igual (Cotou et al., 2024; ensaio piloto de 90 dias).",
                           "Sea bass farmed together with mussels, oysters and sea cucumbers: FCR × "
                           f"{virgula(FATOR_FCR_IMTA, 2)}, same growth (Cotou et al., 2024; 90-day pilot trial)."))
    else:
        temperatura_tanque = c1.slider(
            t("Temperatura do tanque (°C)", "Tank temperature (°C)") + aviso_csv,
            14.0, TEMPERATURA_MAXIMA_VALIDA, TEMPERATURA_TANQUE, 0.5, format="%.1f", key="temperatura_tanque",
            disabled=usa_csv_temperatura,
            help=t(f"{virgula(TEMPERATURA_TANQUE, 0)} °C é o meio do intervalo 18–26 °C indicado pela FAO (2009). "
                   f"O modelo não é válido acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C.",
                   f"{virgula(TEMPERATURA_TANQUE, 0)} °C is the middle of the 18–26 °C range given by FAO (2009). "
                   f"The model is not valid above {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C."))
        densidade = c3.slider(
            t("Densidade (kg/m³)", "Stocking density (kg/m³)"), 10, DENSIDADE_MAXIMA, 40, 5, key="densidade",
            help=t(f"No robalo, até {DENSIDADE_SEM_EFEITO} kg/m³ não há efeito no crescimento; "
                   f"a {DENSIDADE_MAXIMA} kg/m³ a SGR desce 14 % (Sammouth et al., 2009). "
                   "Na dourada não encontrámos dados, por isso a densidade só serve para calcular o volume de tanque.",
                   f"In sea bass, density has no effect on growth up to {DENSIDADE_SEM_EFEITO} kg/m³; "
                   f"at {DENSIDADE_MAXIMA} kg/m³ SGR drops by 14 % (Sammouth et al., 2009). "
                   "No data were found for sea bream, so density is only used to compute tank volume."))

    peso_comercial = c2.slider(t("Tamanho comercial (g)", "Market size (g)"), 250, 600, 400, 25,
                               key="peso_comercial")

    with st.expander(t("Dados da exploração: juvenis, datas, temperaturas e pesagens",
                       "Farm data: juveniles, dates, temperatures and weighings")):
        st.caption(t("Os valores de partida são um exemplo. Substitua-os pelos de uma exploração. "
                     "Os ficheiros são lidos apenas no browser e não são enviados para nenhum servidor.",
                     "The starting values are an example. Replace them with those of a farm. "
                     "Files are read only in the browser and are not sent to any server."))
        c1, c2, c3 = st.columns(3, gap="medium")
        n_juvenis = c1.number_input(t("Número de juvenis", "Number of juveniles"), 100, 5_000_000, N_PEIXES, 1000,
                                    key="n_juvenis")
        peso_inicial = c2.number_input(
            t("Peso dos juvenis à entrada (g)", "Juvenile weight at stocking (g)"), 1.0, 50.0, PESO_INICIAL_G, 0.5,
            format="%.1f", key="peso_inicial",
            help=t("O modelo foi feito para juvenis de 2–4 g; acima de 50 g não é fiável.",
                   "The model was built for 2–4 g juveniles; above 50 g it is not reliable."))
        data_entrada = c3.date_input(t("Data de entrada", "Stocking date"), datetime.date(2024, 4, 1),
                                     format="DD/MM/YYYY", key="data_entrada")

        st.markdown(t("**Medições (CSV).** Um ficheiro por tipo de medição, uma linha por medição. "
                      "Pode ser exportado do Excel (separador `;` ou `,`).",
                      "**Measurements (CSV).** One file per type of measurement, one row per measurement. "
                      "It can be exported from Excel (`;` or `,` separator)."))
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            ficheiro_temp = st.file_uploader(
                t("Temperaturas da água", "Water temperatures"), type="csv", key="ficheiro_temp",
                help=t("Colunas: data, temperatura_c. Substituem a temperatura escolhida acima.",
                       "Columns: date, temperature_c (or data, temperatura_c). They replace the temperature above."))
            st.download_button(t("Exemplo de temperaturas", "Temperature example"), MODELO_TEMPERATURAS,
                               "exemplo_temperaturas.csv", "text/csv", icon=":material/download:")
            erro_temp = st.empty()
        with c2:
            ficheiro_pesos = st.file_uploader(
                t("Pesagens (peso médio da amostra)", "Weighings (mean sample weight)"), type="csv",
                key="ficheiro_pesos",
                help=t("Colunas: data, peso_medio_g. Aparecem no gráfico do peso.",
                       "Columns: date, mean_weight_g (or data, peso_medio_g). They are shown on the weight chart."))
            st.download_button(t("Exemplo de pesagens", "Weighing example"), MODELO_PESAGENS,
                               "exemplo_pesagens.csv", "text/csv", icon=":material/download:")
            erro_pesos = st.empty()

    # Parâmetros do modelo: começam nos valores da literatura e podem ser trocados pelos de uma exploração
    with st.expander(t("Parâmetros do modelo", "Model parameters")):
        st.caption(t("Valores de partida da literatura (ver Modelo e referências). O TGC de uma exploração "
                     "calcula-se com duas pesagens: (peso final^(1/3) − peso inicial^(1/3)) a dividir pela soma "
                     "de (temperatura − 12) em todos os dias entre elas.",
                     "Starting values from the literature (see Model and references). A farm's TGC is computed "
                     "from two weighings: (final weight^(1/3) − initial weight^(1/3)) divided by the sum of "
                     "(temperature − 12) over all the days between them."))
        parametros, fcr_base = {}, {}
        for coluna, e in zip(st.columns(2, gap="large"), ["dourada", "robalo"]):
            p = PARAMETROS[e]
            with coluna:
                st.markdown(f"**{NOMES[e]}**")
                tgc_1_3 = st.number_input(t("TGC (fase W^1/3)", "TGC (W^1/3 stage)"), 0.0003, 0.0060, p["tgc_1_3"],
                                          0.0001, format="%.5f", key=f"tgc13_{e}")
                tgc_2_3 = None
                if p["tgc_2_3"]:
                    tgc_2_3 = st.number_input(t("TGC (fase W^2/3)", "TGC (W^2/3 stage)"), 0.003, 0.060, p["tgc_2_3"],
                                              0.0005, format="%.5f", key=f"tgc23_{e}")
                    st.caption(t("Muda de fase aos ", "Changes stage at ")
                               + f"{virgula(peso_critico({'tgc_1_3': tgc_1_3, 'tgc_2_3': tgc_2_3}), 0)} g")
                fcr_base[e] = st.number_input("FCR", 0.8, 4.0, p["fcr"], 0.05, format="%.2f", key=f"fcr_{e}")
                sobrevivencia = st.number_input(t("Sobrevivência no ciclo (%)", "Survival over the cycle (%)"),
                                                30, 100, round(p["sobrevivencia_ciclo"] * 100), 1, key=f"sobrev_{e}")
                parametros[e] = {"tgc_1_3": tgc_1_3, "tgc_2_3": tgc_2_3, "sobrevivencia_ciclo": sobrevivencia / 100}

    with st.expander(t("Preços e custos", "Prices and costs")):
        st.caption(t("Valores de partida: preço de venda à saída da exploração na Grécia em 2023 (EUMOFA); "
                     "juvenil e ração na Grécia em 2020 (HAPO, 2021). Os preços mudam de ano para ano: "
                     "convém usar os da exploração.",
                     "Starting values: ex-farm sale price in Greece in 2023 (EUMOFA); juveniles and feed in "
                     "Greece in 2020 (HAPO, 2021). Prices change from year to year: a farm's own prices are best."))
        c1, c2, c3, c4 = st.columns(4, gap="medium")
        preco_venda = {
            "dourada": c1.number_input(t("Venda dourada (€/kg)", "Sea bream sale (€/kg)"), 0.0, 50.0,
                                       PRECO_VENDA["dourada"], 0.10, format="%.2f", key="venda_dourada"),
            "robalo": c2.number_input(t("Venda robalo (€/kg)", "Sea bass sale (€/kg)"), 0.0, 50.0,
                                      PRECO_VENDA["robalo"], 0.10, format="%.2f", key="venda_robalo")}
        preco_juvenil = c3.number_input(t("Juvenil (€/unidade)", "Juvenile (€/unit)"), 0.0, 5.0, PRECO_JUVENIL,
                                        0.01, format="%.2f", key="preco_juvenil")
        preco_racao = c4.number_input(t("Ração (€/kg)", "Feed (€/kg)"), 0.0, 10.0, PRECO_RACAO, 0.05,
                                      format="%.2f", key="preco_racao")

# É um exemplo enquanto os dados da exploração e os parâmetros estiverem nos valores de partida
e_exemplo = (n_juvenis == N_PEIXES and peso_inicial == PESO_INICIAL_G and data_entrada == datetime.date(2024, 4, 1)
             and ficheiro_temp is None and ficheiro_pesos is None
             and all(parametros[e]["tgc_1_3"] == PARAMETROS[e]["tgc_1_3"]
                     and parametros[e]["tgc_2_3"] == PARAMETROS[e]["tgc_2_3"]
                     and fcr_base[e] == PARAMETROS[e]["fcr"]
                     and parametros[e]["sobrevivencia_ciclo"] == PARAMETROS[e]["sobrevivencia_ciclo"]
                     for e in ("dourada", "robalo")))


# ---------------------------------------------------------------------------
# 3. Temperatura e dados carregados
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
            st.warning(t(f"Há temperaturas acima de {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C. "
                         "O modelo não é válido aí, por isso foram limitadas a esse valor.",
                         f"Some temperatures are above {virgula(TEMPERATURA_MAXIMA_VALIDA, 0)} °C. "
                         "The model is not valid there, so they were capped at that value."),
                       icon=":material/warning:")
            temperatura = np.minimum(temperatura, TEMPERATURA_MAXIMA_VALIDA)
    except ValueError as erro:
        erro_temp.error(str(erro))

pesagens = None
if ficheiro_pesos is not None:
    try:
        pesagens = ler_csv(ficheiro_pesos, "peso_medio_g")
        pesagens["dia"] = (pesagens["data"] - pd.Timestamp(data_entrada)).dt.days
        pesagens = pesagens[(pesagens["dia"] >= 0) & (pesagens["dia"] < N_DIAS)]
        if pesagens.empty:
            erro_pesos.error(t("Todas as pesagens são anteriores à data de entrada. "
                               "Confirme a data de entrada acima.",
                               "All weighings are earlier than the stocking date. "
                               "Check the stocking date above."))
            pesagens = None
    except ValueError as erro:
        erro_pesos.error(str(erro))
        pesagens = None


# ---------------------------------------------------------------------------
# 4. Simulação
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def simular(especie, temperatura, fator_crescimento, fcr, peso_inicial, data_entrada, parametros):
    """Corre a simulação (o resultado fica guardado para não repetir contas)."""
    return simular_ciclo(especie, n_dias=N_DIAS, n_peixes=N_PEIXES, temperatura=temperatura,
                         data_inicio=str(data_entrada), peso_inicial_g=peso_inicial,
                         fator_crescimento=fator_crescimento, fcr=fcr, parametros=parametros, semente=42)


def simular_especie(especie):
    """Junta os efeitos do cenário escolhido e escala o resultado ao nº de juvenis."""
    cenario = CENARIOS_ALIMENTACAO[especie][alimentacao]
    fator_crescimento = cenario["fator_crescimento"]
    fcr = fcr_base[especie] * cenario["fator_fcr"]
    if especie == "robalo" and densidade is not None:
        fator_crescimento *= fator_crescimento_densidade(densidade)
    if especie == "robalo" and imta:
        fcr *= FATOR_FCR_IMTA
    sim = simular(especie, temperatura, fator_crescimento, fcr, peso_inicial, data_entrada, parametros[especie])

    # Simulamos 1 000 peixes; para outro número de juvenis, os totais crescem na mesma proporção
    escala = n_juvenis / N_PEIXES
    return sim.assign(n_peixes=(sim["n_peixes"] * escala).round().astype(int),
                      biomassa_kg=sim["biomassa_kg"] * escala,
                      racao_kg=sim["racao_kg"] * escala,
                      mortos=(sim["mortos"] * escala).round().astype(int))


def fontes(especie):
    """Fontes dos números do cartão, conforme o cenário escolhido."""
    p = parametros[especie]
    if p["tgc_1_3"] != PARAMETROS[especie]["tgc_1_3"] or p["tgc_2_3"] != PARAMETROS[especie]["tgc_2_3"]:
        lista = [t("Crescimento: TGC introduzido", "Growth: TGC entered")]
    elif especie == "dourada":
        lista = [t("Crescimento", "Growth") + ": Mayer et al. (2012)"]
    else:
        lista = [t("Crescimento: TGC calibrado (Cardia & Lovatelli, 2007)",
                   "Growth: calibrated TGC (Cardia & Lovatelli, 2007)")]
    sobrevivencia_lit = p["sobrevivencia_ciclo"] == PARAMETROS[especie]["sobrevivencia_ciclo"]
    lista.append(t("Sobrevivência", "Survival") + ": "
                 + ("Muniesa et al. (2020)" if sobrevivencia_lit else t("introduzida", "entered")))
    lista.append("FCR: " + ("Kallitsis & Avramidis (2025)" if fcr_base[especie] == PARAMETROS[especie]["fcr"]
                            else t("introduzido", "entered")))
    if alimentacao == "restrita":
        lista.append(t("Ração restrita", "Restricted feeding") + ": "
                     + ("Bonaldo et al. (2010)" if especie == "dourada" else "Türkmen et al. (2012)"))
    if sistema == "tanque":
        lista.append(t("Temperatura do tanque", "Tank temperature") + ": FAO (2009)")
    if especie == "robalo" and densidade is not None:
        lista.append(t("Densidade", "Density") + ": Sammouth et al. (2009)")
    if especie == "robalo" and imta:
        lista.append("IMTA: Cotou et al. (2024)")
    return " · ".join(lista)


with st.spinner(t("A simular...", "Simulating...")):
    simulacoes = {e: simular_especie(e) for e in especies}
dias_alvo = {e: dias_ate_peso(s, peso_comercial) for e, s in simulacoes.items()}


# ---------------------------------------------------------------------------
# 5. Resultados: um cartão por espécie, frase-resumo e calendário de produção
# ---------------------------------------------------------------------------
st.header(t("Resultados", "Results"), anchor="resultados")
if e_exemplo:
    st.caption(t("**Exemplo** com os valores de partida: 1 000 juvenis de 3 g a entrar a 1 de abril, com os "
                 "parâmetros da literatura. Para usar os dados de uma exploração, abrir **Dados da exploração** "
                 "no painel do cenário.",
                 "**Example** with the starting values: 1,000 juveniles of 3 g stocked on 1 April, with "
                 "parameters from the literature. To use a farm's data, open **Farm data** in the scenario panel."))
for aviso in avisos:
    st.caption(aviso)

colunas = st.columns(len(especies), gap="medium")
for coluna, especie in zip(colunas, especies):
    sim = simulacoes[especie]
    dia = dias_alvo[especie]
    with coluna.container(border=True):
        # Quadrado com a cor da espécie nos gráficos
        marca = (f'<span style="display:inline-block;width:0.7em;height:0.7em;border-radius:2px;'
                 f'background:{CORES[especie]};margin-right:0.4em"></span>')
        st.markdown(f"### {marca}{NOMES[especie]} &nbsp;*{CIENTIFICOS[especie]}*", unsafe_allow_html=True)
        if dia is None:
            st.error(t(f"Não chega aos {peso_comercial} g em {N_DIAS} dias. "
                       "Experimente uma temperatura mais alta ou um tamanho comercial menor.",
                       f"Does not reach {peso_comercial} g within {N_DIAS} days. "
                       "Try a higher temperature or a smaller market size."))
            continue
        ate_peso = sim.loc[:dia]
        ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - n_juvenis * peso_inicial / 1000
        fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
        with st.container(horizontal=True, gap="medium"):
            st.metric(t(f"Dias até {peso_comercial} g", f"Days to {peso_comercial} g"), dia,
                      delta=t(f"≈ {virgula(dia / 30.4)} meses", f"≈ {virgula(dia / 30.4)} months"),
                      delta_color="off", delta_arrow="off", width="content")
            st.metric("FCR", virgula(fcr, 2), width="content",
                      help=t("FCR económico: kg de ração por kg de peixe produzido, incluindo a ração comida "
                             "pelos peixes que morreram.",
                             "Economic FCR: kg of feed per kg of fish produced, including feed eaten by fish "
                             "that died."))
            st.metric(t("Sobrevivência", "Survival"), f"{sim.loc[dia, 'n_peixes'] / n_juvenis:.0%}", width="content")
        st.caption(t("Despesca prevista: ", "Expected harvest: ") + mes_e_ano(sim.loc[dia, "data"]))
        st.caption(t("Fontes: ", "Sources: ") + fontes(especie))

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

# Cores e legenda comuns a todos os gráficos
escala_cor = alt.Scale(domain=[NOMES[e] for e in especies], range=[CORES[e] for e in especies])
cor = alt.Color("nome:N", title=None, scale=escala_cor,
                legend=alt.Legend(orient="top-left", direction="horizontal",
                                  symbolType="stroke", symbolStrokeWidth=3, symbolOpacity=1,
                                  labelFontSize=13))
especie_tt = alt.Tooltip("nome:N", title=t("Espécie", "Species"))

# Calendário de produção: da entrada dos juvenis à despesca, em meses do calendário
calendario = pd.DataFrame([{"nome": NOMES[e], "inicio": pd.Timestamp(data_entrada), "fim": simulacoes[e].loc[d, "data"],
                            "rotulo": t("despesca ", "harvest ") + mes_e_ano(simulacoes[e].loc[d, "data"])}
                           for e, d in dias_alvo.items() if d is not None])
if not calendario.empty:
    fim_eixo = calendario["fim"].max() + pd.Timedelta(days=20)
    escala_t = alt.Scale(domain=[calendario["inicio"].min(), fim_eixo])
    barras = alt.Chart(calendario).mark_bar(height=16, cornerRadius=3).encode(
        x=alt.X("inicio:T", scale=escala_t, axis=eixo_de_meses()), x2="fim:T",
        y=alt.Y("nome:N", title=None, sort=[NOMES[e] for e in especies],
                axis=alt.Axis(labelFontSize=13, labelPadding=8, domain=False, ticks=False)),
        color=alt.Color("nome:N", scale=escala_cor, legend=None),
        tooltip=[especie_tt, alt.Tooltip("inicio:T", title=t("Entrada", "Stocking"), format="%d/%m/%Y"),
                 alt.Tooltip("fim:T", title=t("Despesca", "Harvest"), format="%d/%m/%Y")])
    # Rótulo dentro da barra, encostado ao fim (cabe em qualquer largura de ecrã)
    rotulos = alt.Chart(calendario).mark_text(align="right", dx=-8, fontSize=12, color="white",
                                              fontWeight=600).encode(
        x=alt.X("fim:T", scale=escala_t), y=alt.Y("nome:N", sort=[NOMES[e] for e in especies]), text="rotulo:N")
    st.altair_chart(com_estilo((barras + rotulos).properties(
        height=alt.Step(36),
        title=alt.Title(t("Calendário de produção", "Production calendar"),
                        subtitle=t("Da entrada dos juvenis à despesca", "From stocking to harvest")))),
        width="stretch")


# ---------------------------------------------------------------------------
# 6. Gráficos e dados
# ---------------------------------------------------------------------------
aba_crescimento, aba_biomassa, aba_custos, aba_dados = st.tabs(
    t(["Crescimento", "Biomassa", "Custos", "Dados"], ["Growth", "Biomass", "Costs", "Data"]))

with aba_crescimento:
    dia_maximo = min(N_DIAS, int(max(d or N_DIAS for d in dias_alvo.values()) * 1.15))
    if pesagens is not None:
        dia_maximo = max(dia_maximo, min(N_DIAS, int(pesagens["dia"].max()) + 10))
    escala_x = alt.Scale(domain=[0, dia_maximo], nice=False)
    # O eixo do peso vai um pouco acima do tamanho comercial (ou da maior pesagem)
    peso_maximo = peso_comercial * 1.6
    if pesagens is not None:
        peso_maximo = max(peso_maximo, pesagens["valor"].max() * 1.1)
    escala_y = alt.Scale(domain=[0, peso_maximo], nice=False)   # o que passa do topo é cortado (clip)

    # Tabela "longa" com as duas espécies, um ponto de 2 em 2 dias (gráfico mais leve)
    dados = pd.concat([
        s.iloc[:dia_maximo:2].assign(
            nome=NOMES[e],
            minimo=lambda d: (d["peso_medio_g"] - d["peso_dp_g"]).clip(lower=0),
            maximo=lambda d: d["peso_medio_g"] + d["peso_dp_g"])
        for e, s in simulacoes.items()])
    eixo_x = alt.X("dia:Q", scale=escala_x,
                   title=t("Dias desde a entrada dos juvenis", "Days since stocking of juveniles")
                   + f" ({virgula(peso_inicial, 1).replace(',0', '').replace('.0', '')} g)")
    dia_tt = alt.Tooltip("dia:Q", title=t("Dia", "Day"))

    faixa = alt.Chart(dados).mark_area(opacity=0.15, clip=True).encode(
        x=eixo_x, y=alt.Y("minimo:Q", scale=escala_y), y2="maximo:Q", color=cor)
    linha = alt.Chart(dados).mark_line(strokeWidth=2.5, clip=True).encode(
        x=eixo_x,
        y=alt.Y("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), scale=escala_y,
                axis=alt.Axis(format="d")),
        color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("data:T", title=t("Data", "Date"), format="%d/%m/%Y"),
                 alt.Tooltip("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), format=".0f"),
                 alt.Tooltip("peso_dp_g:Q", title=t("Desvio-padrão (g)", "Standard deviation (g)"), format=".0f"),
                 alt.Tooltip("temperatura_c:Q", title=t("Temperatura (°C)", "Temperature (°C)"), format=".1f")])
    alvo = alt.Chart(pd.DataFrame({"y": [peso_comercial]})).mark_rule(
        strokeDash=[6, 4], color=COR_TEXTO_SUAVE).encode(y=alt.Y("y:Q", scale=escala_y))
    alvo_texto = alt.Chart(pd.DataFrame({"y": [peso_comercial], "x": [0]})).mark_text(
        align="left", dx=4, dy=-8, fontSize=12, color=COR_TEXTO_SUAVE).encode(
        x=alt.X("x:Q", scale=escala_x), y=alt.Y("y:Q", scale=escala_y),
        text=alt.value(t("tamanho comercial", "market size") + f" · {peso_comercial} g"))
    chegadas = pd.DataFrame([{"nome": NOMES[e], "dia": d, "peso": peso_comercial}
                             for e, d in dias_alvo.items() if d is not None])
    pontos = alt.Chart(chegadas).mark_point(filled=True, size=110, stroke="white", strokeWidth=2,
                                            opacity=1).encode(
        x=alt.X("dia:Q", scale=escala_x), y=alt.Y("peso:Q", scale=escala_y), color=cor,
        tooltip=[especie_tt, alt.Tooltip("dia:Q", title=t("Chega ao tamanho comercial no dia",
                                                          "Reaches market size on day"))])

    camadas = faixa + linha + alvo + alvo_texto + pontos
    # Uma linha por elemento do gráfico, para o subtítulo não ser cortado em ecrãs estreitos
    subtitulo = [t("Linha: média da população", "Line: population mean"),
                 t("Sombra: ± 1 desvio-padrão entre peixes", "Shading: ± 1 standard deviation between fish")]
    if pesagens is not None:
        # As pesagens da exploração, como losangos escuros por cima das curvas do modelo
        camadas += alt.Chart(pesagens).mark_point(shape="diamond", filled=True, size=90,
                                                  color=COR_PESAGENS, opacity=0.9).encode(
            x=alt.X("dia:Q", scale=escala_x), y=alt.Y("valor:Q", scale=escala_y),
            tooltip=[alt.Tooltip("data:T", title=t("Pesagem", "Weighing"), format="%d/%m/%Y"), dia_tt,
                     alt.Tooltip("valor:Q", title=t("Peso médio medido (g)", "Measured mean weight (g)"),
                                 format=".1f")])
        subtitulo.append(t("Losangos: pesagens da exploração", "Diamonds: farm weighings"))

    grafico_peso = camadas.properties(
        height=380, title=alt.Title(t("Peso médio dos peixes", "Mean fish weight"), subtitle=subtitulo))
    st.altair_chart(com_estilo(grafico_peso), width="stretch")

    # Comparação das pesagens com o modelo, no mesmo dia
    if pesagens is not None:
        medido = t("Medido (g)", "Measured (g)")
        modelo = {e: t(f"{NOMES[e]}: modelo (g)", f"{NOMES[e]}: model (g)") for e in especies}
        comparacao = pesagens.rename(columns={"valor": medido})
        comparacao[t("Data", "Date")] = comparacao["data"].dt.strftime("%d/%m/%Y")
        for e, s in simulacoes.items():
            comparacao[modelo[e]] = s.loc[comparacao["dia"], "peso_medio_g"].round(1).to_numpy()
        st.markdown(t("**Pesagens da exploração vs. modelo**", "**Farm weighings vs. model**"))
        # Diferença média entre o medido e o modelo (em %), para cada espécie
        with st.container(horizontal=True, gap="large"):
            for e in especies:
                desvio = ((comparacao[medido] / comparacao[modelo[e]] - 1) * 100).mean()
                st.metric(t(f"Medido vs. {NOMES[e].lower()} (média)", f"Measured vs. {NOMES[e].lower()} (mean)"),
                          f"{'+' if desvio >= 0 else ''}{virgula(desvio, 0)} %", width="content")
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
        y=alt.Y("temperatura:Q", title=t("Temperatura (°C)", "Temperature (°C)"),
                scale=alt.Scale(domain=[10, 26]), axis=alt.Axis(values=[10, 14, 18, 22, 26])),
        y2=alt.datum(10),
        tooltip=[dia_tt, alt.Tooltip("temperatura:Q", title=t("Temperatura (°C)", "Temperature (°C)"),
                                     format=".1f")]
    ).properties(height=200)
    st.altair_chart(com_estilo(grafico_temp), width="stretch")


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
    col_bio.altair_chart(com_estilo(grafico_biomassa), width="stretch")
    col_racao.altair_chart(com_estilo(grafico_racao), width="stretch")

    # Resumo no dia em que cada espécie chega ao tamanho comercial (números alinhados à direita)
    linhas = []
    for e, d in dias_alvo.items():
        if d is None:
            continue
        linha = {t("Espécie", "Species"): NOMES[e], t("Dias", "Days"): d,
                 t("Peixes vivos", "Live fish"): int(simulacoes[e].loc[d, "n_peixes"]),
                 t("Biomassa (kg)", "Biomass (kg)"): round(simulacoes[e].loc[d, "biomassa_kg"]),
                 t("Ração gasta (kg)", "Feed used (kg)"): round(simulacoes[e].loc[:d, "racao_kg"].sum())}
        if densidade is not None:
            linha[t("Volume de tanque (m³)", "Tank volume (m³)")] = round(
                simulacoes[e].loc[d, "biomassa_kg"] / densidade, 1)
        linhas.append(linha)
    if linhas:
        st.markdown(t(f"**No dia em que chega aos {peso_comercial} g**", f"**On the day it reaches {peso_comercial} g**"))
        resumo = pd.DataFrame(linhas)
        st.dataframe(resumo, hide_index=True, column_config={
            c: st.column_config.NumberColumn(format="localized") for c in resumo.columns[1:]})
        if densidade is not None:
            st.caption(t(f"Volume de tanque necessário para ter essa biomassa a {densidade} kg/m³.",
                         f"Tank volume needed to hold that biomass at {densidade} kg/m³."))


# ---------------------------------------------------------------------------
# 8. Custos e receita (no dia em que chega ao tamanho comercial)
# ---------------------------------------------------------------------------
with aba_custos:
    st.markdown(t(f"Contas no dia em que cada espécie chega aos {peso_comercial} g, com os preços de "
                  "**Preços e custos** (no painel do cenário).",
                  f"Figures on the day each species reaches {peso_comercial} g, using the prices in "
                  "**Prices and costs** (in the scenario panel)."))
    contas = {}
    for e, d in dias_alvo.items():
        if d is None:
            continue
        biomassa = simulacoes[e].loc[d, "biomassa_kg"]
        racao = simulacoes[e].loc[:d, "racao_kg"].sum()
        receita = biomassa * preco_venda[e]
        custo_juvenis = n_juvenis * preco_juvenil
        custo_racao = racao * preco_racao
        # A ração e os juvenis são cerca de 70 % do custo de produção (HAPO, 2021)
        custo_total = (custo_juvenis + custo_racao) / PESO_RACAO_JUVENIS_NO_CUSTO
        contas[NOMES[e]] = {
            t("Receita (€)", "Revenue (€)"): round(receita),
            t("Custo dos juvenis (€)", "Juvenile cost (€)"): round(custo_juvenis),
            t("Custo da ração (€)", "Feed cost (€)"): round(custo_racao),
            t("Custo total estimado (€)", "Estimated total cost (€)"): round(custo_total),
            t("Margem estimada (€)", "Estimated margin (€)"): round(receita - custo_total),
            t("Custo por kg produzido (€/kg)", "Cost per kg produced (€/kg)"): round(custo_total / biomassa, 2),
        }
    if contas:
        tabela_contas = pd.DataFrame(contas)
        st.dataframe(tabela_contas, column_config={
            c: st.column_config.NumberColumn(format="localized") for c in tabela_contas.columns})
        st.caption(t("O custo total é estimado a partir da ração e dos juvenis, que são cerca de 70 % do custo "
                     "de produção nas explorações gregas (HAPO, 2021); o resto (mão de obra, amortizações, "
                     "outros) varia de exploração para exploração. É uma estimativa, não uma contabilidade.",
                     "Total cost is estimated from feed and juveniles, which are about 70 % of production cost "
                     "on Greek farms (HAPO, 2021); the rest (labour, depreciation, other) varies from farm to "
                     "farm. It is an estimate, not an account."))


# ---------------------------------------------------------------------------
# 9. Tabela com os dados simulados (para descarregar)
# ---------------------------------------------------------------------------
with aba_dados:
    st.markdown(t("Valores diários da simulação, até ao fim do gráfico. **Dados simulados.**",
                  "Daily values from the simulation, up to the end of the chart. **Simulated data.**"))
    colunas_tabela = ["especie", "dia", "data", "temperatura_c", "n_peixes",
                      "peso_medio_g", "peso_dp_g", "biomassa_kg", "racao_kg", "mortos"]
    tabela = pd.concat([s.iloc[:dia_maximo][colunas_tabela] for s in simulacoes.values()])
    tabela = tabela.round({"peso_medio_g": 1, "peso_dp_g": 1, "biomassa_kg": 1, "racao_kg": 2})
    tabela["data"] = tabela["data"].dt.date     # só a data, sem 00:00:00
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
# 10. Modelo e referências (sempre à vista, no fim da página)
# ---------------------------------------------------------------------------
SOBRE_PT = r"""
O crescimento depende da temperatura acumulada acima de 12 °C (temperatura efetiva): abaixo de 12 °C
a dourada não cresce (Mayer et al., 2008). Em cada dia, com $T$ a temperatura da água e $W$ o peso (g):

$$W^{1/3} \leftarrow W^{1/3} + TGC_{1/3}\,(T-12) \quad \text{até ao peso crítico}$$

$$W^{2/3} \leftarrow W^{2/3} + TGC_{2/3}\,(T-12) \quad \text{a partir do peso crítico}$$

O peso crítico, $(TGC_{2/3}/TGC_{1/3})^3/8$, é o peso em que as duas fases crescem ao mesmo ritmo
(cerca de 117 g na dourada). Simulamos 1 000 juvenis, com variação individual no crescimento e
mortalidade diária; para outro número de juvenis, os totais crescem na mesma proporção.

| | Dourada | Robalo |
|---|---|---|
| Crescimento | TGC misto: 0,001646 e 0,016095 (Mayer et al., 2012; 20 lotes em jaulas comerciais) | TGC 0,00129, **calibrado** para demorar mais 13 % do que a dourada, como nos ciclos de 14–16 e 16–18 meses de Cardia & Lovatelli (2007) |
| Sobrevivência no ciclo | 80 % (Muniesa et al., 2020) | 85 % (Muniesa et al., 2020) |
| FCR | 2,1 (Kallitsis & Avramidis, 2025) | 2,2 (Kallitsis & Avramidis, 2025) |
| Ração restrita | 80 %: crescimento × 0,92, FCR × 0,83 (Bonaldo et al., 2010) | 75 %: crescimento × 0,88, FCR igual (Türkmen et al., 2012) |
| Densidade em tanque / RAS | sem dados | até 70 kg/m³ sem efeito; 100 kg/m³: crescimento × 0,86 (Sammouth et al., 2009) |
| IMTA | sem dados | FCR × 0,89 (Cotou et al., 2024) |

**Validação:** com o modelo, a dourada vai de 5 g a 400 g em cerca de 17 meses em jaula, perto dos
≈ 16 meses indicados pela FAO (2009) para juvenis de 5 g.

**Pressupostos sem referência:** a variação individual do crescimento (coeficiente de variação de 15 %),
a curva de temperatura do mar (± 4 °C), a temperatura base de 12 °C no robalo (igual à da dourada) e o
TGC do robalo (calibrado).

**Preços:** venda à saída da exploração na Grécia em 2023 (EUMOFA); juvenis e ração na Grécia em 2020
(HAPO, 2021). O custo total é estimado a partir da ração e dos juvenis, cerca de 70 % do custo de produção
(HAPO, 2021).

**Limitações:** os lotes de Mayer et al. começaram com 6–44 g, por isso abaixo de 6 g o modelo é uma
extrapolação; o modelo não tem temperatura ótima (a temperatura está limitada a 25 °C; o ótimo do robalo
é 26 °C, Person-Le Ruyet et al., 2004); a mortalidade e o FCR são constantes ao longo do ciclo; os efeitos
da ração, da densidade e do IMTA vêm de ensaios curtos.
"""

SOBRE_EN = r"""
Growth depends on the temperature accumulated above 12 °C (effective temperature): below 12 °C sea
bream does not grow (Mayer et al., 2008). Each day, with $T$ the water temperature and $W$ the weight (g):

$$W^{1/3} \leftarrow W^{1/3} + TGC_{1/3}\,(T-12) \quad \text{up to the critical weight}$$

$$W^{2/3} \leftarrow W^{2/3} + TGC_{2/3}\,(T-12) \quad \text{from the critical weight on}$$

The critical weight, $(TGC_{2/3}/TGC_{1/3})^3/8$, is the weight at which both stages grow at the same rate
(about 117 g in sea bream). 1,000 juveniles are simulated, with individual variation in growth and daily
mortality; for a different number of juveniles, totals scale in the same proportion.

| | Sea bream | Sea bass |
|---|---|---|
| Growth | Mixed TGC: 0.001646 and 0.016095 (Mayer et al., 2012; 20 commercial cage lots) | TGC 0.00129, **calibrated** to take 13 % longer than sea bream, as in the 14–16 and 16–18 month cycles of Cardia & Lovatelli (2007) |
| Survival over the cycle | 80 % (Muniesa et al., 2020) | 85 % (Muniesa et al., 2020) |
| FCR | 2.1 (Kallitsis & Avramidis, 2025) | 2.2 (Kallitsis & Avramidis, 2025) |
| Restricted feeding | 80 %: growth × 0.92, FCR × 0.83 (Bonaldo et al., 2010) | 75 %: growth × 0.88, same FCR (Türkmen et al., 2012) |
| Density in tank / RAS | no data | no effect up to 70 kg/m³; 100 kg/m³: growth × 0.86 (Sammouth et al., 2009) |
| IMTA | no data | FCR × 0.89 (Cotou et al., 2024) |

**Validation:** with the model, sea bream grows from 5 g to 400 g in about 17 months in sea cages, close
to the ≈ 16 months given by FAO (2009) for 5 g juveniles.

**Assumptions without a reference:** individual growth variation (coefficient of variation of 15 %), the
sea temperature curve (± 4 °C), the 12 °C base temperature for sea bass (same as sea bream) and the sea
bass TGC (calibrated).

**Prices:** ex-farm sale price in Greece in 2023 (EUMOFA); juveniles and feed in Greece in 2020 (HAPO, 2021).
Total cost is estimated from feed and juveniles, about 70 % of production cost (HAPO, 2021).

**Limitations:** the lots in Mayer et al. started at 6–44 g, so below 6 g the model is an extrapolation;
the model has no optimum temperature (temperature is capped at 25 °C; the sea bass optimum is 26 °C,
Person-Le Ruyet et al., 2004); mortality and FCR are constant over the cycle; the effects of feeding,
density and IMTA come from short trials.
"""

st.header(t("Modelo e referências", "Model and references"), anchor="modelo")
st.markdown(t(SOBRE_PT, SOBRE_EN))
st.markdown(t("As referências completas, com DOI, e os cinco notebooks de análise estão no repositório.",
              "Full references with DOIs, and the five analysis notebooks, are in the repository."))
with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    st.link_button(t("Código, notebooks e referências", "Code, notebooks and references"), URL_GITHUB,
                   icon=":material/code:")
    st.link_button(t("Contactar no LinkedIn", "Contact on LinkedIn"), URL_LINKEDIN, icon=":material/person:")
