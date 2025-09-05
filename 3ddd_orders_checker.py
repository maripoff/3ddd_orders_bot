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
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 300))
PORT = int(os.environ.get("PORT", 10000))

URLS = {
    "Вакансии": "https://3ddd.ru/work/vacancies",
    "Заказы": "https://3ddd.ru/work/tasks",
}

# --- КЭШ ---
cache = {
    "Вакансии": None,
    "Заказы": None,
    "last_checked": {name: None for name in URLS}
}

# --- FLASK ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=PORT, threaded=False, use_reloader=False)

Thread(target=run_flask, daemon=True).start()

# --- ПОЛУЧЕНИЕ ПЕРВОЙ ВАКАНСИИ/ЗАДАЧИ ---
async def fetch_first_item(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                text = await resp.text()
        soup = BeautifulSoup(text, "html.parser")
        item = soup.select_one(".work-list-item")
        if item:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://3ddd.ru" + item.select_one("a")["href"]
            return f"{title}\n{link}"
    except Exception as e:
        print(f"Ошибка при fetch_first_item для {url}: {e}")
    return None

# --- ПРОВЕРКА САЙТА И ОБНОВЛЕНИЕ КЭША ---
async def check_site(bot):
    async with aiohttp.ClientSession() as session:
        for name, url in URLS.items():
            try:
                async with session.get(url, timeout=10) as resp:
                    text = await resp.text()
                soup = BeautifulSoup(text, "html.parser")
                item = soup.select_one(".work-list-item")
                if not item:
                    continue

                title = item.select_one("h3").get_text(strip=True)
                link = "https://3ddd.ru" + item.select_one("a")["href"]
                new_value = f"{title}\n{link}"

                # проверка на обновление
                if cache[name] != new_value:
                    cache[name] = new_value
                    if cache["last_checked"][name] is not None:  # пропускаем уведомление при первом старте
                        msg = f"🆕 <b>Новое в разделе {name}:</b>\n{title}\n{link}"
                        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=constants.ParseMode.HTML)
                        print(f"[{datetime.now()}] Отправлено сообщение: {msg}")

                cache["last_checked"][name] = datetime.now()
            except Exception as e:
                print(f"Ошибка при check_site для {name}: {e}")

# --- ФОНОВАЯ ЗАДАЧА ---
async def background_loop(bot):
    while True:
        await check_site(bot)
        await asyncio.sleep(CHECK_INTERVAL)

# --- КОМАНДЫ ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["✅ Бот запущен и работает!\n"]
    for name, checked in cache["last_checked"].items():
        lines.append(f"{name}: {checked.strftime('%Y-%m-%d %H:%M:%S') if checked else 'ещё не проверялось'}")
    lines.append("\nНапиши /commands для списка команд")
    await update.message.reply_text("\n".join(lines))

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    for name in ["Вакансии", "Заказы"]:
        if cache[name]:
            lines.append(f"<b>{name}:</b>\n{cache[name]}")
        else:
            lines.append(f"<b>{name}:</b>\nДанные загружаются...")
    await update.message.reply_text("\n\n".join(lines), parse_mode=constants.ParseMode.HTML)

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/status — проверить состояние бота\n"
        "/latest — показать последний заказ/вакансию\n"
        "/commands — показать список команд"
    )

# --- ЗАПУСК ---
async def main():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("status", status))
    app_bot.add_handler(CommandHandler("latest", latest))
    app_bot.add_handler(CommandHandler("commands", commands))

    # --- Инициализация кэша до старта бота ---
    for name, url in URLS.items():
        first_item = await fetch_first_item(url)
        if first_item:
            cache[name] = first_item
            cache["last_checked"][name] = datetime.now()

    # --- Стартовое сообщение ---
    try:
        await app_bot.bot.send_message(
            chat_id=CHAT_ID,
            text="✅ Бот запущен и работает!\nНапиши /commands для списка команд"
        )
        print("Стартовое сообщение отправлено ✅")
    except Exception as e:
        print(f"Не удалось отправить стартовое сообщение: {e}")

    # --- Запуск фонового цикла ---
    asyncio.create_task(background_loop(app_bot.bot))

    # --- Запуск polling ---
    await app_bot.start()
    await app_bot.updater.start_polling()
    await app_bot.idle()

if __name__ == "__main__":
    asyncio.run(main())
