import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Ключи из переменных окружения
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Состояния для бота
class BotStates(StatesGroup):
    waiting_for_prompt = State()

# Функция запроса к OpenRouter
async def get_openrouter_response(user_text):
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "google/gemini-2.0-flash-001", 
        "messages": [
            {"role": "system", "content": "Ты опытный программист. Отвечай только кодом или краткими пояснениями к нему. Используй Markdown для кода."},
            {"role": "user", "content": user_text}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data, timeout=60) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                return f"Ошибка API: {response.status}"
        except Exception as e:
            return f"Ошибка соединения: {str(e)}"

# Главное меню с кнопкой
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🚀 Написать запрос ИИ", callback_data="start_ai")
    )
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Это бот-посредник для генерации кода через OpenRouter.\n\n"
        "Чтобы отправить сообщение нейросети, нажми кнопку ниже:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "start_ai")
async def ask_for_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_prompt)
    await callback.message.edit_text(
        "🤖 Режим ИИ активирован.\nВведите описание задачи (какой код нужно написать?):",
        reply_markup=None
    )
    await callback.answer()

@dp.message(BotStates.waiting_for_prompt)
async def handle_ai_request(message: types.Message, state: FSMContext):
    # Визуальный индикатор работы
    status_msg = await message.answer("⏳ Генерирую код, пожалуйста, подождите...")
    await bot.send_chat_action(message.chat.id, "typing")
    
    answer = await get_openrouter_response(message.text)
    
    # Удаляем сообщение о загрузке и присылаем ответ
    await status_msg.delete()
    
    if len(answer) > 4096:
        for x in range(0, len(answer), 4096):
            await message.answer(answer[x:x+4096], parse_mode="Markdown")
    else:
        await message.answer(answer, parse_mode="Markdown")
    
    # Снова предлагаем кнопку для нового запроса или выходим из состояния
    await message.answer("Готово! Нужен еще код?", reply_markup=get_main_menu())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
