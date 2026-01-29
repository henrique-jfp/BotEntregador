# 🚨 CONFIGURAÇÃO URGENTE - APIs Gratuitas

## ⚠️ PROBLEMA ATUAL

O bot está usando **apenas OpenStreetMap (OSM)** que é:
- ❌ Lento (1 req/segundo)
- ❌ Impreciso (~70% de acertos)
- ❌ Gera endereços errados

## ✅ SOLUÇÃO: Configurar LocationIQ (5 minutos)

### Passo 1: Criar Conta (2 minutos)
1. Acesse: https://locationiq.com/
2. Clique em **"Sign Up"**
3. Preencha: email + senha
4. ❌ **NÃO precisa de cartão!**
5. Confirme o email

### Passo 2: Pegar API Key (1 minuto)
1. Faça login em: https://my.locationiq.com/
2. No dashboard, copie o **"Access Token"**
3. Exemplo: `pk.abc123xyz456...`

### Passo 3: Configurar no Railway (2 minutos)
1. Vá em: https://railway.app/
2. Selecione seu projeto
3. Vá em **Variables**
4. Adicione:
   ```
   LOCATIONIQ_API_KEY=pk.xxxxxxxxxxxxx
   ```
5. Salve (Railway vai redeployar automaticamente)

## 📊 Resultado Esperado

| Métrica | Antes (OSM) | Depois (LocationIQ) |
|---------|-------------|---------------------|
| Velocidade | 1 req/s | 10 req/s |
| Precisão | ~70% | ~90% |
| Endereços corretos | Baixo | Alto |
| Tempo (100 end.) | 2 minutos | 10 segundos |

## 🔍 Como Verificar se Funcionou

Nos logs do Railway, você verá:
```
✅ Geocoded via LocationIQ: Rua X, 123 -> (-22.9468, -43.1850)
```

Se ver:
```
✅ Geocoded via OSM: ...
```
Significa que LocationIQ não está configurado ainda.

## 💡 Bonus: Geoapify (Opcional)

Para ter 8.000 req/dia no total:

1. Cadastre em: https://www.geoapify.com/
2. Copie a API Key
3. Adicione no Railway:
   ```
   GEOAPIFY_API_KEY=xxxxxxxxxx
   ```

## ❓ Dúvidas?

- Leia: [APIS_GRATUITAS_SEM_CARTAO.md](APIS_GRATUITAS_SEM_CARTAO.md)

**Configure agora para ter precisão de 90%!** 🎯
