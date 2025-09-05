import os
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TOKEN")  # Берём токен из переменных окружения
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Берём chat_id из переменных окружения
CHECK_INTERVAL = 300  # проверка каждые 5 минут

URLS = {
    "Вакансии": "https://3ddd.ru/work/vacancies",
    "Заказы": "https://3ddd.ru/work/tasks",
}

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=TOKEN)
last_seen = {name: None for name in URLS}

# --- ФУНКЦИЯ ПРОВЕРКИ САЙТА ---
async def check_site(name, url):
    global last_seen
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        item = soup.select_one(".work-list-item")
        if not item:
            return

        title = item.select_one("h3").get_text(strip=True)
        link = "https://3ddd.ru" + item.select_one("a")["href"]

        if last_seen[name] != link:
            last_seen[name] = link
            msg = f"🆕 Новое в разделе {name}:\n{title}\n{link}"
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            print("Отправлено сообщение:", msg)
    except Exception as e:
        print(f"Ошибка при проверке {name}: {e}")

# --- ОСНОВНОЙ АСИНХРОННЫЙ ЦИКЛ ---
async def main_loop():
    await bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущен и работает!")
    while True:
        for name, url in URLS.items():
            await check_site(name, url)
        await asyncio.sleep(CHECK_INTERVAL)

# --- ЗАПУСК ---
if __name__ == "__main__":
    asyncio.run(main_loop())
