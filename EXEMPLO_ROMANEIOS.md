# Exemplos de Romaneios para Testar

## Romaneio 1 (Centro de SP)
```
Praça da Sé, 100 - Centro, São Paulo
Rua Direita, 50 - Centro, São Paulo
Viaduto do Chá, 15 - Centro, São Paulo
Rua XV de Novembro, 200 - Centro, São Paulo
```

## Romaneio 2 (Zona Oeste)
```
Av. Paulista, 1000 - Bela Vista, São Paulo
Rua Augusta, 500 - Consolação, São Paulo
Rua Haddock Lobo, 600 - Jardins, São Paulo
Rua Oscar Freire, 300 - Jardins, São Paulo
Av. Faria Lima, 2000 - Pinheiros, São Paulo
```

## Romaneio 3 (Zona Sul)
```
Av. Ibirapuera, 3000 - Moema, São Paulo
Rua dos Pinheiros, 800 - Pinheiros, São Paulo
Av. Brigadeiro Luís Antônio, 1000 - Bela Vista, São Paulo
```

---

## Como Usar no Bot

1. `/start`
2. "📦 Nova Sessão do Dia"
3. Define base: `Rua da Mooca, 1000 - Mooca, São Paulo`
4. Cola **Romaneio 1** (os 4 endereços)
5. Bot confirma: ✅ 4 pacotes adicionados
6. Cola **Romaneio 2** (os 5 endereços)
7. Bot confirma: ✅ 5 pacotes adicionados (Total: 9)
8. Cola **Romaneio 3** (os 3 endereços)
9. Bot confirma: ✅ 3 pacotes adicionados (Total: 12)
10. `/fechar_rota`
11. 🤖 Divide em 2 rotas automaticamente
12. Atribui aos entregadores

---

## Resultado Esperado

**ROTA_1** (~6 pacotes): Zona Centro/Leste  
**ROTA_2** (~6 pacotes): Zona Oeste/Sul

Cada rota vem com ordem otimizada pra minimizar km rodados! 🚀
