# 🚀 Monitor de Notícias - Deploy Render

Deploy completo do Monitor de Notícias no Render.com (100% gratuito!)

## 📋 Estrutura do Projeto

```
monitor-noticias-web/
├── app.py                          # Aplicação Flask principal
├── monitor_multi_sites.py          # Motor de coleta (do seu projeto)
├── requirements.txt                # Dependências Python
├── render.yaml                     # Configuração do Render
├── templates/
│   └── primeira_execucao.html     # Página de loading
├── dados_noticias/                # Dados coletados (criado automaticamente)
└── logs/                          # Logs (criado automaticamente)
```

## 🎯 Funcionalidades da Aplicação Web

### Endpoints Disponíveis:

- **`/`** - Página principal com relatório visual de notícias
- **`/api/status`** - Status da aplicação e última atualização
- **`/api/noticias/<site>`** - API JSON com notícias (metropoles ou correio)
- **`/api/forcar-atualizacao`** - Força atualização manual
- **`/logs`** - Visualiza logs recentes
- **`/health`** - Health check (usado pelo Render)

### Recursos:

✅ **Atualização automática** a cada 30 minutos
✅ **Primeira coleta** ao iniciar
✅ **Thread em background** para não bloquear requisições
✅ **API REST** para integração
✅ **Health check** para monitoramento
✅ **Logs online** acessíveis via navegador

## 🚀 Deploy no Render (Passo a Passo)

### 1️⃣ Preparar o Repositório Git

```bash
# Clone seu projeto ou crie novo diretório
mkdir monitor-noticias-web
cd monitor-noticias-web

# Copie todos os arquivos necessários
# - app.py
# - monitor_multi_sites.py
# - requirements.txt
# - render.yaml
# - templates/primeira_execucao.html

# Inicialize Git
git init
git add .
git commit -m "Initial commit - Monitor de Notícias"

# Crie repositório no GitHub e faça push
git remote add origin https://github.com/SEU_USUARIO/monitor-noticias-web.git
git branch -M main
git push -u origin main
```

### 2️⃣ Deploy no Render

1. **Acesse**: https://render.com
2. **Crie conta** (gratuita) ou faça login
3. **Clique em** "New +" → "Web Service"
4. **Conecte seu GitHub** e selecione o repositório
5. **Configurações automáticas** (detecta render.yaml):
   - Nome: `monitor-noticias`
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. **Clique em** "Create Web Service"
7. **Aguarde** ~5 minutos para o deploy

### 3️⃣ Acessar Aplicação

Após deploy, sua URL será:
```
https://monitor-noticias-XXXXX.onrender.com
```

## ⚙️ Configurações Importantes

### Variáveis de Ambiente (Opcional)

No Render, vá em "Environment" e adicione:

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `PYTHON_VERSION` | `3.11.0` | Versão do Python |
| `PORT` | `10000` | Porta (auto) |

### Plano Gratuito - Limitações

⚠️ **Importante**: O Render free tier tem limitações:

- **Spin down após 15min** de inatividade
- Primeira requisição após spin down leva ~30s
- **750h/mês** de uptime (suficiente!)
- **RAM limitada** (512MB)

**Solução para spin down**:
Use um serviço de ping (ex: UptimeRobot) para fazer requisição a cada 10 minutos:
```
https://seu-app.onrender.com/health
```

## 🧪 Testar Localmente

Antes de fazer deploy:

```bash
# Instale dependências
pip install -r requirements.txt

# Execute aplicação
python app.py

# Acesse no navegador
http://localhost:5000
```

## 📊 Monitoramento

### Ver Logs no Render
1. Dashboard → Seu serviço
2. Aba "Logs"
3. Filtre por data/hora

### Ver Logs na Aplicação
Acesse: `https://seu-app.onrender.com/logs`

### Verificar Status
Acesse: `https://seu-app.onrender.com/api/status`

Resposta:
```json
{
  "status": "online",
  "ultima_atualizacao": "2026-05-08T14:30:00",
  "relatorio_disponivel": true,
  "total_arquivos": 8
}
```

## 🔧 Customizações

### Alterar Intervalo de Atualização

Edite `app.py`, linha 33:
```python
# De 30 minutos para 1 hora
time.sleep(60 * 60)
```

### Adicionar Mais Sites

Edite `monitor_multi_sites.py` seguindo instruções do README original.

### Melhorar Performance

Para evitar timeout no Render (free tier tem limite de 30s):

1. **Reduza limite de artigos** em `monitor_multi_sites.py`:
```python
@property
def limite_artigos(self) -> int:
    return 30  # Era 50-60
```

2. **Execute coleta em background** (já implementado no `app.py`)

## 🆘 Solução de Problemas

### ❌ Deploy falhou

**Erro**: `ModuleNotFoundError`
- Verifique `requirements.txt`
- Certifique-se que `monitor_multi_sites.py` está no repo

**Erro**: `Application timeout`
- Primeira coleta pode demorar. Aguarde até 2 minutos
- Verifique logs no Render

### ❌ Aplicação não atualiza

1. Verifique logs: `/logs`
2. Force atualização: `/api/forcar-atualizacao`
3. Reinicie serviço no dashboard do Render

### ❌ Spin down constante

- Configure UptimeRobot (gratuito) para ping a cada 10min
- URL para monitorar: `https://seu-app.onrender.com/health`

## 🌐 API de Exemplo

### Listar notícias do Metrópoles
```bash
curl https://seu-app.onrender.com/api/noticias/metropoles
```

### Verificar status
```bash
curl https://seu-app.onrender.com/api/status
```

### Forçar atualização
```bash
curl https://seu-app.onrender.com/api/forcar-atualizacao
```

## 📱 Integração

Use a API REST para integrar com:
- Dashboards personalizados
- Aplicativos mobile
- Bots do Telegram/Discord
- Automações (Zapier, n8n)

Exemplo JavaScript:
```javascript
fetch('https://seu-app.onrender.com/api/noticias/metropoles')
  .then(r => r.json())
  .then(data => console.log(`${data.total} notícias encontradas`));
```

## 📝 Próximos Passos

- [ ] Adicionar cache Redis para melhorar performance
- [ ] Implementar autenticação para `/api/forcar-atualizacao`
- [ ] Adicionar webhook para notificações (Telegram/Discord)
- [ ] Criar dashboard de estatísticas
- [ ] Adicionar filtros por categoria/site

## 📜 Licença

Código aberto para uso pessoal e educacional.

---

**💡 Dica**: Para melhor experiência, considere upgrade para Render Pro ($7/mês) que remove spin down e aumenta recursos.
