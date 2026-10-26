# Quanto tempo demora um peixe a chegar ao tamanho comercial?

*Modelo de crescimento em aquacultura: dourada, robalo, pregado e linguado.*

Modelação do crescimento da **dourada** (*Sparus aurata*) e do **robalo** (*Dicentrarchus labrax*) em aquacultura, e simulação do efeito da **temperatura**, da **alimentação** e do **regime de cultivo** no tempo até ao tamanho comercial, na eficiência alimentar e nos custos.

**App interativa:** [dinistcosta.github.io/aquaculture-growth-model](https://dinistcosta.github.io/aquaculture-growth-model/). Abre com um exemplo calculado a partir da literatura e pode ser usada com os dados de uma exploração:
- espécie, sistema de cultivo (jaula, tanque / RAS, IMTA), alimentação e tamanho comercial;
- número e peso dos juvenis, data de entrada, temperaturas e pesagens em CSV (as pesagens são comparadas com o modelo);
- quatro espécies: **dourada**, **robalo**, **pregado** (*Scophthalmus maximus*) e **linguado** (*Solea senegalensis*);
- parâmetros de cada espécie (tamanho comercial, peso de entrada, TGC, FCR, sobrevivência) e preços (venda, juvenis, ração), com custos, receita e margem estimados;
- figuras numeradas: crescimento, calendário de produção, distribuição de tamanhos na colheita, SGR e FCR mês a mês, divisão dos custos, margem ao longo do ciclo e mapa do mês de entrada;
- português e inglês (botão PT / EN; o link com `?lang=en` abre em inglês).

> **Os dados deste projeto são SIMULADOS.** Foram gerados a partir de parâmetros publicados na literatura científica (referências abaixo), com variação aleatória para se parecerem com dados reais. Não são registos de nenhuma exploração. O código está preparado para ser usado com dados reais (ver [Usar dados reais](#usar-dados-reais)).

## Objetivo

Responder a perguntas práticas de uma exploração de aquacultura:
- Quanto tempo demora cada espécie a chegar ao tamanho comercial (400 g)?
- Como variam a taxa de crescimento e o índice de conversão alimentar ao longo do ciclo?
- O que muda com a temperatura da água, com a quantidade de ração e com o regime de cultivo (jaula, tanque/RAS, IMTA, extensivo)?

## Contexto biológico

A dourada e o robalo são as duas principais espécies de peixe marinho produzidas no Mediterrâneo. São engordadas sobretudo em **jaulas no mar**, a partir de juvenis de 2–5 g, até cerca de 350–400 g, num ciclo de 14 a 18 meses (Cardia & Lovatelli, 2007). Como são animais ectotérmicos, o seu crescimento depende muito da **temperatura da água**: abaixo de cerca de 12 °C a dourada deixa de comer e de crescer (Mayer et al., 2008). A **ração** é o maior custo de produção, por isso a eficiência alimentar (FCR) é um indicador económico essencial.

## Dados

### Modelo de crescimento

O crescimento é calculado com o **coeficiente de crescimento térmico (TGC)**: o peixe cresce em função da temperatura acumulada acima de 12 °C (temperatura efetiva). Em cada dia, com $W$ o peso (g) e $T$ a temperatura (°C):

$$W^{1/3} \leftarrow W^{1/3} + TGC_{1/3} \cdot (T - 12) \quad \text{até ao peso crítico}$$

$$W^{2/3} \leftarrow W^{2/3} + TGC_{2/3} \cdot (T - 12) \quad \text{a partir do peso crítico}$$

O peso crítico, $(TGC_{2/3}/TGC_{1/3})^3/8$, é cerca de 117 g na dourada. Este modelo de duas fases foi ajustado por Mayer et al. (2012) a 20 lotes de dourada em jaulas comerciais e validado com mais 6 lotes.

Simulamos uma jaula de 5 000 peixes durante 640 dias, com:
- **variação individual** no ritmo de crescimento;
- **mortalidade** diária;
- **ração** calculada a partir do ganho de biomassa e do FCR;
- **biometrias** de 14 em 14 dias, numa amostra de 50 peixes (com erro de amostragem), no mesmo formato que teriam dados reais.

**Correção (outubro de 2026):** até esta data o projeto usava $dW/dt = 0{,}024 \cdot W^{0,514} \cdot e^{0,060 \cdot T}$, atribuída por engano a Hernández et al. (2003). Essa equação é de Lupatsch, Kissil & Sklan (2003). Aplicada a jaulas comerciais, errava o peso final em 16,6 %, contra cerca de 11 % dos modelos com temperatura efetiva (Mayer et al., 2008). O robalo usava a equação de Lanari et al. (2002) com um fator de calibração de 1,14. Os dois foram substituídos pelo modelo TGC e todos os notebooks foram refeitos.

### Parâmetros e fontes

| Parâmetro | Dourada | Robalo | Fonte |
|---|---|---|---|
| TGC | 0,001646 (fase $W^{1/3}$) · 0,016095 (fase $W^{2/3}$) | 0,00129 (só fase $W^{1/3}$) | Mayer et al. (2012); robalo: **calibração** |
| Temperatura base | 12 °C | 12 °C | Mayer et al. (2008); robalo: **pressuposto** |
| Sobrevivência no ciclo | 80 % | 85 % | Muniesa et al. (2020) |
| Duração de referência do ciclo | 14–16 meses | 16–18 meses | Cardia & Lovatelli (2007) |
| Peso dos juvenis à entrada | 3 g | 3 g | Cardia & Lovatelli (2007) |
| FCR | 2,1 | 2,2 | Kallitsis & Avramidis (2025) |
| Efeito da ração restrita | 80 % da saciedade | 75 % da saciedade | Bonaldo et al. (2010); Türkmen et al. (2012) |
| Regimes de cultivo | tabela da FAO | densidade em RAS; IMTA | FAO (2009); Sammouth et al. (2009); Cotou et al. (2024) |
| Preço de venda (app) | 4,89 €/kg | 6,45 €/kg | EUMOFA (Grécia, 2023) |
| Juvenil e ração (app) | 0,20 €/unidade; ≈ 1,04 €/kg | igual | HAPO (2021), dados de 2020 |

### Pregado e linguado (só na app)

Para estas espécies não foi encontrado um modelo ajustado a dados de explorações comerciais. A app usa o TGC clássico (só a fase $W^{1/3}$, temperatura base 0 °C; Cho, 1992), com valores **calibrados** a partir das fichas da FAO. São os parâmetros menos seguros do projeto e não entram nos notebooks.

| Parâmetro | Pregado | Linguado | Fonte |
|---|---|---|---|
| TGC | 0,00105 | 0,000516 | **Calibração**: FAO (pregado: 5–10 g a 80–100 g em 4–6 meses, a 16 °C; linguado: 5 g a 350 g em 16–18 meses, a 19–21 °C) |
| Tamanho comercial | 1 kg (vende-se entre 0,7 e 2 kg) | 350 g | FAO |
| Temperatura máxima do modelo | 23 °C | 25 °C | FAO; Morais et al. (2016) |
| Sobrevivência no ciclo | 85 % | 99 % | **pressuposto**; Quental-Ferreira et al. (2010), citado em Morais et al. (2016) |
| FCR | 1,15 | 2,2 | FAO (1,1–1,2); Valente et al. (2011), citado em Morais et al. (2016) |
| Preço de venda | 11,29 €/kg | 12,25 €/kg | EUMOFA (Portugal, 2023); mercado de Madrid em 2013 (Morais et al., 2016) |
| Juvenil | 1,32 € | 1,32 € | **sem fonte** (pressuposto igual ao linguado); 3,77 € por kg produzido × 0,35 kg (Bjørndal & Guillen, 2014, citado em Morais et al., 2016) |

**Comparação com dados de cultivo:** a 16 °C o pregado vai de 10 g a 1 kg em cerca de 15 meses no modelo, mais depressa do que os 600–750 dias até 1–1,5 kg indicados para uma exploração em Portugal (o TGC foi calibrado com juvenis). No linguado, Valente et al. (2011) mediram 180 g a 323–354 g em 240 dias a 19 °C, mais devagar do que o modelo prevê.

**Calibração do robalo:** não foi encontrado um TGC do robalo medido em jaulas comerciais. O valor usado faz o robalo demorar mais 13 % do que a dourada a chegar aos 400 g, que é a diferença entre os ciclos de referência das duas espécies (14–16 vs. 16–18 meses; Cardia & Lovatelli, 2007). **Não é um valor publicado** e deve ser substituído pelo TGC de uma exploração quando houver dados (na app, em *Parâmetros do modelo*).

**Pressupostos sem referência**, assinalados como tal no código:
- a variação individual do crescimento (coeficiente de variação de 15 %);
- a curva de temperatura do mar (15–23 °C);
- a temperatura base de 12 °C no robalo (igual à da dourada);
- a temperatura dos tanques/RAS (22 °C, o meio do intervalo 18–26 °C da FAO).

## Métodos

| Notebook | Conteúdo |
|---|---|
| [01_simulacao_dados](notebooks/01_simulacao_dados.ipynb) | Simulação de um ciclo de engorda e validação com a literatura |
| [02_indicadores](notebooks/02_indicadores.ipynb) | SGR, GPD, FCR e sobrevivência; efeito do erro de amostragem |
| [03_modelo_von_bertalanffy](notebooks/03_modelo_von_bertalanffy.ipynb) | Ajuste da curva de von Bertalanffy com `scipy.optimize.curve_fit`, intervalos de confiança, R², resíduos e análise de sensibilidade |
| [04_cenarios](notebooks/04_cenarios.ipynb) | Cenários de temperatura (16, 20, 24 °C) e de alimentação |
| [05_regimes_de_cultivo](notebooks/05_regimes_de_cultivo.ipynb) | Extensivo, semi-intensivo, jaulas, tanques/RAS e IMTA |

As funções estão em [`src/`](src/):

| Ficheiro | Conteúdo |
|---|---|
| `growth.py` | Modelo de crescimento (TGC) e simulação |
| `indicators.py` | Indicadores de produção |
| `von_bertalanffy.py` | Curva de von Bertalanffy e ajuste |
| `regimes.py` | Valores da literatura para os regimes de cultivo |
| `dados.py` | Leitura de CSV |

### Indicadores

| Indicador | Fórmula |
|---|---|
| Taxa de crescimento específica (%/dia) | $SGR = 100 \times (\ln W_f - \ln W_i) / t$ |
| Ganho de peso diário (g/dia) | $GPD = (W_f - W_i) / t$ |
| Índice de conversão alimentar | $FCR = \text{ração (kg)} / \text{ganho de biomassa (kg)}$ |
| Sobrevivência (%) | $100 \times N_f / N_i$ |
| Coeficiente de crescimento térmico | $TGC = (W_f^{1/3} - W_i^{1/3}) / \sum (T - 12)$ |

## Principais resultados

### 1. Crescimento simulado

![Crescimento simulado](figures/01_crescimento_simulado.png)

Com juvenis de 3 g a entrar em abril, a dourada chega aos 400 g em cerca de **17,4 meses** e o robalo em cerca de **19,4 meses**. O crescimento **quase para no inverno**, quando a água se aproxima dos 15 °C. Com juvenis de 5 g, a dourada demora 16,9 meses, perto dos ≈ 16 meses indicados pela FAO (2009).

### 2. Indicadores de produção

![SGR em função do peso e da temperatura](figures/02_sgr_peso_temperatura.png)

- A **SGR desce à medida que o peixe cresce**, de ≈ 2 %/dia nos juvenis para menos de 0,5 %/dia nos peixes comerciais, e cai para quase zero no inverno.
- O **FCR económico (≈ 2,3)** é mais alto do que o biológico, porque inclui a ração comida pelos peixes que morreram. No inverno dispara, porque os peixes quase não crescem mas continuam a morrer.
- Indicadores calculados entre **biometrias muito próximas** (14 dias) não são fiáveis por causa do erro de amostragem; períodos de 8 semanas dão valores estáveis.

### 3. Curva de von Bertalanffy

![Sensibilidade ao W∞](figures/03_sensibilidade_winf.png)

A curva ajusta-se bem (R² ≥ 0,97), mas **o peso assintótico W∞ não é identificável**: os dados de engorda só cobrem o início do crescimento, e o ajuste livre empurra W∞ até ao limite imposto. Com W∞ fixo em 2, 5 ou 13 kg, as curvas são quase iguais na zona com dados, o coeficiente k muda cerca de 2,5 vezes e as previsões fora dos dados divergem. Por isso, **k só pode ser comparado entre estudos que usem o mesmo W∞**. Os resíduos mostram um padrão sazonal que a curva, sem temperatura, não capta.

### 4. Cenários de temperatura e alimentação

![Dias até 400 g por cenário](figures/04_dias_ate_400g.png)

| Ração até à saciedade | Dourada | Robalo |
|---|---|---|
| Dias até 400 g a 16 / 20 / 24 °C | 992 / 496 / 331 | 1 132 / 565 / 377 |

- **Cada grau vale mais com a água fria:** de 16 para 20 °C o ciclo encurta para metade, de 20 para 24 °C encurta um terço, porque só conta a temperatura acima de 12 °C. Um ano inteiro a 16 °C está fora das condições em que o modelo foi ajustado (extrapolação).
- A **dourada chega aos 400 g 12–14 % mais cedo** do que o robalo.
- A **ração restrita** tem efeitos diferentes nas duas espécies:
  - na dourada, atrasa o ciclo cerca de 9 %, mas baixa o FCR económico de 2,3 para 1,9;
  - no robalo, só atrasa o ciclo (cerca de 14 %).

### 5. Regimes de cultivo

![Meses até ao tamanho comercial por regime](figures/05_regimes.png)

- **Validação com a FAO (2009):** para a dourada de 5 g até 350–400 g, a simulação dá 16,0–16,9 meses em jaula (FAO: ≈ 16) e 11,6–12,5 meses em tanque a 22 °C (FAO: ≈ 12).
- **Tanque/RAS:** com temperatura controlada, o ciclo é cerca de **4 a 4,5 meses mais curto** do que em jaula no mar.
- **Densidade em RAS:** o robalo mantém o crescimento até **70 kg/m³** e cresce 14 % mais devagar a 100 kg/m³ (Sammouth et al., 2009).
- **IMTA:** reduz a ração do robalo em cerca de **11 %**, sem alterar o crescimento (Cotou et al., 2024).
- **Extensivo e semi-intensivo:** não foram simulados, porque os peixes se alimentam de alimento natural e o modelo assume ração.

### Limitações

- Os dados são simulados.
- Os lotes de Mayer et al. (2012) começaram com 6–44 g: abaixo de 6 g o modelo é uma extrapolação.
- O TGC do robalo é uma calibração e a sua temperatura base de 12 °C é um pressuposto.
- O modelo não tem temperatura ótima, por isso só é usado até 25 °C (o ótimo do robalo é cerca de 26 °C; Person-Le Ruyet et al., 2004).
- A mortalidade e o FCR são constantes ao longo do ciclo.
- Os efeitos da alimentação, da densidade e do IMTA vêm de ensaios curtos e foram extrapolados para um ciclo inteiro.
- Os custos da app são estimativas: a ração e os juvenis são cerca de 70 % do custo de produção da dourada e do robalo (HAPO, 2021); nas outras espécies usa-se o mesmo valor (pressuposto).
- Os parâmetros do pregado e do linguado são calibrações e pressupostos (ver acima).

## Como correr o projeto

Testado com Python 3.14.

```bash
git clone https://github.com/dinistcosta/aquaculture-growth-model.git
cd aquaculture-growth-model
python3 -m venv venv
source venv/bin/activate          # no Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Depois abrir os notebooks da pasta `notebooks/` por ordem, no VS Code ou no Jupyter (`pip install notebook` e `jupyter notebook`). O notebook 01 gera o ficheiro `data/raw/registos_simulados.csv`, usado pelos seguintes.

### App interativa

```bash
streamlit run app.py
```

A mesma app está publicada no [site do projeto](https://dinistcosta.github.io/aquaculture-growth-model/). O ficheiro `index.html` usa o [stlite](https://github.com/whitphx/stlite) para correr a `app.py` em Python **dentro do browser** (Pyodide), sem servidor. Por isso pode ser alojada no GitHub Pages; a primeira abertura demora 30 a 60 segundos.

### Usar dados reais

**Na app:** em *Dados da exploração*, introduzir o número e o peso dos juvenis e a data de entrada, e carregar dois CSV (um de temperaturas e um de pesagens), com as colunas `data, temperatura_c` e `data, peso_medio_g` (também são aceites os nomes em inglês `date, temperature_c, mean_weight_g`). Em *Parâmetros do modelo* pode ser introduzido o TGC da exploração, calculado com duas pesagens pela fórmula da tabela de indicadores.

**Nos notebooks:** basta um CSV com uma linha por biometria e as colunas:

```
dia, peso_medio_g, temperatura_c, racao_kg, n_peixes
```

`racao_kg` é a ração dada desde a biometria anterior; `especie` e `data` são opcionais. Nos notebooks 02 e 03, substituir o caminho em `ler_registos("../data/raw/registos_simulados.csv")` pelo do novo ficheiro.

## Estrutura

```
aquaculture-growth-model/
├── data/
│   ├── raw/            registos de biometria (simulados)
│   └── processed/
├── notebooks/          análises 01 a 05
├── src/                funções reutilizáveis
├── figures/            gráficos exportados
├── app.py              app interativa (Streamlit)
├── index.html          site do projeto (corre a app.py no browser)
├── PRODUCT.md          contexto do produto (público, objetivos, regras de estilo)
├── requirements.txt
└── README.md
```

## Ferramentas

Python · NumPy · pandas · Matplotlib · seaborn · SciPy · Jupyter · Streamlit · stlite (GitHub Pages)

## Referências

- Bonaldo, A., Isani, G., Fontanillas, R., Parma, L., Grilli, E. & Gatta, P.P. (2010). Growth and feed utilization of gilthead sea bream (*Sparus aurata*, L.) fed to satiation and restrictively at increasing dietary energy levels. *Aquaculture International* 18: 909–919. https://doi.org/10.1007/s10499-009-9312-0
- Cardia, F. & Lovatelli, A. (2007). A review of cage aquaculture: Mediterranean Sea. *FAO Fisheries Technical Paper* 498: 156–187.
- Cho, C.Y. (1992). Feeding systems for rainbow trout and other salmonids with reference to current estimates of energy and protein requirements. *Aquaculture* 100: 107–123.
- Cotou, E., Miliou, H., Chatzoglou, E., Schoina, E., Politakis, N., Kogiannou, D., Fountoulaki, E., Androni, A., Konstantinopoulou, A., Assimakopoulou, G. & Nathanailides, C. (2024). Growth performance and environmental quality indices and biomarkers in a co-culture of the European sea bass with filter and deposit feeders: a case study of an IMTA system. *Fishes* 9: 69. https://doi.org/10.3390/fishes9020069
- El-Desoki, M.O., Younis, Y.M., Youssef, E.D.A., Ahmed, S.M., Ahmed, K.S. & Al-Beak, A.M. (2021). Age, growth and mortality of the European seabass (*Dicentrarchus labrax*) in Bardawil lagoon, North Sinai, Egypt. *International Journal of Aquaculture and Fishery Sciences* 7(4): 42–46. https://doi.org/10.17352/2455-8400.000072
- EUMOFA (European Market Observatory for Fisheries and Aquaculture Products). Perfis de espécie: *Gilthead seabream* e *European seabass* (preços à saída da exploração na Grécia, 2023). https://fishery-aquaculture-market-observatory.ec.europa.eu
- FAO. Cultured Aquatic Species Information Programme: *Psetta maxima* (pregado) e *Solea* spp. (linguado; resumo em The Fish Site, "How to farm sole").
- FAO (2009). *Sparus aurata*. In: Cultured aquatic species fact sheets. Texto de Colloca, F. & Cerasi, S.; editado por Crespi, V. & New, M.
- HAPO (Hellenic Aquaculture Producers Organization) (2021). *Aquaculture in Greece 2021*. Relatório anual.
- Kallitsis, E. & Avramidis, P. (2025). Life cycle assessment of aquaculture production in Greece. *Cleaner Environmental Systems* 16: 100261. https://doi.org/10.1016/j.cesys.2025.100261
- Kraljević, M., Dulčić, J. & Tudor, M. (1998). Growth parameters of the gilt-head sea bream *Sparus aurata* L. in the eastern Adriatic (Croatian waters). *Periodicum Biologorum* 100: 87–91.
- Lupatsch, I., Kissil, G.W. & Sklan, D. (2003). Defining energy and protein requirements of gilthead seabream (*Sparus aurata*) to optimize feeds and feeding regimes. *The Israeli Journal of Aquaculture – Bamidgeh* 55: 243–257. (Modelo usado até outubro de 2026.)
- Morais, S., Aragão, C., Cabrita, E., Conceição, L.E.C., Constenla, M., Costas, B., Dias, J., Duncan, N., Engrola, S., Estevez, A., Gisbert, E., Mañanós, E. et al. (2016). New developments and biological insights into the farming of *Solea senegalensis* reinforcing its aquaculture potential. *Reviews in Aquaculture* 8: 227–263. https://doi.org/10.1111/raq.12091
- Mayer, P., Estruch, V.D., Blasco, J. & Jover, M. (2008). Predicting the growth of gilthead sea bream (*Sparus aurata* L.) farmed in marine cages under real production conditions using temperature- and time-dependent models. *Aquaculture Research* 39: 1046–1052. https://doi.org/10.1111/j.1365-2109.2008.01963.x
- Mayer, P., Estruch, V.D. & Jover, M. (2012). A two-stage growth model for gilthead sea bream (*Sparus aurata*) based on the thermal growth coefficient. *Aquaculture* 358–359: 6–13. https://doi.org/10.1016/j.aquaculture.2012.06.016
- Muniesa, A. et al. (2020). Mapping the knowledge of the main diseases affecting sea bass and sea bream in Mediterranean. *Transboundary and Emerging Diseases* 67: 1089–1100. https://doi.org/10.1111/tbed.13482
- Person-Le Ruyet, J., Mahé, K., Le Bayon, N. & Le Delliou, H. (2004). Effects of temperature on growth and metabolism in a Mediterranean population of European sea bass, *Dicentrarchus labrax*. *Aquaculture* 237: 269–280. https://doi.org/10.1016/j.aquaculture.2004.04.021
- Sammouth, S., Roque d'Orbcastel, E., Gasset, E., Lemarié, G., Breuil, G., Marino, G., Coeurdacier, J.-L., Fivelstad, S. & Blancheton, J.-P. (2009). The effect of density on sea bass (*Dicentrarchus labrax*) performance in a tank-based recirculating system. *Aquacultural Engineering* 40: 72–78. https://doi.org/10.1016/j.aquaeng.2008.11.004
- Somers, I.F. (1988). On a seasonally oscillating growth function. *Fishbyte* 6(1): 8–11.
- Türkmen, S., Eroldoğan, O.T., Yılmaz, H.A., Ölçülü, A., İnan, G.A.K., Erçen, Z. & Tekelioğlu, N. (2012). Compensatory growth response of European sea bass (*Dicentrarchus labrax* L.) under cycled starvation and restricted feeding rate. *Aquaculture Research* 43: 1643–1650. https://doi.org/10.1111/j.1365-2109.2011.02970.x

## Fotografias

As fotografias do ecrã de abertura do site (pasta `imagens/`, recortadas e reduzidas) vêm do Wikimedia Commons:
- Dourada: Isabelle Cheret, Ifremer, CC BY 4.0 ("Daurades royales (Sparus aurata) en bassin").
- Robalo: Olivier Dugornay, Ifremer, CC BY 4.0 ("Bar commun (Dicentrarchus labrax)").
- Pregado: Stéphane Lesbats, Ifremer, CC BY 4.0 ("Turbots (Scophthalmus maximus)").
- Linguado: Mario Lepage, CC BY 3.0 ("Solea senegalensis").

## Agradecimentos

Parte do código e da documentação deste projeto foi desenvolvida com a ajuda do **Claude** (Anthropic), um assistente de inteligência artificial. As escolhas científicas, a verificação das referências e a interpretação dos resultados foram revistas pelo autor.

## Autor

Dinis Costa · Mestrado em Biologia Marinha Aplicada · [LinkedIn](https://www.linkedin.com/in/dinis-costa-a58a67380)
