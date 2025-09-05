import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.ext import Application, CommandHandler
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))

VACANCIES_URL = "https://3ddd.ru/work/vacancies"
TASKS_URL = "https://3ddd.ru/work/tasks"

app = Flask(__name__)

# --- Функции для парсинга ---
async def fetch_page(session, url):
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return ""

async def get_latest_vacancy_and_task():
    async with aiohttp.ClientSession() as session:
        # --- Вакансия ---
        vac_html = await fetch_page(session, VACANCIES_URL)
        vac_soup = BeautifulSoup(vac_html, "html.parser")
        vac_elem = vac_soup.select_one(".b-vacancies__item a")
        if vac_elem:
            vac_title = vac_elem.get_text(strip=True)
            vac_link = "https://3ddd.ru" + vac_elem.get("href")
        else:
            vac_title = "нет данных"
            vac_link = ""

        # --- Заказ/задача ---
        task_html = await fetch_page(session, TASKS_URL)
        task_soup = BeautifulSoup(task_html, "html.parser")
        task_elem = task_soup.select_one(".b-orders__item a")
        if task_elem:
            task_title = task_elem.get_text(strip=True)
            task_link = "https://3ddd.ru" + task_elem.get("href")
        else:
            task_title = "нет данных"
            task_link = ""

        return (vac_title, vac_link), (task_title, task_link)

# --- Telegram команды ---
async def latest(update, context):
    (vac_title, vac_link), (task_title, task_link) = await get_latest_vacancy_and_task()
    msg = f"Вакансия:\n{vac_title}\n{vac_link}\n\nЗаказ:\n{task_title}\n{task_link}"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def commands(update, context):
    msg = (
        "/status — проверить, жив ли бот\n"
        "/latest — показать последний заказ/вакансию\n"
        "/commands — показать список команд"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def status(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Бот запущен и работает!")

# --- Отправка стартового сообщения ---
async def send_start_message(bot: Bot):
    try:
        await bot.send_message(chat_id=CHAT_ID, text="Стартовое сообщение отправлено ✅")
        print("Стартовое сообщение отправлено ✅")
    except Exception as e:
        print(f"Ошибка при отправке стартового сообщения: {e}")

# --- Flask ---
@app.route("/")
def index():
    return "Bot is running!"

def start_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# --- Основная функция ---
async def main():
    app_bot = Application.builder().token(TOKEN).build()
    # Регистрация команд
    app_bot.add_handler(CommandHandler("latest", latest))
    app_bot.add_handler(CommandHandler("commands", commands))
    app_bot.add_handler(CommandHandler("status", status))

    # Стартовое сообщение
    await send_start_message(app_bot.bot)

    # Бот живет до остановки процесса
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Flask в отдельном потоке
    Thread(target=start_flask, daemon=True).start()
    # Запуск Telegram
    asyncio.run(main())
