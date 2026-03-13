import json
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

# ==========================================
# 1. CONFIGURAÇÕES GERAIS
# ==========================================
# Defina o intervalo de datas para a extração 
MIN_DATE_STR = '2026-03-10T00:00:00'
MAX_DATE_STR = '2026-03-10T23:59:59'

min_date = datetime.strptime(MIN_DATE_STR, '%Y-%m-%dT%H:%M:%S')
max_date = datetime.strptime(MAX_DATE_STR, '%Y-%m-%dT%H:%M:%S')

MAX_PAGINAS_POR_PERFIL = 10
URL_BASE = "https://nitter.tiekoetter.com"

# Lista de perfis 
perfis_brutos = [
    "@ContaratoSenado", "@DamaresAlves", "@LulaOficial"
]
# Limpeza: remove espaços e '@' mantendo maiúsculas/minúsculas originais
perfis_limpos = sorted(list(set([p.replace('@', '').strip() for p in perfis_brutos])))


# ==========================================
# 2. FUNÇÕES AUXILIARES
# ==========================================
def converter_data_nitter(data_str):
    # Transforma a string de data do Nitter em um objeto datetime do Python.
    if not data_str: 
        return None
    try:
        texto_limpo = data_str.replace('·', '').replace('  ', ' ').strip()
        return datetime.strptime(texto_limpo, '%b %d, %Y %I:%M %p UTC')
    except Exception:
        return None


# ==========================================
# 3. INICIALIZAÇÃO E EXECUÇÃO
# ==========================================
if __name__ == "__main__":
    print(f"Buscando publicações entre {min_date.strftime('%d/%m/%Y %H:%M:%S')} e {max_date.strftime('%d/%m/%Y %H:%M:%S')} \n")

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Descomente para rodar em 2º plano (invisível)
    chrome_options.add_argument("--log-level=3") # Suprime a maioria dos avisos
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging']) # Oculta os logs do DevTools e do USB/GCM
    driver = webdriver.Chrome(options=chrome_options)

    dados_gerais = {}

    try:
        for index, usuario in enumerate(perfis_limpos, start=1):
            url_atual = f"{URL_BASE}/{usuario}"
            print(f"\n[{index}/{len(perfis_limpos)}] Extraindo @{usuario}...")
            
            # Estrutura inicial de armazenamento para o usuário atual
            dados_gerais[usuario] = {"status": "sucesso", "perfil": {}, "tweets": []}
            pagina_atual = 1
            atingiu_data_limite = False
            
            while pagina_atual <= MAX_PAGINAS_POR_PERFIL and not atingiu_data_limite:
                try:
                    driver.get(url_atual)
                    
                    # Aguarda o carregamento dos tweets ou da página de erro do servidor
                    WebDriverWait(driver, 15).until(
                        lambda d: d.find_elements(By.CLASS_NAME, "timeline-item") or 
                                "Page not found" in d.title or
                                d.find_elements(By.CLASS_NAME, "error-panel")
                    )
                    
                    # Verificação de bloqueio da plataforma
                    if "Page not found" in driver.title or driver.find_elements(By.CLASS_NAME, "error-panel"):
                        print(f"    Instância bloqueou a paginação na página {pagina_atual}.")
                        break 
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # EXTRAÇÃO DO PERFIL
                    if pagina_atual == 1:
                        
                        try: dados_gerais[usuario]["perfil"]["bio"] = soup.find('div', class_='profile-bio').text.strip()
                        except AttributeError: dados_gerais[usuario]["perfil"]["bio"] = None

                        try: dados_gerais[usuario]["perfil"]["localizacao"] = soup.find('div', class_='profile-location').text.strip()
                        except AttributeError: dados_gerais[usuario]["perfil"]["localizacao"] = None

                        try: 
                            joindate_div = soup.find('div', class_='profile-joindate')
                            dados_gerais[usuario]["perfil"]["data_entrada"] = joindate_div.find('span').get('title')
                        except AttributeError: 
                            dados_gerais[usuario]["perfil"]["data_entrada"] = None

                        try:
                            stats = soup.find('ul', class_='profile-statlist').find_all('span', class_='profile-stat-num')
                            dados_gerais[usuario]["perfil"]["tweets_total"] = stats[0].text.strip()
                            dados_gerais[usuario]["perfil"]["seguindo"] = stats[1].text.strip()
                            dados_gerais[usuario]["perfil"]["seguidores"] = stats[2].text.strip()
                        except (AttributeError, IndexError):
                            pass

                    # EXTRAÇÃO DOS TWEETS
                    timeline_items = soup.find_all('div', class_='timeline-item')
                    
                    for item in timeline_items:
                        # Ignora o elemento que contém apenas o botão de carregar mais
                        if item.find('div', class_='show-more'): 
                            continue
                            
                        tweet = {}
                        tweet['fixado'] = True if item.find(class_='pinned') else False
                            
                        try: tweet['texto'] = item.find('div', class_='tweet-content').text.strip()
                        except AttributeError: tweet['texto'] = None
                            
                        # Pula lixo do HTML (sem texto e sem anexos)
                        if not tweet['texto'] and not item.find('div', class_='attachments'): 
                            continue
                            
                        # Extração de Data e Link
                        try:
                            data_element = item.find('span', class_='tweet-date').a
                            tweet['data_str'] = data_element.get('title')
                            tweet['link_original'] = f"https://twitter.com{data_element.get('href')}"
                        except AttributeError:
                            tweet['data_str'] = None
                            tweet['link_original'] = None
                        
                        # Filtro de Data (Decide se salva, ignora ou para a varredura)
                        data_tweet_obj = converter_data_nitter(tweet['data_str'])
                        
                        if data_tweet_obj:
                            if data_tweet_obj > max_date:
                                continue # Tweet além do limite superior, apenas pula
                                
                            if data_tweet_obj < min_date:
                                if tweet['fixado']: 
                                    print(f"       Ignorando Tweet Fixado antigo ({data_tweet_obj.strftime('%d/%m/%Y')})")
                                    continue 
                                else:
                                    print(f"       Limite atingido: Tweet de {data_tweet_obj.strftime('%d/%m/%Y %H:%M')}. Encerrando varredura.")
                                    atingiu_data_limite = True
                                    break 
                        
                        # Extração de Mídias (Imagens e Vídeos)
                        tweet['midias'] = []
                        try:
                            attachments = item.find('div', class_='attachments')
                            if attachments:
                                for img in attachments.find_all('img'):
                                    if img.get('src'): tweet['midias'].append(f"{URL_BASE}{img.get('src')}")
                                for vid in attachments.find_all('video'):
                                    if vid.get('poster'): tweet['midias'].append(f"{URL_BASE}{vid.get('poster')}")
                        except Exception: 
                            pass
                            
                        # Extração de Citações (Quote Tweets)
                        try:
                            quote_box = item.find('div', class_='quote')
                            if quote_box:
                                tweet['tweet_citado'] = {
                                    "autor": quote_box.find('a', class_='tweet-name').text.strip(),
                                    "texto": quote_box.find('div', class_='quote-text').text.strip()
                                }
                            else: tweet['tweet_citado'] = None
                        except AttributeError: tweet['tweet_citado'] = None
                            
                        # Extração de Métricas 
                        try:
                            metricas_div = item.find('div', class_='tweet-stats')
                            tweet['metricas'] = {
                                'comentarios': metricas_div.find('span', class_='icon-comment').parent.text.strip(),
                                'retweets': metricas_div.find('span', class_='icon-retweet').parent.text.strip(),
                                'likes': metricas_div.find('span', class_='icon-heart').parent.text.strip()
                            }
                        except AttributeError:
                            tweet['metricas'] = {'comentarios': None, 'retweets': None, 'likes': None}
                            
                        dados_gerais[usuario]["tweets"].append(tweet)
                    
                    # LÓGICA DE PAGINAÇÃO 
                    if not atingiu_data_limite:
                        show_more_divs = soup.find_all('div', class_='show-more')
                        proximo_cursor = None
                        
                        # Identifica o botão correto de paginação (evita o "Load newest" do topo)
                        for div in show_more_divs:
                            if div.a and '?cursor=' in div.a.get('href', ''):
                                proximo_cursor = div.a.get('href')
                                break 
                                
                        if proximo_cursor:
                            # Monta a nova URL garantindo a barra de divisão
                            if proximo_cursor.startswith('?'):
                                url_atual = f"{URL_BASE}/{usuario}{proximo_cursor}"
                            else:
                                url_atual = f"{URL_BASE}{proximo_cursor}"
                                
                            pagina_atual += 1
                            print(f"       Carregando página {pagina_atual}: {url_atual}")
                            time.sleep(random.uniform(2.0, 4.0)) 
                        else:
                            print(f"       Fim da linha do tempo. Não há mais páginas.")
                            break
                    
                except TimeoutException:
                    print(f"  -> Erro: Tempo esgotado para a página {pagina_atual} de @{usuario}.")
                    if pagina_atual == 1: 
                        dados_gerais[usuario]["status"] = "erro_timeout"
                    break
                except Exception as e:
                    print(f"  -> Erro inesperado: {e}")
                    break

            print(f"  -> Total: {len(dados_gerais[usuario]['tweets'])} publicações capturadas dentro da janela.")
            time.sleep(random.uniform(3.0, 5.0)) # Pausa antes de ir para o próximo usuário

    finally:
        driver.quit()
        print(f"\nNavegador encerrado.")

    # ==========================================
    # 4. EXPORTAÇÃO DOS DADOS
    # ==========================================
    nome_arquivo = "dados_extraidos.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_gerais, f, ensure_ascii=False, indent=4)

    print(f"Extração concluída com sucesso! Todos os dados salvos no arquivo '{nome_arquivo}'.")