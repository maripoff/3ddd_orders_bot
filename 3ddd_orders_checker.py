import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import constants, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread
from datetime import datetime
import nest_asyncio

# --- Настройки ---
TOKEN = os.environ.get("TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 300))  # интервал проверки
PORT = int(os.environ.get("PORT", 10000))

URLS = {
    "Вакансии": "https://3ddd.ru/work/vacancies",
    "Заказы": "https://3ddd.ru/work/tasks",
}

last_seen = {name: None for name in URLS}
last_checked = {name: None for name in URLS}
first_run = True  # предотвращение рассылки при старте

# --- Flask ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=False, use_reloader=False)

# --- Проверка сайта ---
async def check_site(bot, name, url, session):
    global first_run
    try:
        async with session.get(url, timeout=10) as response:
            text = await response.text()
        soup = BeautifulSoup(text, "html.parser")
        item = soup.select_one(".work-list-item")
        if not item:
            return

        title = item.select_one("h3").get_text(strip=True)
        link = "https://3ddd.ru" + item.select_one("a")["href"]

        if last_seen[name] != link:
            last_seen[name] = link
            if not first_run:
                msg = f"🆕 <b>Новое в разделе {name}:</b>\n{title}\n{link}"
                await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=constants.ParseMode.HTML)
                print(f"[{datetime.now()}] Отправлено сообщение: {msg}")
        last_checked[name] = datetime.now()
    except Exception as e:
        import traceback
        print(f"Ошибка при проверке {name}: {e}")
        print(traceback.format_exc())

# --- JobQueue ---
async def job_check(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    async with aiohttp.ClientSession() as session:
        for name, url in URLS.items():
            await check_site(bot, name, url, session)

# --- Команды ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = ["✅ Бот запущен и работает!\n"]
    for name, checked in last_checked.items():
        msg_lines.append(f"{name}: {checked.strftime('%Y-%m-%d %H:%M:%S') if checked else 'ещё не проверялось'}")
    msg_lines.append("\nНапиши /commands, чтобы увидеть список команд")
    await update.message.reply_text("\n".join(msg_lines))

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = []
    for name, link in last_seen.items():
        msg_lines.append(f"<b>{name}:</b> {link if link else 'нет данных'}")
    await update.message.reply_text("\n".join(msg_lines), parse_mode=constants.ParseMode.HTML)

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/status — проверить, жив ли бот и время последней проверки\n"
        "/latest — показать последний заказ/вакансию\n"
        "/commands — показать список команд"
    )

# --- Основной запуск ---
async def main():
    global first_run
    app_bot = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем команды
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CommandHandler("latest", latest))
    app_bot.add_handler(CommandHandler("commands", commands))

    # Стартовое сообщение
    async def send_startup_message():
        global first_run
        try:
            await app_bot.bot.send_message(
                chat_id=CHAT_ID,
                text="✅ Бот запущен и работает!\nНапиши /commands, чтобы увидеть список доступных команд"
            )
            print("Стартовое сообщение отправлено ✅")
        except Exception as e:
            print("Не удалось отправить стартовое сообщение:", e)
        first_run = False  # теперь разрешаем рассылку новых сообщений

    await app_bot.initialize()
    await send_startup_message()

    # JobQueue
    job_queue = app_bot.job_queue
    job_queue.run_repeating(job_check, interval=CHECK_INTERVAL, first=CHECK_INTERVAL)

    # Запуск polling
    await app_bot.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()  # чтобы избежать проблем с loop
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
