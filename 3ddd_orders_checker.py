import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, constants
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

last_seen = {name: None for name in URLS}
last_checked = {name: None for name in URLS}

first_run = True  # флаг для предотвращения рассылки при старте

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
    global first_run
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
            # отправляем сообщения только если это не первый запуск
            if not first_run:
                msg = f"🆕 <b>Новое в разделе {name}:</b>\n{title}\n{link}"
                await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=constants.ParseMode.HTML)
                print("Отправлено сообщение:", msg)
    except Exception as e:
        print(f"Ошибка при проверке {name}: {e}")

# --- ФОНОВАЯ ЗАДАЧА ---
async def main_loop(bot):
    global first_run
    async with aiohttp.ClientSession() as session:
        while True:
            for name, url in URLS.items():
                try:
                    await check_site(bot, name, url, session)
                    last_checked[name] = datetime.now()
                except Exception as e:
                    print(f"Ошибка в main_loop для {name}: {e}")
            first_run = False  # после первой проверки разрешаем уведомления
            await asyncio.sleep(CHECK_INTERVAL)

# --- КОМАНДЫ TELEGRAM ---
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

# --- ЗАПУСК BOT ---
async def on_startup(bot):
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text="✅ Бот запущен и работает!\nНапиши /commands, чтобы увидеть список доступных команд"
        )
        print("Стартовое сообщение отправлено ✅")
    except Exception as e:
        print("Не удалось отправить стартовое сообщение:", e)
    # Запускаем фоновую задачу
    asyncio.create_task(main_loop(bot))

def main():
    app_bot = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем команды
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CommandHandler("latest", latest))
    app_bot.add_handler(CommandHandler("commands", commands))

    # Добавляем on_startup
    app_bot.post_init = lambda app: on_startup(app.bot)

    # Запуск бота (не оборачиваем в asyncio.run)
    app_bot.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
