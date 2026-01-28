# 🔐 VARIÁVEIS DE AMBIENTE - RAILWAY

## ✅ **OBRIGATÓRIAS** (Bot NÃO funciona sem)

### **1. TELEGRAM_BOT_TOKEN**
```
Descrição: Token do bot do Telegram
Obrigatório: ✅ SIM
Exemplo: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Como obter:**
1. Abra Telegram
2. Fale com [@BotFather](https://t.me/BotFather)
3. Digite `/mybots`
4. Selecione seu bot (ou crie com `/newbot`)
5. Clique em **"API Token"**
6. Copie o token

---

### **2. ADMIN_TELEGRAM_ID**
```
Descrição: Seu ID numérico no Telegram (administrador)
Obrigatório: ✅ SIM
Exemplo: 123456789
```

**Como obter:**
1. Abra Telegram
2. Fale com [@userinfobot](https://t.me/userinfobot)
3. Envie qualquer mensagem
4. Bot retorna seu ID numérico
5. Copie apenas os números

---

### **3. PORT**
```
Descrição: Porta para o servidor HTTP (Railway precisa)
Obrigatório: ✅ SIM (para Railway)
Valor: 8080
```

**Configuração:**
- Railway precisa que apps exponham uma porta HTTP
- Seu bot usa isso para "health check"
- **Sempre use: 8080**

---

## ⚠️ **OPCIONAIS** (Bot funciona sem, mas com limitações)

### **4. GOOGLE_API_KEY**
```
Descrição: Chave Google Maps/Geocoding API
Obrigatório: ❌ OPCIONAL
Exemplo: AIzaSyXXXXXXXXXXXXXXXXXXXXXX
```

**Para que serve:**
- Geocoding automático de endereços
- Converter "Rua X, 123" em coordenadas
- Melhor precisão nos mapas

**Se NÃO configurar:**
- Bot usa coordenadas simuladas (ainda funciona)
- Menos precisão nas rotas
- **Recomendo adicionar depois**

**Como obter:**
1. Acesse: https://console.cloud.google.com
2. Crie projeto (se não tem)
3. **APIs & Services** → **Library**
4. Busque "Geocoding API"
5. Clique **"Enable"**
6. **Credentials** → **Create Credentials** → **API Key**
7. Copie a chave

---

## 📋 **RESUMO: O QUE COLOCAR NO RAILWAY**

### **MÍNIMO PARA FUNCIONAR:**

```env
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
ADMIN_TELEGRAM_ID=seu_id_numerico
PORT=8080
```

**Com isso o bot:**
- ✅ Fica online 24/7
- ✅ Responde comandos
- ✅ Gerencia entregas
- ✅ Divide rotas
- ✅ Tudo funciona!

---

### **CONFIGURAÇÃO COMPLETA (RECOMENDADA):**

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_TELEGRAM_ID=123456789
PORT=8080
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXX
```

**Com isso você ganha:**
- ✅ Tudo do mínimo
- ✅ Geocoding preciso
- ✅ Mapas mais exatos
- ✅ Melhor otimização de rotas

---

## 🚀 **PASSO A PASSO NO RAILWAY**

1. **Acesse seu projeto no Railway**
2. Clique na aba **"Variables"**
3. Clique em **"+ New Variable"**
4. Adicione uma por uma:

**Variável 1:**
```
Name: TELEGRAM_BOT_TOKEN
Value: [cole seu token do BotFather]
```

**Variável 2:**
```
Name: ADMIN_TELEGRAM_ID
Value: [cole seu ID do userinfobot]
```

**Variável 3:**
```
Name: PORT
Value: 8080
```

**Variável 4 (opcional):**
```
Name: GOOGLE_API_KEY
Value: [cole sua chave do Google Cloud]
```

5. Clique em **"Save"** ou simplesmente clique fora
6. Railway vai **re-deployar automaticamente**
7. Aguarde 1-2 minutos
8. Bot está online! 🎉

---

## ✅ **VERIFICAÇÃO**

### **Como saber se está funcionando:**

1. **Vá na aba "Logs" do Railway**
2. Deve aparecer:
   ```
   🔥 Iniciando Bot Multi-Entregador...
   🌍 Dummy server rodando na porta 8080
   ✅ Token presente: 123456789...
   ✅ Admin ID configurado: 123456789
   🚀 Bot iniciado! (Tentativa 1/5)
   ```

3. **Teste no Telegram:**
   - Envie `/start` pro bot
   - Deve responder em menos de 1 segundo

---

## ❌ **ERROS COMUNS**

### **Erro: "TELEGRAM_BOT_TOKEN não configurado"**
**Solução:** Adicione a variável `TELEGRAM_BOT_TOKEN` no Railway

### **Erro: "Bot parou após múltiplas falhas"**
**Solução:** Token inválido. Verifique no BotFather

### **Erro: "ADMIN_TELEGRAM_ID não configurado"**
**Solução:** Adicione a variável `ADMIN_TELEGRAM_ID` (só números!)

### **Erro: "Port already in use"**
**Solução:** Use `PORT=8080` (Railway gerencia automaticamente)

---

## 🔒 **SEGURANÇA**

### **NUNCA:**
- ❌ Commite variáveis no código
- ❌ Compartilhe seu token
- ❌ Deixe `.env` público no GitHub

### **SEMPRE:**
- ✅ Use variáveis de ambiente (Railway)
- ✅ Mantenha tokens secretos
- ✅ Adicione `.env` no `.gitignore`

---

## 📊 **VARIÁVEIS FUTURAS (NÃO PRECISA AGORA)**

Esses serviços o bot suporta, mas você **não precisa configurar agora**:

### **Banco Inter (Fechamento automático):**
```env
BANK_INTER_CLIENT_ID=...
BANK_INTER_CLIENT_SECRET=...
BANK_INTER_CERT_PATH=...
BANK_INTER_KEY_PATH=...
BANK_INTER_CONTA=...
```
**Use quando:** Quiser integração bancária (avançado)

### **Google Vision (OCR de PDFs):**
```env
GOOGLE_VISION_CREDENTIALS_JSON_BASE64=...
```
**Use quando:** Precisar ler PDFs escaneados (legado, não precisa mais)

---

## 🎯 **CONCLUSÃO**

### **PARA COMEÇAR, VOCÊ PRECISA DE 3 VARIÁVEIS:**

1. ✅ `TELEGRAM_BOT_TOKEN`
2. ✅ `ADMIN_TELEGRAM_ID`
3. ✅ `PORT=8080`

### **Total de tempo:** 5 minutos

**Pronto! Bot online 24/7 no Railway! 🚀**

---

## 🆘 **PRECISA DE AJUDA?**

- Token não funciona? Gere novo no BotFather
- ID não aceita? Use só números (sem espaços)
- Logs com erro? Me mostra que te ajudo!

**Qualquer dúvida, só chamar!** 🔥
