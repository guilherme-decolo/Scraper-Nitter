# X/Twitter Scraper via Nitter
Um web scraper construído em Python para extrair dados de perfis e publicações do X (antigo Twitter) utilizando instâncias do **Nitter**.

## Funcionalidades

- **Extração de Perfil Completa:** Captura biografia, localização, data de criação da conta, número de seguidores, seguindo e total de tweets.
- **Extração Detalhada de Tweets:** Captura texto, data, links originais, mídias (imagens/vídeos anexados), tweets citados (*quote tweets*) e métricas de engajamento (likes, retweets, comentários).
- **Filtro Temporal:** Define limites estritos de data (`MIN_DATE` e `MAX_DATE`). O scraper varre a linha do tempo e para ao atingir postagens fora da janela.
- **Paginação Automática:** Navega pelas páginas do Nitter.

## Tecnologias Utilizadas

- **Python 3**
- **Selenium (WebDriver):** Usado para contornar bloqueios anti-bot e desafios JavaScript.
- **BeautifulSoup4:** Para o parsing rápido e extração de elementos do HTML.

## Como Rodar

1. Clone o repositório
2. Crie um ambiente virtual (recomendado):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Edite as variáveis no arquivo scraper_nitter.py:

    Altere a lista `perfis_brutos` com os perfis que deseja coletar.

    Ajuste as variáveis `MIN_DATE_STR` e `MAX_DATE_STR` para a janela de tempo da sua pesquisa.

6. Execute o script:
   ```
   python scraper_nitter.py
   ```
