#!/usr/bin/env python3
"""
Aplicação Flask para Monitor de Notícias
Deploy: Render.com (gratuito)
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pathlib import Path
from datetime import datetime
import json
import os
import threading
import time

# Importa o monitor
from monitor_multi_sites import MonitorMultiSites, GeradorRelatorioHTML, AnalisadorImportancia

app = Flask(__name__)

# Configurações
DADOS_DIR = Path("dados_noticias")
DADOS_DIR.mkdir(exist_ok=True)

# Estado global
ultima_atualizacao = None
em_atualizacao = False


def executar_coleta():
    """Executa coleta de notícias em background"""
    global ultima_atualizacao, em_atualizacao
    
    while True:
        try:
            em_atualizacao = True
            print(f"🔄 Iniciando coleta: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            monitor = MonitorMultiSites()
            monitor.executar()
            
            ultima_atualizacao = datetime.now()
            em_atualizacao = False
            
            print(f"✅ Coleta concluída: {ultima_atualizacao.strftime('%d/%m/%Y %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Erro na coleta: {str(e)}")
            em_atualizacao = False
        
        # Aguarda 30 minutos
        time.sleep(30 * 60)


@app.route('/')
def index():
    """Página principal com o relatório de notícias"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_html = DADOS_DIR / f"relatorio_multi_{hoje}.html"
    
    # Se não existe, tenta buscar o mais recente
    if not arquivo_html.exists():
        arquivos = sorted(DADOS_DIR.glob("relatorio_multi_*.html"), reverse=True)
        if arquivos:
            arquivo_html = arquivos[0]
        else:
            # Primeira execução - coleta agora
            return render_template('primeira_execucao.html')
    
    # Lê o HTML gerado
    with open(arquivo_html, 'r', encoding='utf-8') as f:
        conteudo_html = f.read()
    
    return conteudo_html


@app.route('/api/status')
def status():
    """Endpoint para verificar status da aplicação"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_html = DADOS_DIR / f"relatorio_multi_{hoje}.html"
    
    return jsonify({
        'status': 'em_atualizacao' if em_atualizacao else 'online',
        'ultima_atualizacao': ultima_atualizacao.isoformat() if ultima_atualizacao else None,
        'relatorio_disponivel': arquivo_html.exists(),
        'total_arquivos': len(list(DADOS_DIR.glob("*.json")))
    })


@app.route('/api/noticias/<site>')
def noticias_site(site):
    """Retorna notícias de um site específico em JSON"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_json = DADOS_DIR / f"noticias_{site}_{hoje}.json"
    
    if not arquivo_json.exists():
        # Busca arquivo mais recente
        arquivos = sorted(DADOS_DIR.glob(f"noticias_{site}_*.json"), reverse=True)
        if arquivos:
            arquivo_json = arquivos[0]
        else:
            return jsonify({'erro': 'Nenhum dado disponível'}), 404
    
    with open(arquivo_json, 'r', encoding='utf-8') as f:
        noticias = json.load(f)
    
    return jsonify({
        'site': site,
        'total': len(noticias),
        'noticias': noticias
    })


@app.route('/api/forcar-atualizacao')
def forcar_atualizacao():
    """Força uma atualização manual"""
    global em_atualizacao
    
    if em_atualizacao:
        return jsonify({'erro': 'Atualização já em andamento'}), 409
    
    # Executa em thread separada para não bloquear
    thread = threading.Thread(target=lambda: MonitorMultiSites().executar())
    thread.daemon = True
    thread.start()
    
    return jsonify({'mensagem': 'Atualização iniciada'})


@app.route('/logs')
def logs():
    """Mostra logs recentes"""
    hoje = datetime.now().strftime('%Y-%m-%d')
    arquivo_log = Path(f"logs/monitor_{hoje}.log")
    
    if not arquivo_log.exists():
        return "Nenhum log disponível para hoje", 404
    
    with open(arquivo_log, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    # Pega últimas 100 linhas
    ultimas_linhas = linhas[-100:]
    
    return '<pre>' + ''.join(ultimas_linhas) + '</pre>'


@app.route('/health')
def health():
    """Health check para Render"""
    return jsonify({'status': 'healthy'}), 200


# Esta função vai rodar assim que o servidor ligar, independente do Gunicorn
def inicializar_bot():
    print("🚀 Servidor iniciado. Disparando thread de coleta...")
    thread = threading.Thread(target=executar_coleta, daemon=True)
    thread.start()

# Chamamos a função diretamente no corpo do arquivo
inicializar_bot()

# O Gunicorn usa apenas a variável 'app', ele não executa o app.run()
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
