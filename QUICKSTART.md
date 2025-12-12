# 🚀 GUIA DE USO RÁPIDO

## ⚡ Setup em 3 Minutos

### 1. Instale

```bash
pip install -r requirements.txt
```

### 2. Configure

Copie `.env.example` para `.env` e preencha:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEFxxxxx  # Crie com @BotFather
ADMIN_TELEGRAM_ID=123456789              # Seu ID (fale com @userinfobot)
GOOGLE_API_KEY=AIzaSyXXXXXXXXXX         # (Opcional, pra geocoding real)
```

### 3. Cadastre Entregadores

Edite `bot_multidelivery/config.py`:

```python
DELIVERY_PARTNERS: List[DeliveryPartner] = [
    DeliveryPartner(telegram_id=111111111, name="João (Sócio)", is_partner=True),
    DeliveryPartner(telegram_id=222222222, name="Maria (Sócio)", is_partner=True),
    DeliveryPartner(telegram_id=333333333, name="Carlos", is_partner=False),
]
```

**Como pegar telegram_id**: Fale com [@userinfobot](https://t.me/userinfobot)

### 4. Rode

```bash
python main_multidelivery.py
```

---

## 📱 Fluxo Completo (Passo a Passo)

### 👔 ADMIN (Você)

1. Abra o bot no Telegram → `/start`
2. Clique: **"📦 Nova Sessão do Dia"**
3. Digite o endereço da BASE:
   ```
   Rua das Flores, 123 - São Paulo
   ```
4. Cole o primeiro romaneio (endereços, um por linha):
   ```
   Av. Paulista, 1000
   Rua Augusta, 500
   Praça da Sé, 100
   ```
5. ✅ Bot confirma: "3 pacotes adicionados"
6. Cole mais romaneios se quiser (repete passo 4)
7. Quando terminar: `/fechar_rota`
8. 🤖 Bot divide em 2 territórios automaticamente
9. Atribua cada rota:
   - Clique: **"Atribuir ROTA_1"** → Escolhe entregador
   - Clique: **"Atribuir ROTA_2"** → Escolhe entregador
10. ✅ Entregadores recebem rotas nos chats privados

### 🚴 ENTREGADOR

1. Recebe mensagem com rota completa:
   ```
   🗺️ SUA ROTA - ROTA_1
   
   📍 Base: Rua das Flores, 123
   📦 Total: 7 pacotes
   
   📋 Ordem de entrega:
   
   1. Praça da Sé, 100
      🆔 PKG002
   
   2. Av. Ipiranga, 200
      🆔 PKG007
   ...
   ```
2. Clique: **"🗺️ Minha Rota Hoje"** (revê rota completa)
3. Ao entregar: **"✅ Marcar Entrega"** → Seleciona pacote
4. Progresso atualiza automaticamente

---

## 🎯 Comandos Principais

### Admin
- `/start` - Menu principal
- `/fechar_rota` - Divide rotas após adicionar romaneios
- **"📊 Status Atual"** - Progresso em tempo real
- **"💰 Relatório Financeiro"** - Custos do dia

### Entregador
- `/start` - Menu
- **"🗺️ Minha Rota Hoje"** - Ver rota
- **"✅ Marcar Entrega"** - Concluir pacote

---

## 💰 Sistema de Custos

- **Sócios** (`is_partner=True`): R$ 0/pacote
- **Colaboradores** (`is_partner=False`): R$ 1/pacote

Exemplo:
```
João (Sócio) entregou 10 pacotes → Custo: R$ 0,00
Carlos entregou 8 pacotes → Custo: R$ 8,00
```

---

## 🧪 Testar Sem Bot

Quer ver a divisão territorial funcionando sem rodar o bot?

```bash
python test_clustering.py
```

Mostra como 10 endereços de São Paulo são divididos em 2 territórios otimizados.

---

## 🔥 FAQ

**Q: Posso adicionar mais de 2 entregadores?**  
A: Sim! Edite `BotConfig.CLUSTER_COUNT = 3` em `config.py` e adicione mais entregadores.

**Q: Geocoding não tá funcionando**  
A: Por padrão usa coordenadas simuladas. Pra usar Google Geocoding real, preencha `GOOGLE_API_KEY` e descomente os TODOs no `bot.py`.

**Q: Como adicionar mais entregadores depois?**  
A: Edite `config.py` e reinicie o bot. Ou implemente CRUD de entregadores (próxima feature).

**Q: Dados persistem?**  
A: Não. Estado atual fica em memória. Pra produção, integre com Redis/PostgreSQL.

---

## 🚀 Próximos Upgrades

- [ ] Geocoding automático via Google Maps API
- [ ] Banco de dados (PostgreSQL)
- [ ] Dashboard web pro admin
- [ ] Visualização de rotas no mapa
- [ ] Notificações push
- [ ] Histórico de entregas

---

**Mind Blown Level**: 9/10 🤯

Sistema 100% funcional. Divida territórios. Manda pra galera. GO! 🔥
