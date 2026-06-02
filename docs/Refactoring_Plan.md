# 🏗️ Plano de Refatoração: Desmembrando o Monolito (bot.py)

**Objetivo:** Transformar o arquivo único de ~5000 linhas em uma arquitetura modular, testável e escalável.

## 1. Nova Estrutura de Pastas

```text
bot_multidelivery/
├── bot.py                <-- (Será reduzido para ~100 linhas: Apenas inicialização)
├── core/
│   ├── patching.py       <-- Monkey Patching (Emojis)
│   ├── middlewares.py    <-- Logs, Auth checks
│   └── loader.py         <-- Carregamento dinâmico de handlers
├── handlers/             <-- Onde a lógica vai morar
│   ├── __init__.py
│   ├── common.py         <-- /start, /help, Cancelar
│   ├── admin.py          <-- Painel Admin, Gestão de Time
│   ├── sessions.py       <-- Abertura/Fechamento de Sessões
│   ├── deliverer.py      <-- Ações do Entregador (Iniciar rota, finalizar)
│   ├── upload.py         <-- Processamento de Romaneios (PDF/XLSX)
│   └── dashboard.py      <-- Visualização de gráficos
└── navigation/
    ├── menus.py          <-- Construção de Teclados (Inline/Reply)
    └── callbacks.py      <-- Roteador de Callbacks (Botões)
```

## 2. Etapas da Migração

### FASE 1: Fundação (Seguro) 🛡️
1.  **Monkey Patching:** Extrair a lógica de emojis para `core/patching.py`.
2.  **Menus:** Mover dicionários de teclados e funções de criação de botões para `navigation/menus.py`.

### FASE 2: Comandos Básicos 🏃
3.  **Handlers Simples:** Mover `/start` e `/help` para `handlers/common.py`.
4.  **Admin:** Mover comandos de cadastro de entregadores para `handlers/admin.py`.

### FASE 3: O Núcleo do Negócio (Crítico) 🧠
5.  **Sessões:** Extrair lógica de Start/Stop session da `handlers/sessions.py`.
6.  **Uploads:** Isolar o parser de arquivos em `handlers/upload.py`.
7.  **Callbacks:** Criar um "Router" inteligente para distribuir os cliques dos botões para os arquivos corretos, em vez de ter um `if/elif` gigante.

## 3. Padrão de Codificação (Good Practices)

Todo novo handler seguirá este padrão:

```python
# Exemplo: handlers/admin.py
from telegram import Update
from telegram.ext import ContextTypes
from ..services import admin_service

async def cadastrar_entregador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Docstring explicando o que a função faz.
    """
    # 1. Validação
    if not is_admin(update.effective_user.id):
        return
    
    # 2. Lógica de Negócio (Chamando Service, não fazendo SQL aqui)
    result = admin_service.create_user(...)
    
    # 3. Resposta Visual
    await update.message.reply_text(f"Sucesso: {result}")
```

---
**Status:** Iniciando FASE 1...
