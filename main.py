import os
import asyncio
import logging
import socket
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токены
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Состояния
class BotStates(StatesGroup):
    waiting_for_prompt = State()

dp = Dispatcher()

# Функция запроса к OpenRouter
async def get_openrouter_response(user_text):
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://huggingface.co",
    }
    data = {
        "model": "arcee-ai/trinity-large-preview:free", 
        "messages": [
            {"role": "system", "content": "Ты программист. Отвечай кодом в Markdown."},
            {"role": "user", "content": user_text}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=90) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices']['message']['content']
                return f"Ошибка API: {response.status}"
        except Exception as e:
            return f"Ошибка сети: {str(e)}"

# Клавиатура
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 Написать запрос ИИ", callback_data="start_ai"))
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Привет! Нажми кнопку, чтобы начать:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "start_ai")
async def ask_for_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_prompt)
    await callback.message.edit_text("🤖 Опиши задачу:")
    await callback.answer()

@dp.message(BotStates.waiting_for_prompt)
async def handle_ai_request(message: types.Message, state: FSMContext):
    status_msg = await message.answer("⏳ Думаю...")
    answer = await get_openrouter_response(message.text)
    await status_msg.delete()
    
    if len(answer) > 4096:
        for x in range(0, len(answer), 4096):
            await message.answer(answer[x:x+4096], parse_mode="Markdown")
    else:
        await message.answer(answer, parse_mode="Markdown")
    
    await message.answer("Готово!", reply_markup=get_main_menu())
    await state.clear()

async def main():
    logger.info("Запуск...")
    
    # СОЗДАЕМ СЕССИЮ И БОТА ТОЛЬКО ЗДЕСЬ (ВНУТРИ LOOP)
    connector = aiohttp.TCPConnector(family=socket.AF_INET)
    session = AiohttpSession(connector=connector)
    bot = Bot(token=TG_TOKEN, session=session)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
