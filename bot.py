import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
import openai
from dotenv import load_dotenv

# Load env variables
load_dotenv("mood_bot.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO)

# Webhook settings (вшито вручную)
WEBHOOK_HOST = "https://mood-bot-frbb.onrender.com"
WEBHOOK_PATH = f"/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Init bot and dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Configure OpenRouter
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = OPENROUTER_API_KEY

# Simple keyboard
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("🍽 Хочу в ресторан"))
main_kb.add(KeyboardButton("🎬 Пойду в кино"))
main_kb.add(KeyboardButton("🎭 Театр / выставка"))
main_kb.add(KeyboardButton("🤷‍♂️ Мне скучно"))

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Что хочешь сегодня сделать?", reply_markup=main_kb)

@dp.message_handler()
async def handle_text(message: types.Message):
    user_text = message.text.lower()

    if "ресторан" in user_text:
        await message.reply("Вот несколько ресторанов рядом с тобой... (в следующей версии)")
    elif "кино" in user_text:
        await message.reply("Сейчас в кино: «Дюна 2», «Оппенгеймер»... (в следующей версии)")
    elif "театр" in user_text or "выставка" in user_text:
        await message.reply("Афиша на сегодня: ... (в следующей версии)")
    else:
        try:
            response = openai.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты дружелюбный помощник, советующий, как провести досуг в городе."},
                    {"role": "user", "content": user_text}
                ]
            )
            idea = response.choices[0].message.content
            await message.reply(idea)
        except Exception as e:
            await message.reply("Произошла ошибка при обращении к GPT 😕")
            import traceback
            logging.error("GPT error:\n" + traceback.format_exc())

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
