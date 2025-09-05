import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
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
bot = Bot(token=TOKEN)  # parse_mode убрали из конструктора
last_seen = {name: None for name in URLS}

# --- ФУНКЦИЯ ПРОВЕРКИ САЙТА ---
async def check_site(name, url, session):
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

# --- Flask сервер для Render ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- ЗАПУСК ---
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main_loop())
