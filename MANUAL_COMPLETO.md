# 📚 MANUAL COMPLETO - Bot Multi-Entregador

## 🔑 VARIÁVEIS DE AMBIENTE (.env)

### ✅ OBRIGATÓRIAS (Bot não funciona sem)

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_TELEGRAM_ID=123456789
```

| Variável | Descrição | Como obter | Exemplo |
|----------|-----------|------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token do bot criado no Telegram | Fale com @BotFather → `/newbot` | `123456789:ABCdef...` |
| `ADMIN_TELEGRAM_ID` | Seu Telegram ID (administrador) | Fale com @userinfobot | `123456789` |

### ⚠️ OPCIONAL (Bot funciona sem, mas com limitações)

```env
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXX
```

| Variável | Descrição | Quando usar | Status |
|----------|-----------|-------------|--------|
| `GOOGLE_API_KEY` | Chave Google Maps/Geocoding | Para geocoding automático de endereços | 🚧 Em desenvolvimento |

**Nota**: Atualmente o bot usa coordenadas simuladas. Com essa chave ativada, os endereços serão geocodificados automaticamente via Google Maps API.

---

## 👥 TIPOS DE USUÁRIOS

### 1️⃣ **ADMIN** (Administrador - Você)

**Quem é**: Pessoa que gerencia todas as entregas  
**Telegram ID**: Definido em `ADMIN_TELEGRAM_ID` no .env  
**Acesso especial**: Menu administrativo completo

### 2️⃣ **ENTREGADOR** (Delivery Partner)

**Quem é**: Pessoas que fazem as entregas  
**Telegram IDs**: Cadastrados em `bot_multidelivery/config.py`  
**Tipos**:
- **Sócio** (`is_partner=True`): Custo R$ 0/pacote
- **Colaborador** (`is_partner=False`): Custo R$ 1/pacote

---

## 🎯 FUNCIONALIDADES POR USUÁRIO

---

## 👔 ADMIN (Administrador)

### 📋 Menu Principal

Ao enviar `/start`, o admin vê:

```
🔥 BOT ADMIN - Multi-Entregador

Bem-vindo, chefe! Escolha uma opção:

📦 Nova Sessão do Dia
📊 Status Atual
💰 Relatório Financeiro
```

---

### 📦 FUNÇÃO 1: Nova Sessão do Dia

**Quando usar**: Início do dia, antes de sair para entregas

**Fluxo completo**:

1. **Clica**: "📦 Nova Sessão do Dia"
2. **Bot pergunta**: "Onde o carro estará estacionado hoje?"
3. **Você digita**: Endereço da base (ex: "Rua das Flores, 123")
4. **Bot mostra 3 opções** de envio:
   - 📝 **Texto**: Cole endereços (um por linha)
   - 📄 **CSV**: Anexe planilha Excel/Google Sheets
   - 📕 **PDF**: Anexe documento PDF
5. **Você escolhe** uma opção:
   
   **Opção A - Texto (Manual)**:
   ```
   Av. Paulista, 1000
   Rua Augusta, 500
   Praça da Sé, 100
   ```
   
   **Opção B - CSV (Anexar arquivo)**:
   - Clica 📎
   - Escolhe arquivo `.csv`
   - Bot processa automaticamente
   
   **Opção C - PDF (Anexar arquivo)**:
   - Clica 📎
   - Escolhe arquivo `.pdf`
   - Bot extrai endereços automaticamente

6. **Bot confirma**: "✅ 3 pacotes adicionados"
7. **Você pode** enviar mais romaneios (mistura formatos!)
8. **Quando terminar**: Digita `/fechar_rota`

**O que acontece**:
- ✅ Sistema armazena todos os endereços
- ✅ Aceita múltiplos romaneios antes de fechar
- ✅ Mostra total acumulado

**Resultado esperado**:
```
✅ Base definida: Rua das Flores, 123

📋 Agora envie os romaneios:

📝 Opção 1: Cole texto (um endereço por linha)
📄 Opção 2: Anexe arquivo CSV
📕 Opção 3: Anexe arquivo PDF

Quando terminar, digite: /fechar_rota
```

**📋 FORMATOS DE ROMANEIO ACEITOS**:

Veja documento completo: [FORMATOS_ROMANEIO.md](FORMATOS_ROMANEIO.md)

1. **Texto Manual** (mais rápido para poucos endereços)
   - Um por linha: `Rua A, 123\nRua B, 456`
   - Com numeração: `1. Rua A, 123\n2. Rua B, 456`
   - Com emojis: `📦 Rua A, 123`

2. **CSV** (melhor para planilhas)
   - Excel: Salvar Como → CSV UTF-8
   - Google Sheets: Download → CSV
   - Detecta colunas automaticamente

3. **PDF** (documentos prontos)
   - PDF digital: Extração automática
   - PDF escaneado: OCR (requer Tesseract)

**Pode misturar formatos na mesma sessão!**

---

### 🛣️ FUNÇÃO 2: Fechar Rota (Comando `/fechar_rota`)

**Quando usar**: Depois de adicionar todos os romaneios do dia

**O que faz**:
1. 🤖 IA divide entregas em **2 territórios otimizados** (K-Means geográfico)
2. 📍 Ordena clusters por distância da base
3. 🗺️ Otimiza ordem de entrega dentro de cada cluster (Greedy Nearest Neighbor)
4. 🎯 Mostra resumo e botões para atribuir rotas

**Resultado esperado**:
```
🎯 Rotas Divididas!

📍 Base: Rua das Flores, 123
📦 Total: 10 pacotes

ROTA_1: 5 pacotes
ROTA_2: 5 pacotes

🚀 Agora atribua as rotas aos entregadores:

[Atribuir ROTA_1]
[Atribuir ROTA_2]
```

**Próximo passo**: Clica nos botões para atribuir cada rota

---

### 👤 FUNÇÃO 3: Atribuir Rotas aos Entregadores

**Fluxo**:

1. **Clica**: "Atribuir ROTA_1"
2. **Bot mostra** lista de entregadores cadastrados:
   ```
   João (Sócio)
   Maria (Sócio)
   Carlos
   Ana
   ```
3. **Você clica** no nome do entregador
4. **Bot confirma**: "✅ ROTA_1 atribuída a João!"
5. **Bot envia** a rota automaticamente no chat privado do entregador
6. **Repete** para ROTA_2

**O que acontece**:
- ✅ Entregador recebe rota completa no Telegram dele
- ✅ Rota vem com ordem otimizada
- ✅ Cada pacote tem ID único

**Quando todas rotas são atribuídas**:
```
🎉 Todas as rotas foram distribuídas!

Boa entrega!
```

---

### 📊 FUNÇÃO 4: Status Atual

**Quando usar**: Durante o dia, para acompanhar progresso

**Clica**: "📊 Status Atual"

**O que mostra**:
```
📊 STATUS - 2025-12-12

📍 Base: Rua das Flores, 123
📦 Total: 10 pacotes
✅ Entregues: 6
⏳ Pendentes: 4

Rotas:
• ROTA_1: João - 4/5 (80.0%)
• ROTA_2: Carlos - 2/5 (40.0%)
```

**Informações**:
- ✅ Quantos pacotes no total
- ✅ Quantos já foram entregues
- ✅ Quantos ainda faltam
- ✅ Progresso individual de cada entregador
- ✅ Porcentagem de conclusão

**Atualiza em tempo real**: Sempre que um entregador marca uma entrega, o status muda

---

### 💰 FUNÇÃO 5: Relatório Financeiro

**Quando usar**: No fim do dia, para fechar contas

**Clica**: "💰 Relatório Financeiro"

**O que mostra**:
```
💰 RELATÓRIO FINANCEIRO - 2025-12-12

• João (Sócio): R$ 0,00
• Carlos: R$ 4,00
• Maria (Sócio): R$ 0,00
• Ana: R$ 2,00

CUSTO TOTAL: R$ 6,00
```

**Cálculo**:
- **Sócios** (`is_partner=True`): R$ 0,00 por pacote
- **Colaboradores** (`is_partner=False`): R$ 1,00 por pacote
- **Total**: Soma de todos os custos

**Exemplo real**:
- João (sócio) entregou 5 pacotes → R$ 0,00
- Carlos entregou 4 pacotes → R$ 4,00
- **Total do dia**: R$ 4,00

---

## 🚴 ENTREGADOR (Delivery Partner)

### 📋 Menu Principal

Ao enviar `/start`, o entregador vê:

```
👋 Olá, João!

Você receberá sua rota quando o admin distribuir as entregas.

🗺️ Minha Rota Hoje
✅ Marcar Entrega
```

---

### 🗺️ FUNÇÃO 1: Minha Rota Hoje

**Quando usar**: Para ver/rever a rota completa

**Clica**: "🗺️ Minha Rota Hoje"

**O que mostra**:
```
🗺️ SUA ROTA - ROTA_1

📍 Base: Rua das Flores, 123
📦 Total: 5 pacotes

📋 Ordem de entrega:

1. Praça da Sé, 100
   🆔 PKG002

2. Av. Ipiranga, 200
   🆔 PKG007

3. Rua da Consolação, 800
   🆔 PKG006

4. Av. Brigadeiro Luís Antônio, 1000
   🆔 PKG009

5. Av. Paulista, 1000
   🆔 PKG000

✅ Marque entregas usando o botão 'Marcar Entrega'
```

**Informações**:
- ✅ Endereço da base (onde o carro está)
- ✅ Número total de pacotes na sua rota
- ✅ Ordem otimizada pela IA (do mais próximo ao mais distante)
- ✅ ID único de cada pacote

**Ordem otimizada**: IA calcula qual entrega fazer primeiro para economizar tempo/km

---

### ✅ FUNÇÃO 2: Marcar Entrega

**Quando usar**: Depois de fazer cada entrega

**Fluxo**:

1. **Clica**: "✅ Marcar Entrega"
2. **Bot mostra** pacotes pendentes:
   ```
   📋 Selecione o pacote entregue:

   [📦 Praça da Sé, 100... (ID: PKG002)]
   [📦 Av. Ipiranga, 200... (ID: PKG007)]
   [📦 Rua da Consolação... (ID: PKG006)]
   ```
3. **Você clica** no pacote que acabou de entregar
4. **Bot confirma** e remove da lista
5. **Progresso atualiza** automaticamente

**Limite de exibição**: Mostra até 10 pacotes por vez (se tiver mais, aparece depois)

**Quando termina tudo**:
```
🎉 Todas as suas entregas foram concluídas!
```

---

### 📨 FUNÇÃO 3: Receber Rota (Automático)

**Quando acontece**: Quando o admin atribui uma rota a você

**Não precisa fazer nada**: O bot envia automaticamente

**Mensagem recebida**:
```
🗺️ SUA ROTA - ROTA_1

📍 Base: Rua das Flores, 123
📦 Total: 5 pacotes

📋 Ordem de entrega:

1. Praça da Sé, 100
   🆔 PKG002

2. Av. Ipiranga, 200
   🆔 PKG007

...

✅ Marque entregas usando o botão 'Marcar Entrega'
```

**Importante**: 
- ✅ Você recebe a rota automaticamente
- ✅ Não precisa pedir
- ✅ Sempre vem com ordem otimizada

---

## 🔄 FLUXO COMPLETO (Dia Típico)

### 🌅 Manhã (08:00 - 09:00)

```
ADMIN:
1. Abre bot → /start
2. "📦 Nova Sessão do Dia"
3. Define base: "Rua X, onde o carro está"
4. Envia romaneios:
   - Opção A: Cola texto com endereços
   - Opção B: Anexa CSV
   - Opção C: Anexa PDF
5. /fechar_rota
6. IA divide em 2 rotas automaticamente
7. Atribui ROTA_1 → João
8. Atribui ROTA_2 → Carlos

ENTREGADORES (automático):
- João recebe ROTA_1 no chat
- Carlos recebe ROTA_2 no chat
```

### 🚚 Durante o Dia (09:00 - 17:00)

```
ENTREGADORES:
- Fazem entregas seguindo a ordem
- Marcam cada entrega: "✅ Marcar Entrega"
- Podem rever rota: "🗺️ Minha Rota Hoje"

ADMIN (acompanhando):
- "📊 Status Atual" → Vê progresso em tempo real
- Vê quantos entregues/faltam
- Vê % de conclusão de cada um
```

### 🌆 Fim do Dia (17:00+)

```
ADMIN:
- "💰 Relatório Financeiro"
- Vê custos por entregador
- Total do dia calculado automaticamente
- Fecha contas com entregadores
```

---

## 🎯 RESUMO DE FUNCIONALIDADES

### ADMIN (6 funções)

| # | Função | Quando usar | O que faz |
|---|--------|-------------|-----------|
| 1 | `/start` | Abrir bot | Mostra menu admin |
| 2 | Nova Sessão do Dia | Início do dia | Define base e recebe romaneios (texto/CSV/PDF) |
| 3 | `/fechar_rota` | Depois de enviar todos romaneios | IA divide em rotas otimizadas |
| 4 | Atribuir Rotas | Depois de fechar rota | Escolhe qual entregador faz qual rota |
| 5 | Status Atual | Durante o dia | Vê progresso em tempo real |
| 6 | Relatório Financeiro | Fim do dia | Vê custos e fecha contas |

### ENTREGADOR (3 funções)

| # | Função | Quando usar | O que faz |
|---|--------|-------------|-----------|
| 1 | `/start` | Abrir bot | Mostra menu entregador |
| 2 | Minha Rota Hoje | Ver/rever rota | Mostra rota completa otimizada |
| 3 | Marcar Entrega | Após cada entrega | Registra pacote entregue |

---

## 🧠 TECNOLOGIAS (O que o bot faz por baixo dos panos)

### 1. **K-Means Geográfico**
- Divide entregas em N territórios (padrão: 2)
- Considera distância real (Haversine - curvatura da Terra)
- Inicialização K-Means++ (espaça centroides inteligentemente)

### 2. **Greedy Nearest Neighbor**
- Otimiza ordem dentro de cada território
- Sempre vai pro endereço mais próximo
- Começa da base (onde o carro está)

### 3. **Sistema de Custos**
- Calcula automaticamente por entregador
- Diferencia sócios (R$ 0) vs colaboradores (R$ 1)
- Relatório financeiro em tempo real

### 4. **Tracking em Tempo Real**
- Admin vê progresso atualizado
- Contadores de entregues/pendentes
- Porcentagem de conclusão

---

## 📝 CONFIGURAÇÕES AVANÇADAS

### Em `bot_multidelivery/config.py`:

```python
# Número de territórios (quantas rotas dividir)
CLUSTER_COUNT = 2  # Padrão: 2 entregadores

# Máximo de romaneios por lote
MAX_ROMANEIOS_PER_BATCH = 10

# Custo por pacote (não-sócios)
# Definido em: cost_per_package = 1.0
```

### Cadastrar Entregadores:

```python
DELIVERY_PARTNERS: List[DeliveryPartner] = [
    DeliveryPartner(
        telegram_id=123456789,      # ID do Telegram
        name="João Silva",           # Nome
        is_partner=True              # True = sócio (R$ 0)
    ),
    DeliveryPartner(
        telegram_id=987654321,
        name="Carlos",
        is_partner=False             # False = colaborador (R$ 1)
    ),
]
```

---

## ⚠️ LIMITAÇÕES ATUAIS

1. **Geocoding**: Usa coordenadas simuladas
   - **Solução futura**: Integrar `GOOGLE_API_KEY`

2. **Persistência**: Dados em memória (perdidos ao reiniciar)
   - **Solução futura**: PostgreSQL ou Redis

3. **Territórios fixos**: 2 por padrão
   - **Solução**: Mudar `CLUSTER_COUNT` em `config.py`

---

## 🚀 PRÓXIMOS UPGRADES (Roadmap)

- [ ] Geocoding automático via Google Maps
- [ ] Banco de dados (PostgreSQL)
- [ ] 3+ entregadores simultâneos
- [ ] Dashboard web para admin
- [ ] Visualização de rotas no mapa
- [ ] Histórico de entregas
- [ ] ML para prever tempo de entrega

---

**Documentação completa!** 📚  
Qualquer dúvida, consulte os arquivos:
- `QUICKSTART.md` - Setup rápido
- `CHECKLIST_HOJE.md` - Checklist passo a passo
- `SETUP_PRODUCAO.md` - Guia de produção
