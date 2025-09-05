import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
CHECK_INTERVAL = 300  # каждые 5 минут
PORT = int(os.environ.get("PORT", 10000))

flask_app = Flask(__name__)

# --- Хэндлеры команд ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен и работает ✅")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Проверка сайта... 🔎")
    result = await check_site()
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)


# --- Проверка сайта ---
async def check_site():
    url = "https://3ddd.ru/3dmodels/popular"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return f"⚠️ Ошибка доступа к сайту: {resp.status}"
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        titles = [el.get_text(strip=True) for el in soup.select(".title")]
        if not titles:
            return "❌ Не удалось найти модели на странице"
        return "✅ Найдены модели:\n" + "\n".join(titles[:5])

    except Exception as e:
        return f"⚠️ Ошибка при проверке: {e}"


# --- Flask endpoint ---
@flask_app.route("/")
def index():
    return "Бот работает!"


# --- Основной запуск ---
def main():
    app_bot = ApplicationBuilder().token(TOKEN).build()

    # --- команды ---
    app_bot.add_handler(CommandHandler("start", start_command))
    app_bot.add_handler(CommandHandler("check", check_command))

    # --- отправляем стартовое сообщение ---
    async def startup():
        bot = Bot(TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text="Стартовое сообщение отправлено ✅")

    asyncio.run(startup())

    # --- Flask в отдельном потоке ---
    Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT, debug=False)).start()

    # --- запускаем бота ---
    app_bot.run_polling()


if __name__ == "__main__":
    main()

        print("⚠️ Второй процесс обнаружен, завершаюсь")
        sys.exit(0)

    main()
