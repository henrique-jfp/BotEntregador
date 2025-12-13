"""
🚀 BOT TELEGRAM - Handler principal
Fluxo completo de admin + entregadores
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import datetime
from .config import BotConfig, DeliveryPartner
from .session import session_manager, Romaneio, Route
from .clustering import DeliveryPoint, TerritoryDivider
from .parsers import parse_csv_romaneio, parse_pdf_romaneio, parse_text_romaneio
from .services import deliverer_service, geocoding_service, genetic_optimizer, gamification_service, predictor, dashboard_ws, scooter_optimizer
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== ADMIN HANDLERS ====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        keyboard = [
            [KeyboardButton("📦 Nova Sessão do Dia")],
            [KeyboardButton("📊 Status Atual")],
            [KeyboardButton("💰 Relatório Financeiro")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🔥 <b>BOT ADMIN - Multi-Entregador</b>\n\n"
            "Bem-vindo, chefe! Escolha uma opção:\n\n"
            "💡 Digite /help para ver todos os comandos",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        # Entregador
        partner = BotConfig.get_partner_by_id(user_id)
        if partner:
            keyboard = [[KeyboardButton("🗺️ Minha Rota Hoje")], [KeyboardButton("✅ Marcar Entrega")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f"👋 Olá, <b>{partner.name}</b>!\n\n"
                "Você receberá sua rota quando o admin distribuir as entregas.\n\n"
                "💡 Digite /help para ver comandos disponíveis",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Você não está cadastrado como entregador.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Ajuda contextual"""
    user_id = update.effective_user.id
    
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        # Help para ADMIN
        help_text = """
<b>CENTRAL DE AJUDA - ADMINISTRADOR</b>

<b>=== COMANDOS PRINCIPAIS ===</b>

/start - Menu principal do bot
/help - Esta mensagem de ajuda
/add_entregador &lt;telegram_id&gt; &lt;nome&gt; [socio] - Cadastra entregador
/entregadores - Lista todos os entregadores
/ranking - Ranking de gamificacao
/prever &lt;origem&gt; | &lt;destino&gt; [prioridade] - Previsao de tempo IA
/distribuir &lt;arquivo.xlsx&gt; &lt;num_entregadores&gt; - Divide romaneio inteligente

<b>=== FLUXO COMPLETO - PASSO A PASSO ===</b>

<b>1. CADASTRAR ENTREGADORES (uma vez)</b>
   /add_entregador 123456789 "Joao Silva" socio
   /add_entregador 987654321 "Maria Santos" colaborador
   
   Diferenca:
   - Socio: Nao paga por pacote (is_partner=true)
   - Colaborador: R$ 1,00 por pacote entregue

<b>2. RECEBER ROMANEIO DA SHOPEE</b>
   Baixe o arquivo Excel do portal Shopee
   Formato: "DD-MM-YYYY Nome.xlsx"
   Contem: tracking, endereco, lat/lon, stop groups

<b>3. DISTRIBUIR ROTA AUTOMATICAMENTE</b>
   /distribuir "05-11-2025 Henrique.xlsx" 3
   
   O que acontece:
   - Le 29 entregas do Excel
   - Agrupa por STOP (mesmo predio)
   - Divide geograficamente (K-means clustering)
   - Otimiza rota de cada entregador (scooter mode)
   - Envia mapa interativo HTML pro chat de cada um
   
   Cada entregador recebe:
   - Resumo: pacotes, paradas, distancia, tempo
   - Arquivo HTML com mapa Leaflet.js
   - Pins clicaveis com Google Maps deeplink
   - Botoes: Entregue / Insucesso / Transferir

<b>4. MONITORAR EM TEMPO REAL</b>
   Dashboard WebSocket: http://localhost:8765/dashboard
   
   Veja:
   - Total de entregas / Entregues / Taxa sucesso
   - Tempo medio por entrega
   - Ranking ao vivo
   - Lista de pacotes com status

<b>5. ANALISAR DESEMPENHO</b>
   /ranking - Gamificacao com conquistas
   /entregadores - Status de cada um
   
   Status Atual (botao):
   - Progresso por entregador
   - Percentual de conclusao
   - Pacotes pendentes

<b>6. RELATORIO FINANCEIRO</b>
   Relatorio Financeiro (botao):
   - Custos por entregador
   - Socios: R$ 0
   - Colaboradores: R$ 1/pacote
   - Total do dia

<b>=== FORMATOS SUPORTADOS ===</b>

<b>Excel Shopee (RECOMENDADO):</b>
Colunas: AT ID, Sequence, Stop, SPX TN, Destination Address, 
         Bairro, City, Zipcode, Latitude, Longitude
Vantagem: Lat/lon ja vem pronto (zero geocoding!)

<b>CSV Generico:</b>
tracking,endereco,lat,lon,prioridade
BR123,Rua X 123,-22.9,-43.1,alta

<b>Texto (legado):</b>
Cole enderecos um por linha
Aceita numeracao (1., 2.) e emojis

<b>PDF (legado):</b>
Anexe documento
OCR automatico se escaneado

<b>=== PREVISAO DE TEMPO IA ===</b>

/prever Botafogo | Copacabana alta

Considera:
- Distancia em linha reta (scooter)
- Horario (rush hour 7-9h, 17-19h)
- Trafego estimado
- Prioridade do pacote
- Historico de entregas

Modo Scooter vantagens:
- Pode usar contramao e calcadas
- Atalhos nao disponiveis para carros
- Menos afetado por trafego
- Mais rapido em distancias curtas

<b>=== ALGORITMO DE OTIMIZACAO ===</b>

<b>Stop Clustering:</b>
29 entregas -> 7 stops (4.1x eficiencia)
Agrupa multiplas entregas no mesmo predio

<b>K-means Geografico:</b>
Divide stops entre entregadores
Minimiza distancia total
Balanceia carga de trabalho

<b>Scooter Optimizer:</b>
Usa distancia euclidiana (linha reta)
Algoritmo guloso: sempre mais proximo
79% economia vs rota Shopee original

<b>=== KEYS NECESSARIAS ===</b>

.env file:
TELEGRAM_TOKEN=seu_token_aqui
ADMIN_TELEGRAM_ID=seu_id_numerico
GOOGLE_CLOUD_CREDENTIALS=caminho/para/credentials.json
GEMINI_API_KEY=sua_key_gemini (opcional)

<b>=== SUPORTE ===</b>

Problemas? Contate o desenvolvedor
GitHub: github.com/seu-repo
Versao: 20/10 - Scooter Mode + Mapa Interativo
"""
    else:
        # Help para ENTREGADOR
        partner = BotConfig.get_partner_by_id(user_id)
        if not partner:
            await update.message.reply_text("❌ Você não está cadastrado como entregador.")
            return
        
        help_text = f"""
<b>CENTRAL DE AJUDA - ENTREGADOR</b>

Ola, <b>{partner.name}</b>!

<b>=== COMANDOS ===</b>

/start - Menu principal
/help - Esta mensagem de ajuda

<b>=== COMO FUNCIONA - PASSO A PASSO ===</b>

<b>1. RECEBER ROTA DO DIA</b>
   O admin vai enviar sua rota otimizada:
   
   Voce recebe:
   - Resumo: X pacotes, Y paradas, Z minutos
   - Arquivo HTML: rota_seu_nome.html
   - Distancia total e atalhos detectados
   - Ponto inicial e final

<b>2. ABRIR MAPA INTERATIVO</b>
   Baixe o arquivo HTML enviado
   Abra no navegador (Chrome/Safari/Firefox)
   
   O mapa mostra:
   - Pins numerados (ordem otimizada)
   - Linha conectando os pontos
   - Sua localizacao atual
   - Header com progresso (X de Y paradas)

<b>3. NAVEGAR ENTRE PARADAS</b>
   Click no pin da proxima parada
   
   Card mostra:
   - Numero da parada
   - Endereco completo
   - Quantidade de pacotes naquele local
   - Status (atual/pendente/entregue)
   
   Botao "Abrir no Google Maps":
   - Abre navegacao GPS automatica
   - Te leva ate o endereco exato

<b>4. MARCAR STATUS DA ENTREGA</b>
   Depois de entregar:
   
   [Entregue] - Entrega bem sucedida
   - Marca pin como laranja (concluido)
   - Atualiza contador no header
   - Notifica o admin
   
   [Insucesso] - Nao conseguiu entregar
   - Marca pin como vermelho (falhou)
   - Registra motivo (destinatario ausente, etc)
   - Admin pode redistribuir
   
   [Transferir] - Transferir para outro entregador
   - Solicita transferencia ao admin
   - Util se pacote pesado demais
   - Ou se saiu da sua rota

<b>5. VISUALIZAR PROGRESSO</b>
   Header do mapa atualiza em tempo real:
   "3 de 7 paradas | 14 pacotes"
   
   Cores dos pins:
   - Verde: Parada atual
   - Roxo: Pendente (ainda nao visitou)
   - Laranja: Entregue (completo)
   - Vermelho: Insucesso (falhou)

<b>=== STOPS (GRUPOS DE ENTREGAS) ===</b>

1 STOP = 1 ENDERECO com multiplas entregas

Exemplo: Predio X, Apto 201, 603, 903
= 3 entregas no mesmo stop

Vantagem:
- Faz todas de uma vez
- Economiza tempo de deslocamento
- Maior eficiencia

<b>=== MODO SCOOTER - DIFERENCIAIS ===</b>

Seu algoritmo e otimizado para scooter eletrica:

Pode fazer:
- Contramao (quando seguro)
- Calcadas (trafego lento)
- Atalhos entre predios
- Vielas e becos

Por isso a rota e DIFERENTE da Shopee!
Economia: ate 79% menos distancia

<b>=== PAGAMENTO ===</b>

{'Voce e <b>SOCIO</b>\nNao paga por pacote entregue\nParticipa dos lucros mensais' if partner.is_partner else 'Voce e <b>COLABORADOR</b>\nR$ 1,00 por pacote entregue\nPagamento no final do dia'}

<b>=== DICAS PRO ===</b>

1. Siga a ordem sugerida
   - IA ja otimizou pra voce
   - Economiza tempo e bateria
   
2. Marque logo apos entregar
   - Admin acompanha em tempo real
   - Evita confusao no final do dia
   
3. Use o Google Maps deeplink
   - Mais preciso que endereco digitado
   - Ja vem com lat/lon exata
   
4. Agrupe entregas do mesmo stop
   - Faca todas antes de sair do predio
   - Evita voltar no mesmo lugar
   
5. Consulte o mapa sempre que precisar
   - Arquivo HTML funciona offline
   - Pode abrir quantas vezes quiser

<b>=== SUPORTE ===</b>

Problemas com:
- Mapa nao abre: Use Chrome/Firefox atualizado
- Google Maps nao funciona: Verifique GPS do celular
- Botoes nao respondem: Recarregue pagina (F5)

Duvidas? Fale com o admin!

Boas entregas!
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de mensagens de texto"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Admin flow
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        await handle_admin_message(update, context, text)
    else:
        # Deliverer flow
        await handle_deliverer_message(update, context, text)


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Fluxo do admin"""
    user_id = update.effective_user.id
    state = session_manager.get_admin_state(user_id)
    
    if text == "📦 Nova Sessão do Dia":
        # Inicia nova sessão
        today = datetime.now().strftime("%Y-%m-%d")
        session_manager.start_new_session(today)
        session_manager.set_admin_state(user_id, "awaiting_base_address")
        
        await update.message.reply_text(
            "🏠 <b>Defina o endereço da BASE</b>\n\n"
            "Onde o carro estará estacionado hoje?\n"
            "Ex: <i>Rua das Flores, 123 - São Paulo</i>",
            parse_mode='HTML'
        )
    
    elif text == "📊 Status Atual":
        await show_status(update, context)
    
    elif text == "💰 Relatório Financeiro":
        await show_financial_report(update, context)
    
    elif state == "awaiting_base_address":
        # Geocodifica base (simulado por enquanto)
        base_address = text
        # TODO: Integrar com Google Geocoding API real
        base_lat, base_lng = -23.5505, -46.6333  # Simulado
        
        session_manager.set_base_location(base_address, base_lat, base_lng)
        session_manager.set_admin_state(user_id, "awaiting_romaneios")
        
        await update.message.reply_text(
            f"✅ Base definida: <b>{base_address}</b>\n\n"
            "📋 Agora envie os <b>romaneios</b>:\n\n"
            "📝 <b>Opção 1:</b> Cole texto (um endereço por linha)\n"
            "📄 <b>Opção 2:</b> Anexe arquivo CSV\n"
            "📕 <b>Opção 3:</b> Anexe arquivo PDF\n\n"
            "Quando terminar, digite: <code>/fechar_rota</code>",
            parse_mode='HTML'
        )
    
    elif state == "awaiting_romaneios":
        # Parse romaneio de texto
        await process_text_romaneio(update, context, text)


async def handle_document_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de arquivos (CSV, PDF)"""
    user_id = update.effective_user.id
    
    # Apenas admin pode enviar arquivos
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode enviar arquivos.")
        return
    
    state = session_manager.get_admin_state(user_id)
    
    if state != "awaiting_romaneios":
        await update.message.reply_text(
            "❌ Inicie uma sessão primeiro: <b>📦 Nova Sessão do Dia</b>",
            parse_mode='HTML'
        )
        return
    
    document = update.message.document
    file_name = document.file_name.lower()
    
    # Download arquivo
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    
    # Parse baseado no tipo
    try:
        if file_name.endswith('.csv'):
            await update.message.reply_text("📄 Processando CSV...")
            addresses = parse_csv_romaneio(bytes(file_content))
        
        elif file_name.endswith('.pdf'):
            await update.message.reply_text("📕 Processando PDF...")
            addresses = parse_pdf_romaneio(bytes(file_content))
        
        else:
            await update.message.reply_text(
                "❌ Formato não suportado.\n"
                "Aceito: <b>.csv</b>, <b>.pdf</b>",
                parse_mode='HTML'
            )
            return
        
        # Cria romaneio com endereços extraídos
        await create_romaneio_from_addresses(update, context, addresses)
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {e}")
        await update.message.reply_text(
            f"❌ Erro ao processar arquivo:\n<code>{str(e)}</code>\n\n"
            "Tente enviar manualmente (um endereço por linha).",
            parse_mode='HTML'
        )


async def process_text_romaneio(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Processa romaneio de texto (manual)"""
    addresses = parse_text_romaneio(text)
    
    if not addresses:
        await update.message.reply_text("❌ Nenhum endereço válido encontrado.")
        return
    
    await create_romaneio_from_addresses(update, context, addresses)


async def create_romaneio_from_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE, addresses: list):
    """Cria romaneio a partir de lista de endereços"""
    if not addresses:
        await update.message.reply_text("❌ Nenhum endereço válido encontrado.")
        return
    
    # Cria pontos de entrega (com geocoding simulado)
    points = []
    for i, addr in enumerate(addresses):
        # Suporta tanto List[str] (legado) quanto List[Dict] (novo)
        if isinstance(addr, dict):
            address = addr.get("address", "")
            package_id = addr.get("id", f"PKG{i:03d}")
            priority = addr.get("priority", "normal")
        else:
            address = addr
            package_id = f"PKG{i:03d}"
            priority = "normal"
        
        # Geocoding com cache inteligente
        lat, lng = geocoding_service.geocode(address)
        
        # IA preditiva: estima tempo de entrega
        base_lat, base_lng = -23.5505, -46.6333  # TODO: pegar da sessão
        distance = ((lat - base_lat)**2 + (lng - base_lng)**2)**0.5 * 111  # km aprox
        estimated_time = predictor.predict_from_package(
            package_id=package_id,
            deliverer_id=0,  # Ainda não atribuído
            distance_km=distance,
            priority=priority
        )
        
        points.append(DeliveryPoint(
            address=address,
            lat=lat,
            lng=lng,
            romaneio_id=str(uuid.uuid4())[:8],
            package_id=package_id,
            priority=priority
        ))
    
    romaneio = Romaneio(
        id=str(uuid.uuid4())[:8],
        uploaded_at=datetime.now(),
        points=points
    )
    
    session_manager.add_romaneio(romaneio)
    session = session_manager.get_active_session()
    
    await update.message.reply_text(
        f"✅ Romaneio <b>#{romaneio.id}</b> adicionado!\n"
        f"📦 {len(points)} pacotes\n\n"
        f"Total acumulado: <b>{session.total_packages} pacotes</b>\n\n"
        "Envie mais romaneios ou digite <code>/fechar_rota</code> para dividir.",
        parse_mode='HTML'
    )


async def cmd_fechar_rota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fecha rota e divide entre entregadores"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode fechar rotas.")
        return
    
    session = session_manager.get_active_session()
    if not session or not session.romaneios:
        await update.message.reply_text("❌ Nenhuma sessão ativa ou romaneios carregados.")
        return
    
    # Consolida todos os pontos
    all_points = []
    for romaneio in session.romaneios:
        all_points.extend(romaneio.points)
    
    # Divide em clusters
    divider = TerritoryDivider(session.base_lat, session.base_lng)
    clusters = divider.divide_into_clusters(all_points, k=BotConfig.CLUSTER_COUNT)
    
    # Otimiza rotas
    routes = []
    for cluster in clusters:
        optimized = divider.optimize_cluster_route(cluster)
        route = Route(
            id=f"ROTA_{cluster.id + 1}",
            cluster=cluster,
            optimized_order=optimized
        )
        routes.append(route)
    
    session_manager.set_routes(routes)
    session_manager.finalize_session()
    session_manager.set_admin_state(user_id, "awaiting_assignment")
    
    # Mostra resumo
    summary = f"🎯 <b>Rotas Divididas!</b>\n\n"
    summary += f"📍 Base: {session.base_address}\n"
    summary += f"📦 Total: {len(all_points)} pacotes\n\n"
    
    for route in routes:
        summary += f"<b>{route.id}</b>: {route.total_packages} pacotes\n"
    
    summary += "\n🚀 Agora atribua as rotas aos entregadores:"
    
    keyboard = []
    for route in routes:
        keyboard.append([InlineKeyboardButton(f"Atribuir {route.id}", callback_data=f"assign_route_{route.id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(summary, parse_mode='HTML', reply_markup=reply_markup)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de botões inline"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("assign_route_"):
        route_id = data.replace("assign_route_", "")
        session_manager.save_temp_data(query.from_user.id, "assigning_route", route_id)
        
        # Mostra lista de entregadores
        keyboard = []
        for partner in BotConfig.DELIVERY_PARTNERS:
            keyboard.append([InlineKeyboardButton(
                f"{partner.name} {'(Sócio)' if partner.is_partner else ''}",
                callback_data=f"deliverer_{partner.telegram_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"👤 Escolha o entregador para <b>{route_id}</b>:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif data.startswith("deliverer_"):
        deliverer_id = int(data.replace("deliverer_", ""))
        route_id = session_manager.get_temp_data(query.from_user.id, "assigning_route")
        
        # Atribui rota
        session = session_manager.get_active_session()
        route = next((r for r in session.routes if r.id == route_id), None)
        
        if route:
            partner = BotConfig.get_partner_by_id(deliverer_id)
            route.assigned_to_telegram_id = deliverer_id
            route.assigned_to_name = partner.name
            
            # Envia rota pro entregador
            await send_route_to_deliverer(context, deliverer_id, route, session)
            
            await query.edit_message_text(
                f"✅ <b>{route_id}</b> atribuída a <b>{partner.name}</b>!\n\n"
                f"📨 Rota enviada no chat privado do entregador.",
                parse_mode='HTML'
            )
            
            # Verifica se todas rotas foram atribuídas
            all_assigned = all(r.assigned_to_telegram_id for r in session.routes)
            if all_assigned:
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text="🎉 <b>Todas as rotas foram distribuídas!</b>\n\nBoa entrega!",
                    parse_mode='HTML'
                )


async def send_route_to_deliverer(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, route: Route, session):
    """Envia rota formatada para o entregador"""
    message = f"🗺️ <b>SUA ROTA - {route.id}</b>\n\n"
    message += f"📍 Base: {session.base_address}\n"
    message += f"📦 Total: {route.total_packages} pacotes\n\n"
    message += "📋 <b>Ordem de entrega:</b>\n\n"
    
    for i, point in enumerate(route.optimized_order, 1):
        message += f"{i}. {point.address}\n"
        message += f"   🆔 <code>{point.package_id}</code>\n\n"
    
    message += "\n✅ Marque entregas usando o botão 'Marcar Entrega'"
    
    await context.bot.send_message(
        chat_id=telegram_id,
        text=message,
        parse_mode='HTML'
    )


# ==================== DELIVERER HANDLERS ====================

async def handle_deliverer_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Fluxo do entregador"""
    user_id = update.effective_user.id
    
    if text == "🗺️ Minha Rota Hoje":
        route = session_manager.get_route_for_deliverer(user_id)
        
        if not route:
            await update.message.reply_text("❌ Você não tem rota atribuída hoje.")
            return
        
        session = session_manager.get_active_session()
        await send_route_to_deliverer(context, user_id, route, session)
    
    elif text == "✅ Marcar Entrega":
        route = session_manager.get_route_for_deliverer(user_id)
        
        if not route:
            await update.message.reply_text("❌ Você não tem rota ativa.")
            return
        
        # Lista pacotes pendentes
        pending = [p for p in route.optimized_order if p.package_id not in route.delivered_packages]
        
        if not pending:
            await update.message.reply_text("🎉 Todas as suas entregas foram concluídas!")
            return
        
        keyboard = []
        for p in pending[:10]:  # Limite 10 por vez
            keyboard.append([InlineKeyboardButton(
                f"📦 {p.address[:40]}... (ID: {p.package_id})",
                callback_data=f"deliver_{p.package_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 Selecione o pacote entregue:",
            reply_markup=reply_markup
        )


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra status atual da sessão"""
    session = session_manager.get_active_session()
    
    if not session:
        await update.message.reply_text("❌ Nenhuma sessão ativa.")
        return
    
    msg = f"📊 <b>STATUS - {session.date}</b>\n\n"
    msg += f"📍 Base: {session.base_address}\n"
    msg += f"📦 Total: {session.total_packages} pacotes\n"
    msg += f"✅ Entregues: {session.total_delivered}\n"
    msg += f"⏳ Pendentes: {session.total_pending}\n\n"
    
    if session.routes:
        msg += "<b>Rotas:</b>\n"
        for route in session.routes:
            status = f"{route.delivered_count}/{route.total_packages} ({route.completion_rate:.1f}%)"
            msg += f"• {route.id}: {route.assigned_to_name or 'Não atribuída'} - {status}\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def show_financial_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Relatório financeiro"""
    session = session_manager.get_active_session()
    
    if not session:
        await update.message.reply_text("❌ Nenhuma sessão ativa.")
        return
    
    msg = f"💰 <b>RELATÓRIO FINANCEIRO - {session.date}</b>\n\n"
    
    costs_by_deliverer = {}
    
    for route in session.routes:
        if route.assigned_to_telegram_id:
            partner = BotConfig.get_partner_by_id(route.assigned_to_telegram_id)
            if partner:
                cost = route.delivered_count * partner.cost_per_package
                costs_by_deliverer[partner.name] = costs_by_deliverer.get(partner.name, 0) + cost
    
    total_cost = 0
    for name, cost in costs_by_deliverer.items():
        msg += f"• {name}: R$ {cost:.2f}\n"
        total_cost += cost
    
    msg += f"\n<b>CUSTO TOTAL: R$ {total_cost:.2f}</b>"
    
    await update.message.reply_text(msg, parse_mode='HTML')


# ==================== DELIVERER MANAGEMENT ====================

async def cmd_add_deliverer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona novo entregador - Admin only"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Comando exclusivo para admin.")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📝 <b>Uso:</b>\n"
            "<code>/add_entregador &lt;telegram_id&gt; &lt;nome&gt; &lt;tipo&gt; &lt;capacidade&gt; &lt;custo&gt;</code>\n\n"
            "<b>Exemplo:</b>\n"
            "<code>/add_entregador 123456789 João parceiro 50 0</code>\n"
            "<code>/add_entregador 987654321 Maria terceiro 30 1.00</code>\n\n"
            "<b>Tipos:</b> parceiro | terceiro\n"
            "<b>Capacidade:</b> Máximo de pacotes por dia\n"
            "<b>Custo:</b> R$ por pacote (0 para parceiro)",
            parse_mode='HTML'
        )
        return
    
    try:
        telegram_id = int(args[0])
        name = args[1]
        tipo = args[2].lower()
        capacidade = int(args[3]) if len(args) > 3 else 50
        custo = float(args[4]) if len(args) > 4 else (0 if tipo == "parceiro" else 1.0)
        
        is_partner = tipo == "parceiro"
        
        # Usa deliverer_service para adicionar
        success = deliverer_service.add_deliverer(
            telegram_id=telegram_id,
            name=name,
            is_partner=is_partner,
            max_capacity=capacidade,
            cost_per_package=custo
        )
        
        if success:
            tipo_emoji = "🤝" if is_partner else "💼"
            await update.message.reply_text(
                f"✅ <b>Entregador cadastrado!</b>\n\n"
                f"{tipo_emoji} <b>{name}</b>\n"
                f"🆔 Telegram: {telegram_id}\n"
                f"📦 Capacidade: {capacidade} pacotes/dia\n"
                f"💰 Custo: R$ {custo:.2f}/pacote",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Erro: Entregador já existe!")
    
    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Erro nos parâmetros: {e}")


async def cmd_list_deliverers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os entregadores - Admin only"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Comando exclusivo para admin.")
        return
    
    deliverers = deliverer_service.get_all_deliverers()
    
    if not deliverers:
        await update.message.reply_text("📭 Nenhum entregador cadastrado ainda.\n\nUse /add_entregador")
        return
    
    active = [d for d in deliverers if d.is_active]
    inactive = [d for d in deliverers if not d.is_active]
    
    msg = "👥 <b>ENTREGADORES CADASTRADOS</b>\n\n"
    
    if active:
        msg += "✅ <b>ATIVOS:</b>\n\n"
        for d in active:
            tipo = "🤝 Parceiro" if d.is_partner else "💼 Terceiro"
            stats = f"{d.total_deliveries} entregas | {d.success_rate:.1f}% sucesso"
            msg += f"• <b>{d.name}</b> ({tipo})\n"
            msg += f"  🆔 {d.telegram_id} | 📦 {d.max_capacity} pacotes\n"
            msg += f"  💰 R$ {d.cost_per_package:.2f}/pacote | {stats}\n\n"
    
    if inactive:
        msg += "❌ <b>INATIVOS:</b>\n\n"
        for d in inactive:
            msg += f"• {d.name} (ID: {d.telegram_id})\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎮 Ranking de entregadores com gamificação"""
    user_id = update.effective_user.id
    
    # Qualquer um pode ver ranking
    leaderboard = gamification_service.get_leaderboard(limit=10)
    
    if not leaderboard:
        await update.message.reply_text("🎮 Ranking ainda vazio. Comece a fazer entregas!")
        return
    
    msg = "🏆 <b>RANKING DOS ENTREGADORES</b>\n\n"
    
    for entry in leaderboard:
        # Medalhas
        medal = "🥇" if entry.rank == 1 else "🥈" if entry.rank == 2 else "🥉" if entry.rank == 3 else f"{entry.rank}º"
        
        # Badges
        badge_icons = " ".join([b.type.value.split()[0] for b in entry.badges[:3]])
        
        # Streak
        streak_text = f"🔥{entry.streak_days}" if entry.streak_days > 0 else ""
        
        msg += f"{medal} <b>{entry.name}</b>\n"
        msg += f"   ⭐ {entry.score} pts | {badge_icons} {streak_text}\n\n"
    
    # Stats pessoais (se é entregador)
    personal_stats = gamification_service.get_deliverer_stats(user_id)
    if personal_stats:
        msg += f"\n📊 <b>SUAS STATS:</b>\n"
        msg += f"Rank: #{personal_stats['rank']} | Score: {personal_stats['score']}\n"
        msg += f"Entregas: {personal_stats['total_deliveries']} | "
        msg += f"Sucesso: {personal_stats['success_rate']:.1f}%\n"
        
        if personal_stats['streak_days'] > 0:
            msg += f"🔥 Streak: {personal_stats['streak_days']} dias\n"
        
        if personal_stats['badges']:
            msg += f"\n🏅 Badges: {len(personal_stats['badges'])}\n"
            for badge in personal_stats['badges'][:5]:
                msg += f"  {badge.type.value}\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_predict_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🤖 Previsão de tempo de entrega com IA - MODO SCOOTER"""
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "🛵 <b>Previsão de Tempo - MODO SCOOTER</b>\n\n"
            "<b>Uso:</b>\n"
            "<code>/prever DISTANCIA_KM [PRIORIDADE]</code>\n\n"
            "<b>Exemplo:</b>\n"
            "<code>/prever 5.2 high</code>\n"
            "<code>/prever 3.0</code>\n\n"
            "Prioridades: low, normal, high, urgent\n\n"
            "💡 <b>Modo Scooter:</b> Pode usar contramão, calçadas e atalhos!",
            parse_mode='HTML'
        )
        return
    
    try:
        distance = float(context.args[0])
        priority = context.args[1] if len(context.args) > 1 else 'normal'
        
        # Prediz tempo
        estimated = predictor.predict_from_package(
            package_id='PREVIEW',
            deliverer_id=user_id,
            distance_km=distance,
            priority=priority
        )
        
        # Avalia precisão do modelo
        accuracy = predictor.evaluate_accuracy()
        msg = f"<b>PREVISAO - MODO SCOOTER ELETRICA</b>\n\n"
        msg += f"Distancia em linha reta: {distance} km\n"
        msg += f"Prioridade: {priority.upper()}\n"
        msg += f"Tempo estimado: <b>{estimated:.1f} minutos</b>\n\n"
        
        msg += f"<b>Vantagens Scooter:</b>\n"
        msg += f"- Pode usar contramao e calcadas\n"
        msg += f"- Atalhos nao disponiveis para carros\n"
        msg += f"- Menos afetado por trafego\n"
        msg += f"- Mais rapido em distancias curtas\n\n"
        msg += f"<b>Precisao do Modelo:</b>\n"
        
        if 'error' in accuracy:
            msg += f"[!] {accuracy['error']}\n"
        else:
            msg += f"[OK] Accuracy: {accuracy['accuracy']}\n"
            msg += f"Erro medio: {accuracy['mae']:.1f} min\n"
            msg += f"Baseado em {accuracy['samples']} entregas\n"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    except ValueError:
        await update.message.reply_text("❌ Distância inválida. Use números (ex: 5.2)")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")


# ==================== MAIN ====================

async def cmd_distribuir_rota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /distribuir <excel_path> <num_entregadores> - Distribui romaneio entre entregadores"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("Apenas o admin pode distribuir rotas.")
        return
    
    # Parse argumentos
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Uso: /distribuir <arquivo.xlsx> <num_entregadores>\n\n"
            "Exemplo: /distribuir romaneio.xlsx 3"
        )
        return
    
    excel_path = args[0]
    try:
        num_entregadores = int(args[1])
    except ValueError:
        await update.message.reply_text("Numero de entregadores deve ser um inteiro.")
        return
    
    await update.message.reply_text("Processando romaneio...")
    
    try:
        # Import aqui para evitar circular import
        from bot.services.shopee_parser import ShopeeRomaneioParser
        from bot_multidelivery.services.roteo_divider import RoteoDivider
        from bot_multidelivery.services.map_generator import MapGenerator
        
        # Parse Excel
        deliveries = ShopeeRomaneioParser.parse(excel_path)
        
        # Pega entregadores disponiveis
        all_deliverers = deliverer_service.list_deliverers()
        if len(all_deliverers) < num_entregadores:
            await update.message.reply_text(
                f"Erro: Cadastrados {len(all_deliverers)} entregadores, mas precisa de {num_entregadores}.\n"
                f"Use /add_entregador para cadastrar mais."
            )
            return
        
        # Monta dicionario de entregadores
        selected = all_deliverers[:num_entregadores]
        entregadores_info = {d['telegram_id']: d['name'] for d in selected}
        
        # Divide romaneio
        divider = RoteoDivider()
        routes = divider.divide_romaneio(deliveries, num_entregadores, entregadores_info)
        
        # Envia resumo pro admin
        summary = f"<b>ROTA DISTRIBUIDA</b>\n\n"
        summary += f"Total: {len(deliveries)} pacotes\n"
        summary += f"Entregadores: {num_entregadores}\n\n"
        
        for i, route in enumerate(routes, 1):
            summary += f"{i}. {route.entregador_nome}\n"
            summary += f"   Pacotes: {route.total_packages}\n"
            summary += f"   Paradas: {len(route.stops)}\n"
            summary += f"   Tempo: {route.total_time_minutes:.0f} min\n\n"
        
        await update.message.reply_text(summary, parse_mode='HTML')
        
        # Envia mapa pro chat de cada entregador
        for route in routes:
            # Prepara dados dos stops
            stops_data = []
            for i, (lat, lon, deliveries_list) in enumerate(route.stops):
                address = deliveries_list[0].address
                num_packages = len(deliveries_list)
                status = 'current' if i == 0 else 'pending'
                stops_data.append((lat, lon, address, num_packages, status))
            
            # Gera HTML do mapa
            html = MapGenerator.generate_interactive_map(
                stops=stops_data,
                entregador_nome=route.entregador_nome,
                current_stop=0,
                total_packages=route.total_packages,
                total_distance_km=route.total_distance_km,
                total_time_min=route.total_time_minutes
            )
            
            # Salva temporariamente
            map_file = f"rota_{route.entregador_id}.html"
            MapGenerator.save_map(html, map_file)
            
            # Envia pro entregador
            try:
                msg = (
                    f"<b>SUA ROTA FOI GERADA!</b>\n\n"
                    f"Pacotes: {route.total_packages}\n"
                    f"Paradas: {len(route.stops)}\n"
                    f"Distancia: {route.total_distance_km:.2f} km\n"
                    f"Tempo estimado: {route.total_time_minutes:.0f} min\n"
                    f"Atalhos detectados: {route.shortcuts}\n\n"
                    f"Inicio: {route.start_point[2][:50]}...\n"
                    f"Fim: {route.end_point[2][:50]}...\n\n"
                    f"Abrindo mapa interativo..."
                )
                
                await context.bot.send_message(
                    chat_id=route.entregador_id,
                    text=msg,
                    parse_mode='HTML'
                )
                
                # Envia arquivo HTML
                with open(map_file, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=route.entregador_id,
                        document=f,
                        filename=f"rota_{route.entregador_nome.replace(' ', '_')}.html",
                        caption="Abra este arquivo no navegador para ver o mapa interativo!"
                    )
                
            except Exception as e:
                logger.error(f"Erro enviando rota para {route.entregador_id}: {e}")
        
        await update.message.reply_text("Rotas enviadas para todos os entregadores!")
        
    except FileNotFoundError:
        await update.message.reply_text(f"Arquivo nao encontrado: {excel_path}")
    except Exception as e:
        logger.error(f"Erro ao distribuir rota: {e}")
        await update.message.reply_text(f"Erro: {str(e)}")


def run_bot():
    """Inicia o bot"""
    app = Application.builder().token(BotConfig.TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("fechar_rota", cmd_fechar_rota))
    app.add_handler(CommandHandler("distribuir", cmd_distribuir_rota))
    app.add_handler(CommandHandler("add_entregador", cmd_add_deliverer))
    app.add_handler(CommandHandler("entregadores", cmd_list_deliverers))
    app.add_handler(CommandHandler("ranking", cmd_ranking))
    app.add_handler(CommandHandler("prever", cmd_predict_time))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("🚀 Bot iniciado! Suporta: texto, CSV, PDF + Deliverer Management")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
