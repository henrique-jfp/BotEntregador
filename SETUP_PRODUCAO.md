# 🚀 GUIA DE SETUP RÁPIDO - PRODUÇÃO

## ⚡ PASSO 1: Criar Bot no Telegram (3 min)

### 1.1 Fale com o BotFather

1. Abra o Telegram
2. Procure por: **@BotFather**
3. Envie: `/newbot`
4. Nome do bot: `Meu Entregador Bot` (ou qualquer nome)
5. Username: `meuEntregadorBot` (tem que terminar com "bot")
6. **COPIE O TOKEN** que ele mostrar (tipo: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 1.2 Pegue seu Telegram ID

1. Procure por: **@userinfobot**
2. Clique em START
3. **COPIE SEU ID** (tipo: `123456789`)

---

## ⚡ PASSO 2: Configure o Bot (2 min)

Crie arquivo `.env` na raiz do projeto:

```bash
# Cole isso e substitua pelos valores reais
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_TELEGRAM_ID=123456789
```

**⚠️ IMPORTANTE**: Use seus valores reais!

---

## ⚡ PASSO 3: Cadastre Entregadores (5 min)

### 3.1 Pegue IDs dos Entregadores

Cada entregador precisa:
1. Falar com **@userinfobot** no Telegram
2. Copiar o ID que aparecer

### 3.2 Edite o Config

Abra: `bot_multidelivery/config.py`

Substitua a lista `DELIVERY_PARTNERS` pelos seus entregadores reais:

```python
DELIVERY_PARTNERS: List[DeliveryPartner] = [
    # Exemplo - SUBSTITUA pelos IDs reais
    DeliveryPartner(telegram_id=111111111, name="João Silva", is_partner=True),
    DeliveryPartner(telegram_id=222222222, name="Maria Santos", is_partner=True),
    DeliveryPartner(telegram_id=333333333, name="Carlos", is_partner=False),
]
```

**is_partner=True** → Sócio (não paga por entrega)  
**is_partner=False** → Colaborador (R$ 1/entrega)

---

## ⚡ PASSO 4: Instale e Rode (3 min)

### 4.1 Instale Dependências

```bash
pip install python-telegram-bot==20.7 python-dotenv
```

### 4.2 Valide Setup

```bash
python validate_setup.py
```

Se aparecer "✅ SETUP COMPLETO", tá pronto!

### 4.3 Rode o Bot

```bash
python main_multidelivery.py
```

Deve aparecer:
```
🚀 Bot iniciado! Multi-Entregador ativo.
```

**⚠️ DEIXE ESSE TERMINAL ABERTO** enquanto usar o bot!

---

## ⚡ PASSO 5: Teste com Entregas Reais (2 min)

### 5.1 Admin (Você)

1. Abra o Telegram
2. Procure seu bot (pelo username que criou)
3. Envie: `/start`
4. Clique: **"📦 Nova Sessão do Dia"**
5. Digite onde o carro está (ex: `Rua das Flores, 123`)
6. Cole os endereços das entregas de hoje (um por linha):
   ```
   Rua ABC, 100
   Av. XYZ, 200
   Travessa 123, 50
   ```
7. Bot confirma: "✅ X pacotes adicionados"
8. Se tiver mais entregas, cola mais endereços
9. Quando tiver todos: `/fechar_rota`
10. Bot divide automaticamente
11. Clica **"Atribuir ROTA_1"** → Escolhe entregador
12. Clica **"Atribuir ROTA_2"** → Escolhe entregador

### 5.2 Entregadores

1. Cada entregador abre o bot no Telegram dele
2. Envia: `/start`
3. Quando você atribuir a rota, ele recebe automático:
   ```
   🗺️ SUA ROTA - ROTA_1
   📍 Base: Rua das Flores, 123
   📦 Total: 5 pacotes
   
   📋 Ordem de entrega:
   1. Rua ABC, 100
   2. Av. XYZ, 200
   ...
   ```
4. Ao entregar: Clica **"✅ Marcar Entrega"** → Seleciona pacote

---

## 🔍 ACOMPANHAMENTO

### Você (Admin)

- **"📊 Status Atual"** → Vê quantos entregues/faltam
- **"💰 Relatório Financeiro"** → Custo do dia

### Entregadores

- **"🗺️ Minha Rota Hoje"** → Revê rota completa
- **"✅ Marcar Entrega"** → Marca pacote entregue

---

## ⚠️ TROUBLESHOOTING

### Bot não inicia?

```bash
# Verifica se instalou tudo
pip install -r requirements.txt

# Roda validação
python validate_setup.py
```

### Bot iniciou mas não responde?

1. Confere se `.env` tem valores corretos
2. Confere se o TOKEN está certo
3. Confere se você falou com o bot certo no Telegram

### Entregador não recebe rota?

1. Confere se o ID dele tá em `config.py`
2. Confere se ele deu `/start` no bot
3. Reinicia o bot e tenta de novo

---

## 🎯 DICA PRO

Se você testar sozinho (simular os 2 entregadores):

1. Instale Telegram no PC + celular
2. Use contas diferentes
3. Ou use Telegram Web em aba anônima

---

## 📱 MODO PRODUÇÃO

Pra deixar rodando 24/7 (depois que testar):

**Opção 1: Render.com (Grátis)**
```bash
# Cria Procfile
echo "worker: python main_multidelivery.py" > Procfile

# Faz deploy no Render
# (tutorial completo depois)
```

**Opção 2: VPS (DigitalOcean, etc)**
```bash
# Instala tudo no servidor
# Roda com screen/tmux
screen -S bot
python main_multidelivery.py
# CTRL+A+D pra sair
```

---

## ✅ CHECKLIST FINAL

Antes de usar nas entregas de hoje:

- [ ] Bot criado no @BotFather
- [ ] TOKEN copiado pro .env
- [ ] Seu ID copiado pro .env
- [ ] IDs dos entregadores no config.py
- [ ] `pip install python-telegram-bot python-dotenv`
- [ ] `python validate_setup.py` → ✅
- [ ] `python main_multidelivery.py` → Rodando
- [ ] Testou enviar `/start` pro bot
- [ ] Testou adicionar endereço fake

**SE TUDO OK**: Usa de verdade com suas entregas! 🚀

---

## 🔥 FLUXO REAL (HOJE)

```
09:00 → Inicia bot (python main_multidelivery.py)
09:05 → Nova sessão, define base
09:10 → Cola todos os endereços de hoje
09:15 → /fechar_rota
09:16 → Atribui rotas pros entregadores
09:17 → Entregadores saem pra fazer entregas
09:18-17:00 → Entregadores marcam conforme entregam
17:00 → Você vê relatório financeiro
17:05 → Fecha o bot (CTRL+C)
```

**Pronto pra ir!** 🚀
