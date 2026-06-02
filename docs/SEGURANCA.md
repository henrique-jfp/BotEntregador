# Guia de Segurança da API

Este projeto agora possui proteção básica contra uso não autorizado da API.

## 1. Configuração do Backend

No seu arquivo `.env`, adicione a seguinte variável:

```env
API_SECRET_KEY=SuaChaveSecretaMuitoDificil123!
```

> **Nota:** Se você não configurar isso, o sistema usará uma chave padrão insegura e avisará no console.

## 2. Como usar no Frontend (WebApp/React)

Todas as requisições `fetch` ou `axios` para o backend (`/api/...`) devem incluir o Header:

```javascript
const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': 'SuaChaveSecretaMuitoDificil123!' // EM PRODUÇÃO: Use process.env.VITE_API_KEY
};

fetch('/api/sessions/create', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(...)
});
```

## 3. Rotas Públicas

As seguintes rotas **não** precisam de autenticação:
- `/api/public/maps/{filename}`: Para abrir mapas gerados no navegador.
- `/assets/*`: Arquivos do frontend React.

## 4. Testando com CURL ou Postman

```bash
curl -X POST http://localhost:8080/api/sessions/create \
  -H "X-API-Key: SuaChaveSecretaMuitoDificil123!" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345}'
```
