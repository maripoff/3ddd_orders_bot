import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
CHECK_INTERVAL = 300  # каждые 5 минут
PORT = int(os.environ.get("PORT", 10000))

URLS = {
    "Вакансии": "https://3ddd.ru/work/vacancies",
    "Заказы": "https://3ddd.ru/work/tasks",
}

# --- ИНИЦИАЛИЗАЦИЯ ---
last_seen = {name: None for name in URLS}

# --- FLASK ДЛЯ RENDER ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

Thread(target=run_flask, daemon=True).start()

# --- ФУНКЦИЯ ПРОВЕРКИ САЙТА ---
async def check_site(bot, name, url, session):
    try:
        async with session.get(url) as response:
            text = await response.text()
        soup = BeautifulSoup(text, "html.parser")
        item = soup.select_one(".work-list-item")
        if not item:
            return None

        title = item.select_one("h3").get_text(strip=True)
        link = "https://3ddd.ru" + item.select_one("a")["href"]

        if last_seen[name] != link:
            last_seen[name] = link
            msg = f"🆕 <b>Новое в разделе {name}:</b>\n{title}\n{link}"
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=constants.ParseMode.HTML)
            print("Отправлено сообщение:", msg)
            return msg
    except Exception as e:
        print(f"Ошибка при проверке {name}: {e}")

# --- АСИНХРОННЫЙ ЦИКЛ ---
async def main_loop(bot):
    async with aiohttp.ClientSession() as session:
        while True:
            for name, url in URLS.items():
                await check_site(bot, name, url, session)
            await asyncio.sleep(CHECK_INTERVAL)

# --- КОМАНДЫ TELEGRAM ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Бот запущен и работает!\nНапиши /commands, чтобы увидеть список команд"
    )

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = []
    for name, link in last_seen.items():
        if link:
            msg_lines.append(f"<b>{name}:</b> {link}")
        else:
            msg_lines.append(f"<b>{name}:</b> нет данных")
    await update.message.reply_text("\n".join(msg_lines), parse_mode=constants.ParseMode.HTML)

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/status — проверить, жив ли бот\n"
        "/latest — показать последний заказ/вакансию\n"
        "/commands — показать список команд"
    )

# --- ЗАПУСК BOT ---
async def runner():
    app_bot = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем команды
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CommandHandler("latest", latest))
    app_bot.add_handler(CommandHandler("commands", commands))

    # Стартовое сообщение после полной инициализации бота
    async def on_startup():
        try:
            await app_bot.bot.send_message(
                chat_id=CHAT_ID,
                text="✅ Бот запущен и работает!\nНапиши /commands, чтобы увидеть список доступных команд"
            )
            print("Стартовое сообщение отправлено ✅")
        except Exception as e:
            print("Не удалось отправить стартовое сообщение:", e)

        # Запускаем фоновую проверку
        asyncio.create_task(main_loop(app_bot.bot))

    # Добавляем обработчик on_startup
    app_bot.post_init = on_startup

    # Запускаем polling (Telegram команды)
    await app_bot.run_polling(stop_signals=None)

# --- ОСНОВНОЙ ---
if __name__ == "__main__":
    asyncio.run(runner())
