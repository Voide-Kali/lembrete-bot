#!/usr/bin/env python3
"""Central profissional de lembretes no Telegram."""

from __future__ import annotations

import asyncio
import html
import logging
import sys
import time
from datetime import datetime, timedelta

import pytz
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import db
from parser import interpretar_lembrete


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TZ = pytz.timezone(config.TIMEZONE)
started_at = time.time()
parse_lock = asyncio.Lock()


def allowed(update: Update) -> bool:
    chat = update.effective_chat
    permitted = bool(chat and chat.id == config.ALLOWED_CHAT_ID)
    if not permitted and chat:
        logger.warning("Acesso recusado para o chat %s", chat.id)
    return permitted


def format_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return value


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Novo lembrete", callback_data="new"),
                InlineKeyboardButton("📋 Agenda", callback_data="list"),
            ],
            [
                InlineKeyboardButton("🗑 Cancelar", callback_data="cancel_menu"),
                InlineKeyboardButton("📊 Estatísticas", callback_data="stats"),
            ],
            [InlineKeyboardButton("ℹ️ Ajuda", callback_data="help")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("‹ Voltar ao painel", callback_data="dashboard")]]
    )


def dashboard_text(chat_id: str) -> str:
    pending = db.listar_lembretes(chat_id)
    sent = db.contar_enviados(chat_id)
    uptime_minutes = int((time.time() - started_at) / 60)
    next_text = format_date(pending[0][2]) if pending else "nenhum"
    return (
        "<b>⏰ CENTRAL DE LEMBRETES</b>\n"
        "<i>Organização pessoal em linguagem natural</i>\n\n"
        "🟢 <b>Estado:</b> OPERACIONAL\n"
        f"📌 <b>Agendados:</b> {len(pending)}\n"
        f"✅ <b>Concluídos:</b> {sent}\n"
        f"⏭ <b>Próximo:</b> {next_text}\n"
        f"⏱ <b>Uptime:</b> {uptime_minutes}min\n\n"
        "Escreva naturalmente, por exemplo:\n"
        "<i>Me lembra de estudar amanhã às 19h</i>"
    )


def help_text() -> str:
    return (
        "<b>ℹ️ COMO CRIAR LEMBRETES</b>\n\n"
        "Envie uma frase contendo a tarefa e o horário.\n\n"
        "<b>Exemplos</b>\n"
        "• Me lembra de estudar hoje às 19h\n"
        "• Tomar remédio amanhã às 8h\n"
        "• Ligar para João daqui 30 minutos\n"
        "• Entregar trabalho sexta às 14h\n\n"
        f"Fuso horário configurado: <code>{html.escape(config.TIMEZONE)}</code>"
    )


def list_text(chat_id: str) -> str:
    reminders = db.listar_lembretes(chat_id)
    if not reminders:
        return "<b>📋 SUA AGENDA</b>\n\nNenhum lembrete agendado."
    lines = ["<b>📋 SUA AGENDA</b>", ""]
    for index, (_, message, when) in enumerate(reminders, start=1):
        lines.append(
            f"<b>{index}. {html.escape(message)}</b>\n"
            f"    🕒 {format_date(when)}"
        )
    return "\n\n".join(lines)


async def edit_or_reply(update: Update, text: str, keyboard: InlineKeyboardMarkup) -> None:
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        except BadRequest as exc:
            if "Message is not modified" not in str(exc):
                raise
        return
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await edit_or_reply(
        update,
        dashboard_text(str(update.effective_chat.id)),
        main_keyboard(),
    )


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await edit_or_reply(update, list_text(str(update.effective_chat.id)), back_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    await edit_or_reply(update, help_text(), back_keyboard())


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    chat_id = str(update.effective_chat.id)
    text = (
        "<b>📊 ESTATÍSTICAS</b>\n\n"
        f"📌 Pendentes: <b>{len(db.listar_lembretes(chat_id))}</b>\n"
        f"✅ Enviados: <b>{db.contar_enviados(chat_id)}</b>\n"
        f"🌎 Fuso: <code>{html.escape(config.TIMEZONE)}</code>"
    )
    await edit_or_reply(update, text, back_keyboard())


async def show_cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    reminders = db.listar_lembretes(str(update.effective_chat.id))
    if not reminders:
        return await edit_or_reply(
            update,
            "<b>🗑 CANCELAR</b>\n\nNão há lembretes pendentes.",
            back_keyboard(),
        )
    buttons = [
        [
            InlineKeyboardButton(
                f"{format_date(when)} · {message[:25]}",
                callback_data=f"cancel:{reminder_id}",
            )
        ]
        for reminder_id, message, when in reminders[:20]
    ]
    buttons.append([InlineKeyboardButton("‹ Voltar", callback_data="dashboard")])
    await edit_or_reply(
        update,
        "<b>🗑 ESCOLHA O LEMBRETE</b>",
        InlineKeyboardMarkup(buttons),
    )


async def create_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        return
    if parse_lock.locked():
        await update.message.reply_text("Ainda estou processando o lembrete anterior.")
        return
    async with parse_lock:
        progress = await update.message.reply_text("🧠 Interpretando seu lembrete...")
        result = await asyncio.to_thread(interpretar_lembrete, update.message.text)
        if not result:
            await progress.edit_text(
                "<b>Não consegui entender.</b>\n\n"
                "Inclua o que deseja lembrar e quando deve acontecer.\n"
                "Exemplo: <i>Me lembra de estudar amanhã às 19h</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=main_keyboard(),
            )
            return
        reminder_id = db.salvar_lembrete(
            str(update.effective_chat.id),
            update.effective_user.username or update.effective_user.first_name,
            result["mensagem"],
            result["quando"],
        )
        await progress.edit_text(
            "<b>✅ LEMBRETE AGENDADO</b>\n\n"
            f"📝 <b>Tarefa:</b> {html.escape(result['mensagem'])}\n"
            f"🕒 <b>Quando:</b> {format_date(result['quando'])}\n"
            f"🔖 <b>ID:</b> {reminder_id}",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard(),
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not allowed(update):
        return
    await query.answer()
    data = query.data
    if data.startswith("cancel:"):
        reminder_id = int(data.split(":", 1)[1])
        deleted = db.cancelar_lembrete(reminder_id, str(update.effective_chat.id))
        text = "Lembrete cancelado." if deleted else "Lembrete não encontrado."
        await query.edit_message_text(text, reply_markup=back_keyboard())
        return
    actions = {
        "dashboard": show_dashboard,
        "list": show_list,
        "help": show_help,
        "stats": show_stats,
        "cancel_menu": show_cancel_menu,
        "new": show_help,
    }
    action = actions.get(data)
    if action:
        await action(update, context)


async def deliver_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(TZ).replace(tzinfo=None)
    for reminder_id, chat_id, message in db.buscar_pendentes(now):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏳ +10 min", callback_data=f"snooze:10:{reminder_id}"),
                    InlineKeyboardButton("⏰ +1 hora", callback_data=f"snooze:60:{reminder_id}"),
                ]
            ]
        )
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"<b>⏰ LEMBRETE</b>\n\n{html.escape(message)}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            db.marcar_enviado(reminder_id)
        except Exception:
            logger.exception("Erro ao enviar lembrete %s", reminder_id)


async def snooze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not allowed(update):
        return
    _, minutes, reminder_id = query.data.split(":")
    when = datetime.now(TZ).replace(tzinfo=None) + timedelta(minutes=int(minutes))
    updated = db.adiar_lembrete(
        int(reminder_id),
        str(update.effective_chat.id),
        when,
    )
    await query.answer("Lembrete adiado." if updated else "Não foi possível adiar.")
    if updated:
        await query.edit_message_text(
            f"<b>⏳ LEMBRETE ADIADO</b>\n\nNova hora: {when.strftime('%H:%M')}",
            parse_mode=ParseMode.HTML,
        )


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("painel", "Abrir central de lembretes"),
            BotCommand("lembretes", "Ver agenda"),
            BotCommand("cancelar", "Cancelar lembrete"),
            BotCommand("ajuda", "Ver exemplos"),
        ]
    )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Erro ao processar atualização", exc_info=context.error)


def main() -> None:
    if not config.TELEGRAM_TOKEN:
        logger.error(
            "Token do Telegram não configurado. Defina LEMBRETE_TELEGRAM_TOKEN no .env."
        )
        sys.exit(78)
    db.init_db()
    application = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler(["start", "painel"], show_dashboard))
    application.add_handler(CommandHandler("lembretes", show_list))
    application.add_handler(CommandHandler("cancelar", show_cancel_menu))
    application.add_handler(CommandHandler("ajuda", show_help))
    application.add_handler(CallbackQueryHandler(snooze, pattern=r"^snooze:"))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, create_reminder))
    application.add_error_handler(handle_error)
    application.job_queue.run_repeating(deliver_reminders, interval=15, first=2)
    logger.info("Central de lembretes iniciada")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
