#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ANÁLISE DETALHADA DO FLUXO DE ENVIO DO MAPA PARA O ENTREGADOR
Traçando cada passo para garantir que o link correto está sendo enviado
"""

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                  ANÁLISE DO FLUXO DE NOTIFICAÇÃO                           ║
║              (Para onde vai o link quando uma rota é atribuída?)           ║
╚════════════════════════════════════════════════════════════════════════════╝

📍 PASSO 1: Admin atribui rota ao entregador
   Arquivo: bot_multidelivery/routers/routes.py linha 308
   Endpoint: POST /routes/assign-to-deliverers
   
   request.assignments = {
       "rota_001": 123456789,  ← telegram_id do entregador
       "rota_002": 987654321
   }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 2: Chamada async para notificação
   Arquivo: bot_multidelivery/routers/routes.py linha 319
   
   asyncio.create_task(send_route_to_telegram(tg_id, session, route))
   
   ✅ Passa:
      - tg_id: ID do Telegram (ex: 123456789)
      - session: Sessão com dados
      - route: Rota com pontos otimizados

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 3: Construção da URL do WebApp
   Arquivo: bot_multidelivery/routers/routes.py linha 386
   
   webapp_url = f"{BotConfig.WEBAPP_URL}?user_id={tg_id}&tab=myroute"
   
   Exemplo:
   https://seu-app-railway.app?user_id=123456789&tab=myroute
   
   ✅ CORRETO! Usando tab=myroute (vista do entregador)
   ❌ NÃO está tab=routes (vista do admin)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 4: Chamada da função de notificação
   Arquivo: bot_multidelivery/routers/routes.py linha 391-400
   
   success = await notify_route_assigned(
       telegram_id=tg_id,
       route_color=route.color,
       total_packages=route.total_packages,
       distance_km=route.total_distance_km or 0,
       addresses=addresses,
       webapp_url=webapp_url,  ← URL COM tab=myroute ✅
       coordinates=coordinates if len(coordinates) >= 2 else None
   )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 5: Função de conveniência (wrapper)
   Arquivo: bot_multidelivery/services/telegram_notifier.py linha 380
   
   async def notify_route_assigned(..., webapp_url, coordinates):
       return await notifier.send_route_notification(...)
   
   Passa tudo para o método REAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 6: Método que REALMENTE envia a mensagem
   Arquivo: bot_multidelivery/services/telegram_notifier.py linha 290
   
   async def send_route_notification(self, chat_id, ..., webapp_url, coordinates):
       
       # Criar botão com o WebApp
       reply_markup = {
           "inline_keyboard": [[
               {
                   "text": "📱 Abrir Mapa da Rota",
                   "web_app": {"url": webapp_url}  ← webapp_url aqui! ✅
               }
           ]]
       }
       
       # Tentar enviar mapa estático (imagem)
       if coordinates and len(coordinates) >= 2:
           map_url = await self.generate_static_map_url(...)
           
           # Enviar FOTO com botão
           await self.send_photo(
               chat_id=chat_id,
               photo_url=map_url,
               caption=message,
               reply_markup=reply_markup  ← INCLUI O BOTÃO ✅
           )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 PASSO 7: O que o entregador recebe no Telegram
   
   📲 Mensagem com FOTO do mapa (imagem estática)
   
   Caption:
   "🚀 NOVA ROTA DISPONÍVEL!
    
    🔴 VERMELHO
    Pacotes: 45 entregas
    Distância: 5.5 km
    
    📍 Primeiras Paradas:
    1. Rua X, 123
    2. Rua Y, 456
    ..."
   
   Botão abaixo da foto:
   ┌─────────────────────────┐
   │ 📱 Abrir Mapa da Rota   │  ← Clicando aqui abre:
   └─────────────────────────┘     https://app.railway.app?user_id=123456789&tab=myroute
                                    ↓
                                    WebApp abre com a ROTA DO ENTREGADOR (não admin!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ANÁLISE FINAL:

1. webapp_url está CORRETO (tab=myroute)
2. webapp_url é passado corretamente pelos 5 passos
3. webapp_url é incluído no reply_markup
4. O botão no Telegram aponta para webapp_url ✅

❓ POSSÍVEIS PROBLEMAS A VERIFICAR:

1. O WebApp frontend está renderizando tab=myroute CORRETAMENTE?
   Arquivo: webapp/src/RouteAnalysisView.jsx ou webapp/src/App.jsx
   → Verificar se componente "myroute" existe e está correto

2. O user_id está sendo passado e usado?
   → Verificar se frontend consegue ler user_id da URL

3. A rota está sendo CARREGADA com base no user_id?
   → Verificar se backend endpoint /api/routes/{user_id} funciona

4. O entregador está vendo o MAPA ou mensagem de erro?
   → Verificar se há logs de erro no frontend/backend

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 PRÓXIMOS PASSOS DE DEBUG:

1. Verificar RouteAnalysisView.jsx para ver se renderiza tab=myroute
2. Verificar se API /api/routes/{user_id} existe
3. Verificar se frontend consegue ler parametros da URL
4. Testar manualmente abrindo: app.railway.app?user_id=123456789&tab=myroute

""")
