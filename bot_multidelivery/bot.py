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
from .services.map_generator import MapGenerator
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
            [KeyboardButton("📊 Status Atual"), KeyboardButton("💰 Relatório Financeiro")],
            [KeyboardButton("👥 Entregadores"), KeyboardButton("🏆 Ranking")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🚀 <b>BOT MULTI-ENTREGADOR v20/10</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👋 E aí, <b>CHEFE</b>! Pronto pra dominar as entregas?\n\n"
            "<b>⚡ FLUXO RÁPIDO:</b>\n"
            "1️⃣ <code>/importar</code> - Sobe romaneios da Shopee\n"
            "2️⃣ Seleciona entregadores disponíveis\n"
            "3️⃣ <code>/otimizar</code> - Divide + roteiriza + MANDA!\n\n"
            "<b>🛠️ GERENCIAR:</b>\n"
            "• <code>/add_entregador</code> - Cadastra novo entregador\n"
            "• <code>/entregadores</code> - Lista do time\n"
            "• <code>/ranking</code> - Quem tá mandando bem\n\n"
            "💡 <code>/help</code> pra ver TUDO que esse bot faz\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 <i>Bora fazer grana!</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        # Entregador
        partner = BotConfig.get_partner_by_id(user_id)
        if partner:
            keyboard = [
                [KeyboardButton("🗺️ Minha Rota Hoje")],
                [KeyboardButton("✅ Marcar Entrega"), KeyboardButton("❌ Reportar Problema")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            tipo = "🤝 PARCEIRO" if partner.is_partner else "💼 COLABORADOR"
            
            await update.message.reply_text(
                f"🏍️ <b>E AÍ, {partner.name.upper()}!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📛 Status: {tipo}\n"
                f"📦 Capacidade: {partner.max_capacity} pacotes/dia\n"
                f"💰 Ganho: R$ {partner.cost_per_package:.2f}/pacote\n\n"
                f"<b>🎯 COMO FUNCIONA:</b>\n"
                f"1️⃣ Admin distribui as rotas\n"
                f"2️⃣ Você recebe um mapa HTML interativo\n"
                f"3️⃣ Abre no navegador e segue a ordem\n"
                f"4️⃣ Marca cada entrega (✅/❌)\n\n"
                f"🔔 <i>Aguardando distribuição de rotas...</i>\n\n"
                f"💡 <code>/help</code> - Ver todos os comandos\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 <i>Bora faturar!</i>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "⛔ <b>ACESSO NEGADO</b>\n\n"
                "Você não está cadastrado como entregador.\n\n"
                "Entre em contato com o administrador para solicitar cadastro.",
                parse_mode='HTML'
            )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Ajuda contextual profissional e interativa"""
    user_id = update.effective_user.id
    
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        # ════════════════════════════════════════
        # HELP ADMIN - Versão Profissional com UX
        # ════════════════════════════════════════
        
        help_text = """╔═══════════════════════════════════╗
║  <b>🚀 BOT MULTI-ENTREGADOR v2.1</b>  ║
║  <i>Sistema Inteligente de Logística</i>  ║
╚═══════════════════════════════════╝

⏱ <b>Início Rápido</b> — 3 passos em 2 minutos

<b>┏━━ PASSO 1: IMPORTAR ROMANEIOS</b>
┃  
┃  ▸ Envie arquivo ou use <code>/importar</code>
┃  ▸ Formatos: Excel Shopee, CSV, PDF, Texto
┃  ▸ Pode enviar múltiplos romaneios
┃  ┗━▸ Sistema consolida automaticamente
┃
<b>┣━━ PASSO 2: SELECIONAR ENTREGADORES</b>
┃  
┃  ▸ Bot lista equipe disponível
┃  ▸ Marque quem trabalha hoje
┃  ┗━▸ Sistema calcula capacidade total
┃
<b>┗━━ PASSO 3: OTIMIZAR & DISTRIBUIR</b>
   
   ▸ Use <code>/otimizar</code> ou <code>/distribuir</code>
   ▸ IA divide geograficamente (K-means)
   ▸ Scooter Mode otimiza cada rota
   ┗━▸ Mapa HTML enviado para cada um

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📋 COMANDOS ESSENCIAIS</b>

<b>📦 Operação Diária</b>
 ▸ <code>/importar</code> — Importar romaneios
 ▸ <code>/otimizar</code> — Distribuir rotas otimizadas
 ▸ <code>/fechar_rota</code> — Finalizar sessão do dia

<b>👥 Gestão de Equipe</b>
 ▸ <code>/add_entregador</code> — Cadastrar novo membro
 ▸ <code>/entregadores</code> — Listar equipe completa
 ▸ <code>/ranking</code> — Ver gamificação e conquistas

<b>📊 Monitoramento & Análise</b>
 ▸ <code>/status</code> — Progresso em tempo real
 ▸ <code>/prever</code> — Predição IA de tempo/custo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔧 CONFIGURAÇÕES AVANÇADAS</b>

<b>Tipos de Entregador</b>

🔸 <b>PARCEIRO</b> (Sócio do negócio)
   • Custo: <code>R$ 0,00/pacote</code>
   • Participa dos lucros
   • Ideal para proprietários

🔹 <b>COLABORADOR</b> (Terceirizado)
   • Custo: <code>R$ 1,00 a R$ 2,50/pacote</code>
   • Pagamento por produção
   • Ideal para freelancers

<b>Cadastro Wizard:</b>
<code>/add_entregador</code> e siga o assistente interativo

<b>Cadastro Direto:</b>
<code>/add_entregador [ID] [Nome] [tipo] [capacidade] [custo]</code>

Exemplo:
<code>/add_entregador 123456 João parceiro 50 0</code>
<code>/add_entregador 789012 Maria terceiro 30 1.5</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📂 FORMATOS DE ARQUIVO ACEITOS</b>

<b>✅ Excel Shopee</b> — <i>Recomendado</i>
   Lat/lon automático | Detecção inteligente

<b>✅ CSV Genérico</b>
   tracking,endereco,lat,lon,prioridade

<b>✅ PDF Romaneio</b>
   OCR automático | Geocodificação Google

<b>✅ Texto Manual</b>
   Um endereço por linha | Aceita formatação livre

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🧠 TECNOLOGIA SCOOTER MODE</b>

<b>Otimizações Aplicadas:</b>
 ✓ Agrupamento por STOP (mesmo endereço)
 ✓ Divisão geográfica K-means clustering
 ✓ Otimização de rota euclidiana
 ✓ Consideração de contrafluxo seguro
 ✓ Atalhos e vielas permitidas

<b>Resultados:</b>
 • <b>79% de economia</b> vs rota original
 • Redução de 40% no tempo médio
 • Aumento de 60% na capacidade diária

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 PRO TIPS</b>

 • Importe romaneios pela manhã
 • Sempre verifique capacidade da equipe
 • Use /prever antes de distribuir
 • Acompanhe em tempo real com /status
 • Feche a rota ao final do dia

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💬 SUPORTE & ATUALIZAÇÕES</b>

Bot desenvolvido com IA + algoritmos genéticos
Sistema em constante evolução

<code>/help</code> sempre disponível
<b>v2.1</b> | Scooter Mode + IA Preditiva
⚡ Atualizado: 21/12/2025"""

        # Botões interativos para navegação rápida
        keyboard = [
            [
                InlineKeyboardButton("📦 Importar Agora", callback_data="help_import"),
                InlineKeyboardButton("👥 Ver Equipe", callback_data="help_team")
            ],
            [
                InlineKeyboardButton("📊 Status Atual", callback_data="help_status"),
                InlineKeyboardButton("🏆 Ranking", callback_data="help_ranking")
            ],
            [
                InlineKeyboardButton("💡 Início Rápido", callback_data="help_quickstart")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text, 
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    else:
        # ════════════════════════════════════════
        # HELP ENTREGADOR - Versão Simplificada
        # ════════════════════════════════════════
        
        partner = BotConfig.get_partner_by_id(user_id)
        if not partner:
            await update.message.reply_text(
                "⛔ <b>ACESSO NEGADO</b>\n\n"
                "Você não está cadastrado como entregador.\n\n"
                "Fale com o admin pra solicitar cadastro!",
                parse_mode='HTML'
            )
            return
        
        tipo_emoji = "🤝" if partner.is_partner else "💼"
        tipo_texto = "PARCEIRO (Sócio)" if partner.is_partner else "COLABORADOR"
        
        pagamento_info = (
            "Você é <b>SÓCIO</b> do negócio\n"
            "   • Custo: R$ 0,00/pacote\n"
            "   • Participa dos lucros"
            if partner.is_partner else
            f"Você é <b>COLABORADOR</b>\n"
            f"   • Pagamento: <b>R$ {partner.cost_per_package:.2f}/pacote</b>\n"
            f"   • Acerto no final do dia"
        )
        
        help_text = f"""╔═══════════════════════════════════╗
║  <b>📚 MANUAL DO ENTREGADOR</b>     ║
║  <i>Seu guia completo de entregas</i>   ║
╚═══════════════════════════════════╝

👋 Olá, <b>{partner.name}</b>!

<b>📋 SEU PERFIL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 {tipo_emoji} Tipo: <b>{tipo_texto}</b>
 📦 Capacidade: <b>{partner.max_capacity} pacotes/dia</b>
 💰 {pagamento_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚀 FLUXO DE TRABALHO</b>

<b>┏━━ 1. RECEBER ROTA</b>
┃  ▸ Admin envia sua rota otimizada
┃  ▸ Arquivo HTML interativo com mapa
┃  ┗━▸ Baixe e abra no navegador
┃
<b>┣━━ 2. VISUALIZAR MAPA</b>
┃  ▸ Pins numerados por ordem
┃  ▸ Linha conecta toda a rota
┃  ┗━▸ Clique para ver detalhes
┃
<b>┣━━ 3. NAVEGAR</b>
┃  ▸ Botão "Google Maps" em cada pin
┃  ▸ Navegação turn-by-turn automática
┃  ┗━▸ Siga a ordem otimizada
┃
<b>┗━━ 4. MARCAR ENTREGAS</b>
   ▸ ✅ Entregue — Sucesso
   ▸ ❌ Insucesso — Não conseguiu
   ┗━▸ 🔄 Transferir — Passar pra colega

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 CONCEITO DE STOPS</b>

<b>1 STOP</b> = Múltiplas entregas no mesmo local

<b>Exemplo Real:</b>
📍 Edifício Solar das Palmeiras
   ├─ Apto 201 (1 pacote)
   ├─ Apto 603 (2 pacotes)
   └─ Apto 903 (1 pacote)
   
   <b>= 1 STOP com 4 entregas</b>
   
<i>Faça todas de uma vez pra economizar tempo!</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏍️ MODO SCOOTER</b>

<b>Seu algoritmo considera:</b>
 ✓ Contrafluxo (quando seguro)
 ✓ Calçadas e atalhos permitidos
 ✓ Vielas e becos acessíveis
 ✓ Aglomerações de entregas próximas

<b>Resultado:</b>
 • <b>79% mais eficiente</b> que rota original
 • Menos combustível gasto
 • Mais entregas por hora

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 DICAS DE OURO</b>

 ▸ Sempre siga a ordem do mapa
    <i>→ A IA já otimizou pra você</i>

 ▸ Marque entregas imediatamente
    <i>→ Admin monitora em tempo real</i>

 ▸ Use o botão Google Maps
    <i>→ Navegação precisa garantida</i>

 ▸ Agrupe entregas do mesmo STOP
    <i>→ Eficiência = mais ganhos</i>

 ▸ Comunique problemas rapidamente
    <i>→ Suporte ágil do admin</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🆘 SUPORTE</b>

Dúvidas ou problemas?
Fale diretamente com o admin!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚀 Boas entregas, parceiro(a)!</b>
⚡ <b>v2.1</b> | Atualizado: 21/12/2025"""
        
        # Botão simples para entregador
        keyboard = [[
            InlineKeyboardButton("💡 Dica do Dia", callback_data="deliverer_tip")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text, 
            parse_mode='HTML',
            reply_markup=reply_markup
        )


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

    # Wizard: cadastro de entregador
    if state == "adding_deliverer_name":
        data = session_manager.get_temp_data(user_id, "new_deliverer") or {}
        data["name"] = text.strip()
        session_manager.save_temp_data(user_id, "new_deliverer", data)
        session_manager.set_admin_state(user_id, "adding_deliverer_id")

        await update.message.reply_text(
            "📲 Informe o <b>Telegram ID</b> do entregador (apenas números).\n\n"
            "Exemplo: 123456789",
            parse_mode='HTML'
        )
        return

    if state == "adding_deliverer_id":
        digits_only = ''.join(ch for ch in text if ch.isdigit())
        try:
            telegram_id = int(digits_only)
        except ValueError:
            await update.message.reply_text(
                "⚠️ ID inválido. Envie só números (ex: 123456789).",
                parse_mode='HTML'
            )
            return

        data = session_manager.get_temp_data(user_id, "new_deliverer") or {}
        data["telegram_id"] = telegram_id
        session_manager.save_temp_data(user_id, "new_deliverer", data)
        session_manager.set_admin_state(user_id, "adding_deliverer_partner")

        keyboard = [[
            InlineKeyboardButton("🤝 Sim, é sócio", callback_data="add_partner_yes"),
            InlineKeyboardButton("💼 Não, é colaborador", callback_data="add_partner_no")
        ]]

        await update.message.reply_text(
            "🤔 Esse entregador é <b>sócio</b>?\n\n"
            "Sócios têm custo R$ 0,00/pacote.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if state == "adding_deliverer_cost":
        try:
            cost = float(text.strip().replace(',', '.'))
            if cost < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Valor inválido. Envie um número (ex: 1.50).",
                parse_mode='HTML'
            )
            return

        data = session_manager.get_temp_data(user_id, "new_deliverer") or {}
        data["cost"] = cost
        session_manager.save_temp_data(user_id, "new_deliverer", data)

        await send_deliverer_summary(update, user_id, data)
        return
    
    if text == "📦 Nova Sessão do Dia":
        # Inicia nova sessão
        today = datetime.now().strftime("%Y-%m-%d")
        session_manager.start_new_session(today)
        session_manager.set_admin_state(user_id, "awaiting_base_address")
        
        await update.message.reply_text(
            "🟢 <b>NOVA SESSÃO INICIADA!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Data: <b>{today}</b>\n\n"
            "🎯 <b>PRÓXIMO PASSO:</b>\n"
            "Defina a <b>LOCALIZAÇÃO DA BASE</b> (onde o carro/bike está)\n\n"
            "📍 <b>OPÇÃO 1 (RECOMENDADO):</b>\n"
            "   Use o 📎 anexo → 📍 Localização do Telegram\n"
            "   ✅ Otimiza bateria das bikes!\n\n"
            "📝 <b>OPÇÃO 2:</b>\n"
            "   Digite o endereço completo\n"
            "   <i>Ex: Rua das Flores, 123 - Botafogo, RJ</i>\n\n"
            "❗ Envie a localização ou endereço na próxima mensagem.",
            parse_mode='HTML'
        )
    
    elif text == "📊 Status Atual":
        await show_status(update, context)
    
    elif text == "💰 Relatório Financeiro":
        await show_financial_report(update, context)

    elif text == "👥 Entregadores":
        await cmd_list_deliverers(update, context)

    elif text == "🏆 Ranking":
        await cmd_ranking(update, context)
    
    elif state == "awaiting_base_address":
        # Geocodifica o endereço digitado
        base_address = text
        
        # Tenta geocodificar com o serviço disponível
        try:
            coords = await geocoding_service.geocode_address(base_address)
            if coords:
                base_lat, base_lng = coords
            else:
                base_lat, base_lng = -23.5505, -46.6333  # Fallback SP
                await update.message.reply_text(
                    "⚠️ Não consegui localizar o endereço exato. Usando coordenadas aproximadas.\n"
                    "📍 Use o anexo de localização do Telegram para maior precisão!",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.warning(f"Erro ao geocodificar: {e}")
            base_lat, base_lng = -23.5505, -46.6333  # Fallback
        
        session_manager.set_base_location(base_address, base_lat, base_lng)
        session_manager.set_admin_state(user_id, "awaiting_romaneios")
        
        await update.message.reply_text(
            f"✅ <b>BASE CONFIGURADA!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 Local: <b>{base_address}</b>\n"
            f"🌐 Coords: <code>{base_lat:.6f}, {base_lng:.6f}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>PRÓXIMO PASSO:</b> Envie os romaneios!\n\n"
            f"<b>📂 MÉTODOS ACEITOS:</b>\n\n"
            f"📄 <b>1. Arquivo Excel (.xlsx)</b>\n"
            f"   Formato Shopee (RECOMENDADO)\n"
            f"   Usa: <code>/importar</code>\n\n"
            f"📝 <b>2. Texto Direto</b>\n"
            f"   Cole endereços (um por linha)\n\n"
            f"📊 <b>3. Arquivo CSV</b>\n"
            f"   Formato: tracking,endereco,lat,lon\n\n"
            f"📕 <b>4. PDF Scaneado</b>\n"
            f"   OCR automático (legado)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 Quando terminar: <code>/fechar_rota</code>",
            parse_mode='HTML'
        )
    
    elif state == "awaiting_romaneios":
        # Parse romaneio de texto
        await process_text_romaneio(update, context, text)

    else:
        # Fallback para textos não mapeados
        await update.message.reply_text(
            "🤔 Não entendi. Use os botões do menu ou /help para ver os comandos.",
            parse_mode='HTML'
        )


async def handle_location_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para localização do Telegram (anexo de location)"""
    user_id = update.effective_user.id
    
    # Apenas admin pode definir localização da base
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode definir a base.")
        return
    
    state = session_manager.get_admin_state(user_id)
    
    if state != "awaiting_base_address":
        await update.message.reply_text(
            "⚠️ Não estou esperando uma localização agora.\n"
            "Use 📦 Nova Sessão do Dia para começar.",
            parse_mode='HTML'
        )
        return
    
    # Extrai coordenadas da localização
    location = update.message.location
    base_lat = location.latitude
    base_lng = location.longitude
    
    # Tenta fazer reverse geocoding para obter o endereço
    try:
        address = await geocoding_service.reverse_geocode(base_lat, base_lng)
        base_address = address if address else f"Coordenadas: {base_lat:.6f}, {base_lng:.6f}"
    except Exception as e:
        logger.warning(f"Erro no reverse geocoding: {e}")
        base_address = f"Coordenadas: {base_lat:.6f}, {base_lng:.6f}"
    
    session_manager.set_base_location(base_address, base_lat, base_lng)
    session_manager.set_admin_state(user_id, "awaiting_romaneios")
    
    await update.message.reply_text(
        f"✅ <b>BASE CONFIGURADA COM LOCALIZAÇÃO EXATA!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 Local: <b>{base_address}</b>\n"
        f"🌐 Coords: <code>{base_lat:.6f}, {base_lng:.6f}</code>\n"
        f"🚴 <b>Otimizado para economia de bateria!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚀 <b>PRÓXIMO PASSO:</b> Envie os romaneios!\n\n"
        f"<b>📂 MÉTODOS ACEITOS:</b>\n\n"
        f"📄 <b>1. Arquivo Excel (.xlsx)</b>\n"
        f"   Formato Shopee (RECOMENDADO)\n"
        f"   Usa: <code>/importar</code>\n\n"
        f"📝 <b>2. Texto Direto</b>\n"
        f"   Cole endereços (um por linha)\n\n"
        f"📊 <b>3. Arquivo CSV</b>\n"
        f"   Formato: tracking,endereco,lat,lon\n\n"
        f"📕 <b>4. PDF Scaneado</b>\n"
        f"   OCR automático (legado)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 Quando terminar: <code>/fechar_rota</code>",
        parse_mode='HTML'
    )


async def send_deliverer_summary(update: Update, user_id: int, data: dict):
    """Mostra resumo e pede confirmação do novo entregador."""
    name = data.get("name", "—")
    telegram_id = data.get("telegram_id", "—")
    is_partner = data.get("is_partner", False)
    capacity = data.get("capacity", 9999)
    cost = 0.0 if is_partner else data.get("cost", 1.0)

    session_manager.set_admin_state(user_id, "confirming_deliverer")

    tipo_txt = "🤝 Sócio (custo R$ 0,00)" if is_partner else "💼 Colaborador"

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar cadastro", callback_data="confirm_add_deliverer")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_add_deliverer")]
    ]

    msg = (
        "📋 <b>Confirmar entregador</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Nome: <b>{name}</b>\n"
        f"🆔 ID: <code>{telegram_id}</code>\n"
        f"🏷️ Tipo: {tipo_txt}\n"
        f"📦 Capacidade: <b>flexível</b> (define por rota)\n"
        f"💰 Custo: R$ {cost:.2f}/pacote\n\n"
        "Confirmar cadastro?"
    )

    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if target_message:
        await target_message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_document_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de arquivos (CSV, PDF)"""
    user_id = update.effective_user.id
    
    # Apenas admin pode enviar arquivos
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode enviar arquivos.")
        return
    
    # Cria sessão automaticamente se não existe
    session = session_manager.get_active_session()
    state = session_manager.get_admin_state(user_id)
    
    if not session:
        today = datetime.now().strftime("%Y-%m-%d")
        session_manager.start_new_session(today)
        session_manager.set_admin_state(user_id, "awaiting_base_address")
        
        await update.message.reply_text(
            "🟢 <b>Sessão criada automaticamente!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Data: <b>{today}</b>\n\n"
            "🎯 Antes de importar, defina a <b>LOCALIZAÇÃO DA BASE</b>:\n\n"
            "📍 <b>OPÇÃO 1 (RECOMENDADO):</b>\n"
            "   Use o 📎 anexo → 📍 Localização do Telegram\n"
            "   ✅ Otimiza bateria das bikes!\n\n"
            "📝 <b>OPÇÃO 2:</b>\n"
            "   Digite o endereço completo\n"
            "   <i>Ex: Rua das Flores, 123 - Botafogo, RJ</i>",
            parse_mode='HTML'
        )
        return
    
    if state != "awaiting_romaneios":
        await update.message.reply_text(
            "⚠️ <b>Configure a base primeiro!</b>\n\n"
            "Envie o endereço da base (onde o carro está) para continuar.",
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
        if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            await update.message.reply_text(
                "📊 <b>PROCESSANDO EXCEL SHOPEE...</b>\n\n"
                "• Lendo planilha\n"
                "• Extraindo lat/long embutidos\n"
                "• Validando dados\n\n"
                "⏳ <i>Aguarde...</i>",
                parse_mode='HTML'
            )
            # Salva temporariamente para openpyxl
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(bytes(file_content))
                tmp_path = tmp.name
            
            try:
                from bot.services.shopee_parser import ShopeeRomaneioParser
                deliveries = ShopeeRomaneioParser.parse(tmp_path)
                addresses = [{
                    'id': d.tracking,
                    'address': f"{d.address}, {d.bairro}, {d.city}",
                    'lat': d.latitude,
                    'lon': d.longitude,
                    'priority': 'normal'
                } for d in deliveries]
            finally:
                import os
                os.unlink(tmp_path)
        
        elif file_name.endswith('.csv'):
            await update.message.reply_text(
                "📄 <b>PROCESSANDO CSV...</b>\n\n"
                "• Lendo linhas do arquivo\n"
                "• Validando formato\n"
                "• Extraíndo endereços\n\n"
                "⏳ <i>Aguarde...</i>",
                parse_mode='HTML'
            )
            addresses = parse_csv_romaneio(bytes(file_content))
        
        elif file_name.endswith('.pdf'):
            await update.message.reply_text(
                "📕 <b>PROCESSANDO PDF...</b>\n\n"
                "• Extraindo texto (OCR)\n"
                "• Identificando endereços\n"
                "• Validando dados\n\n"
                "⏳ <i>Isso pode demorar 10-20 segundos...</i>",
                parse_mode='HTML'
            )
            addresses = parse_pdf_romaneio(bytes(file_content))
        
        else:
            await update.message.reply_text(
                "❌ <b>FORMATO NÃO SUPORTADO!</b>\n\n"
                "📂 <b>Formatos aceitos:</b>\n"
                "• <b>.xlsx</b> - Excel Shopee (RECOMENDADO)\n"
                "• <b>.csv</b> - CSV genérico\n"
                "• <b>.pdf</b> - PDF scaneado (OCR)\n\n"
                "💡 Dica: Use o formato Excel da Shopee!",
                parse_mode='HTML'
            )
            return
        
        # Cria romaneio com endereços extraídos
        await create_romaneio_from_addresses(update, context, addresses)
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {e}")
        await update.message.reply_text(
            f"❌ <b>ERRO NO PROCESSAMENTO!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚫 Detalhes do erro:\n"
            f"<code>{str(e)[:200]}</code>\n\n"
            f"💡 <b>ALTERNATIVAS:</b>\n\n"
            f"1️⃣ Cole os endereços manualmente\n"
            f"   (um por linha)\n\n"
            f"2️⃣ Use arquivo Excel da Shopee\n"
            f"   Formato oficial: DD-MM-YYYY Nome.xlsx\n\n"
            f"3️⃣ Verifique o formato do arquivo\n"
            f"   CSV: tracking,endereco,lat,lon",
            parse_mode='HTML'
        )


async def process_text_romaneio(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Processa romaneio de texto (manual)"""
    addresses = parse_text_romaneio(text)
    
    if not addresses:
        await update.message.reply_text(
            "❌ <b>NENHUM ENDEREÇO IDENTIFICADO</b>\n\n"
            "Não consegui encontrar endereços válidos no texto!\n\n"
            "<b>📝 FORMATO ESPERADO:</b>\n"
            "Rua Exemplo, 123 - Bairro, Cidade\n"
            "Av. Principal, 456 - Outro Bairro\n\n"
            "<b>💡 DICAS:</b>\n"
            "• Um endereço por linha\n"
            "• Inclua rua, número e bairro\n"
            "• Evite abreviações demais",
            parse_mode='HTML'
        )
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
            # Se veio do Excel Shopee, já tem lat/lon
            lat = addr.get("lat")
            lon = addr.get("lon")
        else:
            address = addr
            package_id = f"PKG{i:03d}"
            priority = "normal"
            lat = None
            lon = None
        
        # Geocoding com cache inteligente (só se não vier pronto)
        if lat is None or lon is None:
            lat, lng = geocoding_service.geocode(address)
        else:
            lng = lon
        
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
        # Gera mapa para preview/admin
        stops_data = []
        for i, point in enumerate(optimized):
            status = 'current' if i == 0 else 'pending'
            stops_data.append((point.lat, point.lng, point.address, 1, status))

        eta_minutes = max(10, route.total_distance_km / 25 * 60 + len(optimized) * 3)
        base_loc = (session.base_lat, session.base_lng, session.base_address) if session.base_lat and session.base_lng else None
        html = MapGenerator.generate_interactive_map(
            stops=stops_data,
            entregador_nome=f"{route.id}",
            current_stop=0,
            total_packages=route.total_packages,
            total_distance_km=route.total_distance_km,
            total_time_min=eta_minutes,
            base_location=base_loc
        )
        map_file = f"map_{route.id}.html"
        MapGenerator.save_map(html, map_file)
        route.map_file = map_file
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
    
    summary += "\n🚀 Agora atribua as rotas aos entregadores (pré-visualize os mapas abaixo):"
    await update.message.reply_text(summary, parse_mode='HTML')

    # Envia mapas para o admin pré-visualizar e escolher entregador
    import asyncio
    from telegram.error import NetworkError, TimedOut
    
    for route in routes:
        caption = (
            f"🗺️ <b>Preview {route.id}</b>\n"
            f"📦 Pacotes: {route.total_packages}\n"
            f"🛣️ Distância: {route.total_distance_km:.1f} km\n"
            f"⏱️ ETA: ~{max(10, route.total_distance_km/25*60 + len(route.optimized_order)*3):.0f} min\n\n"
            "Selecione o entregador:" )

        keyboard = [[InlineKeyboardButton("Escolher entregador", callback_data=f"assign_route_{route.id}")]]

        if route.map_file:
            try:
                # Verifica tamanho do arquivo antes de enviar
                import os
                file_size = os.path.getsize(route.map_file)
                
                # Limite do Telegram: 50MB, mas vamos usar 20MB como segurança
                if file_size > 20 * 1024 * 1024:
                    logger.warning(f"Arquivo {route.map_file} muito grande ({file_size} bytes), enviando só mensagem")
                    raise ValueError("Arquivo muito grande")
                
                with open(route.map_file, 'rb') as f:
                    # Timeout de 30 segundos para envio
                    await asyncio.wait_for(
                        context.bot.send_document(
                            chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                            document=f,
                            filename=route.map_file,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            read_timeout=30,
                            write_timeout=30
                        ),
                        timeout=45.0
                    )
                    logger.info(f"✅ Mapa {route.id} enviado com sucesso")
                    
            except (asyncio.TimeoutError, NetworkError, TimedOut, ValueError) as e:
                logger.warning(f"⚠️ Timeout/erro ao enviar mapa {route.id}: {e}. Enviando só texto...")
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=caption + f"\n\n⚠️ Mapa disponível em: {route.map_file}",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"❌ Falha ao enviar mapa {route.id} para admin: {e}")
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=caption + "\n\n❌ Erro ao enviar mapa",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await context.bot.send_message(
                chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                text=caption,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Pequeno delay entre envios para evitar rate limit
        await asyncio.sleep(0.5)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de botões inline"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("assign_route_"):
        route_id = data.replace("assign_route_", "")
        session_manager.save_temp_data(query.from_user.id, "assigning_route", route_id)
        
        # Mostra lista de entregadores
        deliverers = [d for d in deliverer_service.get_all_deliverers() if d.is_active]
        keyboard = []
        for partner in deliverers:
            keyboard.append([InlineKeyboardButton(
                f"{partner.name} {'(Sócio)' if partner.is_partner else ' (Colaborador)'}",
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

    elif data.startswith("add_partner_"):
        is_partner = data.endswith("yes")
        temp = session_manager.get_temp_data(query.from_user.id, "new_deliverer") or {}
        temp["is_partner"] = is_partner
        temp["capacity"] = 9999  # Sem limite; rotas definem qtd de pacotes
        if is_partner:
            temp["cost"] = 0.0
            session_manager.save_temp_data(query.from_user.id, "new_deliverer", temp)
            await send_deliverer_summary(update, query.from_user.id, temp)
        else:
            session_manager.save_temp_data(query.from_user.id, "new_deliverer", temp)
            session_manager.set_admin_state(query.from_user.id, "adding_deliverer_cost")
            await query.edit_message_text(
                "💰 Qual o <b>custo por pacote</b>? (ex: 1.50)",
                parse_mode='HTML'
            )

    elif data == "confirm_add_deliverer":
        temp = session_manager.get_temp_data(query.from_user.id, "new_deliverer") or {}
        required = ["name", "telegram_id", "is_partner"]
        if not all(key in temp for key in required):
            await query.edit_message_text(
                "⚠️ Dados incompletos. Refaça o cadastro com /add_entregador.",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(query.from_user.id)
            return

        # Verifica duplicidade
        existing = deliverer_service.get_deliverer(temp["telegram_id"])
        if existing:
            await query.edit_message_text(
                "❌ Já existe um entregador com esse ID.",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(query.from_user.id)
            return

        deliverer = deliverer_service.add_deliverer(
            telegram_id=temp["telegram_id"],
            name=temp["name"],
            is_partner=temp.get("is_partner", False),
            max_capacity=temp.get("capacity", 9999)
        )

        # Atualiza custo customizado se colaborador
        if not deliverer.is_partner and "cost" in temp:
            deliverer_service.update_deliverer(temp["telegram_id"], cost_per_package=temp["cost"])

        tipo_emoji = "🤝" if deliverer.is_partner else "💼"
        custo = 0.0 if deliverer.is_partner else temp.get("cost", deliverer.cost_per_package)

        await query.edit_message_text(
            f"✅ <b>Entregador cadastrado!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{tipo_emoji} <b>{deliverer.name}</b>\n"
            f"🆔 ID: <code>{deliverer.telegram_id}</code>\n"
            f"📦 Capacidade: {deliverer.max_capacity} pacotes/dia\n"
            f"💰 Custo: R$ {custo:.2f}/pacote",
            parse_mode='HTML'
        )

        session_manager.clear_admin_state(query.from_user.id)

    elif data == "cancel_add_deliverer":
        session_manager.clear_admin_state(query.from_user.id)
        await query.edit_message_text(
            "Cadastro cancelado.",
            parse_mode='HTML'
        )

    # ═══════════════════════════════════════════════
    # HANDLERS DOS BOTÕES DO /help
    # ═══════════════════════════════════════════════
    
    elif data == "help_import":
        await query.edit_message_text(
            "📦 <b>IMPORTAR ROMANEIOS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Como importar:</b>\n"
            "1. Digite <code>/importar</code> ou\n"
            "2. Envie o arquivo diretamente\n\n"
            "<b>Formatos aceitos:</b>\n"
            "• Excel Shopee (.xlsx) — Recomendado\n"
            "• CSV genérico (.csv)\n"
            "• PDF Romaneio (.pdf)\n"
            "• Texto manual (.txt)\n\n"
            "💡 Pode enviar múltiplos arquivos!\n"
            "O sistema consolida automaticamente.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar", callback_data="help_back")
            ]])
        )
    
    elif data == "help_team":
        deliverers = deliverer_service.get_all_deliverers()
        if not deliverers:
            team_text = "❌ Nenhum entregador cadastrado ainda.\n\nUse <code>/add_entregador</code> para começar!"
        else:
            team_text = f"👥 <b>EQUIPE ATUAL</b> ({len(deliverers)} membros)\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for d in deliverers[:5]:  # Limita a 5 para não ficar muito longo
                tipo = "🤝 PARCEIRO" if d.is_partner else "💼 COLABORADOR"
                status = "🟢 Ativo" if d.is_active else "🔴 Inativo"
                team_text += f"{tipo} <b>{d.name}</b>\n"
                team_text += f"   {status} • {d.max_capacity} pacotes/dia\n\n"
            
            if len(deliverers) > 5:
                team_text += f"\n<i>...e mais {len(deliverers) - 5} entregadores</i>\n"
            
            team_text += "\nUse <code>/entregadores</code> para ver todos"
        
        await query.edit_message_text(
            team_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar", callback_data="help_back")
            ]])
        )
    
    elif data == "help_status":
        session = session_manager.get_active_session()
        if not session or not session.routes:
            status_text = (
                "📊 <b>STATUS ATUAL</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "❌ Nenhuma sessão ativa no momento.\n\n"
                "Comece importando romaneios:\n"
                "<code>/importar</code>"
            )
        else:
            total_packages = sum(r.total_packages for r in session.routes)
            total_distance = sum(r.total_distance_km for r in session.routes)
            assigned = sum(1 for r in session.routes if r.assigned_to_telegram_id)
            
            status_text = (
                f"📊 <b>STATUS DA SESSÃO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🗓️ Sessão: {session.session_id}\n"
                f"📍 Base: {session.base_address or 'Não definida'}\n\n"
                f"📦 Total de pacotes: <b>{total_packages}</b>\n"
                f"🛣️ Distância total: <b>{total_distance:.1f} km</b>\n"
                f"👥 Rotas criadas: <b>{len(session.routes)}</b>\n"
                f"✅ Rotas distribuídas: <b>{assigned}/{len(session.routes)}</b>\n\n"
            )
            
            if assigned < len(session.routes):
                status_text += "💡 Use <code>/otimizar</code> para distribuir rotas pendentes"
            else:
                status_text += "🎉 Todas as rotas foram distribuídas!"
        
        await query.edit_message_text(
            status_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar", callback_data="help_back")
            ]])
        )
    
    elif data == "help_ranking":
        top_deliverers = gamification_service.get_top_deliverers(limit=5)
        
        if not top_deliverers:
            ranking_text = (
                "🏆 <b>RANKING</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "❌ Nenhuma entrega registrada ainda.\n\n"
                "O ranking aparecerá após as primeiras entregas!"
            )
        else:
            ranking_text = "🏆 <b>TOP 5 ENTREGADORES</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for i, (deliverer, stats) in enumerate(top_deliverers):
                medal = medals[i] if i < len(medals) else f"{i+1}."
                ranking_text += (
                    f"{medal} <b>{deliverer.name}</b>\n"
                    f"   📦 {stats.get('deliveries', 0)} entregas\n"
                    f"   ⭐ Nível {stats.get('level', 1)}\n\n"
                )
            
            ranking_text += "\nUse <code>/ranking</code> para ver detalhes"
        
        await query.edit_message_text(
            ranking_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar", callback_data="help_back")
            ]])
        )
    
    elif data == "help_quickstart":
        quickstart_text = """⚡ <b>INÍCIO RÁPIDO</b> — 3 passos simples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>┏━━ PASSO 1: IMPORTAR</b>
┃  
┃  Digite: <code>/importar</code>
┃  Ou envie arquivo diretamente
┃  
┃  💡 Aceita: Excel, CSV, PDF, TXT
┃  💡 Pode enviar vários de uma vez
┃
<b>┣━━ PASSO 2: SELECIONAR EQUIPE</b>
┃  
┃  Bot mostra entregadores disponíveis
┃  Marque quem vai trabalhar hoje
┃  
┃  💡 Sistema calcula capacidade total
┃
<b>┗━━ PASSO 3: OTIMIZAR</b>
   
   Digite: <code>/otimizar</code>
   
   Sistema automaticamente:
   ✓ Divide rotas geograficamente
   ✓ Otimiza cada percurso
   ✓ Envia mapa para cada um
   
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎯 RESULTADO:</b>
Cada entregador recebe:
• Mapa HTML interativo
• Ordem otimizada de entregas
• Botões de navegação Google Maps
• Sistema de marcação de status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱️ <b>Tempo total: ~2 minutos</b>
🚀 <b>Economia: 79% vs rota original</b>"""

        await query.edit_message_text(
            quickstart_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar", callback_data="help_back")
            ]])
        )
    
    elif data == "help_back":
        # Volta para o /help principal
        await cmd_help(update, context)
        return
    
    elif data == "deliverer_tip":
        tips = [
            "💡 <b>Dica do Dia:</b>\n\nSempre siga a ordem do mapa. A IA já otimizou a melhor rota para economizar tempo e combustível!",
            "💡 <b>Dica do Dia:</b>\n\nMarque as entregas imediatamente após concluir. Isso ajuda o admin a monitorar em tempo real!",
            "💡 <b>Dica do Dia:</b>\n\nAgrupe entregas do mesmo STOP (mesmo endereço). Você ganha tempo e aumenta sua eficiência!",
            "💡 <b>Dica do Dia:</b>\n\nUse o botão 'Google Maps' em cada pin do mapa. A navegação já vem configurada!",
            "💡 <b>Dica do Dia:</b>\n\nComunique problemas rapidamente ao admin. Quanto antes ele souber, mais rápido pode ajudar!"
        ]
        
        import random
        tip = random.choice(tips)
        
        await query.edit_message_text(
            tip,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Outra dica", callback_data="deliverer_tip")
            ]])
        )

    elif data.startswith("deliver_"):
        package_id = data.replace("deliver_", "")
        delivered = session_manager.mark_package_delivered(query.from_user.id, package_id)

        if delivered:
            # Atualiza stats básicas
            try:
                deliverer_service.update_stats_after_delivery(query.from_user.id, True, delivery_time_minutes=10)
            except Exception as e:
                logger.warning(f"Falha ao atualizar stats do entregador: {e}")

            await query.edit_message_text(
                f"✅ Pacote <code>{package_id}</code> marcado como entregue!",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ Pacote não encontrado na sua rota ativa.",
                parse_mode='HTML'
            )


async def send_route_to_deliverer(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, route: Route, session):
    """Envia rota formatada para o entregador"""
    # Garante que existe mapa HTML
    if not route.map_file:
        stops_data = []
        for i, point in enumerate(route.optimized_order):
            status = 'current' if i == 0 else 'pending'
            stops_data.append((point.lat, point.lng, point.address, 1, status))

        eta_minutes = max(10, route.total_distance_km / 25 * 60 + len(route.optimized_order) * 3)
        session = session_manager.get_session()
        base_loc = (session.base_lat, session.base_lng, session.base_address) if session and session.base_lat and session.base_lng else None
        html = MapGenerator.generate_interactive_map(
            stops=stops_data,
            entregador_nome=f"{route.id}",
            current_stop=0,
            total_packages=route.total_packages,
            total_distance_km=route.total_distance_km,
            total_time_min=eta_minutes,
            base_location=base_loc
        )
        route.map_file = f"map_{route.id}.html"
        MapGenerator.save_map(html, route.map_file)

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

    if route.map_file:
        import asyncio
        from telegram.error import NetworkError, TimedOut
        try:
            import os
            file_size = os.path.getsize(route.map_file)
            
            if file_size > 20 * 1024 * 1024:
                logger.warning(f"Arquivo {route.map_file} muito grande para entregador {telegram_id}")
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"⚠️ Mapa muito grande. Disponível em: {route.map_file}"
                )
            else:
                with open(route.map_file, 'rb') as f:
                    await asyncio.wait_for(
                        context.bot.send_document(
                            chat_id=telegram_id,
                            document=f,
                            filename=route.map_file,
                            caption="🗺️ Abra o mapa HTML para navegar a rota.",
                            read_timeout=30,
                            write_timeout=30
                        ),
                        timeout=45.0
                    )
                    logger.info(f"✅ Mapa enviado para entregador {telegram_id}")
        except (asyncio.TimeoutError, NetworkError, TimedOut) as e:
            logger.warning(f"⚠️ Timeout ao enviar mapa para entregador {telegram_id}: {e}")
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"⚠️ Não foi possível enviar o mapa. Disponível em: {route.map_file}"
            )
        except Exception as e:
            logger.error(f"❌ Falha ao enviar mapa para entregador {telegram_id}: {e}")
            await context.bot.send_message(
                chat_id=telegram_id,
                text="❌ Erro ao enviar mapa. Contate o administrador."
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
        await update.message.reply_text(
            "📭 <b>NENHUMA SESSÃO ATIVA</b>\n\n"
            "Use <code>/importar</code> para começar um novo dia de entregas!",
            parse_mode='HTML'
        )
        return
    
    # Barra de progresso visual
    total = session.total_packages
    entregues = session.total_delivered
    percent = (entregues / total * 100) if total > 0 else 0
    bar_length = 10
    filled = int(bar_length * percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    msg = f"📊 <b>STATUS DA OPERAÇÃO</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📅 Data: <b>{session.date}</b>\n"
    msg += f"📍 Base: {session.base_address}\n\n"
    msg += f"<b>📦 ENTREGAS:</b>\n"
    msg += f"{bar} {percent:.0f}%\n\n"
    msg += f"✅ Entregues: <b>{entregues}</b>\n"
    msg += f"⏳ Pendentes: <b>{session.total_pending}</b>\n"
    msg += f"📊 Total: <b>{total}</b> pacotes\n\n"
    
    if session.routes:
        msg += "<b>🚚 ROTAS ATIVAS:</b>\n\n"
        for i, route in enumerate(session.routes, 1):
            entregador = route.assigned_to_name or "❓ Sem entregador"
            progresso = f"{route.delivered_count}/{route.total_packages}"
            percent_rota = route.completion_rate
            
            emoji_status = "🟢" if percent_rota == 100 else "🟡" if percent_rota > 50 else "🔴"
            
            msg += f"{emoji_status} <b>Rota {i}</b> - {entregador}\n"
            msg += f"   📦 {progresso} ({percent_rota:.0f}%) | 🛣️ {route.total_distance_km:.1f}km\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def show_financial_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Relatório financeiro"""
    session = session_manager.get_active_session()
    
    if not session:
        await update.message.reply_text(
            "📭 <b>NENHUMA SESSÃO ATIVA</b>\n\n"
            "Não há dados financeiros para exibir.",
            parse_mode='HTML'
        )
        return
    
    msg = f"💰 <b>RELATÓRIO FINANCEIRO</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📅 Data: <b>{session.date}</b>\n\n"
    
    costs_by_deliverer = {}
    deliveries_by_deliverer = {}
    
    for route in session.routes:
        if route.assigned_to_telegram_id:
            partner = BotConfig.get_partner_by_id(route.assigned_to_telegram_id)
            if partner:
                cost = route.delivered_count * partner.cost_per_package
                costs_by_deliverer[partner.name] = costs_by_deliverer.get(partner.name, 0) + cost
                deliveries_by_deliverer[partner.name] = deliveries_by_deliverer.get(partner.name, 0) + route.delivered_count
    
    if costs_by_deliverer:
        msg += "<b>💸 CUSTOS POR ENTREGADOR:</b>\n\n"
        for name in sorted(costs_by_deliverer.keys()):
            cost = costs_by_deliverer[name]
            deliveries = deliveries_by_deliverer[name]
            emoji = "🤝" if cost == 0 else "💼"
            msg += f"{emoji} <b>{name}</b>\n"
            msg += f"   📦 {deliveries} entregas\n"
            msg += f"   💵 R$ {cost:.2f}\n\n"
    
    total_cost = sum(costs_by_deliverer.values())
    total_deliveries = sum(deliveries_by_deliverer.values())
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"<b>📊 TOTAIS:</b>\n"
    msg += f"📦 Entregas: <b>{total_deliveries}</b>\n"
    msg += f"💰 Custo Total: <b>R$ {total_cost:.2f}</b>\n\n"
    
    if total_deliveries > 0:
        avg_cost = total_cost / total_deliveries
        msg += f"📈 Custo Médio: R$ {avg_cost:.2f}/entrega\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━"
    
    await update.message.reply_text(msg, parse_mode='HTML')


# ==================== DELIVERER MANAGEMENT ====================

async def cmd_add_deliverer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona novo entregador - Admin only"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Comando exclusivo para admin.")
        return

    # Inicia wizard guiado
    session_manager.clear_admin_state(user_id)
    session_manager.set_admin_state(user_id, "adding_deliverer_name")
    session_manager.save_temp_data(user_id, "new_deliverer", {})

    await update.message.reply_text(
        "🧑‍💼 <b>Cadastro de Entregador</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Vamos cadastrar em 4 passos rápidos.\n\n"
        "1️⃣ Nome completo do entregador?",
        parse_mode='HTML'
    )


async def cmd_list_deliverers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os entregadores - Admin only"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Comando exclusivo para admin.")
        return
    
    deliverers = deliverer_service.get_all_deliverers()
    
    if not deliverers:
        await update.message.reply_text(
            "📭 <b>NENHUM ENTREGADOR CADASTRADO</b>\n\n"
            "Seu time está vazio! Use:\n\n"
            "<code>/add_entregador</code> - Cadastrar novo entregador",
            parse_mode='HTML'
        )
        return
    
    active = [d for d in deliverers if d.is_active]
    inactive = [d for d in deliverers if not d.is_active]
    
    msg = "👥 <b>TIME DE ENTREGADORES</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if active:
        msg += f"✅ <b>ATIVOS</b> ({len(active)})\n\n"
        for i, d in enumerate(active, 1):
            tipo_emoji = "🤝" if d.is_partner else "💼"
            tipo_texto = "Parceiro" if d.is_partner else "Terceiro"
            
            # Status baseado na taxa de sucesso
            if d.success_rate >= 95:
                status_emoji = "🌟"
            elif d.success_rate >= 80:
                status_emoji = "🟢"
            elif d.success_rate >= 60:
                status_emoji = "🟡"
            else:
                status_emoji = "🔴"
            
            msg += f"{status_emoji} <b>{i}. {d.name}</b> ({tipo_emoji} {tipo_texto})\n"
            msg += f"   🆔 ID: <code>{d.telegram_id}</code>\n"
            msg += f"   📦 Capacidade: {d.max_capacity} pacotes/dia\n"
            msg += f"   💰 Custo: R$ {d.cost_per_package:.2f}/pacote\n"
            msg += f"   📊 Stats: {d.total_deliveries} entregas | {d.success_rate:.0f}% sucesso\n\n"
    
    if inactive:
        msg += f"\n❌ <b>INATIVOS</b> ({len(inactive)})\n\n"
        for d in inactive:
            msg += f"• {d.name} (ID: {d.telegram_id})\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎮 Ranking de entregadores com gamificação"""
    user_id = update.effective_user.id
    
    # Qualquer um pode ver ranking
    leaderboard = gamification_service.get_leaderboard(limit=10)
    
    if not leaderboard:
        await update.message.reply_text(
            "🎮 <b>RANKING VAZIO</b>\n\n"
            "Ninguém fez entregas ainda!\n"
            "Comece a trabalhar e domine a parada! 🔥",
            parse_mode='HTML'
        )
        return
    
    msg = "🏆 <b>RANKING DOS ENTREGADORES</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for entry in leaderboard:
        # Medalhas
        if entry.rank == 1:
            medal = "🥇"
        elif entry.rank == 2:
            medal = "🥈"
        elif entry.rank == 3:
            medal = "🥉"
        else:
            medal = f"🟦 {entry.rank}º"
        
        # Badges
        badge_icons = " ".join([b.type.value.split()[0] for b in entry.badges[:3]])
        if not badge_icons:
            badge_icons = "—"
        
        # Streak
        streak_text = f"🔥 {entry.streak_days}d" if entry.streak_days > 0 else ""
        
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
            "🧠 <b>OTIMIZAR E DISTRIBUIR ROTAS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📝 FORMATO:</b>\n"
            "<code>/otimizar &lt;arquivo.xlsx&gt; &lt;N_entregadores&gt;</code>\n\n"
            "<b>🎯 EXEMPLO:</b>\n"
            "<code>/otimizar romaneio_05-11.xlsx 3</code>\n\n"
            "<b>⚡ O QUE ACONTECE:</b>\n"
            "1️⃣ Lê romaneio da Shopee\n"
            "2️⃣ Agrupa entregas por STOP (mesmo prédio)\n"
            "3️⃣ Divide geograficamente (K-means)\n"
            "4️⃣ Otimiza cada rota (Scooter Mode)\n"
            "5️⃣ Gera mapa HTML interativo\n"
            "6️⃣ Envia pra cada entregador automaticamente\n\n"
            "❗ Certifique-se de ter <code>/importar</code> o arquivo antes!",
            parse_mode='HTML'
        )
        return
    
    excel_path = args[0]
    try:
        num_entregadores = int(args[1])
    except ValueError:
        await update.message.reply_text("Numero de entregadores deve ser um inteiro.")
        return
    
    await update.message.reply_text(
        "⏳ <b>PROCESSANDO ROMANEIO...</b>\n\n"
        "• Carregando entregas do arquivo\n"
        "• Agrupando por STOP\n"
        "• Dividindo entre entregadores\n"
        "• Otimizando rotas (Scooter Mode)\n\n"
        "🔥 <i>Isso pode levar uns 10-20 segundos...</i>",
        parse_mode='HTML'
    )
    
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
                f"❌ <b>ENTREGADORES INSUFICIENTES!</b>\n\n"
                f"👥 Cadastrados: <b>{len(all_deliverers)}</b>\n"
                f"✅ Necessários: <b>{num_entregadores}</b>\n\n"
                f"🚨 <b>Faltam {num_entregadores - len(all_deliverers)} entregadores!</b>\n\n"
                f"Use <code>/add_entregador</code> pra cadastrar mais.",
                parse_mode='HTML'
            )
            return
        
        # Monta dicionario de entregadores
        selected = all_deliverers[:num_entregadores]
        entregadores_info = {d['telegram_id']: d['name'] for d in selected}
        
        # Divide romaneio
        divider = RoteoDivider()
        routes = divider.divide_romaneio(deliveries, num_entregadores, entregadores_info)
        
        # Envia resumo pro admin
        total_distance = sum(r.total_distance_km for r in routes)
        total_time = sum(r.total_time_minutes for r in routes)
        
        summary = f"✅ <b>ROTAS OTIMIZADAS E DISTRIBUÍDAS!</b>\n"
        summary += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        summary += f"📦 <b>RESUMO GERAL:</b>\n"
        summary += f"• Total: {len(deliveries)} pacotes\n"
        summary += f"• Entregadores: {num_entregadores}\n"
        summary += f"• Distância Total: {total_distance:.1f} km\n"
        summary += f"• Tempo Total: {total_time:.0f} min\n\n"
        
        summary += f"👥 <b>ROTAS POR ENTREGADOR:</b>\n\n"
        
        for i, route in enumerate(routes, 1):
            summary += f"🔸 <b>{i}. {route.entregador_nome}</b>\n"
            summary += f"   📦 {route.total_packages} pacotes | 📍 {len(route.stops)} paradas\n"
            summary += f"   🛣️ {route.total_distance_km:.1f}km | ⏱️ {route.total_time_minutes:.0f}min\n"
            summary += f"   ⚡ Atalhos: {route.shortcuts}\n\n"
        
        summary += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        summary += f"📲 Mapas HTML enviados para cada entregador!\n"
        summary += f"👀 Monitore pelo dashboard: http://localhost:8765\n\n"
        summary += f"🔥 <i>Bora faturar!</i>"
        
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
            session = session_manager.get_session()
            base_loc = (session.base_lat, session.base_lng, session.base_address) if session and session.base_lat and session.base_lng else None
            html = MapGenerator.generate_interactive_map(
                stops=stops_data,
                entregador_nome=route.entregador_nome,
                current_stop=0,
                total_packages=route.total_packages,
                total_distance_km=route.total_distance_km,
                total_time_min=route.total_time_minutes,
                base_location=base_loc
            )
            
            # Salva temporariamente
            map_file = f"rota_{route.entregador_id}.html"
            MapGenerator.save_map(html, map_file)
            
            # Envia pro entregador
            try:
                msg = (
                    f"🏍️ <b>SUA ROTA DO DIA ESTÁ PRONTA!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📦 <b>RESUMO:</b>\n"
                    f"• Pacotes: <b>{route.total_packages}</b>\n"
                    f"• Paradas: <b>{len(route.stops)}</b>\n"
                    f"• Distância: <b>{route.total_distance_km:.1f} km</b>\n"
                    f"• Tempo: <b>{route.total_time_minutes:.0f} min</b>\n"
                    f"• Atalhos: <b>{route.shortcuts}</b> ⚡\n\n"
                    f"🎯 <b>INÍCIO:</b>\n{route.start_point[2][:60]}\n\n"
                    f"🏁 <b>FIM:</b>\n{route.end_point[2][:60]}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🗺️ Baixe o <b>mapa HTML</b> abaixo!\n"
                    f"🔥 Abra no navegador e siga os pins!\n\n"
                    f"<i>Boa sorte, parceiro! 🚀</i>"
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
    """Inicia o bot com retry automático"""
    import os
    import time
    
    # Validação crítica de variáveis de ambiente
    token = os.getenv('TELEGRAM_BOT_TOKEN') or BotConfig.TELEGRAM_TOKEN
    admin_id = os.getenv('ADMIN_TELEGRAM_ID')
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN não configurado! Defina a variável de ambiente.")
        print("❌ ERRO CRÍTICO: TELEGRAM_BOT_TOKEN vazio.")
        print("Configure com: export TELEGRAM_BOT_TOKEN='seu_token' (Linux/Mac)")
        print("ou: $env:TELEGRAM_BOT_TOKEN='seu_token' (Windows PowerShell)")
        return
    
    if not admin_id:
        logger.warning("⚠️ ADMIN_TELEGRAM_ID não configurado. Bot rodará mas sem admin.")
    else:
        logger.info(f"✅ Admin ID configurado: {admin_id}")
    
    logger.info(f"✅ Token presente: {token[:10]}...{token[-4:]}")
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Configurar timeouts no builder do Application
            app = (
                Application.builder()
                .token(token)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .pool_timeout(30)
                .build()
            )
            
            # Handlers
            app.add_handler(CommandHandler("start", cmd_start))
            app.add_handler(CommandHandler("help", cmd_help))
            app.add_handler(CommandHandler("importar", handle_document_message))  # Novo comando!
            app.add_handler(CommandHandler("otimizar", cmd_distribuir_rota))  # Renomeado!
            app.add_handler(CommandHandler("distribuir", cmd_distribuir_rota))  # Mantido por compatibilidade
            app.add_handler(CommandHandler("fechar_rota", cmd_fechar_rota))
            app.add_handler(CommandHandler("add_entregador", cmd_add_deliverer))
            app.add_handler(CommandHandler("entregadores", cmd_list_deliverers))
            app.add_handler(CommandHandler("ranking", cmd_ranking))
            app.add_handler(CommandHandler("prever", cmd_predict_time))
            app.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
            app.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
            app.add_handler(CallbackQueryHandler(handle_callback_query))
            
            logger.info(f"🚀 Bot iniciado! (Tentativa {retry_count + 1}/{max_retries})")
            
            # run_polling sem parâmetros de timeout (já configurados no builder)
            app.run_polling(
                drop_pending_updates=True, 
                allowed_updates=["message", "callback_query"]
            )
            
            # Se chegou aqui, o bot foi parado normalmente
            break
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot encerrado pelo usuário.")
            break
        except Exception as e:
            from telegram.error import Conflict, NetworkError, TimedOut
            
            if isinstance(e, Conflict):
                logger.error(
                    "❌ CONFLITO: Múltiplas instâncias do bot rodando!\n"
                    "Soluções:\n"
                    "1. Pare qualquer bot rodando localmente\n"
                    "2. No Render: certifique que é Background Worker (não Web Service)\n"
                    "3. Aguarde 1-2 minutos para timeout do outro bot"
                )
                break  # Não tenta reconectar em caso de conflito
                
            elif isinstance(e, (NetworkError, TimedOut)):
                retry_count += 1
                wait_time = min(30, 5 * retry_count)  # Espera progressiva: 5, 10, 15, 20, 25 segundos
                logger.warning(
                    f"⚠️ Erro de rede/timeout: {e}\n"
                    f"🔄 Tentando reconectar em {wait_time} segundos... "
                    f"(Tentativa {retry_count}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                retry_count += 1
                logger.error(f"❌ Erro no polling: {e}", exc_info=True)
                if retry_count < max_retries:
                    wait_time = 10
                    logger.info(f"🔄 Tentando reconectar em {wait_time} segundos...")
                    time.sleep(wait_time)
    
    if retry_count >= max_retries:
        logger.error("❌ Número máximo de tentativas alcançado. Bot encerrado.")
        print("\n⚠️ Bot parou após múltiplas falhas. Verifique sua conexão e tente novamente.")


if __name__ == "__main__":
    run_bot()
