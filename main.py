import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# Вставьте ваши токены
TELEGRAM_TOKEN = "8642325152:AAGPvLD1iGAeMj5vsa0tSNoyT7Zj61y1Kyw"
OPENROUTER_API_KEY = "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"

# Настройка клиента OpenRouter (через SDK OpenAI)
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Отправь мне вопрос, и я спрошу у нейросети.")

@dp.message()
async def handle_message(message: types.Message):
    # Уведомляем пользователя, что бот «думает»
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        response = await client.chat.completions.create(
            model="arcee-ai/trinity-large-preview:free", # Можно заменить на любую модель с OpenRouter
            messages=[{"role": "user", "content": message.text}]
        )
        answer = response.choices[0].message.content
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
