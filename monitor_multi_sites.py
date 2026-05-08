#!/usr/bin/env python3
"""
Sistema de Monitoramento de Notícias Multi-Sites
Versão 3.1 - Otimizada com Logging e Tratamento de Erros

Fontes:
- Metrópoles
- Correio Braziliense

Melhorias v3.1:
- Sistema de logging em arquivo e console
- Tratamento robusto de erros (continua se um site falhar)
- Estatísticas de coleta
- Mensagens de erro mais claras

Autor: Sistema de Monitoramento
Data: 2026
"""

import json
import time
import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup


def enviar_alerta_telegram(titulo, link, resumo=""):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        return # Se não configurou as variáveis, não faz nada

    mensagem = (
        f"🚨 <b>NOTÍCIA IMPORTANTE</b>\n\n"
        f"📌 {titulo}\n\n"
        f"🔗 <a href='{link}'>Leia mais aqui</a>"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")



def configurar_logging(diretorio_logs: str = "logs") -> logging.Logger:
    """Configura sistema de logging"""
    Path(diretorio_logs).mkdir(exist_ok=True)
    
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_log = Path(diretorio_logs) / f"monitor_{data_hoje}.log"
    
    logger = logging.getLogger('MonitorNoticias')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    formato = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler_arquivo = logging.FileHandler(arquivo_log, encoding='utf-8')
    handler_arquivo.setLevel(logging.INFO)
    handler_arquivo.setFormatter(formato)
    logger.addHandler(handler_arquivo)
    
    handler_console = logging.StreamHandler()
    handler_console.setLevel(logging.INFO)
    handler_console.setFormatter(formato)
    logger.addHandler(handler_console)
    
    return logger


class ConfiguracaoGeral:
    """Configurações globais do sistema"""
    
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    TIMEOUT_REQUISICAO = 15
    INTERVALO_ENTRE_REQUISICOES = 3
    
    # Critérios de importância (compartilhados entre todos os sites)
    PONTUACAO_MINIMA_IMPORTANTE = 6
    
    PALAVRAS_MUITO_ALTA = [
        'presidente anuncia', 'presidente sanciona', 'presidente veta',
        'reforma aprovada', 'reforma sancionada', 'lei aprovada',
        'stf decide', 'stf determina', 'supremo decide',
        'operação da pf', 'operação federal', 'prisão preventiva',
        'estado de emergência', 'calamidade pública',
        'bilhões aprovados', 'pacote de', 'investimento de'
    ]
    
    PALAVRAS_ALTA = [
        'congresso aprova', 'senado aprova', 'câmara aprova',
        'governador anuncia', 'ministro anuncia',
        'medida provisória', 'projeto de lei aprovado',
        'stf', 'supremo tribunal',
        'operação policial prende', 'mpf denuncia',
        'urgência', 'emergencial'
    ]
    
    PALAVRAS_MEDIA = [
        'presidente', 'governador', 'ministro',
        'congresso', 'senado federal', 'câmara dos deputados',
        'reforma tributária', 'reforma administrativa',
        'orçamento aprovado', 'r$ bilh',
        'operação policial', 'polícia federal',
        'metrô', 'hospital regional', 'obra de'
    ]


class ConfiguracaoSite(ABC):
    """Classe base para configuração de cada site"""
    
    @property
    @abstractmethod
    def nome(self) -> str:
        """Nome do site"""
        pass
    
    @property
    @abstractmethod
    def urls_monitoradas(self) -> Dict[str, str]:
        """URLs a serem monitoradas"""
        pass
    
    @property
    @abstractmethod
    def limite_artigos(self) -> int:
        """Quantos artigos coletar por página"""
        pass
    
    @property
    @abstractmethod
    def slug(self) -> str:
        """Identificador único do site (para arquivos)"""
        pass


class ConfiguracaoMetropoles(ConfiguracaoSite):
    """Configuração específica do Metrópoles"""
    
    @property
    def nome(self) -> str:
        return "Metrópoles"
    
    @property
    def slug(self) -> str:
        return "metropoles"
    
    @property
    def urls_monitoradas(self) -> Dict[str, str]:
        return {
            "brasil": "https://www.metropoles.com/brasil",
            "distrito-federal": "https://www.metropoles.com/distrito-federal",
        }
    
    @property
    def limite_artigos(self) -> int:
        return 50


class ConfiguracaoCorreioBraziliense(ConfiguracaoSite):
    """Configuração específica do Correio Braziliense"""
    
    @property
    def nome(self) -> str:
        return "Correio Braziliense"
    
    @property
    def slug(self) -> str:
        return "correio"
    
    @property
    def urls_monitoradas(self) -> Dict[str, str]:
        return {
            "cidades-df": "https://www.correiobraziliense.com.br/cidades-df",
            "politica": "https://www.correiobraziliense.com.br/politica",
            "brasil": "https://www.correiobraziliense.com.br/brasil",
            "economia": "https://www.correiobraziliense.com.br/economia",
        }
    
    @property
    def limite_artigos(self) -> int:
        return 60  # Aumentado de 40 para 60


class GerenciadorHistorico:
    """Gerencia o histórico de notícias coletadas"""
    
    def __init__(self, arquivo_historico: Path):
        self.arquivo = arquivo_historico
        self.dados = self._carregar()
    
    def _carregar(self) -> Dict:
        if self.arquivo.exists():
            with open(self.arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"urls_vistas": [], "noticias": []}
    
    def salvar(self) -> None:
        with open(self.arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, ensure_ascii=False, indent=2)
    
    def url_ja_vista(self, url: str) -> bool:
        return url in self.dados["urls_vistas"]
    
    def adicionar_url(self, url: str) -> None:
        if url not in self.dados["urls_vistas"]:
            self.dados["urls_vistas"].append(url)
    
    def adicionar_noticias(self, noticias: List[Dict]) -> None:
        self.dados["noticias"].extend(noticias)


class ColetorNoticias:
    """Responsável por coletar notícias dos sites"""
    
    def __init__(self, config_site: ConfiguracaoSite, historico: GerenciadorHistorico, 
                 analisador: 'AnalisadorImportancia', logger: logging.Logger = None):
        self.config_site = config_site
        self.config_geral = ConfiguracaoGeral()
        self.historico = historico
        self.analisador = analisador
        self.logger = logger or logging.getLogger('MonitorNoticias')
    
    def coletar_todas(self) -> Dict:
        """Coleta notícias de todas as URLs configuradas e retorna estatísticas"""
        self.logger.info("="*70)
        self.logger.info(f"📰 Fonte: {self.config_site.nome}")
        self.logger.info(f"⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self.logger.info("="*70)
        
        todas_noticias = []
        estatisticas = {
            'total_coletadas': 0,
            'por_categoria': {},
            'erros': 0,
            'tempo_inicio': time.time()
        }
        
        for categoria, url in self.config_site.urls_monitoradas.items():
            self.logger.info(f"🔍 Coletando: {categoria.upper()}...")
            
            try:
                noticias = self._coletar_url(url, categoria)
                
                # Classifica subcategorias
                for noticia in noticias:
                    noticia['fonte'] = self.config_site.slug
                    noticia['categoria'] = self.analisador.classificar_subcategoria(noticia)
                
                todas_noticias.extend(noticias)
                estatisticas['total_coletadas'] += len(noticias)
                
                # Estatísticas por categoria
                if categoria == 'brasil' and noticias:
                    subcats = {}
                    for n in noticias:
                        subcats[n['categoria']] = subcats.get(n['categoria'], 0) + 1
                    for subcat, count in sorted(subcats.items()):
                        self.logger.info(f"   • {subcat}: {count} notícias")
                        estatisticas['por_categoria'][subcat] = count
                else:
                    self.logger.info(f"   ✓ {len(noticias)} notícias novas")
                    estatisticas['por_categoria'][categoria] = len(noticias)
                
                time.sleep(self.config_geral.INTERVALO_ENTRE_REQUISICOES)
                
            except Exception as e:
                self.logger.error(f"   ✗ Erro ao coletar {categoria}: {str(e)[:100]}")
                estatisticas['erros'] += 1
                continue  # Continua com próxima categoria
        
        estatisticas['tempo_total'] = time.time() - estatisticas['tempo_inicio']
        self.logger.info("")
        
        return {
            'noticias': todas_noticias,
            'estatisticas': estatisticas
        }
    
    def _coletar_url(self, url: str, categoria: str) -> List[Dict]:
        """Coleta notícias de uma URL específica com retry"""
        max_tentativas = 3
        
        for tentativa in range(1, max_tentativas + 1):
            try:
                response = requests.get(
                    url,
                    headers={'User-Agent': self.config_geral.USER_AGENT},
                    timeout=self.config_geral.TIMEOUT_REQUISICAO
                )
                response.raise_for_status()
                
                # Força encoding correto (Correio usa UTF-8)
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                elementos = self._encontrar_elementos_noticias(soup)
                
                # Log de debug
                self.logger.info(f"   📊 {len(elementos)} elementos HTML encontrados")
                
                noticias = self._extrair_noticias(elementos, categoria)
                
                return noticias
                
            except requests.Timeout:
                self.logger.warning(f"   ⏱️ Timeout na tentativa {tentativa}/{max_tentativas}")
                if tentativa < max_tentativas:
                    time.sleep(2 * tentativa)  # Backoff exponencial
                continue
                
            except requests.RequestException as e:
                self.logger.warning(f"   ⚠️ Erro de conexão (tentativa {tentativa}/{max_tentativas}): {str(e)[:80]}")
                if tentativa < max_tentativas:
                    time.sleep(2 * tentativa)
                continue
                
            except Exception as e:
                self.logger.error(f"   ✗ Erro inesperado: {str(e)[:100]}")
                break
        
        self.logger.error(f"   ✗ Falhou após {max_tentativas} tentativas")
        return []
    
    def _encontrar_elementos_noticias(self, soup: BeautifulSoup) -> List:
        """Encontra elementos HTML que contêm notícias"""
        elementos = []
        
        # Estratégia 1: Tags article
        articles = soup.find_all('article', limit=self.config_site.limite_artigos)
        elementos.extend(articles)
        
        # Estratégia 2: Containers específicos do Correio (procura DENTRO deles)
        if self.config_site.slug == 'correio':
            # Containers do Correio que agrupam notícias
            containers = soup.find_all('div', class_=lambda x: x and any(
                k in str(x).lower() for k in ['hardnews', 'items', 'lista', 'feed']
            ))
            
            # Dentro de cada container, pega os articles
            for container in containers:
                articles_dentro = container.find_all('article')
                elementos.extend(articles_dentro)
                
                # Se não tem articles, pega divs que parecem notícia
                if not articles_dentro:
                    divs_dentro = container.find_all('div', recursive=False)
                    for div in divs_dentro:
                        # Só adiciona se tem link
                        if div.find('a', href=True):
                            elementos.append(div)
        
        # Estratégia 3: Divs com classes específicas de notícia
        if len(elementos) < 15:
            divs = soup.find_all('div', class_=lambda x: x and any(
                k in str(x).lower() for k in ['post', 'card', 'materia', 'noticia', 'news-item']
            ))
            for div in divs:
                if div.find('a', href=True):  # Só se tiver link
                    elementos.append(div)
        
        # Remove duplicatas mantendo ordem
        elementos_unicos = []
        seen = set()
        for elem in elementos:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                elementos_unicos.append(elem)
        
        return elementos_unicos[:self.config_site.limite_artigos]
    
    def _extrair_noticias(self, elementos: List, categoria: str) -> List[Dict]:
        """Extrai informações das notícias dos elementos HTML"""
        noticias = []
        
        for elemento in elementos:
            try:
                noticia = self._extrair_noticia_individual(elemento, categoria)
                if noticia:
                    noticias.append(noticia)
            except:
                continue
        
        return noticias
    
    def _extrair_noticia_individual(self, elemento, categoria: str) -> Optional[Dict]:
        """Extrai uma notícia individual de um elemento HTML"""
        url = self._extrair_url(elemento)
        if not url or self.historico.url_ja_vista(url):
            return None
        
        titulo = self._extrair_titulo(elemento)
        if not titulo or len(titulo) < 15 or len(titulo) > 300:
            return None
        
        descricao = self._extrair_descricao(elemento)
        data_publicacao = self._extrair_data_publicacao(elemento)
        
        self.historico.adicionar_url(url)
        
        return {
            "titulo": titulo,
            "url": url,
            "descricao": descricao,
            "categoria": categoria,
            "data_publicacao": data_publicacao,
            "data_coleta": datetime.now().isoformat()
        }
    
    def _extrair_url(self, elemento) -> Optional[str]:
        """Extrai e normaliza URL da notícia"""
        link_tag = elemento.find('a', href=True)
        if not link_tag:
            if elemento.name == 'a' and elemento.get('href'):
                link_tag = elemento
            else:
                return None
        
        url = link_tag['href']
        
        # Normaliza URL baseado no site
        if not url.startswith('http'):
            if self.config_site.slug == 'metropoles':
                base = 'https://www.metropoles.com'
            elif self.config_site.slug == 'correio':
                base = 'https://www.correiobraziliense.com.br'
            else:
                return None
            
            url = base + (url if url.startswith('/') else '/' + url)
        
        # Filtra URLs inválidas
        urls_ignorar = ['/autor/', '/tag/', '/search/', '/categoria/', '/page/',
                       'facebook.com', 'twitter.com', 'instagram.com']
        if any(x in url for x in urls_ignorar):
            return None
        
        return url
    
    def _extrair_titulo(self, elemento) -> str:
        """Extrai título da notícia usando múltiplas estratégias"""
        titulo = None
        
        # Método 1: Tags de heading (H1, H2, H3, H4)
        for tag in ['h1', 'h2', 'h3', 'h4']:
            h_tag = elemento.find(tag)
            if h_tag:
                titulo = h_tag.get_text(strip=True)
                if len(titulo) > 15:
                    break
        
        # Método 2: Classes com 'title', 'headline', 'titulo'
        if not titulo or len(titulo) < 15:
            title_elem = elemento.find(class_=lambda x: x and any(
                k in str(x).lower() for k in ['title', 'headline', 'titulo', 'manchete', 'chamada']
            ))
            if title_elem:
                titulo = title_elem.get_text(strip=True)
        
        # Método 3: Primeiro link com texto longo
        if not titulo or len(titulo) < 15:
            links = elemento.find_all('a', href=True)
            for link in links:
                link_text = link.get_text(strip=True)
                if 20 < len(link_text) < 200:
                    titulo = link_text
                    break
        
        # Método 4: Atributos do link principal
        if not titulo or len(titulo) < 15:
            link = elemento.find('a', href=True)
            if link:
                titulo = link.get('title') or link.get('aria-label', '')
        
        # Método 5: Qualquer strong ou span com texto longo
        if not titulo or len(titulo) < 15:
            strong = elemento.find(['strong', 'span', 'b'])
            if strong:
                texto = strong.get_text(strip=True)
                if len(texto) > 15:
                    titulo = texto
        
        # Limpa o título
        if titulo:
            # Remove caracteres especiais mal codificados
            titulo = titulo.replace('Ã©', 'é').replace('Ã³', 'ó').replace('Ã£', 'ã')
            titulo = titulo.replace('Ã¡', 'á').replace('Ã­', 'í').replace('Ãº', 'ú')
            titulo = titulo.replace('Ã§', 'ç').replace('Ã', 'í').replace('Ã', 'ô')
            titulo = ' '.join(titulo.split())  # Remove espaços extras
        
        return titulo if titulo else ""
    
    def _extrair_descricao(self, elemento) -> str:
        """Extrai descrição da notícia"""
        p_tag = elemento.find('p')
        if p_tag:
            descricao = p_tag.get_text(strip=True)
            if descricao:
                descricao = ' '.join(descricao.split())
                return descricao[:500] + '...' if len(descricao) > 500 else descricao
        
        desc_elem = elemento.find(class_=lambda x: x and any(
            k in str(x).lower() for k in ['excerpt', 'summary', 'resumo', 'descricao']
        ))
        if desc_elem:
            descricao = desc_elem.get_text(strip=True)
            descricao = ' '.join(descricao.split())
            return descricao[:500] + '...' if len(descricao) > 500 else descricao
        
        return ""
    
    def _extrair_data_publicacao(self, elemento) -> str:
        """Extrai data de publicação da notícia"""
        time_tag = elemento.find('time')
        if time_tag:
            return time_tag.get('datetime', '') or time_tag.get_text(strip=True)
        return ""


class AnalisadorImportancia:
    """Analisa e classifica a importância das notícias"""
    
    def __init__(self):
        self.config = ConfiguracaoGeral()
    
    def classificar_subcategoria(self, noticia: Dict) -> str:
        """Classifica notícia em subcategorias"""
        categoria_original = noticia['categoria']
        
        # Correio: cidades-df vira distrito-federal
        if categoria_original == 'cidades-df':
            return 'distrito-federal'
        
        # Só classifica subcategorias para 'brasil'
        if categoria_original != 'brasil':
            return categoria_original
        
        texto = (noticia['titulo'] + ' ' + noticia.get('descricao', '')).lower()
        
        palavras_economia = [
            'economia', 'pib', 'inflação', 'juros', 'selic', 'dólar', 'bolsa',
            'mercado', 'emprego', 'desemprego', 'salário', 'renda',
            'banco central', 'bc', 'ipca', 'igp', 'déficit', 'superávit',
            'investimento', 'exportação', 'importação', 'comércio',
            'crescimento econômico', 'recessão', 'crise econômica'
        ]
        
        palavras_politica = [
            'presidente', 'ministro', 'congresso', 'senado', 'câmara',
            'deputado', 'senador', 'governo', 'governador', 'prefeito',
            'partido', 'pt', 'pl', 'psdb', 'mdb', 'psd', 'união brasil',
            'eleição', 'votação', 'projeto de lei', 'pec', 'medida provisória',
            'stf', 'supremo', 'justiça', 'ministério', 'reforma',
            'política', 'político', 'planalto', 'brasília política'
        ]
        
        pontos_economia = sum(1 for palavra in palavras_economia if palavra in texto)
        pontos_politica = sum(1 for palavra in palavras_politica if palavra in texto)
        
        if pontos_economia > pontos_politica and pontos_economia >= 2:
            return 'brasil-economia'
        elif pontos_politica >= 2:
            return 'brasil-política'
        else:
            return 'brasil'
    
    def calcular_pontuacao(self, noticia: Dict) -> int:
        """Calcula pontuação de importância da notícia"""
        texto = (noticia['titulo'] + ' ' + noticia.get('descricao', '')).lower()
        pontuacao = 0
        
        for palavra in self.config.PALAVRAS_MUITO_ALTA:
            if palavra in texto:
                pontuacao += 5
        
        for palavra in self.config.PALAVRAS_ALTA:
            if palavra in texto:
                pontuacao += 4
        
        for palavra in self.config.PALAVRAS_MEDIA:
            if palavra in texto:
                pontuacao += 2
        
        return pontuacao
    
    def eh_importante(self, noticia: Dict) -> bool:
        """Verifica se notícia é importante"""
        return self.calcular_pontuacao(noticia) >= self.config.PONTUACAO_MINIMA_IMPORTANTE
    
    def obter_top5(self, noticias: List[Dict]) -> List[Dict]:
        """Retorna as 5 notícias mais importantes por pontuação"""
        if not noticias:
            return []
        
        noticias_com_pontuacao = [
            (n, self.calcular_pontuacao(n)) for n in noticias
        ]
        noticias_com_pontuacao.sort(key=lambda x: x[1], reverse=True)
        
        return [n for n, p in noticias_com_pontuacao[:5]]


class GeradorRelatorioHTML:
    """Gera relatórios HTML das notícias coletadas"""
    
    def __init__(self, analisador: AnalisadorImportancia):
        self.analisador = analisador
    
    def gerar_multi_sites(self, dados_por_site: Dict[str, Dict], data: str, arquivo_saida: Path) -> None:
        """Gera relatório HTML unificado com múltiplos sites"""
        
        html = self._gerar_cabecalho_multi(dados_por_site, data)
        html += self._gerar_seletor_sites(dados_por_site)
        
        for site_slug, dados in dados_por_site.items():
            noticias = dados['noticias']
            importantes = dados['importantes']
            top5 = dados['top5']
            nome_site = dados['nome']
            
            html += f'<div id="site-{site_slug}" class="site-content">\n'
            html += self._gerar_abas(len(noticias), len(top5), len(importantes))
            html += self._gerar_aba_top5(top5, site_slug)
            html += self._gerar_aba_todas(noticias, site_slug)
            html += self._gerar_aba_importantes(importantes, site_slug)
            html += '</div>\n'
        
        html += self._gerar_rodape_multi()
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✓ Relatório multi-sites gerado: {arquivo_saida}")
    
    def _gerar_cabecalho_multi(self, dados_por_site, data) -> str:
        """Gera cabeçalho HTML multi-sites"""
        total_noticias = sum(len(d['noticias']) for d in dados_por_site.values())
        total_importantes = sum(len(d['importantes']) for d in dados_por_site.values())
        
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Notícias - {data}</title>
    <style>{self._obter_css()}</style>
</head>
<body>
    <h1>Monitor de Notícias Multi-Fontes</h1>
    
    <div class="stats">
        <div class="stat-item">
            <span class="stat-label">Data</span>
            <span class="stat-value">{datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Fontes</span>
            <span class="stat-value">{len(dados_por_site)}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total de Notícias</span>
            <span class="stat-value">{total_noticias}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Importantes</span>
            <span class="stat-value">{total_importantes}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Atualização</span>
            <span class="stat-value">{datetime.now().strftime('%H:%M')}</span>
        </div>
    </div>
"""
    
    def _gerar_seletor_sites(self, dados_por_site) -> str:
        """Gera botões para alternar entre sites"""
        html = '<div class="site-selector">\n'
        
        for idx, (slug, dados) in enumerate(dados_por_site.items()):
            active = ' active' if idx == 0 else ''
            html += f'''        <button class="site-button{active}" onclick="trocarSite('{slug}')">
            <span>{dados['nome']}</span>
            <span class="site-badge">{len(dados['noticias'])}</span>
        </button>\n'''
        
        html += '    </div>\n\n'
        return html
    
    def _gerar_abas(self, total, top5, importantes) -> str:
        """Gera botões de navegação entre abas"""
        return f"""
    <div class="tabs">
        <button class="tab-button active" onclick="abrirAba(event, 'top5')">
            Top 5 <span class="tab-badge">{top5}</span>
        </button>
        <button class="tab-button" onclick="abrirAba(event, 'todas')">
            Todas <span class="tab-badge">{total}</span>
        </button>
        <button class="tab-button" onclick="abrirAba(event, 'importantes')">
            Importantes <span class="tab-badge">{importantes}</span>
        </button>
    </div>
"""
    
    def _gerar_aba_top5(self, top5: List[Dict], site_slug: str) -> str:
        """Gera conteúdo da aba Top 5"""
        html = f'    <div id="tab-{site_slug}-top5" class="tab-content active">\n'
        
        if not top5:
            html += self._mensagem_vazia("🏆", "Nenhuma notícia no ranking")
            html += '    </div>\n'
            return html
        
        for i, noticia in enumerate(top5, 1):
            pontuacao = self.analisador.calcular_pontuacao(noticia)
            html += f"""
        <div class="ranking-item">
            <div class="ranking-numero">{i}</div>
            <div class="ranking-conteudo">
                <span class="ranking-pontuacao">{pontuacao} pontos</span>
                <h3><a href="{noticia['url']}" target="_blank">{noticia['titulo']}</a></h3>
                {f'<div class="descricao">{noticia["descricao"]}</div>' if noticia.get('descricao') else ''}
                {self._gerar_meta(noticia, True)}
            </div>
        </div>
"""
        
        html += '    </div>\n'
        return html
    
    def _gerar_aba_todas(self, noticias: List[Dict], site_slug: str) -> str:
        """Gera conteúdo da aba com todas as notícias"""
        html = f'    <div id="tab-{site_slug}-todas" class="tab-content">\n'
        html += self._gerar_noticias_por_categoria(noticias, f"{site_slug}-todas")
        html += '    </div>\n'
        return html
    
    def _gerar_aba_importantes(self, importantes: List[Dict], site_slug: str) -> str:
        """Gera conteúdo da aba de notícias importantes"""
        html = f'    <div id="tab-{site_slug}-importantes" class="tab-content">\n'
        
        if not importantes:
            html += self._mensagem_vazia("⭐", "Nenhuma notícia importante")
        else:
            html += self._gerar_noticias_por_categoria(importantes, f"{site_slug}-importantes")
        
        html += '    </div>\n'
        return html
    
    def _gerar_noticias_por_categoria(self, noticias: List[Dict], prefixo: str) -> str:
        """Agrupa e gera HTML de notícias por categoria"""
        if not noticias:
            return self._mensagem_vazia("📭", "Nenhuma notícia encontrada")
        
        por_categoria = {}
        for noticia in noticias:
            cat = noticia['categoria']
            por_categoria.setdefault(cat, []).append(noticia)
        
        ordem_categorias = ['distrito-federal', 'brasil-política', 'brasil-economia', 'brasil', 'politica', 'economia']
        categorias_ordenadas = []
        
        for cat in ordem_categorias:
            if cat in por_categoria:
                categorias_ordenadas.append((cat, por_categoria[cat]))
        
        for cat, nots in sorted(por_categoria.items()):
            if cat not in ordem_categorias:
                categorias_ordenadas.append((cat, nots))
        
        nomes_categorias = {
            'distrito-federal': 'Distrito Federal',
            'brasil-política': 'Brasil — Política',
            'brasil-economia': 'Brasil — Economia',
            'brasil': 'Brasil — Geral',
            'politica': 'Política',
            'economia': 'Economia'
        }
        
        html = ""
        for idx, (categoria, noticias_cat) in enumerate(categorias_ordenadas):
            cat_id = f"{prefixo}_cat_{idx}"
            nome_exibicao = nomes_categorias.get(categoria, categoria.replace('-', ' ').title())
            
            html += f"""
        <div class="categoria">
            <div class="categoria-header" onclick="toggleCategoria('{cat_id}')">
                <div class="categoria-titulo">
                    <span class="categoria-icone expandido" id="icone_{cat_id}">▶</span>
                    <span>{nome_exibicao}</span>
                    <span class="categoria-count">{len(noticias_cat)}</span>
                </div>
            </div>
            <div class="categoria-conteudo expandido" id="{cat_id}">
                <div class="noticias-container">
"""
            
            for noticia in noticias_cat:
                eh_importante = self.analisador.eh_importante(noticia)
                html += f"""
                    <div class="noticia{' importante' if eh_importante else ''}">
                        {f'<span class="badge-importante">IMPORTANTE</span>' if eh_importante and 'todas' in prefixo else ''}
                        <h3><a href="{noticia['url']}" target="_blank">{noticia['titulo']}</a></h3>
                        {f'<div class="descricao">{noticia["descricao"]}</div>' if noticia.get('descricao') else ''}
                        {self._gerar_meta(noticia)}
                    </div>
"""
            
            html += """
                </div>
            </div>
        </div>
"""
        
        return html
    
    def _gerar_meta(self, noticia: Dict, mostrar_categoria: bool = False) -> str:
        """Gera badges de metadados da notícia"""
        html = '                        <div class="meta">\n'
        
        if mostrar_categoria:
            html += f'                            <span class="badge categoria">{noticia["categoria"].replace("-", " ").title()}</span>\n'
        
        if noticia.get('data_publicacao'):
            try:
                dt = datetime.fromisoformat(noticia['data_publicacao'].replace('Z', '+00:00'))
                data_pub = dt.strftime('%d/%m/%Y às %H:%M')
                html += f'                            <span class="badge publicacao">Publicado: {data_pub}</span>\n'
            except:
                pass
        
        dt_coleta = datetime.fromisoformat(noticia['data_coleta'])
        hora_coleta = dt_coleta.strftime('%d/%m/%Y às %H:%M')
        html += f'                            <span class="badge coleta">Coletado: {hora_coleta}</span>\n'
        html += '                        </div>\n'
        
        return html
    
    def _mensagem_vazia(self, icone: str, mensagem: str) -> str:
        return f'        <div class="mensagem-vazia"><h3>{mensagem}</h3></div>\n'
    
    def _gerar_rodape_multi(self) -> str:
        """Gera JavaScript e fecha HTML"""
        return """
    <script>
        let siteAtual = Object.keys(document.querySelectorAll('.site-content').length > 0 ? 
            {'0': document.querySelector('.site-content').id.replace('site-', '')} : {})[0];
        
        function trocarSite(site) {
            // Esconde todos os sites
            document.querySelectorAll('.site-content').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.site-button').forEach(b => b.classList.remove('active'));
            
            // Mostra o site selecionado
            document.getElementById('site-' + site).classList.add('active');
            event.target.closest('.site-button').classList.add('active');
            siteAtual = site;
        }
        
        function abrirAba(event, aba) {
            const siteContent = event.target.closest('.site-content');
            const siteId = siteContent.id.replace('site-', '');
            
            siteContent.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            siteContent.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.closest('.tab-button').classList.add('active');
            document.getElementById('tab-' + siteId + '-' + aba).classList.add('active');
        }
        
        function toggleCategoria(id) {
            const conteudo = document.getElementById(id);
            const icone = document.getElementById('icone_' + id);
            conteudo.classList.toggle('expandido');
            icone.classList.toggle('expandido');
        }
        
        // Ativa primeiro site ao carregar
        window.addEventListener('DOMContentLoaded', function() {
            const firstSite = document.querySelector('.site-content');
            if (firstSite) {
                firstSite.classList.add('active');
            }
        });
    </script>
</body>
</html>
"""

    def _obter_css(self) -> str:
        """Retorna CSS completo com design profissional"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
            background: #F2F2F2;
            min-height: 100vh;
            color: #0D0D0D;
        }
        
        h1 {
            color: #0D0D0D;
            border-bottom: 4px solid #4ED9BF;
            padding-bottom: 20px;
            margin-bottom: 30px;
            font-size: 2.2em;
            font-weight: 600;
            letter-spacing: -0.5px;
        }
        
        /* Estatísticas */
        .stats {
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin: 25px 0;
            box-shadow: 0 2px 8px rgba(13, 13, 13, 0.08);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            border-left: 4px solid #4ED9BF;
        }
        
        .stat-item { 
            display: flex; 
            flex-direction: column;
            gap: 8px;
        }
        
        .stat-label { 
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }
        
        .stat-value { 
            font-size: 1.8em;
            font-weight: 700;
            color: #4ED9BF;
        }
        
        /* Seletor de Sites */
        .site-selector {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            background: white;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(13, 13, 13, 0.08);
        }
        
        .site-button {
            flex: 1;
            padding: 18px 25px;
            border: 2px solid #E0E0E0;
            background: white;
            color: #0D0D0D;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            position: relative;
        }
        
        .site-button:hover {
            border-color: #4ED9BF;
            background: #F9FFFE;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(78, 217, 191, 0.15);
        }
        
        .site-button.active {
            background: linear-gradient(135deg, #4ED9BF 0%, #3BC9AF 100%);
            color: white;
            border-color: #4ED9BF;
            box-shadow: 0 6px 20px rgba(78, 217, 191, 0.3);
        }
        
        .site-badge {
            background: rgba(13, 13, 13, 0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 700;
        }
        
        .site-button.active .site-badge {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .site-content {
            display: none;
        }
        
        .site-content.active {
            display: block;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Abas */
        .tabs {
            display: flex;
            gap: 12px;
            margin-bottom: 25px;
            background: white;
            padding: 12px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(13, 13, 13, 0.08);
        }
        
        .tab-button {
            flex: 1;
            padding: 14px 20px;
            border: none;
            background: #F2F2F2;
            color: #666;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .tab-button:hover {
            background: #E8E8E8;
            color: #0D0D0D;
        }
        
        .tab-button.active {
            background: #F28D52;
            color: white;
            box-shadow: 0 4px 12px rgba(242, 141, 82, 0.25);
        }
        
        .tab-badge {
            background: rgba(13, 13, 13, 0.15);
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 700;
        }
        
        .tab-button.active .tab-badge {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s ease-in;
        }
        
        /* Ranking Top 5 */
        .ranking-item {
            background: white;
            padding: 25px;
            margin: 18px 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(13, 13, 13, 0.08);
            display: flex;
            gap: 25px;
            transition: all 0.3s ease;
            position: relative;
            border-left: 5px solid #E0E0E0;
        }
        
        .ranking-item:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(13, 13, 13, 0.12);
        }
        
        .ranking-numero {
            font-size: 3.5em;
            font-weight: 800;
            color: #E0E0E0;
            min-width: 70px;
            text-align: center;
            line-height: 1;
        }
        
        .ranking-conteudo {
            flex: 1;
        }
        
        .ranking-item:nth-child(1) {
            background: linear-gradient(to right, #FFF9E6 0%, white 25%);
            border-left-color: #FFD700;
        }
        
        .ranking-item:nth-child(1) .ranking-numero {
            background: linear-gradient(135deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .ranking-item:nth-child(2) {
            background: linear-gradient(to right, #F5F5F5 0%, white 25%);
            border-left-color: #C0C0C0;
        }
        
        .ranking-item:nth-child(2) .ranking-numero {
            color: #C0C0C0;
        }
        
        .ranking-item:nth-child(3) {
            background: linear-gradient(to right, #FFF0E6 0%, white 25%);
            border-left-color: #CD7F32;
        }
        
        .ranking-item:nth-child(3) .ranking-numero {
            color: #CD7F32;
        }
        
        .ranking-pontuacao {
            position: absolute;
            top: 20px;
            right: 20px;
            background: #F27D52;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.9em;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        
        /* Categorias */
        .categoria {
            margin: 25px 0;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(13, 13, 13, 0.08);
            border-left: 4px solid #4ED9BF;
        }
        
        .categoria-header {
            background: linear-gradient(135deg, #0D0D0D 0%, #1A1A1A 100%);
            color: white;
            padding: 18px 25px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
            transition: background 0.3s ease;
        }
        
        .categoria-header:hover {
            background: linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 100%);
        }
        
        .categoria-titulo {
            text-transform: uppercase;
            font-weight: 700;
            font-size: 1em;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: 1px;
        }
        
        .categoria-count {
            background: #4ED9BF;
            color: #0D0D0D;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 700;
        }
        
        .categoria-icone {
            font-size: 0.8em;
            transition: transform 0.3s ease;
            display: inline-block;
            width: 12px;
            height: 12px;
            border-left: 3px solid #4ED9BF;
            border-bottom: 3px solid #4ED9BF;
            transform: rotate(-45deg);
        }
        
        .categoria-icone.expandido {
            transform: rotate(-135deg);
        }
        
        .categoria-conteudo {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.4s ease-out;
        }
        
        .categoria-conteudo.expandido {
            max-height: 15000px;
            transition: max-height 0.6s ease-in;
        }
        
        .noticias-container {
            padding: 20px;
        }
        
        /* Notícias */
        .noticia {
            background: #FAFAFA;
            padding: 22px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 4px solid #E0E0E0;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .noticia.importante {
            border-left-color: #F28D52;
            background: linear-gradient(to right, #FFF5F0 0%, #FAFAFA 20%);
        }
        
        .noticia:hover {
            background: white;
            transform: translateX(6px);
            box-shadow: 0 4px 16px rgba(13, 13, 13, 0.1);
        }
        
        .badge-importante {
            position: absolute;
            top: 15px;
            right: 15px;
            background: #F27D52;
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.75em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        h3 {
            margin: 0 0 12px 0;
            color: #0D0D0D;
            font-size: 1.2em;
            line-height: 1.5;
            padding-right: 120px;
            font-weight: 600;
        }
        
        .ranking-item h3 {
            padding-right: 100px;
        }
        
        a {
            color: #0D0D0D;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s ease;
            border-bottom: 2px solid transparent;
        }
        
        a:hover {
            color: #4ED9BF;
            border-bottom-color: #4ED9BF;
        }
        
        .descricao {
            color: #555;
            margin: 15px 0;
            line-height: 1.7;
            font-size: 0.95em;
        }
        
        /* Meta badges */
        .meta {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #E8E8E8;
        }
        
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: #F2F2F2;
            color: #666;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .badge.publicacao {
            background: #E8F8F5;
            color: #4ED9BF;
            border: 1px solid #D0F2EA;
        }
        
        .badge.coleta {
            background: #FFF5F0;
            color: #F28D52;
            border: 1px solid #FFE8DC;
        }
        
        .badge.categoria {
            background: #F0F0F0;
            color: #0D0D0D;
            border: 1px solid #E0E0E0;
        }
        
        /* Mensagem vazia */
        .mensagem-vazia {
            text-align: center;
            padding: 80px 20px;
            color: #999;
            background: white;
            border-radius: 12px;
            margin: 25px 0;
        }
        
        .mensagem-vazia-icon {
            font-size: 4em;
            margin-bottom: 20px;
            color: #E0E0E0;
        }
        
        .mensagem-vazia h3 {
            color: #666;
            padding: 0;
            margin-bottom: 10px;
        }
        
        /* Responsivo */
        @media (max-width: 768px) {
            body { padding: 15px; }
            h1 { font-size: 1.6em; }
            .stats { grid-template-columns: 1fr; }
            .site-selector, .tabs { flex-direction: column; }
            h3, .ranking-item h3 { padding-right: 0; margin-bottom: 35px; }
            .badge-importante, .ranking-pontuacao { 
                position: static; 
                display: inline-block; 
                margin-bottom: 12px; 
            }
            .ranking-numero { font-size: 2.5em; min-width: 50px; }
        }
        
        /* Scroll suave */
        html {
            scroll-behavior: smooth;
        }
        
        /* Melhorias de acessibilidade */
        .site-button:focus,
        .tab-button:focus,
        .categoria-header:focus {
            outline: 3px solid #4ED9BF;
            outline-offset: 2px;
        }
"""


class MonitorMultiSites:
    """Classe principal que coordena monitoramento de múltiplos sites"""

    for noticia in resultados['noticias']:
    # 1. Calcula a importância
    pontuacao = self.analisador.calcular_pontuacao(noticia)
    noticia['pontuacao'] = pontuacao
    
    # 2. Verifica se é importante (Nota mínima definida na ConfiguracaoGeral)
    if self.analisador.eh_importante(noticia):
        importantes.append(noticia)
        
        # --- AQUI ENTRA O TELEGRAM ---
        # Chamamos a função de alerta apenas para as importantes
        enviar_alerta_telegram(
            titulo=noticia['titulo'],
            link=noticia['url']
        )
        # -----------------------------

        
    def __init__(self, diretorio_dados: str = "dados_noticias"):
        self.diretorio = Path(diretorio_dados)
        self.diretorio.mkdir(exist_ok=True)
        
        # Configura logging
        self.logger = configurar_logging()
        self.logger.info("="*70)
        self.logger.info("🚀 Monitor de Notícias Multi-Sites Iniciado")
        self.logger.info("="*70)
        
        # Configurações dos sites
        self.sites = [
            ConfiguracaoMetropoles(),
            ConfiguracaoCorreioBraziliense(),
        ]
        
        # Componente compartilhado
        self.analisador = AnalisadorImportancia()
        self.gerador_html = GeradorRelatorioHTML(self.analisador)
    
    def executar(self) -> None:
        """Executa coleta em todos os sites com tratamento de erros"""
        dados_por_site = {}
        estatisticas_globais = {
            'total_noticias': 0,
            'total_importantes': 0,
            'sites_sucesso': 0,
            'sites_falha': 0,
            'tempo_inicio': time.time()
        }
        
        for config_site in self.sites:
            try:
                # Histórico separado por site
                arquivo_historico = self.diretorio / f"historico_{config_site.slug}.json"
                historico = GerenciadorHistorico(arquivo_historico)
                
                # Coletor específico do site
                coletor = ColetorNoticias(config_site, historico, self.analisador, self.logger)
                
                # Coleta
                resultado = coletor.coletar_todas()
                noticias = resultado['noticias']
                stats = resultado['estatisticas']
                
                if noticias:
                    historico.adicionar_noticias(noticias)
                    historico.salvar()
                    
                    # Salva JSON individual do site
                    hoje = datetime.now().strftime('%Y-%m-%d')
                    arquivo_json = self.diretorio / f"noticias_{config_site.slug}_{hoje}.json"
                    
                    with open(arquivo_json, 'w', encoding='utf-8') as f:
                        json.dump(noticias, f, ensure_ascii=False, indent=2)
                    
                    self.logger.info(f"✓ JSON salvo: {arquivo_json}")
                    self.logger.info(f"📊 Estatísticas: {stats['total_coletadas']} notícias em {stats['tempo_total']:.1f}s")
                    if stats['erros'] > 0:
                        self.logger.warning(f"⚠️ {stats['erros']} categoria(s) com erro")
                    self.logger.info("")
                    
                    # Prepara dados para HTML
                    importantes = [n for n in noticias if self.analisador.eh_importante(n)]
                    top5 = self.analisador.obter_top5(noticias)
                    
                    dados_por_site[config_site.slug] = {
                        'nome': config_site.nome,
                        'noticias': noticias,
                        'importantes': importantes,
                        'top5': top5
                    }
                    
                    estatisticas_globais['total_noticias'] += len(noticias)
                    estatisticas_globais['total_importantes'] += len(importantes)
                    estatisticas_globais['sites_sucesso'] += 1
                else:
                    self.logger.warning(f"⚠️ Nenhuma notícia coletada de {config_site.nome}")
                    estatisticas_globais['sites_falha'] += 1
                    
            except Exception as e:
                self.logger.error(f"❌ Erro crítico ao processar {config_site.nome}: {str(e)[:150]}")
                estatisticas_globais['sites_falha'] += 1
                continue  # Continua com próximo site
        
        # Gera HTML se houver dados
        if dados_por_site:
            hoje = datetime.now().strftime('%Y-%m-%d')
            arquivo_html = self.diretorio / f"relatorio_multi_{hoje}.html"
            self.gerador_html.gerar_multi_sites(dados_por_site, hoje, arquivo_html)
            
            # Estatísticas finais
            tempo_total = time.time() - estatisticas_globais['tempo_inicio']
            self.logger.info("="*70)
            self.logger.info("📊 RESUMO DA COLETA")
            self.logger.info("="*70)
            self.logger.info(f"✅ Sites com sucesso: {estatisticas_globais['sites_sucesso']}")
            if estatisticas_globais['sites_falha'] > 0:
                self.logger.warning(f"❌ Sites com falha: {estatisticas_globais['sites_falha']}")
            self.logger.info(f"📰 Total de notícias: {estatisticas_globais['total_noticias']}")
            self.logger.info(f"⭐ Notícias importantes: {estatisticas_globais['total_importantes']}")
            self.logger.info(f"⏱️ Tempo total: {tempo_total:.1f}s")
            self.logger.info(f"📁 Relatório: {arquivo_html}")
            self.logger.info("="*70)
        else:
            self.logger.error("❌ Nenhum site coletou notícias com sucesso")
            self.logger.error("💡 Verifique sua conexão ou os logs acima para detalhes")


def main():
    """Função principal de execução"""
    monitor = MonitorMultiSites()
    monitor.executar()


if __name__ == "__main__":
    main()
