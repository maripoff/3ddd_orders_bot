import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread
from datetime import datetime

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
bot = Bot(token=TOKEN)
last_seen = {name: None for name in URLS}
last_check_time = None

# --- ФУНКЦИЯ ПРОВЕРКИ САЙТА ---
async def check_site(name, url, session):
    global last_check_time
    try:
        async with session.get(url) as response:
            text = await response.text()
        soup = BeautifulSoup(text, "html.parser")
        item = soup.select_one(".work-list-item")
        if not item:
            return

        title = item.select_one("h3").get_text(strip=True)
        link = "https://3ddd.ru" + item.select_one("a")["href"]

        if last_seen[name] != link:
            last_seen[name] = link
            msg = f"🆕 <b>Новое в разделе {name}:</b>\n{title}\n{link}"
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
            print("Отправлено сообщение:", msg)
        last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Ошибка при проверке {name}: {e}")

# --- ОСНОВНОЙ АСИНХРОННЫЙ ЦИКЛ ---
async def main_loop():
    async with aiohttp.ClientSession() as session:
        try:
            await bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущен и работает!", parse_mode=ParseMode.HTML)
        except Exception as e:
            print("Не удалось отправить стартовое сообщение:", e)

        while True:
            for name, url in URLS.items():
                await check_site(name, url, session)
            await asyncio.sleep(CHECK_INTERVAL)

# --- Telegram команды ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    msg = "✅ Я живой!"
    if last_check_time:
        msg += f"\nПоследняя успешная проверка: {last_check_time}"
    await update.message.reply_text(msg)

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    async with aiohttp.ClientSession() as session:
        messages = []
        for name, url in URLS.items():
            try:
                async with session.get(url) as response:
                    text = await response.text()
                soup = BeautifulSoup(text, "html.parser")
                item = soup.select_one(".work-list-item")
                if item:
                    title = item.select_one("h3").get_text(strip=True)
                    link = "https://3ddd.ru" + item.select_one("a")["href"]
                    messages.append(f"<b>{name}:</b> {title}\n{link}")
                else:
                    messages.append(f"<b>{name}:</b> нет элементов")
            except Exception as e:
                messages.append(f"<b>{name}:</b> ошибка при проверке")
        await update.message.reply_text("\n\n".join(messages), parse_mode=ParseMode.HTML)

# --- Flask сервер для Render ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- Запуск ---
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()

    # Telegram бот с обработчиками команд
    app_builder = ApplicationBuilder().token(TOKEN).build()
    app_builder.add_handler(CommandHandler("status", status))
    app_builder.add_handler(CommandHandler("latest", latest))

    # Запуск асинхронного цикла проверки сайта
    async def runner():
        asyncio.create_task(main_loop())
        await app_builder.initialize()
        await app_builder.start()
        await app_builder.updater.start_polling()
        await app_builder.idle()

    asyncio.run(runner())
