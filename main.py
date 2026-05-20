import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import pytz

import config
import db
from parser import interpretar_lembrete

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
TZ = pytz.timezone(config.TIMEZONE)


def formatar_data(quando_str):
    try:
        dt = datetime.strptime(quando_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y as %H:%M")
    except:
        return quando_str


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ola! Sou seu bot de lembretes.\n\n"
        "Me mande uma mensagem como:\n"
        "- me lembra de estudar as 19h\n"
        "- lembra de tomar remedio amanha as 8h\n"
        "- me lembra de ligar pro joao daqui 30 minutos\n\n"
        "Comandos:\n"
        "/lembretes - ver seus lembretes agendados\n"
        "/cancelar - cancelar um lembrete"
    )


async def cmd_lembretes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    lembretes = db.listar_lembretes(chat_id)
    if not lembretes:
        await update.message.reply_text("Voce nao tem lembretes agendados.")
        return
    linhas = ["Seus lembretes agendados:\n"]
    for lid, mensagem, quando in lembretes:
        linhas.append(f"[{lid}] {formatar_data(quando)}\n    {mensagem}")
    await update.message.reply_text("\n\n".join(linhas))


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    lembretes = db.listar_lembretes(chat_id)
    if not lembretes:
        await update.message.reply_text("Voce nao tem lembretes para cancelar.")
        return
    botoes = []
    for lid, mensagem, quando in lembretes:
        label = f"{formatar_data(quando)} - {mensagem[:30]}"
        botoes.append([InlineKeyboardButton(label, callback_data=f"cancelar_{lid}")])
    await update.message.reply_text("Qual lembrete quer cancelar?", reply_markup=InlineKeyboardMarkup(botoes))


async def callback_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    lembrete_id = int(query.data.split("_")[1])
    if db.cancelar_lembrete(lembrete_id, chat_id):
        await query.edit_message_text("Lembrete cancelado.")
    else:
        await query.edit_message_text("Lembrete nao encontrado.")


async def handle_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username or update.effective_user.first_name
    texto = update.message.text
    await update.message.reply_text("Processando seu lembrete...")
    resultado = interpretar_lembrete(texto)
    if not resultado:
        await update.message.reply_text(
            "Nao consegui entender. Tente:\n"
            "me lembra de estudar as 19h\n"
            "lembra de tomar remedio amanha as 8h"
        )
        return
    mensagem = resultado["mensagem"]
    quando = resultado["quando"]
    lembrete_id = db.salvar_lembrete(chat_id, username, mensagem, quando)
    await update.message.reply_text(
        f"Lembrete agendado!\n\nMensagem: {mensagem}\nQuando: {formatar_data(quando)}\nID: {lembrete_id}"
    )


async def verificar_lembretes(bot):
    while True:
        pendentes = db.buscar_pendentes()
        for lid, chat_id, mensagem in pendentes:
            try:
                await bot.send_message(chat_id=chat_id, text=f"Lembrete: {mensagem}")
                db.marcar_enviado(lid)
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete {lid}: {e}")
        await asyncio.sleep(30)


async def main():
    db.init_db()
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lembretes", cmd_lembretes))
    app.add_handler(CommandHandler("cancelar", cmd_cancelar))
    app.add_handler(CallbackQueryHandler(callback_cancelar, pattern="^cancelar_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensagem))
    async with app:
        await app.start()
        await app.updater.start_polling()
        logger.info("Bot de lembretes iniciado!")
        await verificar_lembretes(app.bot)
        await app.updater.stop()


if __name__ == "__main__":
    asyncio.run(main())
