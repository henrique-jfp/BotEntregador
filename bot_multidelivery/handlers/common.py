"""Módulo de Handlers Comuns (Start, Help, Saldo)"""
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from bot_multidelivery.persistence import data_store
from bot_multidelivery.session import session_manager

logger = logging.getLogger(__name__)


def get_week_monday_sunday():
    """Retorna segunda (00:00) e domingo (23:59) da semana atual"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())  # Segunda
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /start
    Diferencia entre Admin (Dashboard) e Entregador (Mapa de Rota)
    Se for sócio, mostra 2 botões
    """
    user = update.effective_user
    tg_id = user.id
    logger.info(f"Comando /start recebido de {user.first_name} (ID: {tg_id})")
    
    # Obter URL base
    webapp_url = os.getenv("WEBAPP_URL", "https://seu-app-railway.app")
    if not webapp_url.startswith("http"):
        webapp_url = f"https://{webapp_url}"

    # Imagem obrigatória de abertura
    cover_path = Path(__file__).resolve().parents[1] / "static" / "start_cover.jpg"

    async def reply_with_cover(message: str, reply_markup: InlineKeyboardMarkup):
        if cover_path.is_file():
            try:
                with cover_path.open("rb") as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=message,
                        reply_markup=reply_markup,
                    )
                    return
            except Exception as e:
                logger.warning(f"⚠️ Falha ao enviar start_cover.jpg: {e}")

        await update.message.reply_text(message, reply_markup=reply_markup)
    
    # Verificar role do usuário
    deliverer = data_store.get_deliverer(tg_id)
    is_admin = deliverer and deliverer.is_admin if deliverer else False
    is_partner = deliverer and deliverer.is_partner if deliverer else False
    
    # ===== ADMIN =====
    if is_admin:
        keyboard = [
            [InlineKeyboardButton("📊 Abrir Dashboard", web_app=WebAppInfo(url=f"{webapp_url}?tab=dashboard&role=admin"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_with_cover(
            f"🚀 **SISTEMA ATUALIZADO V2**\n\n"
            f"👤 Olá, **Administrador** {user.first_name}!\n\n"
            "🔧 Acesso ao Painel de Controle\n\n"
            "Clique abaixo para acessar o Dashboard completo com:\n"
            "• Gerenciamento de rotas\n"
            "• Monitoramento de entregas\n"
            "• Relatórios e análises\n"
            "• Configurações do sistema",
            reply_markup
        )
    
    # ===== ENTREGADOR (SÓCIO) =====
    elif is_partner:
        keyboard = [
            [InlineKeyboardButton("🗺️ Minha Rota do Dia", web_app=WebAppInfo(url=f"{webapp_url}?user_id={tg_id}&tab=myroute"))],
            [InlineKeyboardButton("📊 Meus Resultados", web_app=WebAppInfo(url=f"{webapp_url}?user_id={tg_id}&tab=dashboard&role=partner"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_with_cover(
            f"👋 Olá, **Sócio Entregador** {user.first_name}!\n\n"
            "🎯 Você tem acesso a:\n\n"
            "1️⃣ **Minha Rota** - Visualize sua rota do dia no mapa\n"
            "2️⃣ **Meus Resultados** - Acompanhe suas entregas e ganhos",
            reply_markup
        )
    
    # ===== ENTREGADOR (NORMAL) =====
    else:
        keyboard = [
            [InlineKeyboardButton("🧭 Acessar Sistema", web_app=WebAppInfo(url=f"{webapp_url}?user_id={tg_id}&tab=dashboard"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await reply_with_cover(
            f"👋 Olá, {user.first_name}!\n\n"
            "🚀 Sua rota do dia está pronta!\n\n"
            "Clique no botão abaixo para:\n"
            "📍 Ver o mapa com todos os pontos de entrega\n"
            "✅ Marcar entregas como concluídas\n"
            "📞 Entrar em contato com o cliente",
            reply_markup
        )


async def cmd_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /saldo
    Retorna SALDO ACUMULADO DA SEMANA (segunda a domingo)
    Soma de todos os deliveries completados durante a semana
    """
    user = update.effective_user
    tg_id = user.id
    logger.info(f"Comando /saldo recebido de {user.first_name} (ID: {tg_id})")
    
    try:
        # 1. Verificar se o entregador existe
        deliverer = data_store.get_deliverer(tg_id)
        if not deliverer:
            await update.message.reply_text(
                "❌ Você não está cadastrado no sistema.\n"
                "Entre em contato com o administrador."
            )
            return
        
        # 2. Calcular intervalo da semana
        monday, sunday = get_week_monday_sunday()
        
        # 3. Buscar todas as sessões da semana
        all_sessions = session_manager.get_all_sessions()
        
        total_packages_week = 0
        total_failed_week = 0
        
        # Procurar todas as sessões ativas/finalizadas dessa semana
        for session in all_sessions:
            if not (monday <= session.created_at <= sunday):
                continue
            
            for route in session.routes:
                if route.assigned_to_telegram_id == tg_id:
                    # Contagem detalhada por status nos pontos da rota
                    for point in (route.optimized_order or []):
                        if point.status == 'delivered':
                            total_packages_week += 1
                        elif point.status in ('failed', 'returned'):
                            total_failed_week += 1
        
        # 4. Montar resposta
        monday_str = monday.strftime("%d/%m")
        sunday_str = sunday.strftime("%d/%m")
        
        success_rate = (total_packages_week / (total_packages_week + total_failed_week) * 100) if (total_packages_week + total_failed_week) > 0 else 100
        
        message = f"""📊 **Seu Desempenho da Semana**

📅 **Período:** {monday_str} a {sunday_str}
✅ **Entregues com Sucesso:** {total_packages_week}
❌ **Insucessos/Devoluções:** {total_failed_week}
📈 **Taxa de Eficiência:** {success_rate:.1f}%

🚀 Continue com o ótimo trabalho!"""
        
        await update.message.reply_text(message)
        logger.info(f"✅ Desempenho semanal enviado para {deliverer.name}: {total_packages_week} entregues")
    
    except Exception as e:
        logger.error(f"❌ Erro ao processar /saldo: {str(e)}")
        await update.message.reply_text(
            "❌ Erro ao calcular saldo.\n"
            "Tente novamente mais tarde."
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """
🆘 **Comandos Disponíveis:**

/start - Abre seu dashboard/mapa
/saldo - Mostra seu saldo acumulado da semana
/help - Mostra esta mensagem

📱 **Minha Rota:** Visualize o mapa interativo com suas entregas
💰 **Saldo:** Acompanhe seu ganho da semana em tempo real
"""
    await update.message.reply_text(help_text)
