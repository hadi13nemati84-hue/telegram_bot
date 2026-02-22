import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- تنظیمات اصلی ---
# نکته امنیتی: بهتر است توکن را در Environment Variables قرار دهی
TOKEN = "8513142832:AAEYmXiFws3WfNZmQo4lo5J-FNQClNm4YH8"
ADMIN_ID = 7625626852
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ماشین وضعیت (FSM) ---
class Form(StatesGroup):
    waiting_for_anon_message = State()  # کاربر در حال نوشتن پیام به ادمین
    admin_replying = State()           # ادمین در حال نوشتن پاسخ به کاربر

# --- کیبوردهای ربات ---
def get_main_reply_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📩 ارسال پیام ناشناس به ادمین")],
        [KeyboardButton(text="🏠 منوی اصلی")]
    ], resize_keyboard=True)

def admin_reply_markup(user_id):
    # ذخیره ID کاربر در callback_data برای شناسایی فرستنده
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ پاسخ به این پیام", callback_data=f"reply_{user_id}")]
    ])

# --- هندلرهای کاربر ---
@dp.message(Command("start"))
@dp.message(F.text == "🏠 منوی اصلی")
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear() # پاکسازی حالت‌های قبلی
    await message.answer("🎬 به سیستم پیام‌رسان ناشناس خوش آمدید!\nبرای ارتباط با ادمین از دکمه زیر استفاده کنید:", 
                         reply_markup=get_main_reply_kb())

@dp.message(F.text == "📩 ارسال پیام ناشناس به ادمین")
async def anon_start(message: types.Message, state: FSMContext):
    await message.answer("📝 پیام خود را بنویسید (هویت شما کاملاً مخفی می‌ماند):", 
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 منوی اصلی")]], resize_keyboard=True))
    await state.set_state(Form.waiting_for_anon_message)

@dp.message(Form.waiting_for_anon_message)
async def anon_done(message: types.Message, state: FSMContext):
    if message.text == "🏠 منوی اصلی":
        await state.clear()
        await start_handler(message, state)
        return

    # ارسال پیام به ادمین به همراه دکمه پاسخ
    await bot.send_message(ADMIN_ID, f"🔔 **پیام ناشناس جدید دریافت شد:**")
    await bot.copy_message(
        chat_id=ADMIN_ID, 
        from_chat_id=message.chat.id, 
        message_id=message.message_id,
        reply_markup=admin_reply_markup(message.from_user.id)
    )
    
    await message.answer("✅ پیام شما با موفقیت ارسال شد. در صورت پاسخ ادمین، همین‌جا مطلع خواهید شد.")
    await state.clear()

# --- هندلرهای ادمین ---
@dp.callback_query(F.data.startswith("reply_"))
async def start_admin_reply(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[1] # استخراج ID کاربر از دیتای دکمه
    await state.update_data(reply_to_user=user_id) # ذخیره موقت ID در حافظه FSM
    
    await callback.message.answer(f"📍 در حال پاسخ به کاربر `{user_id}`...\nلطفاً متن پاسخ را بفرستید:")
    await state.set_state(Form.admin_replying)
    await callback.answer()

@dp.message(Form.admin_replying)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("reply_to_user")

    try:
        await bot.send_message(target_user_id, "💬 **پاسخ جدید از طرف ادمین:**")
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await message.answer("✅ پاسخ شما برای کاربر ارسال شد.")
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال پیام! احتمالاً کاربر ربات را بلاک کرده است.\nتوضیح خطا: {e}")
    
    await state.clear()

# --- بخش وب‌سرور ---
async def handle(request):
    return web.Response(text="Bot is running and healthy!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    
    print(f"🚀 Server running on port {PORT}")
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())