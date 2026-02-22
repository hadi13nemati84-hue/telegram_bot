import asyncio
import sqlite3
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- تنظیمات اصلی ---
TOKEN = "8513142832:AAEYmXiFws3WfNZmQo4lo5J-FNQClNm4YH8"
ADMIN_ID = 7625626852
PORT = int(os.environ.get("PORT", 8080)) # مهم برای Render

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- بخش دیتابیس ---
def init_db():
    conn = sqlite3.connect('movie_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

# --- ماشین وضعیت ---
class AdminStates(StatesGroup):
    waiting_for_anon_to_admin = State()

def get_main_reply_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📩 ارسال پیام ناشناس به ادمین")],
        [KeyboardButton(text="🏠 منوی اصلی")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
@dp.message(F.text == "🏠 منوی اصلی")
async def start_handler(message: types.Message):
    await message.answer("🎬 خوش آمدید! برای ارسال نظر یا پیام به ادمین از دکمه زیر استفاده کنید:", 
                         reply_markup=get_main_reply_kb())

@dp.message(F.text == "📩 ارسال پیام ناشناس به ادمین")
async def anon_start(message: types.Message, state: FSMContext):
    await message.answer("📝 پیام خود را بنویسید (هویت شما مخفی می‌ماند):")
    await state.set_state(AdminStates.waiting_for_anon_to_admin)

@dp.message(AdminStates.waiting_for_anon_to_admin)
async def anon_done(message: types.Message, state: FSMContext):
    if message.text == "🏠 منوی اصلی":
        await state.clear()
        await start_handler(message)
        return
    await bot.send_message(ADMIN_ID, "🔔 **پیام ناشناس جدید:**")
    await bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    await message.answer("✅ ارسال شد.")
    await state.clear()

# --- بخش وب‌سرور برای Render (حیاتی) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    init_db()
    # اجرای همزمان وب‌سرور و ربات
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    
    print(f"✅ Web server started on port {PORT}")
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())