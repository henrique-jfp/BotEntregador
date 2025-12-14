"""
🧪 TESTE RÁPIDO COM VOCÊ MESMO
Simula o fluxo completo sem precisar de outros entregadores
"""

print("""
╔════════════════════════════════════════════════════════════╗
║  🔥 TESTE RÁPIDO - Simulate o Bot Sozinho                 ║
╚════════════════════════════════════════════════════════════╝

📱 CENÁRIO: Você vai ser Admin + 2 Entregadores

🎯 SETUP RÁPIDO (faça isso primeiro):

1. ✅ Crie o bot com @BotFather
   - /newbot
   - Nome: Teste Entregador Bot
   - Username: testeMeuEntregadorBot (ou outro)
   - **COPIE O TOKEN**

2. ✅ Pegue seu ID
   - Fale com @userinfobot
   - **COPIE SEU ID**

3. ✅ Configure o .env
   Crie arquivo .env com:
   ```
   TELEGRAM_BOT_TOKEN=seu_token_aqui
   ADMIN_TELEGRAM_ID=seu_id_aqui
   ```

4. ✅ Configure entregadores FAKE em config.py
   Use SEU PRÓPRIO ID 3 vezes (você vai simular todos):
   ```python
   DELIVERY_PARTNERS: List[DeliveryPartner] = [
       DeliveryPartner(telegram_id=SEU_ID, name="Entregador 1", is_partner=True),
       DeliveryPartner(telegram_id=SEU_ID, name="Entregador 2", is_partner=False),
   ]
   ```

5. ✅ Instale dependências
   ```bash
   pip install python-telegram-bot python-dotenv
   ```

6. ✅ Rode o bot
   ```bash
   python main_multidelivery.py
   ```

═══════════════════════════════════════════════════════════════

🎬 FLUXO DE TESTE (no Telegram):

┌─ ADMIN (você) ─────────────────────────────────────────────┐
│ 1. Abra o bot no Telegram                                  │
│ 2. /start                                                   │
│ 3. "📦 Nova Sessão do Dia"                                 │
│ 4. Digite: "Rua Teste, 123"                                │
│ 5. Cole esses endereços (COPIE E COLE):                    │
│                                                             │
│    Av. Paulista, 1000 - Bela Vista, SP                    │
│    Rua Augusta, 500 - Consolação, SP                       │
│    Praça da Sé, 100 - Sé, SP                              │
│    Av. Faria Lima, 2000 - Pinheiros, SP                   │
│    Rua Oscar Freire, 300 - Jardins, SP                    │
│    Av. Rebouças, 1500 - Pinheiros, SP                     │
│                                                             │
│ 6. Bot responde: "✅ 6 pacotes adicionados"                │
│ 7. Digite: /fechar_rota                                    │
│ 8. Bot divide em 2 rotas automaticamente                   │
│ 9. Clique: "Atribuir ROTA_1" → Escolhe "Entregador 1"     │
│ 10. Clique: "Atribuir ROTA_2" → Escolhe "Entregador 2"    │
└─────────────────────────────────────────────────────────────┘

┌─ ENTREGADOR (você também) ─────────────────────────────────┐
│ 11. Você recebe 2 mensagens (uma pra cada rota)           │
│ 12. Clique: "🗺️ Minha Rota Hoje"                          │
│ 13. Clique: "✅ Marcar Entrega"                            │
│ 14. Selecione um pacote                                    │
│ 15. Repete até marcar todos                                │
└─────────────────────────────────────────────────────────────┘

┌─ ADMIN (você de novo) ─────────────────────────────────────┐
│ 16. Clique: "📊 Status Atual"                              │
│     → Vê progresso em tempo real                           │
│ 17. Clique: "💰 Relatório Financeiro"                      │
│     → Vê custos (Entregador 1 = R$0, Entregador 2 = R$X)  │
└─────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════

✅ VALIDAÇÕES:

• A IA dividiu em 2 territórios diferentes?
• As rotas estão otimizadas (começa do mais perto)?
• Conseguiu marcar entregas?
• Status atualiza em tempo real?
• Relatório financeiro calcula certo?

═══════════════════════════════════════════════════════════════

🔥 DEPOIS DO TESTE:

Se tudo funcionou, é só:

1. Pegar IDs REAIS dos entregadores
2. Atualizar config.py com IDs reais
3. Reiniciar bot
4. Usar com entregas de verdade!

═══════════════════════════════════════════════════════════════

⚠️  TROUBLESHOOTING:

Bot não responde?
→ python validate_setup.py

Erro ao iniciar?
→ Confere se .env tá certo
→ Confere se TOKEN é válido
→ pip install python-telegram-bot python-dotenv

Não recebe rota?
→ Confere se seu ID tá em config.py
→ Dá /start no bot antes de atribuir

═══════════════════════════════════════════════════════════════

📱 QUER TESTAR COM 2 TELEFONES?

Instale Telegram no celular + PC, use contas diferentes.
Ou use Telegram Web em aba anônima.

═══════════════════════════════════════════════════════════════

🚀 BOA SORTE NAS ENTREGAS! 

Qualquer dúvida, releia SETUP_PRODUCAO.md
""")
