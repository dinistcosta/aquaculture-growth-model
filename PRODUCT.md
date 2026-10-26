# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Três públicos, com a mesma prioridade:

- **Recrutadores e empregadores** (empresas de aquacultura, consultoras, institutos de investigação) que avaliam o portefólio do autor.
- **Meio académico** (orientadores, júris, programas de doutoramento) que avalia o rigor científico do modelo.
- **Produtores de aquacultura** que querem correr o modelo com os dados do próprio cultivo.

## Product Purpose

Modelo interativo do crescimento da dourada (*Sparus aurata*) e do robalo (*Dicentrarchus labrax*) em aquacultura. Simula o efeito da temperatura da água, da alimentação e do sistema de cultivo (jaula, tanque/RAS, IMTA) no tempo até ao tamanho comercial (400 g) e na eficiência alimentar (FCR).

A visita é um sucesso quando o visitante faz pelo menos uma destas coisas:

- experimenta a app e vê a curva de crescimento mudar;
- percebe o rigor: cada parâmetro tem uma referência publicada e os dados simulados estão assinalados como simulados;
- segue para o repositório no GitHub, os notebooks e o código em `src/`;
- quer contactar o autor.

## Positioning

Um modelo de crescimento assente na literatura publicada: cada parâmetro tem autor e ano, e cada pressuposto sem referência está assinalado. Feito por um biólogo marinho (Mestrado em Biologia Marinha Aplicada), por isso é a biologia que conduz o código, e não o contrário.

## Operating Context

- Alojado no GitHub Pages a partir da raiz de `main`. O `index.html` corre a `app.py` (Streamlit) no browser através do stlite 1.10.0 e do Pyodide, sem servidor. A primeira abertura demora alguns segundos.
- O visitante pode carregar os seus próprios CSV (temperaturas e pesagens) e compará-los com o modelo.
- Os resultados podem ser descarregados em CSV.

## Capabilities and Constraints

- Escolhas: espécie, sistema de cultivo (jaula, tanque/RAS com densidade, IMTA), alimentação, temperatura. Resultados: curva de crescimento, dias até 400 g, despesca, biomassa e ração, tabela de dados.
- Limitação do stlite: um tipo de letra do tema com URL (`"Inter:https://..."`) deixa a página em branco. Usar só `"Inter, sans-serif"`.
- O GitHub Pages precisa do ficheiro `.nojekyll` na raiz.
- **Idioma:** hoje só em português. Decidido: português e inglês, com um botão para mudar de língua.
- **Contacto:** decidido: só o LinkedIn do autor (o email não é publicado, para evitar spam).

## Brand Commitments

- Nenhum emoji: site, app, título, favicon, ecrã de carregamento.
- Títulos sóbrios, por exemplo "Modelo de crescimento de dourada e robalo".
- Texto impessoal: nada de "tu" nem "o meu cultivo".
- Ícones Material só onde têm função, como nos botões de download.

## Evidence on Hand

- Referências da literatura com DOI, listadas no `README.md`.
- Cinco notebooks de análise em `notebooks/` e gráficos exportados em `figures/`.
- Registos de biometria simulados em `data/raw/`.
- Não existem dados reais de explorações, testemunhos, utilizadores nem publicações. Nada disto pode ser inventado. Todos os dados têm de continuar identificados como simulados.

## Product Principles

1. **Cada número tem uma fonte.** Um parâmetro mostra a sua referência ou é assinalado como pressuposto.
2. **O que é simulado vê-se sempre.** O visitante nunca pode confundir dados simulados com registos reais.
3. **Um site para três leitores.** Recrutador, académico e produtor encontram cada um o seu caminho sem atrapalhar os outros.
4. **Sóbrio e profissional.** A credibilidade vem da precisão, não da decoração.
5. **Explicável.** O código mantém-se simples o suficiente para o autor o explicar linha a linha numa entrevista.
