#!/usr/bin/env python3
"""
Script para testar a aplicação Flask localmente antes do deploy
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def testar_endpoints():
    """Testa todos os endpoints da aplicação"""
    
    print("="*70)
    print("🧪 TESTANDO APLICAÇÃO FLASK - MONITOR DE NOTÍCIAS")
    print("="*70)
    print(f"⏰ Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    testes = [
        {
            'nome': 'Health Check',
            'url': f'{BASE_URL}/health',
            'metodo': 'GET'
        },
        {
            'nome': 'Status da Aplicação',
            'url': f'{BASE_URL}/api/status',
            'metodo': 'GET'
        },
        {
            'nome': 'Página Principal',
            'url': f'{BASE_URL}/',
            'metodo': 'GET',
            'timeout': 60  # Primeira coleta pode demorar
        },
        {
            'nome': 'API Notícias Metrópoles',
            'url': f'{BASE_URL}/api/noticias/metropoles',
            'metodo': 'GET'
        },
        {
            'nome': 'API Notícias Correio',
            'url': f'{BASE_URL}/api/noticias/correio',
            'metodo': 'GET'
        }
    ]
    
    resultados = []
    
    for teste in testes:
        print(f"🔍 Testando: {teste['nome']}")
        print(f"   URL: {teste['url']}")
        
        try:
            timeout = teste.get('timeout', 10)
            inicio = time.time()
            
            response = requests.get(teste['url'], timeout=timeout)
            tempo_resposta = time.time() - inicio
            
            status_icon = "✅" if response.status_code == 200 else "⚠️"
            print(f"   {status_icon} Status: {response.status_code}")
            print(f"   ⏱️  Tempo: {tempo_resposta:.2f}s")
            
            # Mostra preview do conteúdo
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"   📊 Dados: {list(data.keys())}")
                if 'total' in data:
                    print(f"   📰 Total notícias: {data['total']}")
            else:
                size_kb = len(response.content) / 1024
                print(f"   📄 Tamanho: {size_kb:.1f} KB")
            
            resultados.append({
                'teste': teste['nome'],
                'sucesso': response.status_code == 200,
                'tempo': tempo_resposta
            })
            
        except requests.Timeout:
            print(f"   ⏱️ TIMEOUT após {timeout}s")
            resultados.append({'teste': teste['nome'], 'sucesso': False, 'erro': 'Timeout'})
            
        except requests.ConnectionError:
            print(f"   ❌ ERRO: Servidor não está rodando")
            print(f"   💡 Execute: python app.py")
            resultados.append({'teste': teste['nome'], 'sucesso': False, 'erro': 'Conexão'})
            
        except Exception as e:
            print(f"   ❌ ERRO: {str(e)[:100]}")
            resultados.append({'teste': teste['nome'], 'sucesso': False, 'erro': str(e)})
        
        print()
    
    # Resumo
    print("="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    
    sucessos = sum(1 for r in resultados if r.get('sucesso', False))
    total = len(resultados)
    
    print(f"\n✅ Sucessos: {sucessos}/{total}")
    print(f"❌ Falhas: {total - sucessos}/{total}")
    
    tempo_total = sum(r.get('tempo', 0) for r in resultados)
    print(f"⏱️  Tempo total: {tempo_total:.2f}s")
    
    if sucessos == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Aplicação pronta para deploy no Render")
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")
        print("💡 Verifique os erros acima antes do deploy")
    
    print("="*70 + "\n")


def testar_forcar_atualizacao():
    """Testa endpoint de atualização forçada"""
    print("\n🔄 Testando atualização forçada...")
    
    try:
        response = requests.get(f'{BASE_URL}/api/forcar-atualizacao')
        if response.status_code == 200:
            print("✅ Atualização iniciada com sucesso")
            print("⏳ Aguarde ~1-2 minutos para conclusão")
        else:
            print(f"⚠️ Status: {response.status_code}")
            print(f"   Resposta: {response.json()}")
    except Exception as e:
        print(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--forcar-atualizacao':
        testar_forcar_atualizacao()
    else:
        testar_endpoints()
        
        print("\n💡 Dicas:")
        print("   • Para testar atualização forçada: python testar_app.py --forcar-atualizacao")
        print("   • Para ver logs: curl http://localhost:5000/logs")
        print("   • Para acessar no navegador: http://localhost:5000")
