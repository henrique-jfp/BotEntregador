# -*- coding: utf-8 -*-
"""
🚀 BOT TELEGRAM - Handler principal
Fluxo completo de admin + entregadores
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import datetime, timedelta
from .config import BotConfig, DeliveryPartner
from .session import session_manager, Romaneio, Route
from .models import Deliverer
from .clustering import DeliveryPoint, TerritoryDivider
from .parsers import parse_csv_romaneio, parse_pdf_romaneio, parse_text_romaneio
from .services import deliverer_service, geocoding_service, genetic_optimizer, gamification_service, predictor, dashboard_ws, scooter_optimizer, financial_service
from .services.map_generator import MapGenerator
from .services.barcode_separator import barcode_separator
from .services.route_analyzer import route_analyzer
from .colors import get_color_name, get_color_for_index
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
    """Comando /help - Lista completa de todas as funcionalidades"""
    user_id = update.effective_user.id
    
    if user_id == BotConfig.ADMIN_TELEGRAM_ID:
        # Mensagem 1 - Visão Geral + Importação
        msg1 = """<b>🚀 BOT MULTI-ENTREGADOR v5.0</b>
<i>Sistema Completo: Sessões + IA + Cores Automáticas</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📂 SESSÕES PERSISTENTES 🆕</b>
<code>/sessoes</code> — Gerenciar sessões
<code>/selecionar_sessao</code> — Escolher sessão ativa
• 💾 Auto-save em JSON (nunca perde dados)
• 📋 Ver todas (ativas + finalizadas)
• 🔵 Trocar entre sessões a qualquer momento
• 📊 Histórico completo com timestamps
• 🎨 Cores automáticas por entregador
• ⚠️ Múltiplas sessões simultâneas suportadas

<i>💡 Sistema "save game" - reinicia o bot sem medo!</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📦 IMPORTAÇÃO & ANÁLISE</b>
<code>/importar</code> — Enviar romaneios
• Shopee, ML, Loggi (CSV/PDF/TXT)
• Parsing automático + validação

<code>/analisar_rota</code> — IA avalia rota 🆕
• 🌍 Geocoding automático (sem lat/lon? sem problema!)
• 🤖 Score 0-10 + prós/contras
• 📊 Densidade, concentração, tempo estimado
• 🗺️ Mapa interativo + análise completa
• ✅ Decide se vale pegar ANTES de aceitar!

<code>/fechar_rota</code> — Dividir rotas
• K-Means + Algoritmo Genético
• 🎨 Atribui COR única por entregador
• Modo Scooter (79% menos distância)
• Mapa HTML com rotas reais (OSRM)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>👥 GESTÃO DE EQUIPE</b>
<code>/add_entregador</code> — Cadastrar
• Sócio ou Colaborador
• Capacidade + custo/pacote

<code>/entregadores</code> — Listar time
<code>/ranking</code> — Gamificação + XP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🎨 SEPARAÇÃO FÍSICA COM CORES</b>
<code>/modo_separacao</code> — Ativar
• 📦 Escaneia barcode → retorna COR DO ENTREGADOR
• 🔴🟢🔵 Usa cores atribuídas na divisão
• 🎯 Mostra sequência: "Entrega #5 de 23"
• 🔢 Etiquetadora MX550 (8 dígitos)
• ⚡ ~3s por pacote (20 pacotes/min)

<code>/status_separacao</code> — Progresso
<code>/fim_separacao</code> — Relatório final

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🗺️ ROTEIRIZAÇÃO INTELIGENTE</b>
🏍️ Scooter — Contrafluxo + atalhos
🚗 Padrão — Google Maps oficial
🧬 Genético — TSP otimizado
🛣️ OSRM — Rotas reais pelas ruas

• STOPS: múltiplos no mesmo pin
• HTML offline + turn-by-turn
• Leaflet Routing Machine integrado"""

        msg2 = """<b>💰 FINANCEIRO COMPLETO</b>

<code>/fechar_dia</code> — Manual
• Calcula custos colaboradores
• Relatório + histórico JSON

<code>/financeiro</code> — Relatórios
• Filtro: dia/semana/mês
• Receitas, custos, lucro
• Gráficos + tendências

<code>/fechar_semana</code> — Sócios
• Lucro após descontar custos
• % configurável por sócio

<code>/config_socios</code> — Define %
• Validação soma = 100%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏦 BANCO INTER (Opcional)</b>
<code>/config_banco_inter</code> — Config
• Upload .crt + .key
• Teste de conexão

<code>/fechar_dia_auto</code> — Auto
• Busca saldo real via API
• Calcula receita automaticamente

<code>/saldo_banco</code> — Consulta
• Saldo + últimas movimentações

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 EXPORTAÇÃO</b>
<code>/exportar</code> — Arquivos
• Excel (.xlsx) multi-abas
• PDF formatado + gráficos
• CSV análise externa"""

        msg3 = """<b>🔮 INTELIGÊNCIA ARTIFICIAL</b>

<code>/projecoes</code> — Machine Learning
• Prevê volume de entregas
• Estima receita futura
• Sugere dimensionamento equipe

<code>/dashboard</code> — Web UI
• Interface navegador
• Monitoramento real-time
• Mapa de calor + KPIs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📱 OUTROS</b>
<code>/start</code> — Menu principal
<code>/help</code> — Este guia
<code>/status</code> — Status sessão
<code>/fechar_rota</code> — Encerrar rota

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 FLUXO DIÁRIO</b>
1️⃣ /add_entregador → Cadastra
2️⃣ /config_socios → Define %
3️⃣ /importar → Romaneios
4️⃣ /otimizar → Rotas IA
5️⃣ /modo_separacao → Físico
6️⃣ Entregadores executam
7️⃣ /fechar_dia → Financeiro
8️⃣ /fechar_semana → Divisão

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🧠 TECNOLOGIA</b>
• K-Means + Algoritmo Genético
• Google Geocoding (cache local)
• Python 3.12 async
• Zero dependência APIs pagas

<b>🔥 Deploy: Railway.app | v4.0</b>"""

        # Envia as 3 mensagens sequencialmente
        await update.message.reply_text(msg1, parse_mode='HTML')
        await update.message.reply_text(msg2, parse_mode='HTML')
        await update.message.reply_text(msg3, parse_mode='HTML')
        
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


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚫 Cancela qualquer operação em andamento"""
    user_id = update.effective_user.id
    
    # Limpa estado do admin no SessionManager
    session_manager.clear_admin_state(user_id)
    
    # Limpa dados temporários do contexto do Telegram
    if context.user_data:
        context.user_data.clear()
        
    # Limpa dados temporários do services se houver
    if hasattr(session_manager, 'temp_data') and user_id in session_manager.temp_data:
        session_manager.temp_data.pop(user_id, None)
    
    # Remove teclado se houver
    reply_markup = ReplyKeyboardRemove()
    
    await update.message.reply_text(
        "🚫 <b>OPERAÇÃO CANCELADA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Todo o fluxo atual foi interrompido e os estados limpos.\n"
        "O bot está pronto para uma nova tarefa.\n\n"
        "<i>Dica: Se algo travou, isso geralmente resolve.</i>",
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
    
    # PRIORIDADE: Se modo separação ativo, tenta processar como código de barras
    if await handle_admin_barcode_scan(update, context, text):
        return  # Foi processado, não continua pro resto
    
    # ═══════════════════════════════════════════
    # MODO ANÁLISE DE ROTA - Aceita texto direto
    # ═══════════════════════════════════════════
    if state == "awaiting_route_value":
        try:
            val = float(text.replace(',', '.'))
        except:
            await update.message.reply_text("⚠️ Digite um número válido (ex: 120.50) ou 0.")
            return

        session_manager.save_temp_data(user_id, "route_value", val)
        session_manager.set_admin_state(user_id, "awaiting_analysis_file")
        
        await update.message.reply_text(
            "🔍 <b>ANÁLISE INTELIGENTE DE ROTA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📎 <b>AGORA, OS DADOS:</b>\n\n"
            "📄 <b>OPÇÃO 1: Arquivo Excel</b>\n"
            "   Anexe o .xlsx da Shopee\n\n"
            "📝 <b>OPÇÃO 2: Cole os Endereços</b>\n"
            "   ✅ <b>Aceita QUALQUER formato:</b>\n"
            "   • Um por linha\n"
            "   • Separados por ; (ponto-vírgula)\n"
            "   • Texto corrido\n"
            "   • Com ou sem numeração\n\n"
            "💡 <b>Pode colar direto aqui!</b>",
            parse_mode='HTML'
        )
        return

    if state == "awaiting_analysis_file":
        # Se não começou com /, é uma lista de endereços
        if not text.startswith('/'):
            await process_route_analysis_text(update, context, text)
            return
    
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
    
    # Handler financeiro: fechamento de dia (input de receita)
    if state == "closing_day_revenue":
        if text.lower() == '/cancelar':
            session_manager.clear_admin_state(user_id)
            await update.message.reply_text("❌ Fechamento cancelado.")
            return
        
        try:
            val = float(text.strip().replace(',', '.'))
            if val < 0: raise ValueError
        except:
            await update.message.reply_text("⚠️ Valor inválido. Tente novamente.")
            return

        # Salva receita
        data = session_manager.get_temp_data(user_id, "day_closing") or {}
        data['revenue'] = val
        data['expenses'] = []  # Lista vazia de despesas customizadas
        
        # Pega custos de entregadores se houver sessão (agora opcionais pois são sócios)
        session = session_manager.get_current_session()
        deliverer_costs = {}
        total_pkg = 0
        total_del = 0
        
        if session:
            for route in session.routes:
                if route.assigned_to_telegram_id:
                    partner = BotConfig.get_partner_by_id(route.assigned_to_telegram_id)
                    if partner:
                        # Se não for sócio, calcula custo
                        cost = route.delivered_count * partner.cost_per_package if not partner.is_partner else 0.0
                        if cost > 0:
                            deliverer_costs[partner.name] = deliverer_costs.get(partner.name, 0) + cost
                        total_pkg += route.total_packages
                        total_del += route.delivered_count
        
        data['deliverer_costs'] = deliverer_costs
        data['total_packages'] = total_pkg
        data['total_deliveries'] = total_del
        
        # Usa data alvo (se for retroativo) ou hoje
        if 'target_date' not in data:
            data['date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            data['date'] = data['target_date']
        
        session_manager.save_temp_data(user_id, "day_closing", data)
        session_manager.set_admin_state(user_id, "closing_day_menu")
        
        # Mostra menu de custos
        await _show_costs_menu(update, context, val, [])
        return

    # Handler financeiro: valor de um custo específico
    if state == "closing_day_expense_value":
        if text.lower() == '/cancelar':
            # Volta pro menu
            session_manager.set_admin_state(user_id, "closing_day_menu")
            data = session_manager.get_temp_data(user_id, "day_closing")
            await _show_costs_menu(update, context, data.get('revenue', 0), data.get('expenses', []))
            return

        try:
            cost_val = float(text.strip().replace(',', '.'))
            if cost_val < 0: raise ValueError
        except:
            await update.message.reply_text("⚠️ Valor inválido. Digite um número positivo.")
            return
            
        data = session_manager.get_temp_data(user_id, "day_closing")
        expense_type = data.get('current_expense_type', 'Outros')
        
        # Adiciona despesa
        new_expense = {
            'type': expense_type,
            'value': cost_val,
            'desc': f"Custo: {expense_type}"
        }
        data['expenses'].append(new_expense)
        del data['current_expense_type'] # limpa temp
        
        session_manager.save_temp_data(user_id, "day_closing", data)
        session_manager.set_admin_state(user_id, "closing_day_menu")
        
        await _show_costs_menu(update, context, data['revenue'], data['expenses'])
        return
    
    # Handler financeiro: fechamento automático (com banco inter)
    if state == "closing_day_auto_costs":
        if text.lower() == '/cancelar':
            session_manager.clear_admin_state(user_id)
            await update.message.reply_text("❌ Fechamento automático cancelado.")
            return
        
        try:
            other_costs = float(text.strip().replace(',', '.'))
            if other_costs < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Valor inválido. Digite um número válido ou 0.",
                parse_mode='HTML'
            )
            return
        
        # Busca dados temporários
        temp_data = session_manager.admin_temp_data.get(user_id, {})
        revenue = temp_data.get('revenue', 0)
        delivery_costs = temp_data.get('delivery_costs', 0)
        
        # Busca session para pacotes/entregas
        session = session_manager.get_current_session()
        total_packages = 0
        total_deliveries = 0
        
        if session and session.routes:
            for route in session.routes:
                total_packages += len(route.packages)
                total_deliveries += 1
        
        # Cria relatório
        report = financial_service.close_day(
            date=datetime.now(),
            revenue=revenue,
            deliverer_costs=delivery_costs,
            other_costs=other_costs,
            total_packages=total_packages,
            total_deliveries=total_deliveries
        )
        
        # Limpa estado
        session_manager.clear_admin_state(user_id)
        
        # Envia relatório
        msg = financial_service.format_daily_report(report)
        msg += "\n\n✅ <b>Fechamento automático concluído!</b>"
        msg += "\n🏦 <i>Receita obtida do Banco Inter</i>"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Handler financeiro: fechamento de semana (custos operacionais)
    if state == "closing_week":
        if text.lower() == '/cancelar':
            session_manager.clear_admin_state(user_id)
            await update.message.reply_text("❌ Fechamento de semana cancelado.")
            return
        
        try:
            operational_costs = float(text.strip().replace(',', '.'))
            if operational_costs < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Valor inválido. Digite um número válido ou 0.\n"
                "Ou /cancelar para abortar.",
                parse_mode='HTML'
            )
            return
        
        # Processa fechamento da semana
        data = session_manager.get_temp_data(user_id, "week_closing")
        week_start = datetime.strptime(data['week_start'], '%Y-%m-%d')
        
        try:
            report, message = financial_service.close_week(
                week_start=week_start,
                operational_costs=operational_costs
            )
            
            # Limpa estado
            session_manager.clear_admin_state(user_id)
            
            # Envia relatório
            await update.message.reply_text(message, parse_mode='HTML')
        
        except ValueError as e:
            await update.message.reply_text(
                f"❌ <b>ERRO AO FECHAR SEMANA</b>\n\n{str(e)}\n\n"
                "Certifique-se de ter fechado os dias da semana com <code>/fechar_dia</code>",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(user_id)
        
        return
    
    if text == "📦 Nova Sessão do Dia":
        # Inicia nova sessão
        today = datetime.now().strftime("%Y-%m-%d")
        session_manager.create_new_session(today)
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
    
    state = session_manager.get_admin_state(user_id)
    
    # ═══════════════════════════════════════════
    # MODO ANÁLISE DE ROTA (sem sessão necessária)
    # ═══════════════════════════════════════════
    if state == "awaiting_analysis_file":
        await process_route_analysis(update, context)
        return
    
    # ═══════════════════════════════════════════
    # IMPORTAÇÃO DE ROMANEIO (precisa de sessão)
    # ═══════════════════════════════════════════
    session = session_manager.get_current_session()
    
    if not session:
        today = datetime.now().strftime("%Y-%m-%d")
        session_manager.create_new_session(today)
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
    
    # ⚡ VALIDAÇÃO: Impede crash se document vier None
    if not document or not document.file_name:
        await update.message.reply_text(
            "❌ <b>Nenhum arquivo detectado!</b>\n\n"
            "📎 Anexe o arquivo e envie direto (sem comandos).",
            parse_mode='HTML'
        )
        return
    
    file_name = document.file_name.lower()
    
    # Download arquivo
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    
    # Parse baseado no tipo
    try:
        # Lógica de importação e processamento
        deliveries = []
        addresses = []
        
        if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            import os  # Garantindo import para uso posterior
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
                from bot_multidelivery.parsers.shopee_parser import ShopeeRomaneioParser
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
                
            # --- LÓGICA DE NOME DE SESSÃO DINÂMICA (ENZO STYLE) ---
            imported_count = len(session.romaneios)
            original_fn = document.file_name
            stem_name = os.path.splitext(original_fn)[0]
            
            # Formato padrão: dd/mm/aaaaDIADASEMANA-(manhã ou tarde)
            try:
                import locale
                try: locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
                except: pass
                dt_obj = datetime.strptime(session.date, '%Y-%m-%d')
                weekday_map = {0:'SEGUNDA', 1:'TERCA', 2:'QUARTA', 3:'QUINTA', 4:'SEXTA', 5:'SABADO', 6:'DOMINGO'}
                wday = weekday_map.get(dt_obj.weekday(), "DIA")
                std_name = f"{dt_obj.strftime('%d/%m/%Y')}{wday}-{session.period}"
            except:
                std_name = f"{session.date}-{session.period}"

            # Regra: Se é o 1º arquivo e é Shopee -> Nome = AT do arquivo
            # Se entrar mais um arquivo -> Nome = Padrãozão
            if imported_count == 0:
                session.session_name = stem_name
            else:
                session.session_name = std_name
            # -----------------------------------------------------

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
            # package_id com índice GLOBAL (será renumerado por rota depois)
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
    session = session_manager.get_current_session()
    
    await update.message.reply_text(
        f"✅ Romaneio <b>#{romaneio.id}</b> adicionado!\n"
        f"📦 {len(points)} pacotes\n\n"
        f"Total acumulado: <b>{session.total_packages} pacotes</b>\n\n"
        "⏳ <b>Gerando minimapa...</b>",
        parse_mode='HTML'
    )
    
    # 🗺️ GERA E ENVIA MINIMAPA COMPLETO (todos os pontos, sem dividir)
    try:
        all_session_points = []
        for rom in session.romaneios:
            all_session_points.extend(rom.points)
        
        if all_session_points:
            # Prepara stops_data (sem otimização, apenas mostra os pontos)
            minimap_stops = []
            for i, point in enumerate(all_session_points):
                minimap_stops.append((point.lat, point.lng, point.address, 1, 'pending'))
            
            # Base location
            base_loc = (session.base_lat, session.base_lng, session.base_address) if session.base_lat and session.base_lng else None
            
            # Gera mapa
            minimap_html = MapGenerator.generate_interactive_map(
                stops=minimap_stops,
                entregador_nome=f"Minimapa Completo - {session.total_packages} pacotes",
                current_stop=-1,  # Sem parada atual
                total_packages=session.total_packages,
                total_distance_km=0,  # Sem cálculo ainda
                total_time_min=0,
                base_location=base_loc
            )
            
            minimap_file = f"minimap_session_{session.session_id}.html"
            MapGenerator.save_map(minimap_html, minimap_file)
            
            # Envia minimapa
            with open(minimap_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    document=f,
                    filename=f"Minimapa_{session.total_packages}pacotes.html",
                    caption=(
                        f"🗺️ <b>MINIMAPA COMPLETO</b>\n\n"
                        f"📦 Total: {session.total_packages} pacotes\n"
                        f"📋 Romaneios: {len(session.romaneios)}\n\n"
                        f"💡 <i>Este mapa mostra TODOS os pontos acumulados.\n"
                        f"Use /fechar_rota para dividir entre entregadores.</i>"
                    ),
                    parse_mode='HTML'
                )
            
            # Limpa arquivo temporário
            import os
            os.unlink(minimap_file)
            logger.info(f"✅ Minimapa enviado com {session.total_packages} pontos")
    
    except Exception as e:
        logger.error(f"❌ Erro ao gerar minimapa: {e}")
        await update.message.reply_text(
            f"⚠️ Minimapa não pôde ser gerado (erro: {e}).\n\n"
            "Envie mais romaneios ou digite <code>/fechar_rota</code> para dividir.",
            parse_mode='HTML'
        )


async def cmd_fechar_rota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fecha rota e divide entre entregadores"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode fechar rotas.")
        return
    
    session = session_manager.get_current_session()
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
    
    # Importa cores
    from .colors import get_color_for_index, get_color_name
    
    # Busca lista de entregadores para permitir transferência nos mapas
    from bot_multidelivery.services.deliverer_service import deliverer_service
    all_deliverers = deliverer_service.get_all_deliverers()
    entregadores_lista = [{'name': d.name, 'id': str(d.telegram_id)} for d in all_deliverers]
    
    # Otimiza rotas
    routes = []
    for idx, cluster in enumerate(clusters):
        optimized = divider.optimize_cluster_route(cluster)
        color = get_color_for_index(idx)  # Atribui cor baseada no índice
        
        route = Route(
            id=f"ROTA_{cluster.id + 1}",
            cluster=cluster,
            color=color,  # Cor única do entregador
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
            base_location=base_loc,
            entregadores_lista=entregadores_lista,
            session_id=session.session_id
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
                            read_timeout=30,
                            write_timeout=30
                        ),
                        timeout=45.0
                    )
                    logger.info(f"✅ Mapa {route.id} enviado com sucesso")
                    
                    # Envia botão em mensagem separada (melhor UX)
                    await context.bot.send_message(
                        chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                        text=f"👇 <b>Atribua {route.id}:</b>",
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
            except (asyncio.TimeoutError, NetworkError, TimedOut, ValueError) as e:
                logger.warning(f"⚠️ Timeout/erro ao enviar mapa {route.id}: {e}. Enviando só texto...")
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=caption + f"\n\n⚠️ Mapa disponível em: {route.map_file}",
                    parse_mode='HTML'
                )
                # Botão separado
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=f"👇 <b>Atribua {route.id}:</b>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"❌ Falha ao enviar mapa {route.id} para admin: {e}")
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=caption + "\n\n❌ Erro ao enviar mapa",
                    parse_mode='HTML'
                )
                # Botão separado
                await context.bot.send_message(
                    chat_id=BotConfig.ADMIN_TELEGRAM_ID,
                    text=f"👇 <b>Atribua {route.id}:</b>",
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


async def process_route_analysis_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Processa lista de endereços (texto) e gera análise inteligente com IA
    """
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "⏳ <b>PROCESSANDO ENDEREÇOS...</b>\n\n"
        "• Parsing lista de endereços\n"
        "• Geocodificando (Google Maps)\n"
        "• Analisando com IA\n"
        "• Gerando mapa\n\n"
        "<i>Aguarde ~15-30 segundos...</i>",
        parse_mode='HTML'
    )
    
    try:
        from bot_multidelivery.parsers.text_parser import parse_text_romaneio
        from bot_multidelivery.services.geocoding_service import geocoding_service
        
        # Parse endereços
        addresses_raw = parse_text_romaneio(text)
        
        if not addresses_raw or len(addresses_raw) == 0:
            await update.message.reply_text(
                "❌ <b>NENHUM ENDEREÇO ENCONTRADO</b>\n\n"
                "Envie uma lista com <b>um endereço por linha</b>:\n\n"
                "<code>Rua A, 123 - Centro, RJ\n"
                "Av. B, 456 - Botafogo, RJ\n"
                "Travessa C, 789 - Copacabana, RJ</code>\n\n"
                "💡 Pode incluir numeração (1., 2.) ou emojis 📦",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(user_id)
            return
        
        await update.message.reply_text(
            f"✅ {len(addresses_raw)} endereços detectados!\n\n"
            f"🌍 Geocodificando em paralelo...",
            parse_mode='HTML'
        )
        
        # Geocodifica todos os endereços
        to_geocode = [{'address': addr, 'delivery': None} for addr in addresses_raw]
        geocoded_results = await geocoding_service.geocode_batch(to_geocode)
        
        # Filtra apenas os que geocodificaram com sucesso
        deliveries_data = []
        failed = 0
        for i, result in enumerate(geocoded_results):
            if result['lat'] and result['lon']:
                deliveries_data.append({
                    'id': f"END_{i+1:03d}",
                    'address': result['address'],
                    'bairro': '',  # Não extraímos bairro de texto livre
                    'lat': result['lat'],
                    'lon': result['lon'],
                    'stop': i + 1
                })
            else:
                failed += 1
                logger.warning(f"❌ Falhou geocoding: {result['address'][:60]}")
        
        if failed > 0:
            await update.message.reply_text(
                f"⚠️ <b>AVISO:</b> {failed}/{len(addresses_raw)} endereços não geocodificados\n\n"
                f"✅ {len(deliveries_data)} prontos para análise\n\n"
                f"💡 Verifique se os endereços estão completos (rua, número, bairro, cidade)",
                parse_mode='HTML'
            )
        
        if not deliveries_data or len(deliveries_data) < 3:
            await update.message.reply_text(
                "❌ <b>ENDEREÇOS INSUFICIENTES</b>\n\n"
                f"Apenas {len(deliveries_data)} endereços geocodificados.\n"
                "Mínimo: 3 endereços válidos.\n\n"
                "💡 Certifique-se de incluir:\n"
                "• Rua/Avenida + número\n"
                "• Bairro\n"
                "• Cidade (Rio de Janeiro, RJ)\n\n"
                "Exemplo:\n"
                "<code>Av. Atlântica, 1234 - Copacabana, Rio de Janeiro, RJ</code>",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(user_id)
            return
        
        # ═══════════════════════════════════════════
        # ANÁLISE COM IA (mesmo código que Excel)
        # ═══════════════════════════════════════════
        from bot_multidelivery.services.route_analyzer import route_analyzer
        analysis = route_analyzer.analyze_route(deliveries_data)
        
        # ═══════════════════════════════════════════
        # GERA MAPA HTML (AGRUPA ENDEREÇOS DUPLICADOS)
        # ═══════════════════════════════════════════
        from collections import OrderedDict
        
        # Agrupa endereços duplicados (preserva ordem)
        address_groups = OrderedDict()
        for d in deliveries_data:
            # Usa coordenadas arredondadas como chave (agrupa pontos muito próximos)
            key = (d['address'], round(d['lat'], 5), round(d['lon'], 5))
            if key not in address_groups:
                address_groups[key] = []
            address_groups[key].append(d)
        
        # Cria stops_data com contagem correta (ordem preservada)
        stops_data = []
        for (address, lat, lon), group in address_groups.items():
            num_packages = len(group)
            stops_data.append((
                lat,
                lon,
                address,
                num_packages,  # Número real de pacotes
                'pending'
            ))
            logger.info(f"📍 Stop {len(stops_data)}: {address[:50]} - {num_packages} pacote(s)")
        
        logger.info(f"🗺️ {len(stops_data)} paradas únicas de {len(deliveries_data)} endereços")
        
        # Gera mapa HTML
        html = MapGenerator.generate_interactive_map(
            stops=stops_data,
            entregador_nome="Análise de Rota (Texto)",
            current_stop=0,
            total_packages=len(deliveries_data),
            total_distance_km=analysis.total_distance_km,
            total_time_min=analysis.estimated_time_minutes,
            base_location=None
        )
        
        # Salva mapa
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            map_path = f.name
        
        # ═══════════════════════════════════════════
        # ENVIA ANÁLISE + MAPA
        # ═══════════════════════════════════════════
        score = analysis.get('score', 0)
        score_emoji = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
        
        msg = (
            f"{score_emoji} <b>ANÁLISE DE ROTA - TEXTO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⭐ <b>Score Viabilidade: {score}/10</b>\n\n"
            f"📊 <b>ESTATÍSTICAS</b>\n"
            f"📦 {analysis.get('total_stops', 0)} pontos de entrega\n"
            f"📏 {analysis.get('total_distance_km', 0):.1f} km (estimado)\n"
            f"⏱️ {analysis.get('estimated_time_min', 0)} min (estimado)\n"
            f"💰 Receita estimada: R$ {analysis.get('estimated_revenue', 0):.2f}\n\n"
        )
        
        # Prós
        pros = analysis.get('pros', [])
        if pros:
            msg += "✅ <b>PONTOS POSITIVOS</b>\n"
            for pro in pros:
                msg += f"• {pro}\n"
            msg += "\n"
        
        # Contras
        cons = analysis.get('cons', [])
        if cons:
            msg += "❌ <b>PONTOS NEGATIVOS</b>\n"
            for con in cons:
                msg += f"• {con}\n"
            msg += "\n"
        
        # Comentário
        comment = analysis.get('comment', '')
        if comment:
            msg += f"💬 <b>CONCLUSÃO</b>\n{comment}\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📍 Veja o mapa abaixo ↓"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
        # Envia mapa
        with open(map_path, 'rb') as map_file:
            await update.message.reply_document(
                document=map_file,
                filename=f"analise_texto_{datetime.now().strftime('%d%m_%H%M')}.html",
                caption="🗺️ <b>Mapa Interativo</b>\nAbra no navegador para visualizar a rota",
                parse_mode='HTML'
            )
        
        # Limpa estado
        session_manager.clear_admin_state(user_id)
        
        logger.info(f"✅ Análise de rota (texto) concluída: {len(deliveries_data)} endereços, score {score}/10")
    
    except Exception as e:
        logger.error(f"❌ Erro ao analisar rota (texto): {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            f"❌ <b>ERRO AO PROCESSAR</b>\n\n"
            f"Detalhes: {str(e)}\n\n"
            f"💡 Certifique-se de enviar endereços completos (rua, número, bairro, cidade)",
            parse_mode='HTML'
        )
        session_manager.clear_admin_state(user_id)


async def process_route_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa Excel da Shopee e gera análise inteligente com IA
    """
    user_id = update.effective_user.id
    document = update.message.document
    
    if not document or not document.file_name:
        await update.message.reply_text(
            "❌ Nenhum arquivo detectado. Envie o Excel da Shopee.",
            parse_mode='HTML'
        )
        return
    
    file_name = document.file_name.lower()
    
    if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
        await update.message.reply_text(
            "❌ <b>Formato inválido!</b>\n\n"
            "Envie um arquivo <b>.xlsx</b> da Shopee.",
            parse_mode='HTML'
        )
        return
    
    # Download e processa
    await update.message.reply_text(
        "⏳ <b>PROCESSANDO ROTA...</b>\n\n"
        "• Lendo Excel\n"
        "• Extraindo coordenadas\n"
        "• Analisando com IA\n"
        "• Gerando mapa\n\n"
        "<i>Aguarde uns 10 segundos...</i>",
        parse_mode='HTML'
    )
    
    try:
        from bot_multidelivery.parsers.shopee_parser import ShopeeRomaneioParser
        import tempfile
        
        # Download
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        # Salva temp
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp.write(bytes(file_content))
            tmp_path = tmp.name
        
        # Parse
        deliveries = ShopeeRomaneioParser.parse(tmp_path)
        
        if not deliveries:
            await update.message.reply_text(
                "❌ Nenhuma entrega encontrada no arquivo!",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(user_id)
            return
        
        # ═══════════════════════════════════════════
        # GEOCODING AUTOMÁTICO (se precisar)
        # ═══════════════════════════════════════════
        from .services.geocoding_service import geocoding_service
        
        missing_coords = sum(1 for d in deliveries if not d.latitude or not d.longitude)
        
        if missing_coords > 0:
            await update.message.reply_text(
                f"🌍 <b>GEOCODIFICANDO ENDEREÇOS...</b>\n\n"
                f"📍 {missing_coords} endereços sem coordenadas\n"
                f"⏳ Processando em paralelo (Google Maps API)...\n\n"
                f"<i>Aguarde ~{max(10, missing_coords // 5)}s</i>",
                parse_mode='HTML'
            )
            
            # Prepara lista de endereços para geocoding em batch
            to_geocode = []
            for d in deliveries:
                if not d.latitude or not d.longitude:
                    # Normaliza bairro
                    bairro = d.bairro.strip() if d.bairro else ""
                    bairro = bairro.replace(", Rio de Janeiro", "").replace(",Rio de Janeiro", "")
                    
                    # Endereço completo (já vem limpo do parser)
                    full_address = f"{d.address}, {bairro}, Rio de Janeiro, RJ, Brasil"
                    
                    to_geocode.append({
                        'delivery': d,
                        'address': full_address,
                        'bairro': bairro
                    })
            
            # Geocodifica em batch (paralelo)
            logger.info(f"🌍 Geocodificando {len(to_geocode)} endereços em batch...")
            geocoded_results = await geocoding_service.geocode_batch(to_geocode)
            
            # Aplica resultados
            geocoded = 0
            failed = 0
            for result in geocoded_results:
                delivery = result['delivery']
                if result['lat'] and result['lon']:
                    delivery.latitude = result['lat']
                    delivery.longitude = result['lon']
                    geocoded += 1
                    logger.info(f"✅ Geocoded: {result['address'][:60]} -> ({result['lat']}, {result['lon']})")
                else:
                    failed += 1
                    logger.warning(f"❌ Falhou: {result['address'][:60]}")
            
            if failed > 0:
                await update.message.reply_text(
                    f"⚠️ <b>AVISO:</b> {failed} endereços não geocodificados\n\n"
                    f"✅ {geocoded} geocodificados com sucesso\n\n"
                    f"💡 Análise pode ser imprecisa para endereços sem coordenadas",
                    parse_mode='HTML'
                )
        
        # Converte para dicts
        deliveries_data = []
        for d in deliveries:
            if d.latitude is not None and d.longitude is not None:  # Aceita 0.0
                deliveries_data.append({
                    'id': d.tracking,
                    'address': f"{d.address}, {d.bairro}",
                    'bairro': d.bairro,
                    'lat': d.latitude,
                    'lon': d.longitude,
                    'stop': d.stop
                })
        
        logger.info(f"📦 {len(deliveries_data)} entregas com coordenadas válidas de {len(deliveries)} totais")
        
        if not deliveries_data:
            await update.message.reply_text(
                "❌ <b>NENHUMA COORDENADA VÁLIDA!</b>\n\n"
                "O arquivo não contém:\n"
                "• Colunas Latitude/Longitude OU\n"
                "• Endereços geocodificáveis\n\n"
                "💡 Verifique o formato do Excel",
                parse_mode='HTML'
            )
            session_manager.clear_admin_state(user_id)
            return
        
        # ═══════════════════════════════════════════
        # ANÁLISE COM IA
        # ═══════════════════════════════════════════
        route_value = session_manager.get_temp_data(user_id, "route_value") or 0.0
        analysis = route_analyzer.analyze_route(deliveries_data, route_value=route_value)
        
        # ═══════════════════════════════════════════
        # GERA MAPA HTML (AGRUPA PACOTES POR ENDEREÇO)
        # ═══════════════════════════════════════════
        
        # Agrupa pacotes por endereço único (mantendo ordem de chegada)
        from collections import defaultdict, OrderedDict
        address_groups = OrderedDict()
        
        for d in deliveries_data:
            if d['lat'] and d['lon']:
                # Usa endereço + coordenadas como chave única
                key = (d['address'], round(d['lat'], 5), round(d['lon'], 5))
                if key not in address_groups:
                    address_groups[key] = []
                address_groups[key].append(d)
        
        # Cria stops com contagem correta de pacotes (ordem preservada)
        stops_data = []
        failed_geocoding = []
        
        for (address, lat, lon), packages in address_groups.items():
            num_packages = len(packages)
            stops_data.append((
                lat,
                lon,
                address,
                num_packages,  # Número real de pacotes neste endereço
                'pending'
            ))
            logger.info(f"📍 Stop {len(stops_data)}: {address[:50]} - {num_packages} pacote(s)")
        
        logger.info(f"🗺️ Total de {len(stops_data)} paradas únicas para {len(deliveries_data)} pacotes")
        
        # DEBUG: Log coordenadas
        logger.info(f"🗺️ Gerando mapa: {len(stops_data)} pontos com coordenadas")
        if failed_geocoding:
            logger.warning(f"⚠️ {len(failed_geocoding)} endereços sem coordenadas:")
            for addr in failed_geocoding[:5]:  # Max 5
                logger.warning(f"   - {addr}")
        
        if not stops_data:
            logger.error("❌ NENHUM PONTO COM COORDENADAS! Mapa ficará em branco.")
        
        html = MapGenerator.generate_interactive_map(
            stops=stops_data,
            entregador_nome="Análise de Rota",
            current_stop=0,
            total_packages=analysis.total_packages,
            total_distance_km=analysis.total_distance_km,
            total_time_min=analysis.estimated_time_minutes,
            base_location=None
        )
        
        map_file = f"analysis_{user_id}.html"
        MapGenerator.save_map(html, map_file)
        
        # ═══════════════════════════════════════════
        # MENSAGEM DE ANÁLISE
        # ═══════════════════════════════════════════
        
        # Score visual
        score_bar = "█" * int(analysis.overall_score) + "░" * (10 - int(analysis.overall_score))
        
        # Bairros formatados
        if analysis.unique_neighborhoods == 1:
            bairros_info = f"<b>{analysis.neighborhood_list[0]}</b>"
        elif analysis.unique_neighborhoods <= 3:
            bairros_info = f"<b>{', '.join(analysis.neighborhood_list)}</b>"
        else:
            bairros_info = f"<b>{analysis.unique_neighborhoods} bairros</b> ({', '.join(analysis.neighborhood_list[:3])}...)"
        
        message = (
            f"🔍 <b>ANÁLISE DE ROTA COMPLETA</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>VALOR REAL: R$ {analysis.route_value:.2f}</b>\n"
            f"🏘️ <b>PERFIL: {analysis.route_type}</b>\n\n"
            f"📊 <b>SCORE GERAL: {analysis.overall_score}/10</b>\n"
            f"<code>{score_bar}</code> {analysis.recommendation}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 <b>RESUMO TÉCNICO:</b>\n"
            f"• <b>{analysis.total_packages} pacotes</b> ({analysis.total_stops} paradas)\n"
            f"• <b>{analysis.unique_addresses} endereços únicos</b>\n"
            f"• <b>{analysis.commercial_count} comerciais</b> | <b>{analysis.vertical_count} condomínios</b>\n"
            f"• <b>{analysis.total_distance_km:.1f} km</b> total\n"
            f"• Bairros: {bairros_info}\n\n"
            f"💸 <b>FINANCEIRO ESTIMADO:</b>\n"
            f"• Ganho/Hora: <b>R$ {analysis.hourly_earnings:.2f}</b>\n"
            f"• Ganho/Pacote: <b>R$ {analysis.package_earnings:.2f}</b>\n"
            f"• Tempo Total: <b>{analysis.estimated_time_minutes:.0f} min</b>\n\n"
            f"🏆 <b>TOP DROPS (Onde você mata a rota):</b>\n"
        )
        
        if analysis.top_drops:
            for idx, (name, count) in enumerate(analysis.top_drops, 1):
                icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉"
                message += f"{icon} {name} ({count} pct)\n"
            message += "\n"

        message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Prós
        if analysis.pros:
            message += "✅ <b>PRÓS:</b>\n"
            for pro in analysis.pros:
                message += f"  • {pro}\n"
            message += "\n"
        
        # Contras
        if analysis.cons:
            message += "❌ <b>CONTRAS:</b>\n"
            for con in analysis.cons:
                message += f"  • {con}\n"
            message += "\n"
        
        message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"🤖 <b>ANÁLISE DA IA:</b>\n\n{analysis.ai_comment}\n\n"
        message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"🗺️ <b>Mapa interativo em anexo!</b>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
        # Envia mapa HTML
        try:
            with open(map_file, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"rota_analise_{datetime.now().strftime('%H%M')}.html",
                    caption="🗺️ Abra no navegador para visualizar!",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Erro ao enviar mapa: {e}")
            await update.message.reply_text(
                f"⚠️ Mapa salvo em: {map_file}",
                parse_mode='HTML'
            )
        
        # Limpa estado
        session_manager.clear_admin_state(user_id)
        
    except Exception as e:
        logger.error(f"Erro na análise de rota: {e}")
        await update.message.reply_text(
            f"❌ <b>ERRO NO PROCESSAMENTO</b>\n\n"
            f"<code>{str(e)[:200]}</code>\n\n"
            f"Tente novamente com outro arquivo.",
            parse_mode='HTML'
        )
        session_manager.clear_admin_state(user_id)


async def cmd_analisar_rota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🔍 Analisa uma rota da Shopee ANTES de aceitar
    Inicia wizard financeiro -> depois pede arquivo
    """
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode analisar rotas.")
        return
    
    # Muda estado para aguardar valor
    session_manager.set_admin_state(user_id, "awaiting_route_value")
    
    await update.message.reply_text(
        "💰 <b>QUANTO PAGA ESSA ROTA?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Para uma análise financeira real, informe o valor total ofertado.\n\n"
        "<i>Digite 0 se não souber ou não quiser informar.</i>\n\n"
        "💲 <b>Digite o valor (ex: 154.50):</b>",
        parse_mode='HTML'
    )


async def cmd_sessoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📂 Lista todas as sessões ativas com botões de Ver Detalhes e Excluir
    """
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode gerenciar sessões.")
        return
    
    sessions = session_manager.list_sessions()
    current_session = session_manager.get_current_session()
    
    if not sessions:
        await update.message.reply_text(
            "📂 <b>NENHUMA SESSÃO ENCONTRADA</b>\n\n"
            "Use o botão <b>📦 Nova Sessão do Dia</b> para começar!",
            parse_mode='HTML'
        )
        return
    
    # Monta lista de sessões ATIVAS
    msg = "📂 <b>SESSÕES ATIVAS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    keyboard = []
    
    for i, session in enumerate(sessions[:10], 1):  # Limita a 10
        # Indicador visual
        if current_session and session.session_id == current_session.session_id:
            indicator = "🔵"
            status_text = "ATIVA"
        elif session.is_finalized:
            indicator = "✅"
            status_text = "Finalizada"
        else:
            indicator = "⚪"
            status_text = "Em andamento"
        
        # Conta entregas feitas
        total_delivered = sum(len(r.delivered_packages) for r in session.routes)
        
        # Nome da sessão
        session_name = session.session_name or f"Sessão {session.session_id[:8]}"
        
        msg += f"{indicator} <b>{i}. {session_name}</b> ({status_text})\n"
        msg += f"   📅 {session.date} | 📦 {session.total_packages} pacotes\n"
        msg += f"   ✅ {total_delivered} entregas | 🗺️ {len(session.routes)} rotas\n\n"
        
        # Botões: Ver Detalhes + Excluir
        keyboard.append([
            InlineKeyboardButton(
                f"👁️ Detalhes",
                callback_data=f"session_details_{session.session_id}"
            ),
            InlineKeyboardButton(
                f"🗑️ Excluir",
                callback_data=f"session_delete_{session.session_id}"
            )
        ])
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 <i>Clique para ver detalhes ou excluir</i>"
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de botões inline"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # ═══════════════════════════════════════════
    # FECHAMENTO DO DIA (WIZARD CUSTOS)
    # ═══════════════════════════════════════════
    if data.startswith("add_cost_"):
        cost_type = data.replace("add_cost_", "")
        user_id = query.from_user.id
        
        # Salva tipo e pede valor
        temp = session_manager.get_temp_data(user_id, "day_closing")
        temp['current_expense_type'] = cost_type
        session_manager.save_temp_data(user_id, "day_closing", temp)
        
        session_manager.set_admin_state(user_id, "closing_day_expense_value")
        
        await query.edit_message_text(
            f"💰 <b>CUSTO: {cost_type.upper()}</b>\n\n"
            f"Qual o valor gasto hoje?\n"
            f"<i>Digite o valor (ex: 50.00)</i>\n\n"
            f"Ou use /cancelar para voltar.",
            parse_mode='HTML'
        )
        return

    if data == "finish_day_closing":
        user_id = query.from_user.id
        data = session_manager.get_temp_data(user_id, "day_closing")
        
        # Define data do fechamento
        closing_date = datetime.now()
        if 'date' in data:
            closing_date = datetime.strptime(data['date'], '%Y-%m-%d')
            
        # Fecha o dia pra valer!
        report = financial_service.close_day(
            date=closing_date,
            revenue=data['revenue'],
            deliverer_costs=data['deliverer_costs'],
            other_costs=sum(e['value'] for e in data['expenses']),
            total_packages=data['total_packages'],
            total_deliveries=data['total_deliveries'],
            expenses=data.get('expenses', [])  # Nova lista detalhada
        )
        
        session_manager.clear_admin_state(user_id)
        
        # Formata relatório
        msg = financial_service.format_daily_report(report)
        msg += "\n\n✅ <b>Fechamento salvo e dia encerrado!</b>"
        
        await query.edit_message_text(msg, parse_mode='HTML')
        return

    # ═══════════════════════════════════════════
    # SELECIONAR SESSÃO (NOVO)
    # ═══════════════════════════════════════════
    if data.startswith("select_session_"):
        session_id = data.replace("select_session_", "")
        session = session_manager.get_session(session_id)
        
        if not session:
            await query.edit_message_text(
                f"❌ Sessão {session_id} não encontrada!",
                parse_mode='HTML'
            )
            return
        
        # Define como sessão atual
        session_manager.set_current_session(session_id)
        
        status_icon = "🔴" if session.is_finalized else "🟢"
        status_text = "Finalizada" if session.is_finalized else "ATIVA"
        
        pending = session.total_pending
        
        # Determina próxima ação sugerida
        next_step = ""
        buttons = []
        
        if not session.romaneios:
            next_step = "📥 <b>Nenhum pacote importado!</b> Use /importar."
        elif not session.routes:
            next_step = "⚙️ <b>Pacotes prontos!</b> Use o botão abaixo para criar rotas."
            buttons.append([InlineKeyboardButton("🚀 Otimizar Agora", callback_data="shortcut_optimize")])
        elif pending > 0:
            next_step = f"🚀 <b>Em andamento!</b> Restam {pending} pacotes."
            buttons.append([InlineKeyboardButton("🎨 Separação", callback_data="shortcut_separacao")])
            buttons.append([InlineKeyboardButton("📊 Status", callback_data="shortcut_status")])
        else:
            next_step = "✅ <b>Tudo entregue!</b> Feche o dia."
            
        markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        await query.edit_message_text(
            f"✅ <b>SESSÃO RESGATADA!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 Nome: <b>{session.session_name}</b>\n"
            f"📅 Data: {session.date}\n"
            f"{status_icon} Status: <b>{status_text}</b>\n\n"
            f"📦 Romaneios: {len(session.romaneios)}\n"
            f"🛣️ Rotas: {len(session.routes)}\n"
            f"⏳ Pendentes: {pending}\n\n"
            f"{next_step}",
            parse_mode='HTML',
            reply_markup=markup
        )
        return

    # ═══════════════════════════════════════════
    # ATALHOS INTELIGENTES (SHORTCUTS)
    # ═══════════════════════════════════════════
    if data == "shortcut_optimize":
        await query.answer("🚀 Iniciando otimização...")
        await cmd_otimizar_rotas(update, context) # Agora existe!
        return
        
    if data.startswith("optimize_num_"):
        await handle_optimization_num(update, context)
        return

    if data == "shortcut_separacao":
        await query.answer("🎨 Abrindo modo separação...")
        await cmd_modo_separacao(update, context)
        return

    if data == "shortcut_status":
        await query.answer("📊 Carregando status...")
        await cmd_status_sessao(update, context)
        return
    
    # ═══════════════════════════════════════════
    # SWITCH DE SESSÃO
    # ═══════════════════════════════════════════
    if data.startswith("switch_session_"):
        session_id = data.replace("switch_session_", "")
        session = session_manager.get_session(session_id)
        
        if not session:
            await query.edit_message_text(
                f"❌ Sessão {session_id} não encontrada!",
                parse_mode='HTML'
            )
            return
        
        # Troca sessão ativa (ou mostra detalhes se já for a atual)
        current = session_manager.get_current_session()
        is_already_active = current and current.session_id == session_id
        
        if not is_already_active:
            session_manager.set_current_session(session_id)
        
        # Monta resumo detalhado
        finalized_text = "✅ Finalizada" if session.is_finalized else "⚪ Em andamento"
        
        # Detalhe das rotas
        routes_info = ""
        if session.routes:
            routes_info += "\n\n<b>🛣️ ROTAS:</b>\n"
            for i, route in enumerate(session.routes[:5], 1):  # Max 5 rotas
                color_name = get_color_name(route.color)
                deliverer = route.assigned_to_name or "Não atribuído"
                packages = len(route.optimized_order)
                routes_info += f"{color_name}: {deliverer} ({packages} pacotes)\n"
            if len(session.routes) > 5:
                routes_info += f"...e mais {len(session.routes) - 5} rotas\n"
        
        title = "🔵 <b>SESSÃO ATIVA</b>" if is_already_active else "🔵 <b>SESSÃO TROCADA!</b>"
        
        await query.edit_message_text(
            f"{title}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{session.session_id}</b>\n"
            f"📅 {session.date}\n"
            f"📦 {session.total_packages} pacotes · {len(session.routes)} rotas\n"
            f"📍 {session.base_address[:50] if session.base_address else 'Sem base definida'}\n"
            f"Status: {finalized_text}"
            f"{routes_info}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{'📍 Você já está nesta sessão!' if is_already_active else '✅ Agora você está trabalhando nesta sessão!'}",
            parse_mode='HTML'
        )
        return
    
    # ═══════════════════════════════════════════
    # 👁️ VER DETALHES DA SESSÃO
    # ═══════════════════════════════════════════
    if data.startswith("session_details_"):
        session_id = data.replace("session_details_", "")
        session = session_manager.get_session(session_id)
        
        if not session:
            await query.edit_message_text(f"❌ Sessão {session_id} não encontrada!", parse_mode='HTML')
            return
        
        # Conta estatísticas
        total_delivered = sum(len(r.delivered_packages) for r in session.routes)
        total_pending = session.total_packages - total_delivered
        
        # Monta mensagem detalhada
        msg = f"📊 <b>DETALHES DA SESSÃO</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"🆔 ID: <code>{session.session_id}</code>\n"
        msg += f"📛 Nome: <b>{session.session_name or 'Sem nome'}</b>\n"
        msg += f"📅 Data: {session.date}\n"
        msg += f"⏰ Período: {session.period or 'Não definido'}\n"
        msg += f"📍 Base: {session.base_address or 'Não definida'}\n\n"
        
        msg += f"<b>📦 PACOTES:</b>\n"
        msg += f"   Total: {session.total_packages}\n"
        msg += f"   ✅ Entregues: {total_delivered}\n"
        msg += f"   ⏳ Pendentes: {total_pending}\n\n"
        
        msg += f"<b>🗺️ ROTAS ({len(session.routes)}):</b>\n"
        
        # Botões para cada rota (baixar mapa)
        keyboard = []
        
        for route in session.routes:
            color_name = get_color_name(route.color) if hasattr(route, 'color') and route.color else "⚪"
            delivered = len(route.delivered_packages)
            total = route.total_packages
            entregador = route.assigned_to_name or "Não atribuído"
            
            msg += f"\n{color_name} <b>{route.id}</b> - {entregador}\n"
            msg += f"   📦 {delivered}/{total} entregas | "
            msg += f"{'✅ Completa' if delivered >= total else '⏳ Em andamento'}\n"
            
            # Botão para baixar mapa da rota
            if route.map_file:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗺️ Mapa {route.id}",
                        callback_data=f"download_map_{session_id}_{route.id}"
                    )
                ])
        
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Botão voltar
        keyboard.append([
            InlineKeyboardButton("◀️ Voltar", callback_data="back_to_sessions")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    # ═══════════════════════════════════════════
    # 🗑️ EXCLUIR SESSÃO (confirmação)
    # ═══════════════════════════════════════════
    if data.startswith("session_delete_"):
        session_id = data.replace("session_delete_", "")
        session = session_manager.get_session(session_id)
        
        if not session:
            await query.edit_message_text(f"❌ Sessão {session_id} não encontrada!", parse_mode='HTML')
            return
        
        # Confirmação antes de excluir
        msg = f"⚠️ <b>CONFIRMAR EXCLUSÃO?</b>\n\n"
        msg += f"Sessão: <b>{session.session_name or session.session_id}</b>\n"
        msg += f"📅 {session.date}\n"
        msg += f"📦 {session.total_packages} pacotes\n"
        msg += f"🗺️ {len(session.routes)} rotas\n\n"
        msg += f"<b>⚠️ Esta ação não pode ser desfeita!</b>\n"
        msg += f"Todas as rotas e dados serão perdidos."
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Sim, excluir", callback_data=f"session_confirm_delete_{session_id}"),
                InlineKeyboardButton("❌ Cancelar", callback_data="back_to_sessions")
            ]
        ]
        
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # ═══════════════════════════════════════════
    # ✅ CONFIRMAR EXCLUSÃO DA SESSÃO
    # ═══════════════════════════════════════════
    if data.startswith("session_confirm_delete_"):
        session_id = data.replace("session_confirm_delete_", "")
        
        # Remove do session manager E do banco de dados
        deleted = session_manager.delete_session(session_id)
        
        if deleted:
            await query.edit_message_text(
                f"🗑️ <b>SESSÃO EXCLUÍDA!</b>\n\n"
                f"A sessão <code>{session_id}</code> foi removida permanentemente.\n\n"
                f"Use /sessoes para ver as sessões restantes.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                f"❌ <b>ERRO AO EXCLUIR</b>\n\n"
                f"Sessão <code>{session_id}</code> não encontrada.",
                parse_mode='HTML'
            )
        return
    
    # ═══════════════════════════════════════════
    # ◀️ VOLTAR PARA LISTA DE SESSÕES
    # ═══════════════════════════════════════════
    if data == "back_to_sessions":
        # Re-gera a lista de sessões
        sessions = session_manager.list_sessions()
        current_session = session_manager.get_current_session()
        
        if not sessions:
            await query.edit_message_text(
                "📂 <b>NENHUMA SESSÃO ENCONTRADA</b>",
                parse_mode='HTML'
            )
            return
        
        msg = "📂 <b>SESSÕES ATIVAS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = []
        
        for i, session in enumerate(sessions[:10], 1):
            if current_session and session.session_id == current_session.session_id:
                indicator = "🔵"
                status_text = "ATIVA"
            elif session.is_finalized:
                indicator = "✅"
                status_text = "Finalizada"
            else:
                indicator = "⚪"
                status_text = "Em andamento"
            
            total_delivered = sum(len(r.delivered_packages) for r in session.routes)
            session_name = session.session_name or f"Sessão {session.session_id[:8]}"
            
            msg += f"{indicator} <b>{i}. {session_name}</b> ({status_text})\n"
            msg += f"   📅 {session.date} | 📦 {session.total_packages} pacotes\n"
            msg += f"   ✅ {total_delivered} entregas | 🗺️ {len(session.routes)} rotas\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"👁️ Detalhes", callback_data=f"session_details_{session.session_id}"),
                InlineKeyboardButton(f"🗑️ Excluir", callback_data=f"session_delete_{session.session_id}")
            ])
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 <i>Clique para ver detalhes ou excluir</i>"
        
        await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # ═══════════════════════════════════════════
    # SELEÇÃO DE CORES PARA ROTAS
    # ═══════════════════════════════════════════
    if data.startswith("color_"):
        if data == "color_confirm":
            # Usuário confirmou as cores → executar otimização
            await _execute_route_distribution(update, context, query)
            return
        
        # Toggle de cor individual
        color_name = data.replace("color_", "")
        
        if 'temp' not in context.user_data:
            context.user_data['temp'] = {}
        
        colors_selected = context.user_data['temp'].get('colors_selected', [])
        
        # Toggle: adiciona ou remove
        if color_name in colors_selected:
            colors_selected.remove(color_name)
        else:
            colors_selected.append(color_name)
        
        context.user_data['temp']['colors_selected'] = colors_selected
        
        # Atualiza teclado com checkmarks
        color_buttons = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if 'vermelho' in colors_selected else ''}🔴 Vermelho", 
                    callback_data="color_vermelho"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if 'azul' in colors_selected else ''}🔵 Azul", 
                    callback_data="color_azul"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if 'verde' in colors_selected else ''}🟢 Verde", 
                    callback_data="color_verde"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if 'amarelo' in colors_selected else ''}🟡 Amarelo", 
                    callback_data="color_amarelo"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{'✅ ' if 'roxo' in colors_selected else ''}🟣 Roxo", 
                    callback_data="color_roxo"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if 'laranja' in colors_selected else ''}🟠 Laranja", 
                    callback_data="color_laranja"
                ),
            ],
            [
                InlineKeyboardButton("✅ Confirmar Cores", callback_data="color_confirm")
            ]
        ]
        
        keyboard = InlineKeyboardMarkup(color_buttons)
        
        num_colors = len(colors_selected)
        color_list = ", ".join(colors_selected) if colors_selected else "nenhuma"
        
        await query.edit_message_text(
            "🎨 <b>ESCOLHA AS CORES DOS ADESIVOS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 <b>Selecionadas ({num_colors}):</b> {color_list}\n\n"
            "🏷️ <b>Selecione as cores disponíveis:</b>\n"
            "• Clique nas cores que você tem como adesivo\n"
            "• Pode escolher quantas quiser\n"
            "• Depois clique em ✅ Confirmar\n\n"
            "<i>💡 As rotas usarão as cores selecionadas</i>",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        return
    
    if data.startswith("assign_route_"):
        route_id = data.replace("assign_route_", "")
        session_manager.save_temp_data(query.from_user.id, "assigning_route", route_id)
        
        # Mostra lista de entregadores
        deliverers = [d for d in deliverer_service.get_all_deliverers() if d.is_active]
        
        if not deliverers:
            await query.edit_message_text(
                f"❌ <b>NENHUM ENTREGADOR CADASTRADO!</b>\n\n"
                f"Rota: <b>{route_id}</b>\n\n"
                f"Use <code>/add_entregador</code> para cadastrar entregadores primeiro.\n\n"
                f"💡 Você precisa ter pelo menos 1 entregador ativo no sistema.",
                parse_mode='HTML'
            )
            return
        
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
        session = session_manager.get_current_session()
        route = next((r for r in session.routes if r.id == route_id), None)
        
        if route:
            # Fix: Usa deliverer_service diretamente e evita BotConfig legado que causa crash
            deliverer = deliverer_service.get_deliverer(deliverer_id)
            if not deliverer:
                await query.edit_message_text(
                    f"❌ Entregador ID {deliverer_id} não encontrado no sistema!",
                    parse_mode='HTML'
                )
                return

            route.assigned_to_telegram_id = deliverer_id
            route.assigned_to_name = deliverer.name
            
            # Envia rota pro entregador
            try:
                await send_route_to_deliverer(context, deliverer_id, route, session)
                
                await query.edit_message_text(
                    f"✅ <b>{route_id}</b> atribuída a <b>{deliverer.name}</b>!\n\n"
                    f"📨 Rota enviada no chat privado do entregador.",
                    parse_mode='HTML'
                )
            except Exception as e:
                await query.edit_message_text(
                    f"✅ <b>{route_id}</b> atribuída a <b>{deliverer.name}</b> (localmente)!\n\n"
                    f"⚠️ Erro ao enviar DM: {str(e)}",
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

        # Define custo antes de criar
        cost_per_package = temp.get("cost", 0.0) if not temp.get("is_partner", False) else 0.0
        
        deliverer = Deliverer(
            telegram_id=temp["telegram_id"],
            name=temp["name"],
            is_partner=temp.get("is_partner", False),
            max_capacity=temp.get("capacity", 9999),
            cost_per_package=cost_per_package,
            is_active=True,
            joined_date=datetime.now()
        )
        
        # Salva via data_store diretamente
        from .persistence import data_store
        data_store.add_deliverer(deliverer)

        tipo_emoji = "🤝" if deliverer.is_partner else "💼"
        custo = deliverer.cost_per_package

        await query.edit_message_text(
            f"✅ <b>Entregador cadastrado!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{tipo_emoji} <b>{deliverer.name}</b>\n"
            f"🆔 ID: <code>{deliverer.telegram_id}</code>\n"
            f"📦 Capacidade: {deliverer.max_capacity} pacotes/dia\n"
            f"💰 Custo: R$ {custo:.2f}/pacote\n\n"
            f"<i>Dados salvos com sucesso em deliverers.json</i>",
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
    
    elif data == "help_start_operation":
        operation_text = """<b>🚀 GUIA: INICIAR OPERAÇÃO DO DIA</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📋 FLUXO COMPLETO (3 ETAPAS)</b>

<b>1️⃣ IMPORTAR ROMANEIOS</b>

Digite <code>/importar</code> ou envie arquivos diretamente.

<b>O que enviar:</b>
• Romaneios da Shopee (.xlsx)
• CSVs de outras plataformas
• PDFs escaneados
• Lista manual de endereços

<b>💡 Pode enviar vários arquivos!</b>
O sistema consolida automaticamente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>2️⃣ SELECIONAR ENTREGADORES</b>

Após importar, o bot pergunta:
<i>"Quem vai trabalhar hoje?"</i>

<b>Selecione:</b>
• Marque os entregadores disponíveis
• Sistema mostra capacidade total
• Valida se é suficiente para os pacotes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>3️⃣ OTIMIZAR E DISTRIBUIR</b>

Digite <code>/otimizar</code> (ou <code>/distribuir</code>)

<b>Sistema automaticamente:</b>
✓ Agrupa entregas por região (K-means)
✓ Divide entre entregadores selecionados
✓ Otimiza cada rota (Scooter Mode)
✓ Gera mapa HTML interativo
✓ Envia para cada entregador no privado

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✅ PRONTO!</b>

Cada entregador recebe:
• Mapa HTML com rota numerada
• Lista de pacotes e endereços
• Botões de navegação Google Maps
• Sistema para marcar entregas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>⏱ Tempo total: ~3 minutos</b>
<b>🎯 Economia: 79% vs manual</b>"""

        await query.edit_message_text(
            operation_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_team_management":
        team_text = """<b>👥 GERENCIAR EQUIPE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>CADASTRAR NOVO ENTREGADOR</b>

Use: <code>/add_entregador</code>

<b>Formato:</b>
<code>/add_entregador [ID] [Nome] [tipo] [capacidade] [custo]</code>

<b>Parâmetros:</b>
• <b>ID</b>: Telegram ID do entregador
• <b>Nome</b>: Nome ou apelido
• <b>Tipo</b>: <code>parceiro</code> ou <code>terceiro</code>
• <b>Capacidade</b>: Pacotes por dia (ex: 50)
• <b>Custo</b>: R$ por pacote (0 para parceiro)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📝 EXEMPLOS PRÁTICOS</b>

<b>Cadastrar sócio:</b>
<code>/add_entregador 123456 João parceiro 60 0</code>

<b>Cadastrar colaborador:</b>
<code>/add_entregador 789012 Maria terceiro 40 1.5</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>TIPOS DE ENTREGADOR</b>

🔸 <b>PARCEIRO</b> (Sócio)
   • Custo: R$ 0,00/pacote
   • Participa dos lucros
   
🔹 <b>COLABORADOR</b> (Terceiro)
   • Custo: R$ 1,00~2,50/pacote
   • Pagamento por produção

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>VER EQUIPE COMPLETA</b>

Use: <code>/entregadores</code>

Mostra lista com:
• Nome e tipo de cada um
• Status (ativo/inativo)
• Capacidade diária
• Estatísticas de entregas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>GAMIFICAÇÃO</b>

Use: <code>/ranking</code>

Veja quem está mandando bem!
• Top entregadores do mês
• Níveis e conquistas
• Taxa de sucesso"""

        await query.edit_message_text(
            team_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_monitoring":
        monitoring_text = """<b>📊 MONITORAMENTO EM TEMPO REAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>COMANDOS DISPONÍVEIS</b>

<b>📍 Status Geral</b>
<code>/status</code>

Mostra:
• Sessão ativa do dia
• Total de pacotes processados
• Rotas criadas e distribuídas
• Progresso de cada entregador

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🤖 Predição com IA</b>
<code>/prever</code>

Calcula antes de distribuir:
• Tempo estimado de entrega
• Custo total da operação
• Melhor divisão de rotas
• Alertas de sobrecarga

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏆 Ranking de Performance</b>
<code>/ranking</code>

Gamificação da equipe:
• Top entregadores
• Níveis e XP
• Conquistas desbloqueadas
• Comparativo de eficiência

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💰 Relatório Financeiro</b>

Em desenvolvimento:
• Custo por entregador
• Lucro vs despesas
• Projeções mensais"""

        await query.edit_message_text(
            monitoring_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_file_formats":
        formats_text = """<b>📂 FORMATOS DE ARQUIVO ACEITOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✅ EXCEL SHOPEE (.xlsx)</b> — <i>Recomendado</i>

<b>Por que usar:</b>
• Lat/lon já inclusos
• Detecção automática de colunas
• Sem necessidade de geocoding
• Processamento instantâneo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✅ CSV GENÉRICO (.csv)</b>

<b>Formato esperado:</b>
<code>tracking,endereco,lat,lon,prioridade</code>

<b>Exemplo:</b>
<code>BR123,Rua A 100,-23.5,-46.6,normal</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✅ PDF ROMANEIO (.pdf)</b>

<b>Suporta:</b>
• PDFs com texto extraível
• PDFs escaneados (OCR automático)
• Geocodificação Google Maps

<b>⚠️ Limite:</b> 50 endereços por PDF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✅ TEXTO MANUAL (.txt)</b>

<b>Formato:</b>
Um endereço completo por linha

<b>Exemplo:</b>
<code>Av Paulista 1000, São Paulo - SP
Rua Oscar Freire 500, São Paulo - SP</code>

Sistema faz geocoding automaticamente.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 DICA:</b>
Pode enviar múltiplos arquivos!
Sistema consolida tudo."""

        await query.edit_message_text(
            formats_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_technology":
        tech_text = """<b>🧠 TECNOLOGIA SCOOTER MODE</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>ALGORITMOS APLICADOS</b>

<b>1️⃣ Agrupamento por STOP</b>
Entregas no mesmo endereço = 1 parada
• Detecta edifícios e prédios
• Agrupa apartamentos/salas
• Economiza tempo de navegação

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>2️⃣ Divisão Geográfica</b>
<b>K-means Clustering</b>
• Divide cidade em territórios
• Equilibra carga entre entregadores
• Minimiza sobreposição de rotas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>3️⃣ Otimização de Rota</b>
<b>Algoritmo Genético</b>
• Calcula melhor sequência
• Distância euclidiana otimizada
• Considera contrafluxo quando seguro

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>4️⃣ Modo Scooter</b>
<b>Atalhos Permitidos:</b>
✓ Calçadas largas
✓ Vielas e becos
✓ Contrafluxo em ruas locais
✓ Aglomerações próximas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 RESULTADOS COMPROVADOS</b>

• <b>79% economia</b> vs rota original
• <b>40% menos tempo</b> por entrega
• <b>60% mais capacidade</b> diária
• <b>95% taxa de sucesso</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🤖 IA PREDITIVA</b>

Sistema aprende com cada entrega:
• Tempo médio por região
• Dificuldade de acesso
• Horários de pico
• Perfil de cada entregador"""

        await query.edit_message_text(
            tech_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_financial":
        financial_text = """<b>💰 SISTEMA FINANCEIRO</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 COMANDOS BÁSICOS</b>

<code>/fechar_dia</code>
Fecha o dia manualmente
• Informa receita do dia
• Sistema calcula custos automaticamente
• Gera relatório com lucro líquido

<code>/financeiro [periodo]</code>
Consulta relatórios financeiros
• <code>dia</code> — Fechamento de hoje
• <code>semana</code> — Últimos 7 dias
• <code>mes</code> — Mês atual completo

<code>/fechar_semana</code>
Fechamento semanal com divisão
• 10% vai para reserva empresa
• 70/30 dividido entre sócios
• Relatório completo gerado

<code>/config_socios</code>
Configura percentuais dos sócios
Exemplo: <code>/config_socios João 70 Maria 30 10</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💡 FLUXO DIÁRIO RECOMENDADO</b>

1️⃣ Fim do dia → <code>/fechar_dia</code>
2️⃣ Informa receita total
3️⃣ Informa outros custos (gasolina, etc)
4️⃣ Sistema calcula e salva automaticamente

<b>🗓️ FLUXO SEMANAL</b>

Domingo/Segunda → <code>/fechar_semana</code>
• Revisa todos os dias da semana
• Confirma divisão de lucros
• Gera relatório para contabilidade"""

        await query.edit_message_text(
            financial_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_advanced_features":
        advanced_text = """<b>🔮 FUNCIONALIDADES AVANÇADAS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 DASHBOARD WEB</b>

<code>/dashboard</code>
Inicia interface web em <code>http://localhost:5000</code>

<b>Recursos:</b>
✅ Gráficos interativos (Chart.js)
✅ Evolução de receitas e lucros
✅ Distribuição de custos (pizza)
✅ Divisão semanal entre sócios
✅ Auto-refresh a cada 5 minutos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📄 EXPORTAÇÃO PROFISSIONAL</b>

<code>/exportar [formato] [dias]</code>

<b>Exemplos:</b>
• <code>/exportar excel 30</code> — Excel 30 dias
• <code>/exportar pdf 7</code> — PDF última semana

<b>Formato Excel:</b> Tabelas formatadas, cores, totais
<b>Formato PDF:</b> Layout A4 landscape, divisão sócios

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏦 INTEGRAÇÃO BANCO INTER</b>

<code>/config_banco_inter</code>
Configura API do Banco Inter
Requer: Client ID, Secret, Certificados

<code>/fechar_dia_auto</code>
Fechamento automático com receita do banco
• Busca extrato do dia
• Calcula receita automaticamente
• Solicita apenas outros custos

<code>/saldo_banco</code>
Consulta saldo em tempo real

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🤖 PROJEÇÕES COM IA</b>

<code>/projecoes [dias]</code>

<b>Exemplos:</b>
• <code>/projecoes 7</code> — Próxima semana
• <code>/projecoes 30</code> — Próximo mês

<b>Algoritmo usa:</b>
✓ Regressão linear
✓ Análise de sazonalidade
✓ Taxa de crescimento
✓ Confiança (alta/média/baixa)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📚 DOCUMENTAÇÃO COMPLETA</b>

Veja: <code>MANUAL_FUNCIONALIDADES_AVANCADAS.md</code>"""

        await query.edit_message_text(
            advanced_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Voltar ao Menu", callback_data="help_main")
            ]])
        )
    
    elif data == "help_main":
        # Volta para o /help principal - recriar a mensagem
        help_text = """<b>🚀 BOT MULTI-ENTREGADOR v3.0</b>
<i>Sistema Inteligente com IA + Dashboard</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>⚡ COMANDOS PRINCIPAIS</b>

<b>📦 OPERACIONAL:</b>
<code>/add_entregador</code> — Cadastrar equipe
<code>/importar</code> — Enviar romaneios
<code>/otimizar</code> — Distribuir rotas IA

<b>💰 FINANCEIRO:</b>
<code>/fechar_dia</code> — Fechamento manual
<code>/financeiro</code> — Relatórios completos
<code>/fechar_semana</code> — Divisão sócios

<b>🚀 AVANÇADO:</b>
<code>/dashboard</code> — Interface web gráfica
<code>/exportar</code> — Excel/PDF profissional
<code>/projecoes</code> — Previsões IA
<code>/fechar_dia_auto</code> — Banco Inter

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Clique nos botões</b> para guias detalhados"""

        keyboard = [
            [InlineKeyboardButton("🚀 Iniciar Operação", callback_data="help_start_operation")],
            [
                InlineKeyboardButton("👥 Gerenciar Equipe", callback_data="help_team_management"),
                InlineKeyboardButton("💰 Financeiro", callback_data="help_financial")
            ],
            [
                InlineKeyboardButton("🔮 Funcionalidades Avançadas", callback_data="help_advanced_features")
            ],
            [
                InlineKeyboardButton("📂 Formatos de Arquivo", callback_data="help_file_formats"),
                InlineKeyboardButton("🧠 Tecnologia", callback_data="help_technology")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    # REMOVER HANDLERS ANTIGOS
    elif data in ["help_import", "help_team", "help_status", "help_ranking", "help_quickstart", "help_back", "help_monitoring"]:
        # Redireciona para o novo menu
        await query.answer("Use os novos botões do menu!", show_alert=True)
        # Volta para o menu principal
        data = "help_main"
        # Reprocessa
        help_text = """<b>🚀 BOT MULTI-ENTREGADOR v3.0</b>
<i>Sistema Inteligente com IA + Dashboard</i>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>⚡ COMANDOS PRINCIPAIS</b>

<b>📦 OPERACIONAL:</b>
<code>/add_entregador</code> — Cadastrar equipe
<code>/importar</code> — Enviar romaneios
<code>/otimizar</code> — Distribuir rotas IA

<b>💰 FINANCEIRO:</b>
<code>/fechar_dia</code> — Fechamento manual
<code>/financeiro</code> — Relatórios completos
<code>/fechar_semana</code> — Divisão sócios

<b>🚀 AVANÇADO:</b>
<code>/dashboard</code> — Interface web gráfica
<code>/exportar</code> — Excel/PDF profissional
<code>/projecoes</code> — Previsões IA
<code>/fechar_dia_auto</code> — Banco Inter

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Clique nos botões</b> para guias detalhados"""

        keyboard = [
            [InlineKeyboardButton("🚀 Iniciar Operação", callback_data="help_start_operation")],
            [
                InlineKeyboardButton("👥 Gerenciar Equipe", callback_data="help_team_management"),
                InlineKeyboardButton("💰 Financeiro", callback_data="help_financial")
            ],
            [
                InlineKeyboardButton("🔮 Funcionalidades Avançadas", callback_data="help_advanced_features")
            ],
            [
                InlineKeyboardButton("📂 Formatos de Arquivo", callback_data="help_file_formats"),
                InlineKeyboardButton("🧠 Tecnologia", callback_data="help_technology")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
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
    # Busca lista de entregadores para permitir transferência
    from bot_multidelivery.services.deliverer_service import deliverer_service
    all_deliverers = deliverer_service.get_all_deliverers()
    entregadores_lista = [{'name': d.name, 'id': str(d.telegram_id)} for d in all_deliverers]
    
    # Garante que existe mapa HTML
    if not route.map_file:
        stops_data = []
        for i, point in enumerate(route.optimized_order):
            status = 'current' if i == 0 else 'pending'
            stops_data.append((point.lat, point.lng, point.address, 1, status))

        eta_minutes = max(10, route.total_distance_km / 25 * 60 + len(route.optimized_order) * 3)
        # session já é passado como argumento, não precisamos buscar novamente
        base_loc = (session.base_lat, session.base_lng, session.base_address) if session and session.base_lat and session.base_lng else None
        html = MapGenerator.generate_interactive_map(
            stops=stops_data,
            entregador_nome=f"{route.id}",
            current_stop=0,
            total_packages=route.total_packages,
            total_distance_km=route.total_distance_km,
            total_time_min=eta_minutes,
            base_location=base_loc,
            entregadores_lista=entregadores_lista,
            session_id=session.session_id if session else None,
            entregador_id=str(telegram_id)
        )
        route.map_file = f"map_{route.id}.html"
        MapGenerator.save_map(html, route.map_file)

    message = f"🗺️ <b>SUA ROTA - {route.id}</b>\n\n"
    message += f"📍 Base: {session.base_address}\n"
    message += f"📦 Total: {route.total_packages} pacotes\n\n"
    message += "📋 <b>Ordem de entrega:</b>\n\n"
    
    # CORREÇÃO: Renumera para sequência limpa 1, 2, 3... (não mostra PKG IDs globais que pulam)
    for i, point in enumerate(route.optimized_order, 1):
        message += f"<b>{i}.</b> {point.address}\n"
        # Mostra package_id original apenas como referência (entre parênteses)
        message += f"    <i>Código: {point.package_id}</i>\n\n"
    
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
        
        session = session_manager.get_current_session()
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
    session = session_manager.get_current_session()
    
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
    session = session_manager.get_current_session()
    
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


# ==================== FINANCIAL COMMANDS ====================

async def cmd_fechar_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Fecha o dia financeiro: Receita -> Custos -> Lucro"""
    user_id = update.effective_user.id
    args = context.args
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode fechar o dia.")
        return
    
    closing_date = datetime.now()
    date_str = "HOJE"
    
    # Suporte a fechamento retroativo: /fechar_dia 2023-10-25
    if args and len(args) == 1:
        try:
            closing_date = datetime.strptime(args[0], "%Y-%m-%d")
            date_str = args[0]
        except ValueError:
            await update.message.reply_text("❌ Data inválida! Use formato AAAA-MM-DD\nEx: /fechar_dia 2023-10-25")
            return
            
    # Pega sessão ativa para calcular custos (se for hoje ou se houver sessão para a data)
    session = session_manager.get_current_session()
    
    # Se for retroativo, tenta achar sessão daquele dia, ou começa zerado
    if date_str != "HOJE":
        # TODO: Implementar busca de sessão por data histórica se necessário
        # Por enquanto, retroativo assume input manual de custos se não tiver sessão ativa
        session = None 
    
    # Limpa dados temporários anteriores para não misturar shutdowns
    session_manager.save_temp_data(user_id, "day_closing", {
        'target_date': closing_date.strftime("%Y-%m-%d")
    })
    
    if not session and date_str == "HOJE":
        await update.message.reply_text(
            "⚠️ <b>Aviso:</b> Nenhuma sessão ativa.\n"
            "Vou iniciar um fechamento avulso.",
            parse_mode='HTML'
        )
    
    # Prepara estado: Passo 1 - Receita
    session_manager.set_admin_state(user_id, "closing_day_revenue")
    
    await update.message.reply_text(
        f"💰 <b>FECHAMENTO FINANCEIRO ({date_str})</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Vamos calcular o lucro real.\n\n"
        "1️⃣ <b>PASSO 1: Faturamento</b>\n"
        "Qual foi o valor TOTAL recebido das rotas?\n\n"
        "<i>Digite o valor (ex: 250.00):</i>",
        parse_mode='HTML'
    )

"""
    
    for name, cost in sorted(deliverer_costs.items()):
        emoji = "🤝" if cost == 0 else "💼"
        msg += f"{emoji} {name}: R$ {cost:.2f}\n"
    
    msg += f"\n<b>Total Custos: R$ {total_costs:.2f}</b>\n"
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "💵 <b>Qual foi a RECEITA BRUTA de hoje?</b>\n\n"
    msg += "Digite o valor em reais (ex: 450.00)\n"
    msg += "Ou digite /cancelar para abortar."
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_financeiro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra relatório financeiro (diário, semanal ou mensal)"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode ver relatórios financeiros.")
        return
    
    # Sem argumentos = relatório de hoje
    if not context.args:
        today = datetime.now()
        report = financial_service.get_daily_report(today)
        
        if not report:
            await update.message.reply_text(
                "❌ <b>SEM DADOS PARA HOJE</b>\n\n"
                "Use <code>/fechar_dia</code> para registrar o fechamento.\n\n"
                "💡 Ou use:\n"
                "• <code>/financeiro semana</code> - Últimos 7 dias\n"
                "• <code>/financeiro mes</code> - Mês atual",
                parse_mode='HTML'
            )
            return
        
        msg = financial_service.format_daily_report(report)
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Com argumentos
    periodo = context.args[0].lower()
    
    if periodo == 'semana':
        # Últimos 7 dias
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        
        reports = financial_service.get_daily_reports_range(start_date, end_date)
        
        if not reports:
            await update.message.reply_text(
                "❌ Nenhum dado encontrado nos últimos 7 dias.",
                parse_mode='HTML'
            )
            return
        
        # Calcula totais
        total_revenue = sum(r.revenue for r in reports)
        total_costs = sum(r.delivery_costs + r.other_costs for r in reports)
        total_profit = sum(r.net_profit for r in reports)
        
        msg = f"""📊 <b>RESUMO SEMANAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Período: {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m/%Y')}
📆 Dias com dados: {len(reports)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💵 TOTAIS DA SEMANA</b>

📈 Receita: <b>R$ {total_revenue:,.2f}</b>
💸 Custos: R$ {total_costs:,.2f}
💰 Lucro: <b>R$ {total_profit:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 MÉDIAS DIÁRIAS</b>

Receita: R$ {total_revenue/len(reports):,.2f}
Lucro: R$ {total_profit/len(reports):,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Use <code>/fechar_semana</code> para dividir lucros"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    elif periodo in ['mes', 'mês']:
        # Mês atual
        now = datetime.now()
        summary = financial_service.get_month_summary(now.year, now.month)
        msg = financial_service.format_month_summary(summary)
        await update.message.reply_text(msg, parse_mode='HTML')
    
    else:
        await update.message.reply_text(
            "❌ Período inválido.\n\n"
            "<b>Use:</b>\n"
            "• <code>/financeiro</code> - Hoje\n"
            "• <code>/financeiro semana</code> - Últimos 7 dias\n"
            "• <code>/financeiro mes</code> - Mês atual",
            parse_mode='HTML'
        )


async def cmd_fechar_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Fecha a semana e divide lucros entre sócios"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode fechar a semana.")
        return
    
    # Pede custos operacionais da semana
    session_manager.set_admin_state(user_id, "closing_week")
    
    # Calcula semana atual (segunda a domingo)
    today = datetime.now()
    weekday = today.weekday()  # 0 = segunda
    week_start = today - timedelta(days=weekday)
    
    session_manager.save_temp_data(user_id, "week_closing", {
        'week_start': week_start.strftime('%Y-%m-%d')
    })
    
    msg = f"""💰 <b>FECHAMENTO SEMANAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Semana: {week_start.strftime('%d/%m/%Y')} a {(week_start + timedelta(days=6)).strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏢 CUSTOS OPERACIONAIS DA SEMANA</b>

Digite o valor total de custos operacionais:
• Aluguel
• Energia
• Internet
• Manutenção
• Outros

<b>Exemplo:</b> 350.00

Ou digite <code>0</code> se não houve custos extras.
Digite /cancelar para abortar."""
    
    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_config_socios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Configura nomes e percentuais dos sócios"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Apenas o admin pode configurar sócios.")
        return
    
    if not context.args:
        # Mostra configuração atual
        cfg = financial_service.partner_config
        
        msg = f"""⚙️ <b>CONFIGURAÇÃO DOS SÓCIOS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>👥 SÓCIOS:</b>

🤝 <b>{cfg.partner_1_name}</b>: {cfg.partner_1_share*100:.0f}%
🤝 <b>{cfg.partner_2_name}</b>: {cfg.partner_2_share*100:.0f}%

<b>🏦 RESERVA EMPRESA:</b> {cfg.reserve_percentage*100:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📝 PARA ALTERAR:</b>

<code>/config_socios Nome1 70 Nome2 30 10</code>

<b>Parâmetros:</b>
1. Nome do sócio 1
2. Percentual do sócio 1 (%)
3. Nome do sócio 2
4. Percentual do sócio 2 (%)
5. Percentual de reserva (%)

<b>Exemplo:</b>
<code>/config_socios João 70 Maria 30 10</code>"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Atualiza configuração
    if len(context.args) != 5:
        await update.message.reply_text(
            "❌ Formato inválido.\n\n"
            "<b>Use:</b>\n"
            "<code>/config_socios Nome1 % Nome2 % Reserva%</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        p1_name = context.args[0]
        p1_share = float(context.args[1]) / 100
        p2_name = context.args[2]
        p2_share = float(context.args[3]) / 100
        reserve = float(context.args[4]) / 100
        
        # Valida
        if p1_share + p2_share != 1.0:
            await update.message.reply_text(
                f"❌ Os percentuais dos sócios devem somar 100%\n"
                f"Você informou: {p1_share*100:.0f}% + {p2_share*100:.0f}% = {(p1_share+p2_share)*100:.0f}%",
                parse_mode='HTML'
            )
            return
        
        # Atualiza
        financial_service.update_partner_config(
            partner_1_name=p1_name,
            partner_1_share=p1_share,
            partner_2_name=p2_name,
            partner_2_share=p2_share,
            reserve_percentage=reserve
        )
        
        await update.message.reply_text(
            f"""✅ <b>CONFIGURAÇÃO ATUALIZADA!</b>

🤝 {p1_name}: {p1_share*100:.0f}%
🤝 {p2_name}: {p2_share*100:.0f}%
🏦 Reserva: {reserve*100:.0f}%""",
            parse_mode='HTML'
        )
    
    except ValueError:
        await update.message.reply_text(
            "❌ Valores inválidos. Use números para os percentuais.",
            parse_mode='HTML'
        )


async def cmd_exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /exportar [excel|pdf] [dias] - Exporta relatórios"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin pode exportar")
        return
    
    from .services import export_service
    
    # Parâmetros
    formato = context.args[0] if len(context.args) > 0 else 'excel'
    days = int(context.args[1]) if len(context.args) > 1 else 30
    
    await update.message.reply_text("📊 Gerando exportação, aguarde...")
    
    try:
        # Busca dados
        reports = []
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=days - i - 1)
            report = financial_service.get_daily_report(date)
            
            if report:
                reports.append({
                    'date': report.date,
                    'revenue': report.revenue,
                    'delivery_costs': report.delivery_costs,
                    'other_costs': report.other_costs,
                    'net_profit': report.net_profit,
                    'total_packages': report.total_packages,
                    'total_deliveries': report.total_deliveries
                })
        
        if not reports:
            await update.message.reply_text("❌ Sem dados para exportar")
            return
        
        # Exporta
        if formato.lower() == 'pdf':
            # Para PDF, busca também config e relatório semanal
            week_start = end_date - timedelta(days=6)
            config = financial_service.partner_config
            weekly_report = financial_service.get_weekly_report(week_start)
            
            weekly_summary = None
            if weekly_report:
                weekly_summary = {
                    'gross_profit': weekly_report.gross_profit,
                    'reserve_amount': weekly_report.reserve_amount,
                    'distributable_profit': weekly_report.distributable_profit,
                    'partner_1_share': weekly_report.partner_1_share,
                    'partner_2_share': weekly_report.partner_2_share
                }
            
            filepath = export_service.export_to_pdf(
                reports,
                week_start=week_start,
                week_end=end_date,
                partner_config={
                    'partner_1_name': config.partner_1_name,
                    'partner_2_name': config.partner_2_name,
                    'partner_1_share': config.partner_1_share,
                    'partner_2_share': config.partner_2_share,
                    'reserve_percentage': config.reserve_percentage
                },
                weekly_summary=weekly_summary
            )
        else:
            filepath = export_service.export_to_excel(
                reports,
                week_start=end_date - timedelta(days=6),
                week_end=end_date
            )
        
        # Envia arquivo
        await update.message.reply_document(
            document=open(filepath, 'rb'),
            caption=f"📊 Relatório de {days} dias - {formato.upper()}"
        )
        
        logger.info(f"Relatório exportado: {filepath}")
    
    except ImportError as e:
        await update.message.reply_text(
            f"❌ Biblioteca não instalada: {str(e)}\n\n"
            f"Instale com:\n<code>pip install openpyxl reportlab</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Erro ao exportar: {e}")
        await update.message.reply_text(f"❌ Erro ao exportar: {e}")


async def cmd_config_banco_inter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /config_banco_inter - Configura credenciais Banco Inter"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin pode configurar")
        return
    
    from .services import bank_inter_service
    
    if len(context.args) == 0:
        # Mostra status
        status = "✅ Configurado" if bank_inter_service.is_configured() else "❌ Não configurado"
        
        await update.message.reply_text(
            f"""🏦 <b>BANCO INTER - API</b>

<b>Status:</b> {status}

<b>🔧 CONFIGURAR:</b>
<code>/config_banco_inter CLIENT_ID CLIENT_SECRET CERT_PATH KEY_PATH CONTA</code>

<b>📚 Como obter:</b>
1. Acesse: https://developers.bancointer.com.br
2. Crie uma aplicação
3. Gere certificado digital
4. Anote Client ID e Secret
5. Use este comando com os dados

<b>⚠️ IMPORTANTE:</b>
• Mantenha as credenciais seguras
• Certificados devem estar no servidor
• Conta deve ser formato: 12345678""",
            parse_mode='HTML'
        )
        return
    
    # Configura
    if len(context.args) != 5:
        await update.message.reply_text(
            "❌ Formato inválido\n\n"
            "<b>Use:</b>\n"
            "<code>/config_banco_inter CLIENT_ID CLIENT_SECRET CERT_PATH KEY_PATH CONTA</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        client_id = context.args[0]
        client_secret = context.args[1]
        cert_path = context.args[2]
        key_path = context.args[3]
        conta = context.args[4]
        
        bank_inter_service.configure_credentials(
            client_id=client_id,
            client_secret=client_secret,
            cert_path=cert_path,
            key_path=key_path,
            conta_corrente=conta
        )
        
        await update.message.reply_text(
            "✅ <b>BANCO INTER CONFIGURADO!</b>\n\n"
            "Agora você pode usar:\n"
            "• <code>/fechar_dia_auto</code> - Fecha dia com receita do banco\n"
            "• <code>/saldo_banco</code> - Consulta saldo atual",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Erro ao configurar Banco Inter: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")


async def cmd_fechar_dia_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /fechar_dia_auto - Fecha dia automaticamente com receita do banco"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    from .services import bank_inter_service
    
    if not bank_inter_service.is_configured():
        await update.message.reply_text(
            "❌ Banco Inter não configurado\n\n"
            "Use <code>/config_banco_inter</code>",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text("🏦 Buscando receita do banco, aguarde...")
    
    try:
        # Busca receita do dia
        today = datetime.now()
        receita = bank_inter_service.calcular_receita_do_dia(today)
        
        # Calcula custos dos entregadores
        session = session_manager.get_current_session()
        delivery_costs = 0
        
        if session and session.routes:
            for route in session.routes:
                partner = BotConfig.get_partner_by_id(route.deliverer_id)
                if partner:
                    delivery_costs += len(route.packages) * partner.cost_per_package
        
        # Solicita outros custos
        session_manager.set_admin_state(user_id, "closing_day_auto_costs")
        session_manager.admin_temp_data[user_id] = {
            'revenue': receita,
            'delivery_costs': delivery_costs
        }
        
        await update.message.reply_text(
            f"""💰 <b>FECHAMENTO AUTOMÁTICO</b>

🏦 <b>Receita do Banco:</b> R$ {receita:,.2f}
👥 <b>Custos Entregadores:</b> R$ {delivery_costs:,.2f}

<b>📝 Outros custos operacionais?</b>
(Gasolina, manutenção, etc)

Digite o valor ou 0:""",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Erro ao fechar dia automático: {e}")
        await update.message.reply_text(
            f"❌ Erro ao buscar dados do banco:\n{e}\n\n"
            f"Verifique:\n"
            f"• Credenciais corretas\n"
            f"• Certificados válidos\n"
            f"• Conexão com a internet",
            parse_mode='HTML'
        )


async def cmd_saldo_banco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /saldo_banco - Consulta saldo do Banco Inter"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    from .services import bank_inter_service
    
    if not bank_inter_service.is_configured():
        await update.message.reply_text(
            "❌ Banco Inter não configurado\n\n"
            "Use <code>/config_banco_inter</code>",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text("🏦 Consultando saldo...")
    
    try:
        saldo_data = bank_inter_service.get_saldo_atual()
        
        disponivel = saldo_data.get('disponivel', 0)
        bloqueado = saldo_data.get('bloqueado', 0)
        
        await update.message.reply_text(
            f"""🏦 <b>BANCO INTER - SALDO</b>

💰 <b>Disponível:</b> R$ {disponivel:,.2f}
🔒 <b>Bloqueado:</b> R$ {bloqueado:,.2f}
━━━━━━━━━━━━━━━━━━━━━━━
💵 <b>Total:</b> R$ {(disponivel + bloqueado):,.2f}

<i>Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>""",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Erro ao consultar saldo: {e}")
        await update.message.reply_text(f"❌ Erro ao consultar saldo:\n{e}")


async def cmd_projecoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /projecoes [dias] - Mostra projeções de lucro"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    from .services import projection_service
    
    days = int(context.args[0]) if len(context.args) > 0 else 7
    
    await update.message.reply_text("🔮 Calculando projeções...")
    
    try:
        # Análise de crescimento
        growth = projection_service.analyze_growth_rate(30)
        
        # Projeções
        predictions = projection_service.predict_next_days(days)
        
        if not predictions:
            await update.message.reply_text(
                "❌ Dados insuficientes para projeções\n\n"
                "São necessários pelo menos 7 dias de histórico"
            )
            return
        
        # Formata mensagem
        msg = f"""🔮 <b>PROJEÇÕES DE LUCRO</b>

📈 <b>Taxa de Crescimento:</b> {growth['growth_rate']:.1f}%
📊 <b>Tendência:</b> {growth['trend']}

━━━━━━━━━━━━━━━━━━━━━━━
<b>📅 PRÓXIMOS {days} DIAS:</b>

"""
        
        total_predicted = 0
        
        for pred in predictions:
            date_obj = datetime.strptime(pred['date'], '%Y-%m-%d')
            date_fmt = date_obj.strftime('%d/%m')
            weekday = pred['weekday'][:3]
            
            confidence_emoji = "🟢" if pred['confidence'] == 'alta' else "🟡" if pred['confidence'] == 'média' else "🔴"
            
            msg += f"\n{confidence_emoji} <b>{date_fmt} ({weekday})</b>\n"
            msg += f"   💰 Lucro: R$ {pred['predicted_profit']:,.2f}\n"
            msg += f"   📈 Receita: R$ {pred['predicted_revenue']:,.2f}\n"
            
            total_predicted += pred['predicted_profit']
        
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━━"
        msg += f"\n💵 <b>TOTAL PREVISTO:</b> R$ {total_predicted:,.2f}"
        msg += f"\n📊 <b>MÉDIA DIÁRIA:</b> R$ {total_predicted/days:,.2f}"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Erro ao gerar projeções: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /dashboard - Inicia dashboard web"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    from .services import start_dashboard_thread
    
    try:
        # Inicia dashboard em thread
        port = 5000
        start_dashboard_thread(host='0.0.0.0', port=port)
        
        await update.message.reply_text(
            f"""📊 <b>DASHBOARD WEB INICIADO!</b>

🌐 <b>Acesse:</b>
<code>http://localhost:{port}</code>

<b>🎨 RECURSOS:</b>
✅ Gráficos interativos em tempo real
✅ Evolução de receitas e lucros
✅ Distribuição de custos
✅ Projeções futuras
✅ Exportação Excel/PDF

<b>💡 DICA:</b>
Para acesso externo, use o IP público do servidor:
<code>http://SEU_IP:{port}</code>

━━━━━━━━━━━━━━━━━━━━━━━
<i>Dashboard rodando em background...</i>""",
            parse_mode='HTML'
        )
    
    except Exception as e:
        logger.error(f"Erro ao iniciar dashboard: {e}")
        await update.message.reply_text(f"❌ Erro ao iniciar dashboard:\n{e}")


# ==================== MODO SEPARAÇÃO POR COR ====================

async def cmd_selecionar_sessao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📂 Seleciona qual sessão usar (quando há múltiplas ativas)"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin pode usar este comando")
        return
    
    sessions = session_manager.list_sessions(finalized_only=False)
    
    if not sessions:
        await update.message.reply_text(
            "❌ <b>NENHUMA SESSÃO ATIVA</b>\n\n"
            "Use <code>/importar</code> para criar uma nova sessão.",
            parse_mode='HTML'
        )
        return
    
    current = session_manager.get_current_session()
    current_id = current.session_id if current else None
    
    # Cria botões para cada sessão
    keyboard = []
    for session in sessions:
        is_current = "✅ " if session.session_id == current_id else ""
        status = "🔒 Finalizada" if session.is_finalized else "🟢 Ativa"
        
        label = (
            f"{is_current}{session.date} ({session.session_id[:6]})\n"
            f"{status} • {len(session.romaneios)} romaneios • {len(session.routes)} rotas"
        )
        
        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"select_session_{session.session_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📂 <b>SELECIONAR SESSÃO</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha qual sessão usar para:\n"
        "• <code>/modo_separacao</code>\n"
        "• <code>/analisar_rota</code>\n"
        "• Outros comandos\n\n"
        "✅ = Sessão atual em uso",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def cmd_modo_separacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎨 Inicia modo separação - bipar códigos de barras"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin pode usar este modo")
        return
    
    # Verifica se há múltiplas sessões ativas
    all_sessions = session_manager.list_sessions(finalized_only=False)
    active_sessions = [s for s in all_sessions if not s.is_finalized]
    
    session = session_manager.get_current_session()
    
    # Se há múltiplas sessões ativas, avisa o usuário
    if len(active_sessions) > 1:
        session_info = f"📅 Usando sessão: <b>{session.date}</b> (<code>{session.session_id[:6]}</code>)\n\n"
        session_info += f"⚠️ Você tem <b>{len(active_sessions)} sessões ativas</b>!\n"
        session_info += f"Use <code>/selecionar_sessao</code> se quiser trocar.\n\n"
    else:
        session_info = ""
    
    if not session or not session.routes:
        msg = (
            "❌ <b>NENHUMA ROTA DIVIDIDA!</b>\n\n"
            f"{session_info}"
            "Fluxo correto:\n"
            "1️⃣ <code>/fechar_rota</code> - Divide rotas\n"
            "2️⃣ Atribui entregadores\n"
            "3️⃣ <code>/modo_separacao</code> - Ativa separação\n\n"
        )
        
        if len(active_sessions) > 1:
            msg += "💡 <i>Ou use /selecionar_sessao para escolher outra sessão</i>"
        else:
            msg += "💡 <i>Divida as rotas primeiro!</i>"
        
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Verifica se todas as rotas têm entregadores atribuídos
    rotas_sem_entregador = [r for r in session.routes if not r.assigned_to_name]
    if rotas_sem_entregador:
        await update.message.reply_text(
            f"⚠️ <b>ROTAS SEM ENTREGADOR!</b>\n\n"
            f"❌ {len(rotas_sem_entregador)} rotas não atribuídas:\n"
            + "\n".join([f"• {r.id}" for r in rotas_sem_entregador]) +
            "\n\n💡 Atribua todos os entregadores antes de separar!",
            parse_mode='HTML'
        )
        return
    
    # Importa função de cores
    from .colors import get_color_name
    
    # Prepara mensagem visual com as cores
    mensagem_cores = "🎨 <b>CORES DAS ROTAS:</b>\n\n"
    
    for route in session.routes:
        color_name = get_color_name(route.color)
        emoji = color_name.split()[0]
        entregador = route.assigned_to_name
        
        mensagem_cores += f"{emoji} <b>{color_name}</b> → {entregador}\n"
        mensagem_cores += f"   📦 {len(route.optimized_order)} pacotes\n\n"
    
    # Ativa modo separação com sessão
    result = barcode_separator.start_separation_mode(session)
    
    # Info sobre múltiplas sessões
    session_warning = ""
    if len(active_sessions) > 1:
        session_warning = f"\n⚠️ Usando sessão: <b>{session.date}</b> (<code>{session.session_id[:6]}</code>)\n"
    
    # Gera link do scanner web (Railway)
    scanner_link = ""
    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')  # Ex: projeto.up.railway.app
    if railway_domain:
        scanner_url = f"https://{railway_domain}/scanner"
        scanner_link = f"\n📱 <b>SCANNER WEB (celular):</b>\n<a href='{scanner_url}'>{scanner_url}</a>\n"
    
    mensagem = f"""🎨 <b>MODO SEPARAÇÃO ATIVADO!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{session_warning}
{mensagem_cores}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{scanner_link}
<b>🔍 COMO USAR:</b>

<b>📱 OPÇÃO 1: Scanner Web (celular)</b>
• Abra o link acima no celular
• Aponte a câmera para o código de barras
• Bot responde automaticamente com a COR

<b>🖥️ OPÇÃO 2: Leitor USB (computador)</b>
• Conecte o leitor USB
• Bipe o código
• Código aparece no chat automaticamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Pegue um pacote da pilha
2️⃣ Bipe/Scaneie o código de barras
3️⃣ Bot responde com a COR
4️⃣ Cole a etiqueta colorida
5️⃣ Próximo pacote!

<b>⚡ VELOCIDADE:</b>
~3 segundos por pacote = 20 pacotes/minuto

<b>📊 PROGRESSO:</b>
Use <code>/status_separacao</code> para ver quantos faltam

<b>🏁 FINALIZAR:</b>
Quando terminar: <code>/fim_separacao</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 <b>BORA SEPARAR!</b>"""
    
    await update.message.reply_text(mensagem, parse_mode='HTML')


async def cmd_fim_separacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏁 Finaliza modo separação e mostra relatório"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    if not barcode_separator.active:
        await update.message.reply_text(
            "⚠️ <b>MODO SEPARAÇÃO INATIVO</b>\n\n"
            "Use <code>/modo_separacao</code> para começar.",
            parse_mode='HTML'
        )
        return
    
    # Finaliza e pega relatório
    relatorio = barcode_separator.end_separation()
    
    await update.message.reply_text(relatorio, parse_mode='HTML')


async def cmd_status_separacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Mostra status atual da separação"""
    user_id = update.effective_user.id
    
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("⛔ Apenas admin")
        return
    
    status = barcode_separator.get_status()
    await update.message.reply_text(status, parse_mode='HTML')


# Intercept barcode scans in text messages (admin only)
async def handle_admin_barcode_scan(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Detecta e processa códigos de barras escaneados"""
    user_id = update.effective_user.id
    
    # Só processa se modo separação estiver ativo
    if not barcode_separator.active:
        return False  # Não foi um scan
    
    # Códigos de barras geralmente são alfanuméricos sem espaços
    # Shopee: letras + números (ex: BR123ABC456)
    # Mercado Livre: numérico longo (ex: 123456789012)
    if len(text) >= 6 and (text.isalnum() or text.isnumeric()):
        response = barcode_separator.scan_package(text)
        
        if response:
            await update.message.reply_text(response, parse_mode='HTML')
            return True  # Foi processado como scan
    
    return False  # Não foi um scan


# ==================== MAIN ====================

async def cmd_otimizar_rotas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🧠 OTIMIZAÇÃO INTERATIVA para chamadas sem argumentos (Botão / Comando simples)
    Usa os dados da sessão ativa.
    """
    user_id = update.effective_user.id
    if user_id != BotConfig.ADMIN_TELEGRAM_ID:
        return
    
    session = session_manager.get_current_session()
    
    # Validações iniciais
    if not session:
        msg = "❌ <b>Nenhuma sessão ativa!</b>\nUse /importar para começar."
        if update.callback_query:
            await update.callback_query.answer(msg)
            await update.callback_query.edit_message_text(msg, parse_mode='HTML')
        else:
            await update.message.reply_text(msg, parse_mode='HTML')
        return

    if not session.romaneios and not session.routes:
         # Se tiver routes mas nao romaneios (ex: reinicio), ok. Mas geralmente tem romaneios.
         # Se estiver vazio tudo...
        msg = "❌ <b>Nenhum pacote importado!</b>\nImporte romaneios antes de otimizar."
        if update.callback_query:
            await update.callback_query.answer(msg)
            await update.callback_query.edit_message_text(msg, parse_mode='HTML')
        else:
            await update.message.reply_text(msg, parse_mode='HTML')
        return

    # Pergunta quantidade de entregadores
    keyboard = []
    # Cria linhas de 3 botões
    row = []
    for n in range(1, 7):
        row.append(InlineKeyboardButton(f"🛵 {n}", callback_data=f"optimize_num_{n}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    total_packages = session.total_packages
    
    msg = (
        "🧠 <b>OTIMIZAÇÃO INTELIGENTE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total de pacotes: <b>{total_packages}</b>\n"
        f"📅 Sessão: {session.session_name}\n\n"
        "🔢 <b>Quantos entregadores vão rodar?</b>"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def handle_optimization_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: Escolheu número de entregadores -> Vai pra seleção de cor"""
    query = update.callback_query
    await query.answer()
    
    num_entregadores = int(query.data.replace("optimize_num_", ""))
    
    # Salva no temp_data para o fluxo de cores usar
    if not hasattr(context.user_data, 'temp'):
        context.user_data['temp'] = {}
        
    context.user_data['temp']['otimizar_num'] = num_entregadores
    # IMPORTANTE: Marca que NÃO estamos usando Excel direto, mas sim sessão
    context.user_data['temp']['otimizar_excel'] = None 
    context.user_data['temp']['colors_selected'] = []
    
    # Chama o seletor de cores (reutiliza lógica existente)
    # Precisamos montar o teclado aqui
    color_buttons = [
        [
            InlineKeyboardButton("🔴 Vermelho", callback_data="color_vermelho"),
            InlineKeyboardButton("🔵 Azul", callback_data="color_azul"),
        ],
        [
            InlineKeyboardButton("🟢 Verde", callback_data="color_verde"),
            InlineKeyboardButton("🟡 Amarelo", callback_data="color_amarelo"),
        ],
        [
            InlineKeyboardButton("🟣 Roxo", callback_data="color_roxo"),
            InlineKeyboardButton("🟠 Laranja", callback_data="color_laranja"),
        ],
        [
            InlineKeyboardButton("✅ Confirmar Cores", callback_data="color_confirm")
        ]
    ]
    
    await query.edit_message_text(
        "🎨 <b>ESCOLHA AS CORES DOS ADESIVOS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Serão criadas <b>{num_entregadores} rotas</b>\n\n"
        "🏷️ <b>Selecione as cores disponíveis:</b>\n"
        "• Clique nas cores que você tem como adesivo\n"
        "• Pode escolher quantas quiser\n"
        "• Depois clique em ✅ Confirmar\n\n"
        "<i>💡 As rotas usarão as cores selecionadas</i>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(color_buttons)
    )


async def _execute_route_distribution(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Executa a distribuição de rotas COM cores selecionadas"""
    
    # Recupera dados armazenados
    temp = context.user_data.get('temp', {})
    excel_path = temp.get('otimizar_excel')
    num_entregadores = temp.get('otimizar_num')
    colors_selected = temp.get('colors_selected', [])
    
    # Se excel_path for None, estamos no modo INTERATIVO (sessão memory)
    is_interactive = excel_path is None
    
    if not num_entregadores:
        msg = "❌ Dados perdidos. Refaça o comando /otimizar"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    # Validação de cores
    if not colors_selected:
        msg = (
            "⚠️ <b>NENHUMA COR SELECIONADA!</b>\n\n"
            "Você precisa escolher pelo menos 1 cor.\n"
            "Volte e selecione as cores dos adesivos disponíveis."
        )
        if query:
            await query.edit_message_text(msg, parse_mode='HTML')
        else:
            await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Edita mensagem pra mostrar processamento
    processing_msg = (
        "⏳ <b>PROCESSANDO ENTREGAS...</b>\n\n"
        f"🎨 Cores selecionadas: {', '.join(colors_selected)}\n\n"
        "• Recuperando pontos da sessão\n"
        "• Agrupando por STOP\n"
        "• Dividindo entre entregadores\n"
        "• Otimizando rotas (Scooter Mode)\n"
        "• Aplicando cores às rotas\n\n"
        "🔥 <i>Isso pode levar uns 10-20 segundos...</i>"
    )
    
    if query:
        await query.edit_message_text(processing_msg, parse_mode='HTML')
    else:
        await update.message.reply_text(processing_msg, parse_mode='HTML')
    
    try:
        # Import aqui para evitar circular import
        from bot_multidelivery.parsers.shopee_parser import ShopeeRomaneioParser
        from bot_multidelivery.services.roteo_divider import RoteoDivider
        from bot_multidelivery.services.map_generator import MapGenerator
        
        # OBTEM OS DADOS (Do arquivo ou da sessão)
        deliveries = []
        if is_interactive:
            # Modo Session: Recupera do current_session.romaneios
            session = session_manager.get_current_session()
            if not session or not session.romaneios:
                raise Exception("Sessão vazia ou perdida.")
                
            # Converter DeliveryPoints da sessão volta para formato que o divider aceita
            # O RoteoDivider espera lista de objetos compatíveis com ShopeeDelivery
            # Vou reconstruir dicts compatíveis
            for romaneio in session.romaneios:
                for pt in romaneio.points:
                    deliveries.append({
                        'tracking': pt.package_id,
                        'address': pt.address,
                        'bairro': '', 
                        'city': '',
                        'lat': pt.lat,
                        'lon': pt.lng,
                        'stop': 0, # STOP será recalculado
                        'customer': '',
                        'phone': ''
                    })
            
            # Precisamos converter dicts para objetos se o divider espera objetos?
            # Releitura rápida do parser: retorna objetos ShopeeDelivery.
            # O divider espera LISTA DE OBJETOS COM ATRIBUTOS.
            # Vou simular objeto compatível.
            from collections import namedtuple
            SimpleDelivery = namedtuple('SimpleDelivery', ['tracking', 'address', 'bairro', 'city', 'latitude', 'longitude', 'stop', 'customer_name', 'phone'])
            
            obj_deliveries = []
            for d in deliveries:
                obj_deliveries.append(SimpleDelivery(
                    tracking=d['tracking'],
                    address=d['address'],
                    bairro=d['bairro'],
                    city=d['city'],
                    latitude=d['lat'],
                    longitude=d['lon'],
                    stop=d['stop'],
                    customer_name=d['customer'],
                    phone=d['phone']
                ))
            deliveries = obj_deliveries

        else:
            # Modo Legado: Lê Excel do path
            deliveries = ShopeeRomaneioParser.parse(excel_path)
        
        # Pega entregadores disponiveis

        all_deliverers = deliverer_service.get_all_deliverers()
        if len(all_deliverers) < num_entregadores:
            msg = (
                f"❌ <b>ENTREGADORES INSUFICIENTES!</b>\n\n"
                f"👥 Cadastrados: <b>{len(all_deliverers)}</b>\n"
                f"✅ Necessários: <b>{num_entregadores}</b>\n\n"
                f"🚨 <b>Faltam {num_entregadores - len(all_deliverers)} entregadores!</b>\n\n"
                f"Use <code>/add_entregador</code> pra cadastrar mais."
            )
            if query:
                await query.edit_message_text(msg, parse_mode='HTML')
            else:
                await update.message.reply_text(msg, parse_mode='HTML')
            return
        
        # Monta dicionario de entregadores
        selected = all_deliverers[:num_entregadores]
        entregadores_info = {d.telegram_id: d.name for d in selected}
        
        # Divide romaneio COM CORES
        divider = RoteoDivider()
        routes = divider.divide_romaneio(
            deliveries, 
            num_entregadores, 
            entregadores_info,
            colors=colors_selected  # ⚡ PASSA AS CORES!
        )
        
        # Mapeia cores pra emojis
        color_emojis = {
            'vermelho': '🔴',
            'azul': '🔵',
            'verde': '🟢',
            'amarelo': '🟡',
            'roxo': '🟣',
            'laranja': '🟠'
        }
        
        # Envia resumo pro admin COM CORES
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
            # Pega cor da rota (se existe)
            route_color = getattr(route, 'color', None)
            color_emoji = color_emojis.get(route_color, '⚪') if route_color else '⚪'
            
            summary += f"{color_emoji} <b>{i}. {route.entregador_nome}</b>\n"
            summary += f"   📦 {route.total_packages} pacotes | 📍 {len(route.stops)} paradas\n"
            summary += f"   🛣️ {route.total_distance_km:.1f}km | ⏱️ {route.total_time_minutes:.0f}min\n"
            summary += f"   ⚡ Atalhos: {route.shortcuts}\n\n"
        
        summary += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        summary += f"📲 Mapas HTML enviados para cada entregador!\n"
        summary += f"👀 Monitore pelo dashboard: http://localhost:8765\n\n"
        summary += f"🔥 <i>Bora faturar!</i>"
        
        # Envia summary
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id, summary, parse_mode='HTML')
        
        # Envia mapa pro chat de cada entregador
        for route in routes:
            # Prepara dados dos stops
            stops_data = []
            for i, (lat, lon, deliveries_list) in enumerate(route.stops):
                address = deliveries_list[0].address
                num_packages = len(deliveries_list)
                status = 'current' if i == 0 else 'pending'
                stops_data.append((lat, lon, address, num_packages, status))
            
            # Pega cor da rota
            route_color = getattr(route, 'color', None)
            color_emoji = color_emojis.get(route_color, '⚪') if route_color else ''
            
            # Gera HTML do mapa
            session = session_manager.get_current_session()
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
                    f"{color_emoji} <b>SUA ROTA DO DIA ESTÁ PRONTA!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎨 <b>COR DA SUA ROTA: {color_emoji} {route_color.upper() if route_color else 'Sem cor'}</b>\n\n"
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
                        caption=f"{color_emoji} Rota {route_color.upper() if route_color else ''} - Abra no navegador!"
                    )
                
            except Exception as e:
                logger.error(f"Erro enviando rota para {route.entregador_id}: {e}")
        
        await context.bot.send_message(
            chat_id,
            "✅ Rotas coloridas enviadas para todos os entregadores!",
            parse_mode='HTML'
        )
        
    except FileNotFoundError:
        msg = f"❌ Arquivo não encontrado: {excel_path}"
        if query:
            await query.edit_message_text(msg)
        else:
            await context.bot.send_message(update.effective_chat.id, msg)
    except Exception as e:
        logger.error(f"Erro ao distribuir rota: {e}")
        msg = f"❌ Erro: {str(e)}"
        if query:
            await query.edit_message_text(msg)
        else:
            await context.bot.send_message(update.effective_chat.id, msg)


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
    
    # ═══════════════════════════════════════════
    # SELEÇÃO DE CORES PARA AS ROTAS
    # ═══════════════════════════════════════════
    
    # Armazena dados temporários pra callback
    if not hasattr(context.user_data, 'temp'):
        context.user_data['temp'] = {}
    
    context.user_data['temp']['otimizar_excel'] = excel_path
    context.user_data['temp']['otimizar_num'] = num_entregadores
    context.user_data['temp']['colors_selected'] = []
    
    # Cores padrão com emojis
    color_buttons = [
        [
            InlineKeyboardButton("🔴 Vermelho", callback_data="color_vermelho"),
            InlineKeyboardButton("🔵 Azul", callback_data="color_azul"),
        ],
        [
            InlineKeyboardButton("🟢 Verde", callback_data="color_verde"),
            InlineKeyboardButton("🟡 Amarelo", callback_data="color_amarelo"),
        ],
        [
            InlineKeyboardButton("🟣 Roxo", callback_data="color_roxo"),
            InlineKeyboardButton("🟠 Laranja", callback_data="color_laranja"),
        ],
        [
            InlineKeyboardButton("✅ Confirmar Cores", callback_data="color_confirm")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(color_buttons)
    
    await update.message.reply_text(
        "🎨 <b>ESCOLHA AS CORES DOS ADESIVOS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Serão criadas <b>{num_entregadores} rotas</b>\n\n"
        "🏷️ <b>Selecione as cores disponíveis:</b>\n"
        "• Clique nas cores que você tem como adesivo\n"
        "• Pode escolher quantas quiser\n"
        "• Depois clique em ✅ Confirmar\n\n"
        "<i>💡 As rotas usarão as cores selecionadas</i>",
        parse_mode='HTML',
        reply_markup=keyboard
    )


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
            app.add_handler(CommandHandler("cancelar", cmd_cancelar))  # 🚫 NOVO COMMANDO DE EMERGÊNCIA
            app.add_handler(CommandHandler("importar", handle_document_message))  # Novo comando!
            app.add_handler(CommandHandler("otimizar", cmd_distribuir_rota))  # Renomeado!
            app.add_handler(CommandHandler("distribuir", cmd_distribuir_rota))  # Mantido por compatibilidade
            app.add_handler(CommandHandler("fechar_rota", cmd_fechar_rota))
            app.add_handler(CommandHandler("analisar_rota", cmd_analisar_rota))  # ⚡ NOVO!
            app.add_handler(CommandHandler("sessoes", cmd_sessoes))  # 📂 NOVO!
            app.add_handler(CommandHandler("selecionar_sessao", cmd_selecionar_sessao))  # 📂 Escolher sessão ativa
            app.add_handler(CommandHandler("add_entregador", cmd_add_deliverer))
            app.add_handler(CommandHandler("entregadores", cmd_list_deliverers))
            app.add_handler(CommandHandler("ranking", cmd_ranking))
            app.add_handler(CommandHandler("prever", cmd_predict_time))
            # Comandos financeiros
            app.add_handler(CommandHandler("fechar_dia", cmd_fechar_dia))
            app.add_handler(CommandHandler("financeiro", cmd_financeiro))
            app.add_handler(CommandHandler("fechar_semana", cmd_fechar_semana))
            app.add_handler(CommandHandler("config_socios", cmd_config_socios))
            app.add_handler(CommandHandler("faturamento", cmd_faturamento))  # 💰 NOVO PARA ENTREGADORES
            
            # Comandos avançados
            app.add_handler(CommandHandler("exportar", cmd_exportar))
            app.add_handler(CommandHandler("config_banco_inter", cmd_config_banco_inter))
            app.add_handler(CommandHandler("fechar_dia_auto", cmd_fechar_dia_auto))
            app.add_handler(CommandHandler("saldo_banco", cmd_saldo_banco))
            app.add_handler(CommandHandler("projecoes", cmd_projecoes))
            app.add_handler(CommandHandler("dashboard", cmd_dashboard))
            
            # ========== SEPARAÇÃO POR COR ==========
            app.add_handler(CommandHandler("modo_separacao", cmd_modo_separacao))
            app.add_handler(CommandHandler("fim_separacao", cmd_fim_separacao))
            app.add_handler(CommandHandler("status_separacao", cmd_status_separacao))
            
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

async def _show_costs_menu(update, context, revenue, expenses):
    """Mostra menu interativo de custos e resumo parcial"""
    
    # Calcula totais parciais
    total_expenses = sum(e['value'] for e in expenses)
    partial_profit = revenue - total_expenses
    
    # Se for mensagem nova ou edição
    msg_text = (
        f"📊 <b>EXTRATO PARCIAL DO DIA</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Faturamento:</b> R$ {revenue:.2f}\n"
        f"🔻 <b>Custos Totais:</b> R$ {total_expenses:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>LUCRO LÍQUIDO: R$ {partial_profit:.2f}</b>\n\n"
        f"📝 <b>Despesas Lançadas:</b>\n"
    )
    
    if not expenses:
        msg_text += "   <i>Nenhuma despesa lançada.</i>\n\n"
    else:
        for idx, exp in enumerate(expenses, 1):
            msg_text += f"   {idx}. {exp['type']}: R$ {exp['value']:.2f}\n"
        msg_text += "\n"
            
    msg_text += "👇 <b>Selecione um custo para adicionar:</b>"
    
    keyboard = [
        [
            InlineKeyboardButton("⛽ Combustível", callback_data="add_cost_Combustível"),
            InlineKeyboardButton("🅿️ Estacionamento", callback_data="add_cost_Estacionamento")
        ],
        [
            InlineKeyboardButton("🍔 Alimentação", callback_data="add_cost_Alimentação"),
            InlineKeyboardButton("🔧 Manutenção", callback_data="add_cost_Manutenção")
        ],
        [
            InlineKeyboardButton("👷 Ajudante", callback_data="add_cost_Ajudante"),
            InlineKeyboardButton("📝 Outros", callback_data="add_cost_Outros")
        ],
        [
            InlineKeyboardButton("✅ FINALIZAR DIA", callback_data="finish_day_closing")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg_text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg_text, parse_mode='HTML', reply_markup=reply_markup)
async def cmd_faturamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Mostra faturamento acumulado para o entregador"""
    user_id = update.effective_user.id
    
    # Verifica cadastro
    partner = BotConfig.get_partner_by_id(user_id)
    if not partner:
        await update.message.reply_text("❌ Você não está cadastrado como entregador.")
        return
        
    start_date, end_date = financial_service.get_current_week_range()
    
    if partner.is_partner:
        # Sócio vê tudo
        share_pct = financial_service.get_partner_share(partner.name)
        
        # Calcula lucro semanal estimado
        report = financial_service.get_weekly_report_preview()
        my_share = report['distributable_profit'] * share_pct
        
        msg = (
            f"🕴️ <b>ÁREA DO SÓCIO: {partner.name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Semana: {start_date} a {end_date}\n\n"
            f"💰 <b>Lucro da Empresa:</b> R$ {report['distributable_profit']:.2f}\n"
            f"〽️ <b>Sua Parte ({share_pct*100:.0f}%):</b> R$ {my_share:.2f}\n\n"
            f"<i>💡 Valor estimativo baseados nos fechamentos da semana.</i>"
        )
    else:
        # Entregador vê ganhos acumulados
        earnings = deliverer_service.get_weekly_earnings(user_id, start_date, end_date)
        
        msg = (
            f"💰 <b>SEU FATURAMENTO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {partner.name}\n"
            f"📅 Semana: {start_date} a {end_date}\n\n"
            f"💵 <b>A Receber: R$ {earnings:.2f}</b>\n\n"
            f"<i>💡 Valor acumulado das entregas realizadas.</i>"
        )
        
    await update.message.reply_text(msg, parse_mode='HTML')
