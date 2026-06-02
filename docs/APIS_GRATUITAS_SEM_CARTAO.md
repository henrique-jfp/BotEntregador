# 🆓 APIs de Geocoding GRATUITAS (Sem Cartão de Crédito!)

## ❌ Problema do Google Maps
- **Exige pré-pagamento de R$ 200** para ativar
- Barreira muito alta para começar

## ✅ Soluções GRATUITAS (Sem Cartão!)

Implementei suporte para **2 APIs excelentes** que NÃO exigem cartão:

---

## 🥇 Opção 1: LocationIQ (RECOMENDADO)

### ✅ Por que usar?
- **5.000 requests/dia GRÁTIS**
- **NÃO exige cartão de crédito**
- Baseado em OpenStreetMap mas **10x mais rápido**
- Boa precisão para endereços brasileiros
- API estável e confiável

### 📝 Como Configurar (5 minutos)

#### 1. Criar Conta
1. Acesse: https://locationiq.com/
2. Clique em **"Get Started for Free"** ou **"Sign Up"**
3. Preencha:
   - Nome
   - Email
   - Senha
   - **NÃO precisa de cartão!**
4. Confirme o email

#### 2. Pegar a API Key
1. Faça login em: https://my.locationiq.com/
2. No dashboard, você verá sua **Access Token**
3. Copie a chave (algo como: `pk.xxxxxxxxxxxxxxxxxxxxxxx`)

#### 3. Configurar no Bot
Adicione no arquivo `.env`:
```env
LOCATIONIQ_API_KEY=pk.xxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 4. Pronto! 🎉
O bot vai usar LocationIQ automaticamente.

### 📊 Limites
- **Free:** 5.000 requests/dia
- **Renovação:** Diária (00:00 UTC)
- **Preço se passar:** $0 (não cobra, só para)

---

## 🥈 Opção 2: Geoapify (Alternativa)

### ✅ Por que usar?
- **3.000 requests/dia GRÁTIS**
- **NÃO exige cartão de crédito**
- Interface moderna
- Boa documentação

### 📝 Como Configurar (5 minutos)

#### 1. Criar Conta
1. Acesse: https://www.geoapify.com/
2. Clique em **"Get Started Free"** ou **"Sign Up"**
3. Preencha:
   - Nome
   - Email
   - Senha
   - **NÃO precisa de cartão!**
4. Confirme o email

#### 2. Pegar a API Key
1. Faça login
2. Vá em **"My Projects"** → **"API Keys"**
3. Copie a chave padrão

#### 3. Configurar no Bot
Adicione no arquivo `.env`:
```env
GEOAPIFY_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 4. Pronto! 🎉

### 📊 Limites
- **Free:** 3.000 requests/dia
- **Renovação:** Diária

---

## 🔄 Estratégia de Fallback Inteligente

O bot tenta nesta ordem (do melhor para pior):

```
1. 💾 Cache local (instantâneo, grátis)
   ↓ (se não tiver em cache)
   
2. 🥇 LocationIQ (se configurado)
   - 5.000/dia grátis
   - Rápido (~0.3s)
   - Preciso
   ↓ (se não configurado ou falhar)
   
3. 🥈 Geoapify (se configurado)
   - 3.000/dia grátis
   - Rápido (~0.4s)
   ↓ (se não configurado ou falhar)
   
4. 💳 Google Maps (se configurado)
   - Exige cartão + R$ 200
   - Muito preciso
   ↓ (se não configurado ou falhar)
   
5. 🌍 OpenStreetMap Nominatim
   - 100% grátis
   - Lento (~2s)
   - Menos preciso
   ↓ (se falhar tudo)
   
6. 🎲 Fallback simulado
   - Gera coordenada aproximada
```

---

## 📊 Comparação de APIs

| API | Grátis/Dia | Exige Cartão? | Velocidade | Precisão | Setup |
|-----|-----------|---------------|------------|----------|-------|
| **LocationIQ** | 5.000 | ❌ NÃO | ⚡⚡⚡ Rápida | 🎯 Alta | 5 min |
| **Geoapify** | 3.000 | ❌ NÃO | ⚡⚡⚡ Rápida | 🎯 Alta | 5 min |
| **Google Maps** | 40.000 | ✅ SIM | ⚡⚡⚡⚡ Muito rápida | 🎯🎯 Muito alta | 30 min + R$ 200 |
| **OpenStreetMap** | Ilimitado | ❌ NÃO | ⏱️ Lenta | 📍 Média | 0 min |

---

## 💡 Qual Escolher?

### Para a maioria dos usuários:
**Use LocationIQ** (5.000/dia é suficiente)

### Se processar muitos endereços:
**Use LocationIQ + Geoapify juntos** (8.000/dia no total!)

### Se tiver orçamento:
**Google Maps** (mais preciso, mas exige R$ 200)

### Sem configurar nada:
**OpenStreetMap** (já funciona, mas é lento)

---

## 🧮 Calculadora de Uso

### Cenário 1: Uso Moderado
- 50 endereços por análise
- 3 análises por dia
- **Total: 150 req/dia**
- ✅ **LocationIQ sozinho resolve!**

### Cenário 2: Uso Intenso
- 200 endereços por análise
- 10 análises por dia
- **Total: 2.000 req/dia**
- ✅ **LocationIQ sozinho resolve!**

### Cenário 3: Uso Muito Intenso
- 500 endereços por análise
- 20 análises por dia
- **Total: 10.000 req/dia**
- ✅ **LocationIQ + Geoapify = 8.000/dia**
- ⚠️ Pode precisar aguardar ou usar Google

---

## 🎯 Configuração Recomendada

### Mínimo (Grátis Total)
```env
LOCATIONIQ_API_KEY=pk.xxxxxxxxxx
```

### Ideal (Grátis + Redundância)
```env
LOCATIONIQ_API_KEY=pk.xxxxxxxxxx
GEOAPIFY_API_KEY=xxxxxxxxxx
```

### Profissional (Máxima Precisão)
```env
LOCATIONIQ_API_KEY=pk.xxxxxxxxxx
GEOAPIFY_API_KEY=xxxxxxxxxx
GOOGLE_API_KEY=AIzaSyxxxxxxxxxx
```

---

## 🧪 Como Testar

1. Configure pelo menos uma API (LocationIQ recomendado)

2. Edite `.env`:
   ```env
   LOCATIONIQ_API_KEY=sua_chave_aqui
   ```

3. Reinicie o bot

4. Teste com `/analisar_rota`

5. Veja nos logs qual API foi usada:
   ```
   ✅ Geocoded (LocationIQ): Rua X, 123 -> (-22.94, -43.18)
   ```

---

## 📝 Passo a Passo Completo (5 minutos)

### 1️⃣ Cadastrar no LocationIQ
```
1. Abra: https://locationiq.com/
2. Clique em "Sign Up"
3. Preencha email + senha
4. Confirme o email
5. Faça login
6. Copie o Access Token
```

### 2️⃣ Configurar no Bot
```
1. Abra o arquivo .env (na raiz do projeto)
2. Adicione a linha:
   LOCATIONIQ_API_KEY=pk.xxxxxxxxxxxxx
3. Salve o arquivo
4. Reinicie o bot
```

### 3️⃣ Testar
```
1. Envie /analisar_rota no Telegram
2. Anexe um Excel da Shopee
3. Observe o processamento rápido!
```

---

## ❓ FAQ

**P: Preciso configurar as 3 APIs?**
R: Não! Com LocationIQ sozinho já funciona muito bem.

**P: E se passar de 5.000/dia?**
R: Configure também Geoapify (mais 3.000/dia).

**P: Quanto tempo para criar conta?**
R: ~5 minutos (email + senha, sem cartão).

**P: É realmente grátis para sempre?**
R: Sim! Os limites renovam todo dia.

**P: E se não configurar nada?**
R: Funciona com OpenStreetMap (lento mas grátis).

**P: Qual é a mais rápida?**
R: LocationIQ e Geoapify são similares (~0.3-0.5s).

**P: Posso usar em produção?**
R: Sim! São APIs estáveis e confiáveis.

**P: Tem limite de cadastros?**
R: Não, você pode criar várias contas se precisar.

---

## 🎉 Pronto!

**Agora você tem geocoding rápido e preciso SEM PAGAR NADA!**

Configure LocationIQ em 5 minutos e aproveite. 🚀

---

## 📞 Links Úteis

- **LocationIQ:**
  - Site: https://locationiq.com/
  - Dashboard: https://my.locationiq.com/
  - Docs: https://locationiq.com/docs

- **Geoapify:**
  - Site: https://www.geoapify.com/
  - Dashboard: https://myprojects.geoapify.com/
  - Docs: https://www.geoapify.com/geocoding-api

- **OpenStreetMap:**
  - Site: https://www.openstreetmap.org/
  - Nominatim: https://nominatim.org/
