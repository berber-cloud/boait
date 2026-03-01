import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class BotStates(StatesGroup):
    waiting_for_prompt = State()

dp = Dispatcher()

async def get_openrouter_response(user_text):
    url = "https://openrouter.ai"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "arcee-ai/trinity-large-preview:free", 
        "messages": [{"role": "system", "content": "Ты программист. Пиши код."}, {"role": "user", "content": user_text}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            res = await resp.json()
            return res['choices'][0]['message']['content']

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Написать запрос ИИ", callback_data="start_ai"))
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Жми кнопку:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "start_ai")
async def ask_for_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_prompt)
    await callback.message.edit_text("🤖 Опиши задачу:")

@dp.message(BotStates.waiting_for_prompt)
async def handle_ai_request(message: types.Message, state: FSMContext):
    msg = await message.answer("⏳ Думаю...")
    answer = await get_openrouter_response(message.text)
    await msg.delete()
    await message.answer(answer, parse_mode="Markdown")
    await state.clear()

async def handle_hf_healthcheck(request):
    return web.Response(text="I am alive")


async def main():
    PROXY_URL = "http://167.71.233.15:8080" 
    logger.info(f"Запуск через прокси {PROXY_URL}...")
    
    # Настройка бота
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=TG_TOKEN, session=session)
    
    # Настройка веб-сервера для Hugging Face (чтобы не было SIGTERM)
    app = web.Application()
    app.router.add_get("/", handle_hf_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 7860) # Порт 7860 обязателен для HF
    
    await site.start()
    logger.info("Веб-сервер запущен на порту 7860")

    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())