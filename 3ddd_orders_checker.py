import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TOKEN")  # Берём токен из переменных окружения
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Берём chat_id из переменных окружения
CHECK_INTERVAL = 300  # проверка каждые 5 минут

URLS = {
    "Вакансии": "https://3ddd.ru/work/vacancies",
    "Заказы": "https://3ddd.ru/work/tasks",
}

# --- ОСНОВНОЙ КОД ---
bot = Bot(token=TOKEN)
last_seen = {name: None for name in URLS}


def check_site(name, url):
    global last_seen
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # ищем первый блок объявления
        item = soup.select_one(".work-list-item")
        if not item:
            return

        title = item.select_one("h3").get_text(strip=True)
        link = "https://3ddd.ru" + item.select_one("a")["href"]

        if last_seen[name] != link:
            last_seen[name] = link
            msg = f"🆕 Новое в разделе {name}:\n{title}\n{link}"
            bot.send_message(chat_id=CHAT_ID, text=msg)
            print("Отправлено сообщение:", msg)
    except requests.RequestException as e:
        print(f"Ошибка запроса для {name}: {e}")
    except TelegramError as e:
        print(f"Ошибка Telegram для {name}: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка для {name}: {e}")


def main():
    try:
        bot.send_message(chat_id=CHAT_ID, text="✅ Бот запущен и работает!")
    except TelegramError as e:
        print(f"Ошибка при отправке стартового сообщения: {e}")

    while True:
        for name, url in URLS.items():
            check_site(name, url)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
