"""
App interativa: crescimento de peixes em aquacultura (dourada, robalo, pregado e linguado).

Para correr no computador:   streamlit run app.py
Também corre no browser, sem instalar nada, através do site do projeto
(index.html, publicado no GitHub Pages com o stlite).

ATENÇÃO: os resultados são SIMULADOS com o modelo de src/growth.py.
Quem usa a app pode pôr os dados de uma exploração (número e peso dos juvenis,
data de entrada, temperaturas e pesagens) para comparar com o modelo.

A página segue a ordem: cenário -> resultados (com figuras) -> notas sobre o modelo.
Está em português e em inglês: o botão PT / EN ao lado do título muda a
língua, e o link com ?lang=en abre logo em inglês.
"""

import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.growth import (PARAMETROS, CENARIOS_ALIMENTACAO, TEMPERATURA_MAXIMA_VALIDA, PESO_INICIAL_G,
                        perfil_temperatura, simular_ciclo, dias_ate_peso, dias_ate_peso_medio, peso_critico)
from src.regimes import (TEMPERATURA_TANQUE, DENSIDADE_SEM_EFEITO, DENSIDADE_MAXIMA,
                         fator_crescimento_densidade, FATOR_FCR_IMTA)

N_DIAS = 1400      # chega para todos os cenários possíveis com os controlos
N_PEIXES = 1000    # peixes simulados; os resultados são depois escalados ao nº de juvenis
ESPECIES = ["dourada", "robalo", "pregado", "linguado"]
CIENTIFICOS = {e: PARAMETROS[e]["nome_cientifico"] for e in ESPECIES}

# Paleta "mar e fichas": banda azul-petróleo no topo, fundo cinzento-esverdeado claro e fichas brancas
# (as mesmas cores estão no index.html e em .streamlit/config.toml)
COR_MAR = "#17474F"            # banda do cabeçalho
COR_FUNDO = "#E9EEEE"
COR_FICHA = "#FFFFFF"          # fichas e fundo das figuras
COR_BORDA = "#D6E0E0"
COR_TEXTO = "#1C2629"
COR_TEXTO_SUAVE = "#56676A"
COR_GRELHA = "#DCE5E5"
COR_TINTA = "#1F5C66"          # azul-petróleo: temperatura, ligações e destaques
COR_PESAGENS = "#1C2629"
# Linhas batimétricas (curvas de profundidade) desenhadas na banda do cabeçalho
BATIMETRIA = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='420' viewBox='0 0 1200 420'%3E"
              "%3Cg fill='none' stroke='%23ffffff' stroke-opacity='0.085' stroke-width='1.3'%3E"
              "%3Cpath d='M-40 60 C160 10 320 120 520 70 S880 0 1240 80'/%3E%3Cpath d='M-40 110 C170 62 330 172 530 124 S890 50 1240 132'/%3E"
              "%3Cpath d='M-40 160 C180 114 340 224 540 178 S900 100 1240 184'/%3E%3Cpath d='M-40 210 C190 166 350 276 550 232 S910 150 1240 236'/%3E"
              "%3Cpath d='M-40 260 C200 218 360 328 560 286 S920 200 1240 288'/%3E%3Cpath d='M-40 310 C210 270 370 380 570 340 S930 250 1240 340'/%3E"
              "%3Cpath d='M-40 360 C220 322 380 432 580 394 S940 300 1240 392'/%3E"
              "%3Cpath d='M700 30 C760 10 860 20 880 60 S800 120 740 100 S650 50 700 30 Z'/%3E"
              "%3Cpath d='M720 46 C770 32 840 40 852 64 S800 100 756 88 S690 58 720 46 Z'/%3E%3C/g%3E%3C/svg%3E\")")
CORES = {"dourada": "#A9781A", "robalo": "#2C5D8A", "pregado": "#9A4632", "linguado": "#4F7A3A"}
LETRA = "IBM Plex Sans"
LETRA_TITULOS = "Source Serif 4"

URL_GITHUB = "https://github.com/dinistcosta/aquaculture-growth-model"
URL_LINKEDIN = "https://www.linkedin.com/in/dinis-costa-a58a67380"

# Data de entrada do exemplo: o próximo 1 de abril (assim a colheita "prevista" nunca é uma data passada)
_hoje = datetime.date.today()
DATA_ENTRADA_EXEMPLO = datetime.date(_hoje.year + (_hoje >= datetime.date(_hoje.year, 4, 1)), 4, 1)

# Ficheiros de exemplo que a pessoa pode descarregar e preencher (datas a partir da entrada do exemplo)
_ano = DATA_ENTRADA_EXEMPLO.year
MODELO_TEMPERATURAS = f"data,temperatura_c\n{_ano}-04-01,16.5\n{_ano}-04-08,17.0\n{_ano}-04-15,17.2\n"
MODELO_PESAGENS = f"data,peso_medio_g\n{_ano}-05-01,9.8\n{_ano}-06-01,24.5\n{_ano}-07-01,48.0\n"

# Tamanho comercial de partida (g): 400 g para dourada e robalo (Cardia & Lovatelli, 2007);
# 1 kg para o pregado (vende-se entre 0,7 e 2 kg; FAO); 350 g para o linguado (FAO).
TAMANHO_COMERCIAL = {"dourada": 400, "robalo": 400, "pregado": 1000, "linguado": 350}
# Peso dos juvenis à entrada (g): 3 g (Cardia & Lovatelli, 2007); pregado 10 g (exploração em
# Portugal, ver src/growth.py); linguado 5 g (FAO).
PESO_ENTRADA = {"dourada": PESO_INICIAL_G, "robalo": PESO_INICIAL_G, "pregado": 10.0, "linguado": 5.0}

# Preços de partida (podem ser alterados na app):
# - venda à saída da exploração em 2023 (EUMOFA, perfis de espécie): dourada 4,89 e robalo
#   6,45 €/kg (Grécia); pregado 11,29 €/kg (Portugal);
# - linguado: 12,25 €/kg no mercado grossista de Madrid em 2013 (Morais et al., 2016);
# - juvenil de dourada e robalo: 0,20 €/unidade = 73,2 milhões de euros / 366 milhões de
#   juvenis em 2020 (HAPO, Aquaculture in Greece 2021; cálculo nosso);
# - juvenil de linguado: os juvenis são 3,77 € por kg produzido (Bjørndal & Guillen, 2014,
#   citado em Morais et al., 2016); 3,77 x 0,35 kg = 1,32 € por peixe (cálculo nosso);
# - juvenil de pregado: SEM FONTE (pressuposto igual ao do linguado);
# - ração: ≈ 1,04 €/kg, preço médio em 2020 na Grécia (HAPO, 2021).
# Segundo a HAPO (2021), a ração e os juvenis são cerca de 70 % do custo de produção da dourada
# e do robalo; usamos o mesmo valor nas outras espécies (pressuposto).
PRECO_VENDA = {"dourada": 4.89, "robalo": 6.45, "pregado": 11.29, "linguado": 12.25}
PRECO_JUVENIL = {"dourada": 0.20, "robalo": 0.20, "pregado": 1.32, "linguado": 1.32}
PRECO_RACAO = 1.04
PESO_RACAO_JUVENIS_NO_CUSTO = 0.70

# Nomes das colunas em inglês que também são aceites nos CSV
COLUNAS_EN = {"date": "data", "temperature_c": "temperatura_c", "mean_weight_g": "peso_medio_g"}

# Tema "mar e fichas" por cima do tema do Streamlit:
# - cabeçalho numa banda azul-petróleo de ponta a ponta (com as mesmas medidas do ecrã de abertura);
# - cartões e figuras em fichas brancas com sombra suave, sobre o fundo cinzento-esverdeado;
# - títulos com letra serifada; legendas e ligações com contraste suficiente;
# - anel de foco visível; linhas de texto com 65-75 caracteres;
# - botões com pelo menos 44 px de altura no telemóvel.
ESTILO = f"""
<style>
  :root {{ --margem: clamp(1rem, 5vw, 5rem); --sombra: 0 1px 2px rgba(16, 40, 45, 0.06), 0 10px 24px -14px rgba(16, 40, 45, 0.45); }}
  h1, h2, h3 {{ font-family: '{LETRA_TITULOS}', Georgia, serif !important; letter-spacing: -0.01em; }}
  h1 {{ font-size: clamp(2rem, 1.3rem + 2.4vw, 3rem) !important; line-height: 1.1 !important; font-weight: 600 !important;
        max-width: 22ch; text-wrap: balance; padding: 0 !important; }}
  h2 {{ font-size: 1.55rem !important; font-weight: 600 !important; padding-top: 1.75rem !important;
        border-bottom: 1px solid {COR_TEXTO_SUAVE}; padding-bottom: 0.35rem !important; margin-bottom: 0.75rem !important; }}
  h3 {{ font-size: 1.2rem !important; font-weight: 600 !important; }}
  .subtitulo {{ font-family: '{LETRA_TITULOS}', Georgia, serif; font-style: italic; font-size: 1.2rem; margin: 0; }}
  /* Sem a barra de ferramentas do Streamlit; margens iguais às do ecrã de abertura (index.html) */
  header[data-testid="stHeader"] {{ display: none; }}
  [data-testid="stMainBlockContainer"] {{ padding-top: 0 !important;
      padding-left: var(--margem) !important; padding-right: var(--margem) !important; }}

  /* Banda do cabeçalho */
  /* Os blocos <style> não ocupam espaço (senão deixam uma faixa vazia por cima da banda) */
  [data-testid="stElementContainer"]:has(style) {{ display: none; }}
  .st-key-cabecalho {{ margin: 0 calc(-1 * var(--margem)); width: calc(100% + 2 * var(--margem)) !important; max-width: none !important;
      padding: 4.5rem var(--margem) 2.5rem;
      background: {COR_MAR} {BATIMETRIA} center / cover no-repeat; gap: 1.1rem; }}
  .st-key-cabecalho h1 {{ color: #F3EFE6; }}
  .st-key-cabecalho .subtitulo {{ color: #C4D6D7; }}
  .st-key-cabecalho p, .st-key-cabecalho strong {{ color: #E3ECEC; }}
  .st-key-cabecalho [data-testid="stCaptionContainer"], .st-key-cabecalho [data-testid="stCaptionContainer"] * {{ color: #C4D6D7; }}
  .st-key-cabecalho [data-testid="stLinkButton"] a, .st-key-cabecalho [data-testid="stButtonGroup"] button {{
      background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.35); color: #F3EFE6; }}
  .st-key-cabecalho [data-testid="stLinkButton"] a *, .st-key-cabecalho [data-testid="stButtonGroup"] button * {{ color: #F3EFE6 !important; }}
  .st-key-cabecalho [data-testid="stLinkButton"] a:hover {{ background: rgba(255, 255, 255, 0.14); border-color: #F3EFE6; }}
  .st-key-cabecalho [data-testid="stButtonGroup"] button[aria-checked="true"] {{ background: #F3EFE6; border-color: #F3EFE6; }}
  .st-key-cabecalho [data-testid="stButtonGroup"] button[aria-checked="true"] * {{ color: {COR_MAR} !important; }}
  .st-key-cabecalho :focus-visible {{ outline-color: #F3EFE6 !important; }}

  /* Fichas: contentores com borda (cenário, cartões das espécies, figuras) */
  /* (cada contentor com borda tem uma key que começa por "ficha", e o Streamlit põe-na na classe) */
  [class*="st-key-ficha"] {{ background: {COR_FICHA}; border-color: {COR_BORDA} !important;
      border-radius: 8px !important; box-shadow: var(--sombra); }}
  [data-testid="stExpander"] details {{ background: {COR_FICHA}; border-color: {COR_BORDA}; border-radius: 6px; }}
  hr {{ border: none !important; border-top: 1px solid {COR_BORDA} !important; }}

  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ opacity: 1; color: {COR_TEXTO_SUAVE}; }}
  [data-testid="stCaptionContainer"] em {{ font-family: '{LETRA_TITULOS}', Georgia, serif; font-style: italic; }}
  [data-testid="stMarkdownContainer"] a {{ color: {COR_TINTA}; text-underline-offset: 0.15em; }}
  [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] p {{ max-width: 72ch; }}
  [data-testid="stButtonGroup"] button[aria-checked="true"],
  [data-testid="stButtonGroup"] button[aria-checked="true"] * {{ color: {COR_TINTA} !important; }}
  :focus-visible {{ outline: 2px solid {COR_TINTA} !important; outline-offset: 2px; }}
  ::selection {{ background: #CFE3E3; }}
  [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; font-family: '{LETRA_TITULOS}', Georgia, serif; }}
  @media (max-width: 640px) {{
    [data-testid="stButtonGroup"] button, [data-testid="stLinkButton"] a {{ min-height: 44px; }}
    [data-testid="stMetricValue"] {{ font-size: 1.6rem; }}
  }}
</style>
"""
# Risca com a cor da espécie no topo de cada cartão de resultados (como no ecrã de abertura)
ESTILO += "<style>" + "".join(f".st-key-ficha_{e} {{ border-top: 3px solid {c} !important; }}"
                              for e, c in CORES.items()) + "</style>"


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


NOMES = {"dourada": t("Dourada", "Sea bream"), "robalo": t("Robalo", "Sea bass"),
         "pregado": t("Pregado", "Turbot"), "linguado": t("Linguado", "Sole")}
MESES = t(["jan.", "fev.", "mar.", "abr.", "maio", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."],
          ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

# Fontes dos valores de partida de cada espécie (aparecem nos cartões)
FONTES = {
    "dourada": {"crescimento": "Mayer et al. (2012)", "sobrevivencia": "Muniesa et al. (2020)",
                "fcr": "Kallitsis & Avramidis (2025)"},
    "robalo": {"crescimento": t("TGC calibrado (Cardia & Lovatelli, 2007)", "calibrated TGC (Cardia & Lovatelli, 2007)"),
               "sobrevivencia": "Muniesa et al. (2020)", "fcr": "Kallitsis & Avramidis (2025)"},
    "pregado": {"crescimento": t("TGC calibrado (FAO)", "calibrated TGC (FAO)"),
                "sobrevivencia": t("pressuposto", "assumption"), "fcr": "FAO"},
    "linguado": {"crescimento": t("TGC calibrado (FAO)", "calibrated TGC (FAO)"),
                 "sobrevivencia": "Quental-Ferreira et al. (2010)", "fcr": "Valente et al. (2011)"},
}

st.set_page_config(page_title=t("Quanto tempo demora um peixe a chegar ao tamanho comercial?",
                                "How long does a fish take to reach market size?"),
                   page_icon=":material/show_chart:", layout="wide")
st.markdown(ESTILO, unsafe_allow_html=True)

# O Streamlit escreve sempre em inglês no campo de envio de ficheiros ("Upload", "200MB per file");
# escondemos esses textos e pomos outros, na língua escolhida, por CSS.
st.markdown(f"""
<style>
  [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p,
  [data-testid="stFileUploaderDropzoneInstructions"] span {{ font-size: 0; max-width: none; }}
  [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"] p::after {{
    content: "{t('Escolher ficheiro', 'Choose file')}"; font-size: 0.875rem; }}
  [data-testid="stFileUploaderDropzoneInstructions"] span::after {{
    content: "{t('ou arrastar para aqui · CSV', 'or drag it here · CSV')}"; font-size: 0.875rem; }}
</style>
""", unsafe_allow_html=True)


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


def gramas(peso):
    """Escreve um peso sem casas decimais inúteis (3 g, 7,5 g)."""
    return virgula(peso, 1).replace(",0", "").replace(".0", "")


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
    """Gráficos com o aspeto de figura de artigo: fundo branco, títulos serifados, grelha fina e pontilhada."""
    return (grafico.configure(font=LETRA, background=COR_FICHA)
            .configure_title(font=f"'{LETRA_TITULOS}', Georgia, serif", color=COR_TEXTO, fontSize=16, fontWeight=600,
                             subtitleFont=LETRA, subtitleColor=COR_TEXTO_SUAVE, subtitleFontSize=12, anchor="start")
            .configure_axis(labelColor=COR_TEXTO_SUAVE, titleColor=COR_TEXTO_SUAVE, gridColor=COR_GRELHA,
                            gridDash=[2, 3], domainColor="#8A9A9C", tickColor="#8A9A9C", labelFontSize=11)
            .configure_legend(labelColor=COR_TEXTO, titleColor=COR_TEXTO_SUAVE)
            .configure_view(strokeWidth=0))


# As figuras são numeradas pela ordem em que aparecem, como num artigo
numero_figura = [0]


def figura(grafico, legenda, coluna=st):
    """Mostra um gráfico com uma legenda numerada por baixo (Fig. 1, Fig. 2, ...)."""
    numero_figura[0] += 1
    with coluna.container(border=True, key=f"ficha_figura_{numero_figura[0]}"):
        st.altair_chart(com_estilo(grafico), width="stretch")
        st.caption(f"*Fig. {numero_figura[0]}.* {legenda}")


# ---------------------------------------------------------------------------
# 1. Cabeçalho (título, autor e botão da língua)
# ---------------------------------------------------------------------------
# Tudo dentro da banda azul-petróleo (classe CSS "st-key-cabecalho", ver ESTILO)
with st.container(key="cabecalho"):
    st.title(t("Quanto tempo demora um peixe a chegar ao tamanho comercial?",
               "How long does a fish take to reach market size?"), anchor=False)
    # Subtítulo e botão da língua na mesma linha
    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        st.markdown(f'<p class="subtitulo">{t("Modelo de crescimento em aquacultura", "Growth model for aquaculture")}</p>',
                    unsafe_allow_html=True, width="content")
        idioma_escolhido = st.segmented_control(
            "Idioma / Language", ["pt", "en"], default=idioma, required=True, key="idioma",
            format_func=str.upper, label_visibility="collapsed")
    st.query_params["lang"] = idioma_escolhido   # o link copiado abre na mesma língua

    st.markdown(t("Simulação do ciclo de engorda da dourada, do robalo, do pregado e do linguado, com parâmetros "
                  "publicados: quando chegam ao tamanho comercial, quanta ração gastam e quanto custa produzi-los, "
                  "em jaula no mar ou em tanque / RAS.",
                  "A grow-out simulation of sea bream, sea bass, turbot and sole, with published parameters: when "
                  "they reach market size, how much feed they use and what it costs to produce them, in sea cages "
                  "or tanks / RAS."))
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.markdown(t("**Dinis Costa** · Mestrado em Biologia Marinha Aplicada",
                      "**Dinis Costa** · MSc in Applied Marine Biology"), width="content")
        st.link_button("LinkedIn", URL_LINKEDIN, icon=":material/person:")
        st.link_button("GitHub", URL_GITHUB, icon=":material/code:")
    st.caption(t("Resultados **simulados** com parâmetros da literatura científica; "
                 "não são dados de nenhuma exploração.",
                 "**Simulated** results based on parameters from the scientific literature; "
                 "they are not data from any farm."))


# ---------------------------------------------------------------------------
# 2. Cenário (controlos à vista, por cima dos resultados)
# ---------------------------------------------------------------------------
# Cada controlo tem uma `key`: assim a escolha mantém-se quando se muda de língua.
st.header(t("Cenário", "Scenario"), anchor="cenario")
with st.container(border=True, key="ficha_cenario"):
    especies = st.pills(
        t("Espécies", "Species"), ESPECIES, selection_mode="multi", default=ESPECIES,
        format_func=lambda e: NOMES[e], key="especies",
        help=t("O pregado e o linguado são criados sobretudo em tanques em terra, e os seus parâmetros "
               "são os menos seguros do modelo (ver Notas sobre o modelo).",
               "Turbot and sole are farmed mostly in land-based tanks, and their parameters are the "
               "least certain in the model (see Notes on the model)."))
    especies = [e for e in ESPECIES if e in (especies or [])]

    c1, c2 = st.columns(2, gap="medium")
    sistema = c1.segmented_control(
        t("Sistema de cultivo", "Farming system"), ["jaula", "tanque"], default="jaula", required=True,
        format_func=lambda s: t("Jaula no mar", "Sea cage") if s == "jaula" else t("Tanque / RAS", "Tank / RAS"),
        key="sistema",
        help=t("**Jaula no mar:** a temperatura é a do mar e varia ± 4 °C ao longo do ano "
               "(mínimo em fevereiro, máximo em agosto).  \n"
               "**Tanque / RAS:** tanque em terra com temperatura controlada (constante).",
               "**Sea cage:** water temperature follows the sea and varies by ± 4 °C over the year "
               "(lowest in February, highest in August).  \n"
               "**Tank / RAS:** land-based tank with controlled (constant) temperature."))

    alimentacao = c2.segmented_control(
        t("Alimentação", "Feeding"), ["saciedade", "restrita"], default="saciedade", required=True,
        format_func=lambda a: t("Até à saciedade", "To satiation") if a == "saciedade" else t("Restrita", "Restricted"),
        key="alimentacao",
        help=t("**Restrita:** 80 % da saciedade na dourada (Bonaldo et al., 2010) e "
               "75 % no robalo (Türkmen et al., 2012). Sem dados para o pregado e o linguado.",
               "**Restricted:** 80 % of satiation in sea bream (Bonaldo et al., 2010) and "
               "75 % in sea bass (Türkmen et al., 2012). No data for turbot and sole."))

    # Com um CSV de temperaturas carregado, o slider da temperatura deixa de ser usado
    usa_csv_temperatura = st.session_state.get("ficheiro_temp") is not None
    aviso_csv = t(" · substituída pelo CSV", " · replaced by the CSV") if usa_csv_temperatura else ""

    c1, c2 = st.columns(2, gap="medium")
    densidade = None
    imta = False
    if sistema == "jaula":
        media = c1.slider(t("Temperatura média anual do mar (°C)", "Mean annual sea temperature (°C)") + aviso_csv,
                          15.0, 21.0, 19.0, 0.5, format="%.1f", key="media", disabled=usa_csv_temperatura)
        if "robalo" in especies:
            with c2:
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
            help=t(f"{virgula(TEMPERATURA_TANQUE, 0)} °C é o meio do intervalo 18–26 °C indicado pela FAO (2009) "
                   "para a dourada. O pregado come melhor a 14–18 °C (FAO) e o linguado é criado a cerca de 20 °C "
                   "(Morais et al., 2016).",
                   f"{virgula(TEMPERATURA_TANQUE, 0)} °C is the middle of the 18–26 °C range given by FAO (2009) "
                   "for sea bream. Turbot feeds best at 14–18 °C (FAO) and sole is farmed at about 20 °C "
                   "(Morais et al., 2016)."))
        densidade = c2.slider(
            t("Densidade (kg/m³)", "Stocking density (kg/m³)"), 10, DENSIDADE_MAXIMA, 40, 5, key="densidade",
            help=t(f"No robalo, até {DENSIDADE_SEM_EFEITO} kg/m³ não há efeito no crescimento; "
                   f"a {DENSIDADE_MAXIMA} kg/m³ a SGR desce 14 % (Sammouth et al., 2009). "
                   "Nas outras espécies não encontrámos dados, por isso a densidade só serve para calcular o volume de tanque.",
                   f"In sea bass, density has no effect on growth up to {DENSIDADE_SEM_EFEITO} kg/m³; "
                   f"at {DENSIDADE_MAXIMA} kg/m³ SGR drops by 14 % (Sammouth et al., 2009). "
                   "No data were found for the other species, so density is only used to compute tank volume."))

    with st.expander(t("Dados da exploração: juvenis, datas, temperaturas e pesagens",
                       "Farm data: juveniles, dates, temperatures and weighings")):
        st.caption(t("Os valores de partida são um exemplo. Substitua-os pelos de uma exploração. "
                     "Os ficheiros são lidos apenas no browser e não são enviados para nenhum servidor.",
                     "The starting values are an example. Replace them with those of a farm. "
                     "Files are read only in the browser and are not sent to any server."))
        c1, c2 = st.columns(2, gap="medium")
        n_juvenis = c1.number_input(t("Número de juvenis", "Number of juveniles"), 100, 5_000_000, N_PEIXES, 1000,
                                    key="n_juvenis")
        data_entrada = c2.date_input(t("Data de entrada", "Stocking date"), DATA_ENTRADA_EXEMPLO,
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

    # Parâmetros de cada espécie: começam nos valores da literatura e podem ser trocados pelos de uma exploração
    with st.expander(t("Parâmetros de cada espécie: tamanhos, TGC, FCR e sobrevivência",
                       "Species parameters: sizes, TGC, FCR and survival")):
        st.caption(t("Valores de partida da literatura (ver Notas sobre o modelo). O TGC de uma exploração "
                     "calcula-se com duas pesagens: (peso final^(1/3) − peso inicial^(1/3)) a dividir pela soma de "
                     "(temperatura − base) em todos os dias entre elas; a base é 12 °C na dourada e no robalo "
                     "e 0 °C no pregado e no linguado.",
                     "Starting values from the literature (see Notes on the model). A farm's TGC is computed from "
                     "two weighings: (final weight^(1/3) − initial weight^(1/3)) divided by the sum of "
                     "(temperature − base) over all the days between them; the base is 12 °C for sea bream and "
                     "sea bass and 0 °C for turbot and sole."))
        parametros, fcr_base, peso_comercial, peso_inicial = {}, {}, {}, {}
        colunas_param = st.columns(2, gap="large")
        for i, e in enumerate(ESPECIES):
            p = PARAMETROS[e]
            with colunas_param[i % 2]:
                st.markdown(f"**{NOMES[e]}** *{CIENTIFICOS[e]}*")
                c1, c2 = st.columns(2)
                peso_inicial[e] = c1.number_input(t("Peso de entrada (g)", "Stocking weight (g)"), 1.0, 200.0,
                                                  PESO_ENTRADA[e], 0.5, format="%.1f", key=f"peso_inicial_{e}")
                peso_comercial[e] = c2.number_input(t("Tamanho comercial (g)", "Market size (g)"), 100, 3000,
                                                    TAMANHO_COMERCIAL[e], 25, key=f"peso_comercial_{e}")
                tgc_1_3 = c1.number_input(t("TGC (fase W^1/3)", "TGC (W^1/3 stage)"), 0.0001, 0.0060, p["tgc_1_3"],
                                          0.0001, format="%.5f", key=f"tgc13_{e}")
                tgc_2_3 = None
                if p["tgc_2_3"]:
                    tgc_2_3 = c2.number_input(t("TGC (fase W^2/3)", "TGC (W^2/3 stage)"), 0.003, 0.060,
                                              p["tgc_2_3"], 0.0005, format="%.5f", key=f"tgc23_{e}")
                fcr_base[e] = c1.number_input("FCR", 0.6, 4.0, p["fcr"], 0.05, format="%.2f", key=f"fcr_{e}")
                sobrevivencia = c2.number_input(t("Sobrevivência no ciclo (%)", "Survival over the cycle (%)"),
                                                30, 100, round(p["sobrevivencia_ciclo"] * 100), 1, key=f"sobrev_{e}")
                if tgc_2_3:
                    st.caption(t("Muda de fase aos ", "Changes stage at ")
                               + f"{virgula(peso_critico({'tgc_1_3': tgc_1_3, 'tgc_2_3': tgc_2_3}), 0)} g")
                parametros[e] = {"tgc_1_3": tgc_1_3, "tgc_2_3": tgc_2_3, "sobrevivencia_ciclo": sobrevivencia / 100}

    with st.expander(t("Preços e custos", "Prices and costs")):
        st.caption(t("Valores de partida: venda à saída da exploração em 2023 (EUMOFA; linguado: mercado de "
                     "Madrid em 2013); juvenis e ração na Grécia em 2020 (HAPO, 2021); juvenil de linguado a "
                     "partir de Bjørndal & Guillen (2014); juvenil de pregado sem fonte. Os preços mudam de ano "
                     "para ano: convém usar os da exploração.",
                     "Starting values: ex-farm sale price in 2023 (EUMOFA; sole: Madrid market in 2013); "
                     "juveniles and feed in Greece in 2020 (HAPO, 2021); sole juvenile from Bjørndal & Guillen "
                     "(2014); turbot juvenile without a source. Prices change from year to year: a farm's own "
                     "prices are best."))
        preco_venda, preco_juvenil = {}, {}
        colunas_preco = st.columns(4, gap="medium")
        for coluna, e in zip(colunas_preco, ESPECIES):
            preco_venda[e] = coluna.number_input(t(f"Venda {NOMES[e].lower()} (€/kg)", f"{NOMES[e]} sale (€/kg)"),
                                                 0.0, 50.0, PRECO_VENDA[e], 0.10, format="%.2f", key=f"venda_{e}")
            preco_juvenil[e] = coluna.number_input(t(f"Juvenil {NOMES[e].lower()} (€)", f"{NOMES[e]} juvenile (€)"),
                                                   0.0, 10.0, PRECO_JUVENIL[e], 0.01, format="%.2f",
                                                   key=f"juvenil_{e}")
        preco_racao = st.number_input(t("Ração (€/kg)", "Feed (€/kg)"), 0.0, 10.0, PRECO_RACAO, 0.05,
                                      format="%.2f", key="preco_racao")

if not especies:
    st.info(t("Escolha pelo menos uma espécie no cenário.", "Choose at least one species in the scenario."),
              icon=":material/info:")
    st.stop()

# É um exemplo enquanto os dados da exploração e os parâmetros estiverem nos valores de partida
e_exemplo = (n_juvenis == N_PEIXES and data_entrada == DATA_ENTRADA_EXEMPLO
             and ficheiro_temp is None and ficheiro_pesos is None
             and all(parametros[e]["tgc_1_3"] == PARAMETROS[e]["tgc_1_3"]
                     and parametros[e]["tgc_2_3"] == PARAMETROS[e]["tgc_2_3"]
                     and fcr_base[e] == PARAMETROS[e]["fcr"]
                     and parametros[e]["sobrevivencia_ciclo"] == PARAMETROS[e]["sobrevivencia_ciclo"]
                     and peso_inicial[e] == PESO_ENTRADA[e]
                     for e in ESPECIES))


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
    except ValueError as erro:
        erro_temp.error(str(erro))

# Temperaturas acima do limite de cada espécie: o modelo deixa de as usar (limita-as ao máximo)
for e in especies:
    maxima = PARAMETROS[e]["temperatura_maxima"]
    if temperatura.max() > maxima:
        st.warning(t(f"{NOMES[e]}: há temperaturas acima de {virgula(maxima, 0)} °C, o limite do modelo para "
                     "esta espécie. Acima disso o crescimento foi calculado como se a água estivesse a esse valor.",
                     f"{NOMES[e]}: some temperatures are above {virgula(maxima, 0)} °C, the model's limit for this "
                     "species. Above it, growth was computed as if the water were at that value."),
                   icon=":material/warning:")

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
    """Corre a simulação (o resultado fica guardado para não repetir contas).

    Devolve a tabela diária e o peso de cada peixe de 5 em 5 dias (para o histograma da colheita).
    """
    tabela = simular_ciclo(especie, n_dias=N_DIAS, n_peixes=N_PEIXES, temperatura=temperatura,
                           data_inicio=str(data_entrada), peso_inicial_g=peso_inicial,
                           fator_crescimento=fator_crescimento, fcr=fcr, parametros=parametros, semente=42,
                           guardar_pesos_cada=5)
    pesos = tabela.attrs.pop("pesos")    # fora da tabela: o pandas não junta tabelas com arrays nos atributos
    return tabela, pesos


def simular_especie(especie):
    """Junta os efeitos do cenário escolhido e escala o resultado ao nº de juvenis."""
    sem_restricao = CENARIOS_ALIMENTACAO.get(especie, {}).get("saciedade", {"fator_crescimento": 1.0, "fator_fcr": 1.0})
    cenario = CENARIOS_ALIMENTACAO.get(especie, {}).get(alimentacao, sem_restricao)
    fator_crescimento = cenario["fator_crescimento"]
    fcr = fcr_base[especie] * cenario["fator_fcr"]
    if especie == "robalo" and densidade is not None:
        fator_crescimento *= fator_crescimento_densidade(densidade)
    if especie == "robalo" and imta:
        fcr *= FATOR_FCR_IMTA
    sim, pesos = simular(especie, temperatura, fator_crescimento, fcr, peso_inicial[especie], data_entrada,
                         parametros[especie])

    # Simulamos 1 000 peixes; para outro número de juvenis, os totais crescem na mesma proporção
    escala = n_juvenis / N_PEIXES
    sim = sim.assign(n_peixes=(sim["n_peixes"] * escala).round().astype(int),
                     biomassa_kg=sim["biomassa_kg"] * escala,
                     racao_kg=sim["racao_kg"] * escala,
                     mortos=(sim["mortos"] * escala).round().astype(int))
    return sim, pesos


def fontes(especie):
    """Fontes dos números do cartão, conforme o cenário escolhido."""
    p, f = parametros[especie], FONTES[especie]
    tgc_mudou = p["tgc_1_3"] != PARAMETROS[especie]["tgc_1_3"] or p["tgc_2_3"] != PARAMETROS[especie]["tgc_2_3"]
    lista = [t("Crescimento", "Growth") + ": " + (t("TGC introduzido", "TGC entered") if tgc_mudou else f["crescimento"])]
    sobrevivencia_lit = p["sobrevivencia_ciclo"] == PARAMETROS[especie]["sobrevivencia_ciclo"]
    lista.append(t("Sobrevivência", "Survival") + ": "
                 + (f["sobrevivencia"] if sobrevivencia_lit else t("introduzida", "entered")))
    lista.append("FCR: " + (f["fcr"] if fcr_base[especie] == PARAMETROS[especie]["fcr"] else t("introduzido", "entered")))
    if alimentacao == "restrita":
        restrita = {"dourada": "Bonaldo et al. (2010)", "robalo": "Türkmen et al. (2012)"}
        lista.append(t("Ração restrita", "Restricted feeding") + ": "
                     + restrita.get(especie, t("sem dados (igual à saciedade)", "no data (same as satiation)")))
    if especie == "robalo" and densidade is not None:
        lista.append(t("Densidade", "Density") + ": Sammouth et al. (2009)")
    if especie == "robalo" and imta:
        lista.append("IMTA: Cotou et al. (2024)")
    return " · ".join(lista)


with st.spinner(t("A simular...", "Simulating...")):
    resultados = {e: simular_especie(e) for e in especies}
simulacoes = {e: r[0] for e, r in resultados.items()}
pesos_individuais = {e: r[1] for e, r in resultados.items()}
dias_alvo = {e: dias_ate_peso(s, peso_comercial[e]) for e, s in simulacoes.items()}


# ---------------------------------------------------------------------------
# 5. Resultados: um cartão por espécie e calendário de produção
# ---------------------------------------------------------------------------
st.header(t("Resultados", "Results"), anchor="resultados")
if e_exemplo:
    st.caption(t(f"**Exemplo** com os valores de partida: 1 000 juvenis a entrar a 1 de abril de {DATA_ENTRADA_EXEMPLO.year}, "
                 "com os parâmetros da literatura. Para usar os dados de uma exploração, abrir **Dados da exploração** "
                 "no [painel do cenário](#cenario).",
                 f"**Example** with the starting values: 1,000 juveniles stocked on 1 April {DATA_ENTRADA_EXEMPLO.year}, "
                 "with parameters from the literature. To use a farm's data, open **Farm data** in the "
                 "[scenario panel](#cenario)."))
for aviso in avisos:
    st.caption(aviso)

for inicio in range(0, len(especies), 2):          # dois cartões por linha
    linha_especies = especies[inicio:inicio + 2]
    for coluna, especie in zip(st.columns(2, gap="medium"), linha_especies):
        sim = simulacoes[especie]
        dia = dias_alvo[especie]
        alvo_g = peso_comercial[especie]
        with coluna.container(border=True, key=f"ficha_{especie}"):
            # Quadrado com a cor da espécie nos gráficos
            marca = (f'<span style="display:inline-block;width:0.7em;height:0.7em;border-radius:1px;'
                     f'background:{CORES[especie]};margin-right:0.4em"></span>')
            st.markdown(f"### {marca}{NOMES[especie]} &nbsp;*{CIENTIFICOS[especie]}*", unsafe_allow_html=True)
            if dia is None:
                st.error(t(f"Não chega aos {alvo_g} g em {N_DIAS} dias. "
                           "Experimente uma temperatura mais alta ou um tamanho comercial menor.",
                           f"Does not reach {alvo_g} g within {N_DIAS} days. "
                           "Try a higher temperature or a smaller market size."))
                continue
            ate_peso = sim.loc[:dia]
            ganho_biomassa = ate_peso["biomassa_kg"].iloc[-1] - n_juvenis * peso_inicial[especie] / 1000
            fcr = ate_peso["racao_kg"].sum() / ganho_biomassa
            with st.container(horizontal=True, gap="medium"):
                st.metric(t(f"Meses até {milhares(alvo_g)} g", f"Months to {milhares(alvo_g)} g"),
                          virgula(dia / 30.4), width="content")
                st.metric("FCR", virgula(fcr, 2), width="content",
                          help=t("FCR económico: kg de ração por kg de peixe produzido, incluindo a ração comida "
                                 "pelos peixes que morreram.",
                                 "Economic FCR: kg of feed per kg of fish produced, including feed eaten by fish "
                                 "that died."))
                st.metric(t("Sobrevivência", "Survival"), f"{sim.loc[dia, 'n_peixes'] / n_juvenis:.0%}",
                          width="content")
            st.caption(t(f"{milhares(dia)} dias · juvenis de {gramas(peso_inicial[especie])} g · colheita prevista: ",
                         f"{milhares(dia)} days · {gramas(peso_inicial[especie])} g juveniles · expected harvest: ")
                       + mes_e_ano(sim.loc[dia, "data"]))
            st.caption("*" + t("Fontes: ", "Sources: ") + fontes(especie) + "*")

# Cores e legenda comuns a todos os gráficos
escala_cor = alt.Scale(domain=[NOMES[e] for e in especies], range=[CORES[e] for e in especies])
cor = alt.Color("nome:N", title=None, scale=escala_cor,
                legend=alt.Legend(orient="top", direction="horizontal", offset=6,
                                  symbolType="stroke", symbolStrokeWidth=3, symbolOpacity=1,
                                  labelFontSize=13))
especie_tt = alt.Tooltip("nome:N", title=t("Espécie", "Species"))
ordem_nomes = [NOMES[e] for e in especies]

# Calendário de produção: da entrada dos juvenis à colheita, em meses do calendário
calendario = pd.DataFrame([{"nome": NOMES[e], "inicio": pd.Timestamp(data_entrada), "fim": simulacoes[e].loc[d, "data"],
                            "rotulo": t("colheita ", "harvest ") + mes_e_ano(simulacoes[e].loc[d, "data"])}
                           for e, d in dias_alvo.items() if d is not None])
if not calendario.empty:
    fim_eixo = calendario["fim"].max() + pd.Timedelta(days=20)
    escala_t = alt.Scale(domain=[calendario["inicio"].min(), fim_eixo])
    barras = alt.Chart(calendario).mark_bar(height=16, cornerRadius=2).encode(
        x=alt.X("inicio:T", scale=escala_t, axis=eixo_de_meses()), x2="fim:T",
        y=alt.Y("nome:N", title=None, sort=ordem_nomes,
                axis=alt.Axis(labelFontSize=13, labelPadding=8, domain=False, ticks=False)),
        color=alt.Color("nome:N", scale=escala_cor, legend=None),
        tooltip=[especie_tt, alt.Tooltip("inicio:T", title=t("Entrada", "Stocking"), format="%d/%m/%Y"),
                 alt.Tooltip("fim:T", title=t("Colheita", "Harvest"), format="%d/%m/%Y")])
    # Rótulo dentro da barra, encostado ao fim (cabe em qualquer largura de ecrã)
    rotulos = alt.Chart(calendario).mark_text(align="right", dx=-8, fontSize=12, color="white",
                                              fontWeight=600).encode(
        x=alt.X("fim:T", scale=escala_t), y=alt.Y("nome:N", sort=ordem_nomes), text="rotulo:N")
    figura((barras + rotulos).properties(height=alt.Step(36),
                                         title=alt.Title(t("Calendário de produção", "Production calendar"))),
           t("Da entrada dos juvenis à colheita de cada espécie, no calendário.",
             "From stocking to harvest for each species, on the calendar."))


# ---------------------------------------------------------------------------
# 6. Figuras, por separadores
# ---------------------------------------------------------------------------
aba_crescimento, aba_colheita, aba_indicadores, aba_custos, aba_entrada, aba_dados = st.tabs(
    t(["Crescimento", "Colheita", "Indicadores", "Custos", "Entrada", "Dados"],
      ["Growth", "Harvest", "Indicators", "Costs", "Stocking", "Data"]))

dia_maximo = min(N_DIAS, int(max(d or N_DIAS for d in dias_alvo.values()) * 1.15))
if pesagens is not None:
    dia_maximo = max(dia_maximo, min(N_DIAS, int(pesagens["dia"].max()) + 10))
escala_x = alt.Scale(domain=[0, dia_maximo], nice=False)
eixo_x = alt.X("dia:Q", scale=escala_x, title=t("Dias desde a entrada dos juvenis", "Days since stocking"))
dia_tt = alt.Tooltip("dia:Q", title=t("Dia", "Day"))

with aba_crescimento:
    # O eixo do peso vai um pouco acima do maior tamanho comercial (ou da maior pesagem)
    peso_maximo = max(peso_comercial[e] for e in especies) * 1.5
    if pesagens is not None:
        peso_maximo = max(peso_maximo, pesagens["valor"].max() * 1.1)
    escala_y = alt.Scale(domain=[0, peso_maximo], nice=False)   # o que passa do topo é cortado (clip)

    # Tabela "longa" com as espécies, um ponto de 2 em 2 dias (gráfico mais leve)
    dados = pd.concat([
        s.iloc[:dia_maximo:2].assign(
            nome=NOMES[e],
            minimo=lambda d: (d["peso_medio_g"] - d["peso_dp_g"]).clip(lower=0),
            maximo=lambda d: d["peso_medio_g"] + d["peso_dp_g"])
        for e, s in simulacoes.items()])

    faixa = alt.Chart(dados).mark_area(opacity=0.14, clip=True).encode(
        x=eixo_x, y=alt.Y("minimo:Q", scale=escala_y), y2="maximo:Q", color=cor)
    linha = alt.Chart(dados).mark_line(strokeWidth=2.3, clip=True).encode(
        x=eixo_x,
        y=alt.Y("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), scale=escala_y,
                axis=alt.Axis(format="d")),
        color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("data:T", title=t("Data", "Date"), format="%d/%m/%Y"),
                 alt.Tooltip("peso_medio_g:Q", title=t("Peso médio (g)", "Mean weight (g)"), format=".0f"),
                 alt.Tooltip("peso_dp_g:Q", title=t("Desvio-padrão (g)", "Standard deviation (g)"), format=".0f"),
                 alt.Tooltip("temperatura_c:Q", title=t("Temperatura (°C)", "Temperature (°C)"), format=".1f")])
    # Uma linha tracejada por cada tamanho comercial diferente
    tamanhos = pd.DataFrame({"y": sorted({peso_comercial[e] for e in especies}), "x": 0})
    alvo = alt.Chart(tamanhos).mark_rule(strokeDash=[6, 4], color=COR_TEXTO_SUAVE).encode(
        y=alt.Y("y:Q", scale=escala_y))
    alvo_texto = alt.Chart(tamanhos).mark_text(align="left", dx=4, dy=-8, fontSize=12, color=COR_TEXTO_SUAVE).encode(
        x=alt.X("x:Q", scale=escala_x), y=alt.Y("y:Q", scale=escala_y),
        text=alt.Text("y:Q", format="d"))
    chegadas = pd.DataFrame([{"nome": NOMES[e], "dia": d, "peso": peso_comercial[e]}
                             for e, d in dias_alvo.items() if d is not None])
    pontos = alt.Chart(chegadas).mark_point(filled=True, size=110, stroke=COR_FICHA, strokeWidth=2,
                                            opacity=1).encode(
        x=alt.X("dia:Q", scale=escala_x), y=alt.Y("peso:Q", scale=escala_y), color=cor,
        tooltip=[especie_tt, alt.Tooltip("dia:Q", title=t("Chega ao tamanho comercial no dia",
                                                          "Reaches market size on day"))])

    camadas = faixa + linha + alvo + alvo_texto + pontos
    legenda_peso = t("Peso médio dos peixes (linha) e ± 1 desvio-padrão entre peixes (sombra). As linhas tracejadas "
                     "marcam o tamanho comercial (g) e os pontos o dia em que cada espécie lá chega.",
                     "Mean fish weight (line) and ± 1 standard deviation between fish (shading). Dashed lines mark "
                     "market size (g) and dots the day each species reaches it.")
    if pesagens is not None:
        # As pesagens da exploração, como losangos escuros por cima das curvas do modelo
        camadas += alt.Chart(pesagens).mark_point(shape="diamond", filled=True, size=90,
                                                  color=COR_PESAGENS, opacity=0.9).encode(
            x=alt.X("dia:Q", scale=escala_x), y=alt.Y("valor:Q", scale=escala_y),
            tooltip=[alt.Tooltip("data:T", title=t("Pesagem", "Weighing"), format="%d/%m/%Y"), dia_tt,
                     alt.Tooltip("valor:Q", title=t("Peso médio medido (g)", "Measured mean weight (g)"),
                                 format=".1f")])
        legenda_peso += t(" Losangos: pesagens da exploração.", " Diamonds: farm weighings.")
    figura(camadas.properties(height=380, title=alt.Title(t("Crescimento", "Growth"))), legenda_peso)

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
        line={"color": COR_TINTA, "strokeWidth": 2},
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                           stops=[alt.GradientStop(color=COR_FICHA, offset=0),
                                  alt.GradientStop(color=COR_TINTA, offset=1)]),
        opacity=0.3).encode(
        x=eixo_x,
        y=alt.Y("temperatura:Q", title=t("Temperatura (°C)", "Temperature (°C)"),
                scale=alt.Scale(domain=[10, 26]), axis=alt.Axis(values=[10, 14, 18, 22, 26])),
        y2=alt.datum(10),
        tooltip=[dia_tt, alt.Tooltip("temperatura:Q", title=t("Temperatura (°C)", "Temperature (°C)"),
                                     format=".1f")]
    ).properties(height=180)
    figura(grafico_temp, t("Temperatura da água ao longo do ciclo.", "Water temperature over the cycle."))


# ---------------------------------------------------------------------------
# 7. Colheita: distribuição de tamanhos no dia em que a média chega ao tamanho comercial
# ---------------------------------------------------------------------------
with aba_colheita:
    st.markdown(t("Nem todos os peixes chegam juntos ao tamanho comercial: no dia em que **a média** lá chega, "
                  "parte dos peixes ainda está abaixo.",
                  "Not all fish reach market size together: on the day **the mean** gets there, some fish are "
                  "still below it."))
    especies_colheita = [e for e in especies if dias_alvo[e] is not None]
    for inicio in range(0, len(especies_colheita), 2):
        for coluna, e in zip(st.columns(2, gap="medium"), especies_colheita[inicio:inicio + 2]):
            dia = dias_alvo[e]
            dia_guardado = min((d for d in pesos_individuais[e] if d >= dia), default=max(pesos_individuais[e]))
            pesos = pd.DataFrame({"peso": pesos_individuais[e][dia_guardado]})
            acima = (pesos["peso"] >= peso_comercial[e]).mean()
            cv = pesos["peso"].std() / pesos["peso"].mean()
            barras = alt.Chart(pesos).mark_bar(color=CORES[e], opacity=0.85, binSpacing=1).encode(
                x=alt.X("peso:Q", bin=alt.Bin(maxbins=28), title=t("Peso (g)", "Weight (g)")),
                y=alt.Y("count():Q", title=t("Peixes", "Fish")),
                tooltip=[alt.Tooltip("peso:Q", bin=alt.Bin(maxbins=28), title=t("Peso (g)", "Weight (g)")),
                         alt.Tooltip("count():Q", title=t("Peixes", "Fish"))])
            regra = alt.Chart(pd.DataFrame({"x": [peso_comercial[e]]})).mark_rule(
                strokeDash=[6, 4], color=COR_TEXTO, strokeWidth=1.5).encode(x="x:Q")
            figura((barras + regra).properties(height=240, title=alt.Title(NOMES[e])),
                   t(f"Peso de cada peixe no dia {dia} ({peso_comercial[e]} g tracejado): "
                     f"**{acima:.0%}** acima do tamanho comercial; coeficiente de variação de {cv:.0%}.",
                     f"Weight of each fish on day {dia} ({peso_comercial[e]} g dashed): "
                     f"**{acima:.0%}** above market size; coefficient of variation {cv:.0%}."), coluna)
    st.caption(t("A variação entre peixes vem do pressuposto de 15 % de variação no ritmo de crescimento "
                 "individual. Numa exploração, as triagens por tamanhos reduzem esta dispersão.",
                 "Variation between fish comes from the assumed 15 % variation in individual growth rate. "
                 "On a farm, size grading reduces this spread."))


# ---------------------------------------------------------------------------
# 8. Indicadores: SGR e FCR mês a mês, biomassa e ração
# ---------------------------------------------------------------------------
def indicadores_mensais(sim, nome):
    """SGR e FCR económico em períodos de 30 dias, a partir da simulação diária."""
    linhas = []
    for inicio in range(0, dia_maximo - 30, 30):
        a, b = sim.loc[inicio], sim.loc[inicio + 30]
        ganho = b["biomassa_kg"] - a["biomassa_kg"]
        racao = sim.loc[inicio + 1:inicio + 30, "racao_kg"].sum()
        linhas.append({"nome": nome, "mes": inicio // 30 + 1, "data": b["data"],
                       "sgr": 100 * (np.log(b["peso_medio_g"]) - np.log(a["peso_medio_g"])) / 30,
                       "fcr": racao / ganho if ganho > 0 else np.nan})
    return pd.DataFrame(linhas)


with aba_indicadores:
    mensal = pd.concat([indicadores_mensais(s, NOMES[e]) for e, s in simulacoes.items()])
    mes_x = alt.X("mes:Q", title=t("Mês do ciclo", "Month of the cycle"), axis=alt.Axis(tickMinStep=1))
    tooltip_mes = [especie_tt, alt.Tooltip("mes:Q", title=t("Mês", "Month")),
                   alt.Tooltip("data:T", title=t("Fim do período", "End of period"), format="%m/%Y")]
    grafico_sgr = alt.Chart(mensal).mark_line(point=alt.OverlayMarkDef(size=28), strokeWidth=2).encode(
        x=mes_x, y=alt.Y("sgr:Q", title="SGR (%/dia)" if idioma == "pt" else "SGR (%/day)"), color=cor,
        tooltip=tooltip_mes + [alt.Tooltip("sgr:Q", title="SGR", format=".2f")]
    ).properties(height=250, title=alt.Title(t("Taxa de crescimento específica", "Specific growth rate")))
    grafico_fcr = alt.Chart(mensal).mark_line(point=alt.OverlayMarkDef(size=28), strokeWidth=2, clip=True).encode(
        x=mes_x, y=alt.Y("fcr:Q", title=t("FCR económico", "Economic FCR"), scale=alt.Scale(domain=[0, 5])),
        color=cor, tooltip=tooltip_mes + [alt.Tooltip("fcr:Q", title="FCR", format=".2f")]
    ).properties(height=250, title=alt.Title(t("FCR económico mês a mês", "Monthly economic FCR")))
    c1, c2 = st.columns(2, gap="medium")
    figura(grafico_sgr, t("Percentagem do peso ganha por dia, em períodos de 30 dias. Desce à medida que o peixe "
                          "cresce e cai no inverno.",
                          "Percentage of body weight gained per day, over 30-day periods. It falls as the fish "
                          "grows and drops in winter."), c1)
    figura(grafico_fcr, t("kg de ração por kg de biomassa ganha em cada mês. Valores acima de 5 (meses frios, em que "
                          "os peixes quase não crescem mas continuam a morrer) ficam fora da escala.",
                          "kg of feed per kg of biomass gained each month. Values above 5 (cold months, when fish "
                          "barely grow but keep dying) are off the scale."), c2)

    # Biomassa e ração acumulada (uma linha por espécie e por dia)
    dados_bio = pd.concat([
        s.iloc[:dia_maximo:2].assign(nome=NOMES[e], racao_acumulada=s["racao_kg"].cumsum().iloc[:dia_maximo:2])
        for e, s in simulacoes.items()])
    grafico_biomassa = alt.Chart(dados_bio).mark_line(strokeWidth=2.3).encode(
        x=eixo_x, y=alt.Y("biomassa_kg:Q", title=t("Biomassa (kg)", "Biomass (kg)")), color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("biomassa_kg:Q", title=t("Biomassa (kg)", "Biomass (kg)"), format=",.0f"),
                 alt.Tooltip("n_peixes:Q", title=t("Peixes vivos", "Live fish"), format=",")]
    ).properties(height=250, title=alt.Title(t("Biomassa", "Biomass")))
    grafico_racao = alt.Chart(dados_bio).mark_line(strokeWidth=2.3, strokeDash=[6, 3]).encode(
        x=eixo_x, y=alt.Y("racao_acumulada:Q", title=t("Ração (kg)", "Feed (kg)")), color=cor,
        tooltip=[especie_tt, dia_tt,
                 alt.Tooltip("racao_acumulada:Q", title=t("Ração acumulada (kg)", "Cumulative feed (kg)"),
                             format=",.0f")]
    ).properties(height=250, title=alt.Title(t("Ração acumulada", "Cumulative feed")))
    c1, c2 = st.columns(2, gap="medium")
    figura(grafico_biomassa, t(f"Peso total dos peixes vivos ({milhares(n_juvenis)} juvenis à entrada).",
                               f"Total weight of live fish ({milhares(n_juvenis)} juveniles stocked)."), c1)
    figura(grafico_racao, t("Soma da ração dada desde a entrada.", "Sum of feed given since stocking."), c2)

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
        st.markdown(t("**No dia em que cada espécie chega ao tamanho comercial**",
                      "**On the day each species reaches market size**"))
        resumo = pd.DataFrame(linhas)
        st.dataframe(resumo, hide_index=True, column_config={
            c: st.column_config.NumberColumn(format="localized") for c in resumo.columns[1:]})
        if densidade is not None:
            st.caption(t(f"Volume de tanque necessário para ter essa biomassa a {densidade} kg/m³.",
                         f"Tank volume needed to hold that biomass at {densidade} kg/m³."))


# ---------------------------------------------------------------------------
# 9. Custos e receita
# ---------------------------------------------------------------------------
def custo_total(custo_juvenis, custo_racao):
    """Custo total estimado: a ração e os juvenis são cerca de 70 % do custo (HAPO, 2021)."""
    return (custo_juvenis + custo_racao) / PESO_RACAO_JUVENIS_NO_CUSTO


with aba_custos:
    st.markdown(t("Contas com os preços de **Preços e custos** (no painel do cenário).",
                  "Figures use the prices in **Prices and costs** (in the scenario panel)."))
    contas, partes, margens = {}, [], []
    for e, d in dias_alvo.items():
        if d is None:
            continue
        sim = simulacoes[e]
        biomassa = sim.loc[d, "biomassa_kg"]
        custo_juvenis = n_juvenis * preco_juvenil[e]
        custo_racao = sim.loc[:d, "racao_kg"].sum() * preco_racao
        total = custo_total(custo_juvenis, custo_racao)
        receita = biomassa * preco_venda[e]
        contas[NOMES[e]] = {
            t("Receita (€)", "Revenue (€)"): round(receita),
            t("Custo dos juvenis (€)", "Juvenile cost (€)"): round(custo_juvenis),
            t("Custo da ração (€)", "Feed cost (€)"): round(custo_racao),
            t("Custo total estimado (€)", "Estimated total cost (€)"): round(total),
            t("Margem estimada (€)", "Estimated margin (€)"): round(receita - total),
            t("Custo por kg produzido (€/kg)", "Cost per kg produced (€/kg)"): round(total / biomassa, 2),
        }
        for parte, valor in [(t("Juvenis", "Juveniles"), custo_juvenis), (t("Ração", "Feed"), custo_racao),
                             (t("Outros (estimado)", "Other (estimated)"), total - custo_juvenis - custo_racao)]:
            partes.append({"nome": NOMES[e], "parte": parte, "valor": valor, "receita": receita})
        # Margem se a colheita fosse feita em cada dia do ciclo (de 5 em 5 dias)
        racao_acumulada = sim["racao_kg"].cumsum() * preco_racao
        for dia in range(0, dia_maximo, 5):
            margens.append({"nome": NOMES[e], "dia": dia,
                            "margem": sim.loc[dia, "biomassa_kg"] * preco_venda[e]
                            - custo_total(custo_juvenis, racao_acumulada.loc[dia])})

    if contas:
        tabela_contas = pd.DataFrame(contas).rename_axis(t("Conta", "Item")).reset_index()
        st.dataframe(tabela_contas, hide_index=True, column_config={
            c: st.column_config.NumberColumn(format="localized") for c in tabela_contas.columns[1:]})

        partes = pd.DataFrame(partes)
        ordem_partes = [t("Juvenis", "Juveniles"), t("Ração", "Feed"), t("Outros (estimado)", "Other (estimated)")]
        barras = alt.Chart(partes).mark_bar(height=18).encode(
            y=alt.Y("nome:N", title=None, sort=ordem_nomes, axis=alt.Axis(labelFontSize=13, ticks=False, domain=False)),
            x=alt.X("sum(valor):Q", title="€", stack="zero"),
            color=alt.Color("parte:N", title=None, sort=ordem_partes,
                            scale=alt.Scale(domain=ordem_partes, range=[COR_TEXTO_SUAVE, COR_TINTA, "#C9BBA3"]),
                            legend=alt.Legend(orient="top", direction="horizontal")),
            order=alt.Order("ordem:Q"),
            tooltip=[especie_tt, alt.Tooltip("parte:N", title=t("Parte", "Item")),
                     alt.Tooltip("valor:Q", title="€", format=",.0f")]
        ).transform_calculate(ordem=f"indexof({ordem_partes}, datum.parte)")
        receita = alt.Chart(partes.drop_duplicates("nome")).mark_tick(
            thickness=3, size=30, color=COR_TEXTO).encode(
            y=alt.Y("nome:N", sort=ordem_nomes), x="receita:Q",
            tooltip=[especie_tt, alt.Tooltip("receita:Q", title=t("Receita (€)", "Revenue (€)"), format=",.0f")])
        margens = pd.DataFrame(margens)
        melhor = margens.loc[margens.groupby("nome")["margem"].idxmax()]
        grafico_margem = alt.Chart(margens).mark_line(strokeWidth=2.3).encode(
            x=eixo_x, y=alt.Y("margem:Q", title=t("Margem estimada (€)", "Estimated margin (€)")), color=cor,
            tooltip=[especie_tt, dia_tt, alt.Tooltip("margem:Q", title="€", format=",.0f")])
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=COR_TEXTO_SUAVE).encode(y="y:Q")
        pontos_melhor = alt.Chart(melhor).mark_point(filled=True, size=100, stroke=COR_FICHA, strokeWidth=2,
                                                     opacity=1).encode(
            x=alt.X("dia:Q", scale=escala_x), y="margem:Q", color=cor,
            tooltip=[especie_tt, alt.Tooltip("dia:Q", title=t("Melhor dia de colheita", "Best harvest day")),
                     alt.Tooltip("margem:Q", title="€", format=",.0f")])
        c1, c2 = st.columns(2, gap="medium")
        figura((barras + receita).properties(height=alt.Step(40), title=alt.Title(t("Custos", "Costs"))),
               t("Custos até ao tamanho comercial (barras) e receita da venda (traço preto).",
                 "Costs up to market size (bars) and sale revenue (black tick)."), c1)
        figura((zero + grafico_margem + pontos_melhor).properties(
                   height=260, title=alt.Title(t("Margem ao longo do ciclo", "Margin over the cycle"))),
               t("Margem estimada se a colheita fosse feita nesse dia. O ponto marca o dia de maior margem.",
                 "Estimated margin if the harvest were on that day. The dot marks the day of highest margin."), c2)
        st.caption(t("O custo total é estimado a partir da ração e dos juvenis, que são cerca de 70 % do custo "
                     "de produção da dourada e do robalo nas explorações gregas (HAPO, 2021); o resto (mão de "
                     "obra, amortizações, outros) varia de exploração para exploração. Nas outras espécies "
                     "usamos o mesmo valor (pressuposto). É uma estimativa, não uma contabilidade.",
                     "Total cost is estimated from feed and juveniles, which are about 70 % of sea bream and "
                     "sea bass production cost on Greek farms (HAPO, 2021); the rest (labour, depreciation, "
                     "other) varies from farm to farm. The same share is assumed for the other species. It is "
                     "an estimate, not an account."))


# ---------------------------------------------------------------------------
# 10. Mês de entrada: dias até ao tamanho comercial em muitos cenários
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def mapa_entrada(especie, peso_inicial, peso_alvo, parametros, fator):
    """Dias até ao tamanho comercial para cada mês de entrada (1–12) e temperatura média do mar (15–21 °C)."""
    cenarios, temperaturas = [], []
    for media_mar in range(15, 22):
        for mes in range(1, 13):
            _, curva = perfil_temperatura(N_DIAS, data_inicio=f"2024-{mes:02d}-01", media=float(media_mar))
            cenarios.append({"media": media_mar, "mes": mes})
            temperaturas.append(curva)
    dias = dias_ate_peso_medio(especie, np.array(temperaturas), peso_inicial, peso_alvo, parametros, fator)
    return pd.DataFrame(cenarios).assign(dias=dias)


with aba_entrada:
    especie_mapa = st.segmented_control(
        t("Espécie", "Species"), especies, default=especies[0], required=True,
        format_func=lambda e: NOMES[e], key="especie_mapa")
    if especie_mapa not in especies:
        especie_mapa = especies[0]
    if sistema == "tanque":
        st.markdown(t("Num tanque a temperatura é constante, por isso o mês de entrada não muda a duração do "
                      "ciclo. O mapa mostra o caso da **jaula no mar**, com a curva sazonal de temperatura.",
                      "In a tank the temperature is constant, so the stocking month does not change the cycle "
                      "length. The map shows the **sea cage** case, with the seasonal temperature curve."))
    fator = CENARIOS_ALIMENTACAO.get(especie_mapa, {}).get(alimentacao, {"fator_crescimento": 1.0})["fator_crescimento"]
    mapa = mapa_entrada(especie_mapa, peso_inicial[especie_mapa], peso_comercial[especie_mapa],
                        parametros[especie_mapa], fator)
    mapa["meses"] = mapa["dias"] / 30.4
    mapa["mes_nome"] = [MESES[m - 1] for m in mapa["mes"]]
    celulas = alt.Chart(mapa).mark_rect(stroke=COR_FICHA, strokeWidth=1.5).encode(
        x=alt.X("mes_nome:O", sort=MESES, title=t("Mês de entrada dos juvenis", "Stocking month"),
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("media:O", sort="descending", title=t("Temperatura média do mar (°C)", "Mean sea temperature (°C)")),
        color=alt.Color("meses:Q", title=t("Meses", "Months"),
                        scale=alt.Scale(range=["#F1E7D2", "#7FA8A8", COR_TINTA, "#14343A"]),
                        legend=alt.Legend(orient="right", gradientLength=180)),
        tooltip=[alt.Tooltip("mes_nome:O", title=t("Entrada", "Stocking")),
                 alt.Tooltip("media:O", title=t("Temperatura média (°C)", "Mean temperature (°C)")),
                 alt.Tooltip("dias:Q", title=t("Dias", "Days"), format=".0f"),
                 alt.Tooltip("meses:Q", title=t("Meses", "Months"), format=".1f")])
    escuro = mapa["meses"] > mapa["meses"].quantile(0.55)
    texto = alt.Chart(mapa.assign(escuro=escuro)).mark_text(fontSize=11).encode(
        x=alt.X("mes_nome:O", sort=MESES), y=alt.Y("media:O", sort="descending"),
        text=alt.Text("meses:Q", format=".0f"),
        color=alt.condition("datum.escuro", alt.value("white"), alt.value(COR_TEXTO)))
    figura((celulas + texto).properties(height=alt.Step(34), title=alt.Title(
               t(f"{NOMES[especie_mapa]}: meses até {peso_comercial[especie_mapa]} g",
                 f"{NOMES[especie_mapa]}: months to {peso_comercial[especie_mapa]} g"))),
           t("Meses até ao tamanho comercial consoante o mês de entrada e a temperatura média do mar. Cálculo para um "
             "peixe médio, sem variação individual nem mortalidade, por isso pode diferir uns dias dos cartões.",
             "Months to market size depending on the stocking month and mean sea temperature. Computed for an "
             "average fish, without individual variation or mortality, so it may differ by a few days from the cards."))


# ---------------------------------------------------------------------------
# 11. Tabela com os dados simulados (para descarregar)
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
        tabela = tabela.replace({"especie": {"dourada": "sea_bream", "robalo": "sea_bass",
                                             "pregado": "turbot", "linguado": "sole"}}).rename(columns={
            "especie": "species", "dia": "day", "data": "date", "temperatura_c": "temperature_c",
            "n_peixes": "n_fish", "peso_medio_g": "mean_weight_g", "peso_dp_g": "weight_sd_g",
            "biomassa_kg": "biomass_kg", "racao_kg": "feed_kg", "mortos": "deaths"})
    st.dataframe(tabela, hide_index=True, height=320)
    st.download_button(t("Descarregar CSV", "Download CSV"), tabela.to_csv(index=False).encode("utf-8"),
                       file_name=t("simulacao_crescimento.csv", "growth_simulation.csv"), mime="text/csv",
                       icon=":material/download:")


# ---------------------------------------------------------------------------
# 12. Notas sobre o modelo (fechadas por defeito, no fim da página)
# ---------------------------------------------------------------------------
SOBRE_PT = r"""
**Modelo de crescimento.** O peixe cresce em função da temperatura acumulada acima de uma temperatura base
(coeficiente de crescimento térmico, TGC). Em cada dia, com $T$ a temperatura da água e $W$ o peso (g):

$$W^{1/3} \leftarrow W^{1/3} + TGC_{1/3}\,(T-T_{base}) \quad \text{até ao peso crítico}$$

$$W^{2/3} \leftarrow W^{2/3} + TGC_{2/3}\,(T-T_{base}) \quad \text{a partir do peso crítico (só a dourada)}$$

Na dourada o peso crítico, $(TGC_{2/3}/TGC_{1/3})^3/8$, é cerca de 117 g. Simulamos 1 000 juvenis, com variação
individual no crescimento e mortalidade diária; para outro número de juvenis, os totais crescem na mesma proporção.

| | Crescimento | Sobrevivência | FCR |
|---|---|---|---|
| Dourada | TGC misto 0,001646 e 0,016095, base 12 °C (Mayer et al., 2012; 20 lotes em jaulas comerciais) | 80 % (Muniesa et al., 2020) | 2,1 (Kallitsis & Avramidis, 2025) |
| Robalo | TGC 0,00129, base 12 °C, **calibrado** para demorar mais 13 % do que a dourada (Cardia & Lovatelli, 2007) | 85 % (Muniesa et al., 2020) | 2,2 (Kallitsis & Avramidis, 2025) |
| Pregado | TGC 0,00105, base 0 °C, **calibrado** com a pré-engorda da FAO (5–10 g a 80–100 g em 4–6 meses, a 16 °C) | 85 % (**pressuposto**) | 1,15 (FAO: 1,1–1,2) |
| Linguado | TGC 0,000516, base 0 °C, **calibrado** com a FAO (5 g a 350 g em 16–18 meses, a 19–21 °C) | 99 % (Quental-Ferreira et al., 2010, em esteiros) | 2,2 (Valente et al., 2011) |

**Outros efeitos (só onde há dados):** ração restrita na dourada (Bonaldo et al., 2010) e no robalo (Türkmen et al.,
2012); densidade em RAS (Sammouth et al., 2009) e IMTA (Cotou et al., 2024) no robalo.

**Validação:** a dourada vai de 5 g a 400 g em cerca de 17 meses em jaula (FAO, 2009: ≈ 16 meses). O pregado, a 16 °C,
vai de 10 g a 1 kg em cerca de 15 meses, mais depressa do que os 600–750 dias até 1–1,5 kg indicados para uma
exploração em Portugal: o TGC foi calibrado com juvenis e o crescimento abranda nos peixes grandes. No linguado,
Valente et al. (2011) mediram 180 g a 323–354 g em 240 dias a 19 °C, mais devagar do que o modelo prevê.

**Pressupostos sem referência:** a variação individual do crescimento (15 %), a curva de temperatura do mar
(± 4 °C), a temperatura base do robalo (12 °C), a sobrevivência do pregado, o preço do juvenil de pregado e a
parte da ração e dos juvenis no custo (70 %) fora da dourada e do robalo.

**Preços:** venda em 2023 (EUMOFA: dourada e robalo na Grécia, pregado em Portugal); linguado no mercado de Madrid
em 2013 (Morais et al., 2016); juvenis e ração na Grécia em 2020 (HAPO, 2021); juvenil de linguado a partir de
Bjørndal & Guillen (2014).

**Limitações:** os parâmetros do pregado e do linguado são os menos seguros (notebook 06) e o modelo é otimista nos peixes grandes; abaixo de
6 g o modelo da dourada é uma extrapolação; o modelo não tem temperatura ótima, por isso cada espécie tem um
limite (25 °C; pregado 23 °C); a mortalidade e o FCR são constantes ao longo do ciclo.
"""

SOBRE_EN = r"""
**Growth model.** Fish grow with the temperature accumulated above a base temperature (thermal growth
coefficient, TGC). Each day, with $T$ the water temperature and $W$ the weight (g):

$$W^{1/3} \leftarrow W^{1/3} + TGC_{1/3}\,(T-T_{base}) \quad \text{up to the critical weight}$$

$$W^{2/3} \leftarrow W^{2/3} + TGC_{2/3}\,(T-T_{base}) \quad \text{from the critical weight on (sea bream only)}$$

In sea bream the critical weight, $(TGC_{2/3}/TGC_{1/3})^3/8$, is about 117 g. 1,000 juveniles are simulated, with
individual variation in growth and daily mortality; for a different number of juveniles, totals scale in proportion.

| | Growth | Survival | FCR |
|---|---|---|---|
| Sea bream | Mixed TGC 0.001646 and 0.016095, base 12 °C (Mayer et al., 2012; 20 commercial cage lots) | 80 % (Muniesa et al., 2020) | 2.1 (Kallitsis & Avramidis, 2025) |
| Sea bass | TGC 0.00129, base 12 °C, **calibrated** to take 13 % longer than sea bream (Cardia & Lovatelli, 2007) | 85 % (Muniesa et al., 2020) | 2.2 (Kallitsis & Avramidis, 2025) |
| Turbot | TGC 0.00105, base 0 °C, **calibrated** on FAO pre-growing (5–10 g to 80–100 g in 4–6 months, at 16 °C) | 85 % (**assumption**) | 1.15 (FAO: 1.1–1.2) |
| Sole | TGC 0.000516, base 0 °C, **calibrated** on FAO (5 g to 350 g in 16–18 months, at 19–21 °C) | 99 % (Quental-Ferreira et al., 2010, in ponds) | 2.2 (Valente et al., 2011) |

**Other effects (only where data exist):** restricted feeding in sea bream (Bonaldo et al., 2010) and sea bass
(Türkmen et al., 2012); RAS density (Sammouth et al., 2009) and IMTA (Cotou et al., 2024) in sea bass.

**Validation:** sea bream grows from 5 g to 400 g in about 17 months in sea cages (FAO, 2009: ≈ 16 months). Turbot, at
16 °C, grows from 10 g to 1 kg in about 15 months, faster than the 600–750 days to 1–1.5 kg reported for a farm in
Portugal: the TGC was calibrated on juveniles and growth slows in large fish. In sole, Valente et al. (2011)
measured 180 g to 323–354 g in 240 days at 19 °C, slower than the model predicts.

**Assumptions without a reference:** individual growth variation (15 %), the sea temperature curve (± 4 °C), the
sea bass base temperature (12 °C), turbot survival, the turbot juvenile price and the feed-and-juvenile share of
cost (70 %) outside sea bream and sea bass.

**Prices:** 2023 sale prices (EUMOFA: sea bream and sea bass in Greece, turbot in Portugal); sole at the Madrid
market in 2013 (Morais et al., 2016); juveniles and feed in Greece in 2020 (HAPO, 2021); sole juvenile from
Bjørndal & Guillen (2014).

**Limitations:** turbot and sole parameters are the least certain (notebook 06) and the model is optimistic for large fish; below 6 g the sea
bream model is an extrapolation; the model has no optimum temperature, so each species has a limit (25 °C; turbot
23 °C); mortality and FCR are constant over the cycle.
"""

st.divider()
with st.expander(t("Notas sobre o modelo: equações, parâmetros, pressupostos e referências",
                   "Notes on the model: equations, parameters, assumptions and references")):
    st.markdown(t(SOBRE_PT, SOBRE_EN))
    st.markdown(t("As referências completas, com DOI, e os seis notebooks de análise estão no repositório.",
                  "Full references with DOIs, and the six analysis notebooks, are in the repository."))
    st.link_button(t("Código, notebooks e referências", "Code, notebooks and references"), URL_GITHUB,
                   icon=":material/code:")
st.caption(f"Dinis Costa · [LinkedIn]({URL_LINKEDIN}) · [GitHub]({URL_GITHUB})")
