import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- تنظیمات ---
TOKEN = "8513142832:AAEYmXiFws3WfNZmQo4lo5J-FNQClNm4YH8"
ADMIN_ID = 7625626852
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- وضعیت‌ها ---
class ChatStates(StatesGroup):
    user_chatting = State()     # کاربر در حال چت با ادمین است
    admin_chatting = State()    # ادمین در حال چت با یک کاربر خاص است

# --- کیبوردها ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📩 شروع چت ناشناس")],
        [KeyboardButton(text="🏠 منوی اصلی")]
    ], resize_keyboard=True)

def get_admin_stop_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ پایان گفتگو")]
    ], resize_keyboard=True)

def admin_reply_button(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ورود به چت", callback_data=f"chat_{user_id}")]
    ])

# --- بخش کاربران ---
@dp.message(Command("start"))
@dp.message(F.text == "🏠 منوی اصلی")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("سلام! برای شروع گفتگو با ادمین روی دکمه زیر بزن:", reply_markup=get_main_kb())

@dp.message(F.text == "📩 شروع چت ناشناس")
async def start_anon_chat(message: types.Message, state: FSMContext):
    await state.set_state(ChatStates.user_chatting)
    await message.answer("✅ شما وارد حالت چت ناشناس شدید. هر پیامی بفرستید برای ادمین ارسال می‌شود.\n(برای خروج '🏠 منوی اصلی' را بزنید)", 
                         reply_markup=get_main_kb())

@dp.message(ChatStates.user_chatting)
async def user_to_admin(message: types.Message, state: FSMContext):
    if message.text == "🏠 منوی اصلی":
        await start_cmd(message, state)
        return

    # ارسال پیام کاربر به ادمین با دکمه ورود به چت
    await bot.send_message(ADMIN_ID, f"👤 **پیام جدید از کاربر ناشناس:**")
    await bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=admin_reply_button(message.from_user.id)
    )
    await message.answer("📨 پیام شما فرستاده شد.")

# --- بخش ادمین ---
@dp.callback_query(F.data.startswith("chat_"))
async def admin_enter_chat(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[1]
    await state.update_data(active_user=user_id)
    await state.set_state(ChatStates.admin_chatting)
    
    await callback.message.answer(f"🔄 متصل شدید به کاربر `{user_id}`.\nحالا هر چه بنویسید برای او ارسال می‌شود.", 
                                 reply_markup=get_admin_stop_kb())
    await callback.answer()

@dp.message(ChatStates.admin_chatting)
async def admin_to_user(message: types.Message, state: FSMContext):
    if message.text == "❌ پایان گفتگو":
        await state.clear()
        await message.answer("✅ گفتگو با کاربر به پایان رسید.", reply_markup=types.ReplyKeyboardRemove())
        return

    data = await state.get_data()
    target_id = data.get("active_user")

    try:
        await bot.copy_message(
            chat_id=target_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        # ادمین در همین State می‌ماند تا چت ادامه یابد
    except Exception:
        await message.answer("❌ خطا! ارتباط با کاربر قطع شده است.")
        await state.clear()

# --- وب‌سرور (برای Render) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await asyncio.gather(site.start(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())