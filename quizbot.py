Asadulloh Ibroximov, [12/26/25 1:47 AM]
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import pandas as pd
import io
from datetime import datetime, timedelta
import re

# Konfiguratsiya
BOT_TOKEN = "8541925769:AAGd89Y1lQNt5_xJUBvYKEh4eaIrzqARciU"
SUPER_ADMIN_ID = 7715235794  # Super admin (siz)
CHANNEL_USERNAME = "@haqiqatlar_torimi"

# Logging sozlash
logging.basicConfig(level=logging.INFO)

# Bot va dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Ma'lumotlar bazasi - eski faylni o'chirib yangisini yaratish
DB_FILE = 'school_bot.db'
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print("⚠️ Eski ma'lumotlar bazasi o'chirildi, yangisi yaratilmoqda...")

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# Jadval yaratish (to'liq yangi)
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    full_name TEXT,
    age INTEGER,
    location TEXT,
    parent_name TEXT,
    parent_phone TEXT,
    group_id INTEGER,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    position TEXT,
    is_super_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_username TEXT UNIQUE,
    channel_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Super admin va asosiy kanalni qo'shish
try:
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, full_name, is_super_admin) VALUES (?, ?, ?)", 
                   (SUPER_ADMIN_ID, "Super Admin", 1))
    cursor.execute("INSERT OR IGNORE INTO channels (channel_username, channel_name) VALUES (?, ?)", 
                   (CHANNEL_USERNAME, "Asosiy kanal"))
    conn.commit()
    print("✅ Super admin va asosiy kanal qo'shildi")
except Exception as e:
    print(f"❌ Xatolik admin qo'shishda: {e}")

# FSM holatlari
class StudentForm(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_age = State()
    waiting_for_location = State()
    waiting_for_parent_name = State()
    waiting_for_parent_phone = State()
    waiting_for_group = State()

class AdminForm(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_channel_username = State()
    waiting_for_channel_name = State()

class SuperAdminForm(StatesGroup):
    waiting_for_admin_username = State()
    waiting_for_admin_fullname = State()
    waiting_for_admin_phone = State()
    waiting_for_admin_position = State()

# Yordamchi funksiyalar
async def check_subscription(user_id):
    """Barcha kanallarga obuna bo'lishni tekshirish"""
    cursor.execute("SELECT channel_username FROM channels WHERE is_active = 1")
    channels = cursor.fetchall()
    
    if not channels:
        return True  # Agar kanal bo'lmasa, tekshirish o'tkazilmaydi
    
    for channel in channels:
        channel_username = channel[0]
        try:
            chat_member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            if chat_member.status not in ['creator', 'administrator', 'member']:
                return False
        except Exception as e:
            logging.error(f"Kanalni tekshirishda xatolik {channel_username}: {e}")
            continue
    
    return True

Asadulloh Ibroximov, [12/26/25 1:47 AM]


def get_verification_keyboard():
    """Tasdiqlash tugmasi"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Men obuna bo'ldim, tekshirish", callback_data="check_subscription")]
    ])
    return keyboard

def get_groups_keyboard():
    """Guruhlar tugmalari"""
    cursor.execute("SELECT id, name FROM groups")
    groups = cursor.fetchall()
    keyboard = []
    for group_id, group_name in groups:
        keyboard.append([InlineKeyboardButton(text=group_name, callback_data=f"group_{group_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard():
    """Oddiy admin paneli"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Barcha ma'lumotlar Excel", callback_data="get_excel")],
        [InlineKeyboardButton(text="👥 Guruhlarni boshqarish", callback_data="manage_groups")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="get_stats")],
        [InlineKeyboardButton(text="📢 Kanalga obuna tekshirish", callback_data="check_channels")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_super_admin_keyboard():
    """Super admin paneli"""
    keyboard = [
        [InlineKeyboardButton(text="👑 Super Admin Panel", callback_data="super_admin_panel")],
        [InlineKeyboardButton(text="📊 Barcha ma'lumotlar Excel", callback_data="get_excel")],
        [InlineKeyboardButton(text="👥 Guruhlarni boshqarish", callback_data="manage_groups")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="get_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_super_admin_panel_keyboard():
    """Super admin maxsus paneli"""
    keyboard = [
        [InlineKeyboardButton(text="📢 Kanallarni boshqarish", callback_data="manage_channels")],
        [InlineKeyboardButton(text="👨‍🏫 Adminlar ro'yxati", callback_data="list_admins")],
        [InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="add_super_admin")],
        [InlineKeyboardButton(text="📈 To'liq statistika", callback_data="full_stats")],
        [InlineKeyboardButton(text="📥 Adminlar Excel", callback_data="admins_excel")],
        [InlineKeyboardButton(text="🔙 Asosiy panel", callback_data="back_to_super_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_channels_management_keyboard():
    """Kanallar boshqaruvi"""
    cursor.execute("SELECT id, channel_name, channel_username, is_active FROM channels")
    channels = cursor.fetchall()
    
    keyboard = []
    for channel_id, channel_name, channel_username, is_active in channels:
        status = "✅" if is_active else "❌"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {channel_name}", 
                callback_data=f"channel_detail_{channel_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="➕ Yangi kanal", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton(text="🔙 Super admin", callback_data="super_admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_group_detail_keyboard(group_id):
    """Guruh batafsil ma'lumotlari"""
    keyboard = [
        [InlineKeyboardButton(text="📋 O'quvchilar ro'yxati", callback_data=f"list_group_{group_id}")],
        [InlineKeyboardButton(text="📥 Excel yuklash", callback_data=f"excel_group_{group_id}")],
        [InlineKeyboardButton(text="🗑 Guruhni o'chirish", callback_data=f"deletegroup_{group_id}")],
        [InlineKeyboardButton(text="🔙 Guruhlar ro'yxati", callback_data="view_groups")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

Asadulloh Ibroximov, [12/26/25 1:47 AM]


def get_groups_list_keyboard():
    """Guruhlar ro'yxati"""
    cursor.execute("SELECT id, name FROM groups")
    groups = cursor.fetchall()
    keyboard = []
    for group_id, group_name in groups:
        keyboard.append([InlineKeyboardButton(text=f"📚 {group_name}", callback_data=f"group_detail_{group_id}")])
    keyboard.append([InlineKeyboardButton(text="➕ Yangi guruh", callback_data="add_group")])
    keyboard.append([InlineKeyboardButton(text="🔙 Admin panel", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    print(f"👤 Foydalanuvchi {user_id} start bosdi")
    
    # Kanalga obuna tekshirish
    is_subscribed = await check_subscription(user_id)
    print(f"📢 Obuna holati: {is_subscribed}")
    
    if not is_subscribed:
        # Kanallar ro'yxatini ko'rsatish
        cursor.execute("SELECT channel_name, channel_username FROM channels WHERE is_active = 1")
        channels = cursor.fetchall()
        
        if not channels:
            text = "⚠️ Hech qanday kanal sozlanmagan. Iltimos, admin bilan bog'laning."
            await message.answer(text)
            return
        
        text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
        for channel_name, channel_username in channels:
            text += f"📢 {channel_name}\n"
            text += f"   👉 {channel_username}\n\n"
        
        text += "Obuna bo'lgach, quyidagi tugmani bosing:"
        
        await message.answer(text, reply_markup=get_verification_keyboard())
        return
    
    # Admin tekshirish
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    print(f"👑 Admin tekshirish: {admin_info}")
    
    if admin_info:
        is_super_admin = admin_info[0]
        if is_super_admin:
            await message.answer("👑 Super Admin panelga xush kelibsiz!", reply_markup=get_super_admin_keyboard())
        else:
            await message.answer("👨‍🏫 Admin panelga xush kelibsiz!", reply_markup=get_admin_keyboard())
    else:
        # Foydalanuvchi allaqachon ro'yxatdan o'tganmi?
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        already_registered = cursor.fetchone()
        
        if already_registered:
            await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz!")
        else:
            await message.answer("✅ Kanalga obuna bo'ldingiz!\n\nIsmingizni kiriting (Ism Familiya):")
            await state.set_state(StudentForm.waiting_for_full_name)

# Admin panel
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    if admin_info:
        is_super_admin = admin_info[0]
        if is_super_admin:
            await message.answer("👑 Super Admin panelga xush kelibsiz!", reply_markup=get_super_admin_keyboard())
        else:
            await message.answer("👨‍🏫 Admin panelga xush kelibsiz!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ Siz admin emassiz!")

# Super admin paneli
@dp.message(Command("admin399"))
async def cmd_super_admin(message: types.Message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    if admin_info and admin_info[0] == 1:
        await message.answer("👑 Super Admin maxsus paneli", reply_markup=get_super_admin_panel_keyboard())
    else:
        await message.answer("❌ Sizda super admin huquqi yo'q!")

Asadulloh Ibroximov, [12/26/25 1:47 AM]


# Kanal obunasini tekshirish
@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback.message.delete()
        
        # Admin tekshirish
        cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
        admin_info = cursor.fetchone()
        
        if admin_info:
            is_super_admin = admin_info[0]
            if is_super_admin:
                await callback.message.answer("👑 Super Admin panelga xush kelibsiz!", reply_markup=get_super_admin_keyboard())
            else:
                await callback.message.answer("👨‍🏫 Admin panelga xush kelibsiz!", reply_markup=get_admin_keyboard())
        else:
            # Foydalanuvchi allaqachon ro'yxatdan o'tganmi?
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            already_registered = cursor.fetchone()
            
            if already_registered:
                await callback.message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz!")
            else:
                await callback.message.answer("✅ Kanalga obuna bo'ldingiz!\n\nIsmingizni kiriting (Ism Familiya):")
                await state.set_state(StudentForm.waiting_for_full_name)
    else:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
    
    await callback.answer()

# Super admin paneli (callback)
@dp.callback_query(F.data == "super_admin_panel")
async def super_admin_panel_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    if admin_info and admin_info[0] == 1:
        await callback.message.edit_text("👑 Super Admin maxsus paneli", reply_markup=get_super_admin_panel_keyboard())
    else:
        await callback.answer("❌ Sizda super admin huquqi yo'q!", show_alert=True)
    
    await callback.answer()

# Kanallarni boshqarish
@dp.callback_query(F.data == "manage_channels")
async def manage_channels(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    if admin_info and admin_info[0] == 1:
        cursor.execute("SELECT COUNT(*) FROM channels")
        channel_count = cursor.fetchone()[0]
        
        text = f"📢 Kanallar boshqaruvi\n\n"
        text += f"📊 Jami kanallar: {channel_count}\n\n"
        text += "Quyidagi kanallarni boshqarishingiz mumkin:"
        
        await callback.message.edit_text(text, reply_markup=get_channels_management_keyboard())
    else:
        await callback.answer("❌ Sizda super admin huquqi yo'q!", show_alert=True)
    
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


# Kanal haqida ma'lumot
@dp.callback_query(F.data.startswith("channel_detail_"))
async def channel_detail(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT channel_name, channel_username, is_active FROM channels WHERE id = ?", (channel_id,))
    channel = cursor.fetchone()
    
    if not channel:
        await callback.answer("Kanal topilmadi!")
        return
    
    channel_name, channel_username, is_active = channel
    status = "Faol ✅" if is_active else "Faol emas ❌"
    
    text = f"📢 **{channel_name}**\n\n"
    text += f"👤 Username: {channel_username}\n"
    text += f"📊 Holat: {status}\n\n"
    text += "Amallar:"
    
    keyboard = []
    if is_active:
        keyboard.append([InlineKeyboardButton(text="❌ Kanalni o'chirish", callback_data=f"deactivate_channel_{channel_id}")])
    else:
        keyboard.append([InlineKeyboardButton(text="✅ Kanalni yoqish", callback_data=f"activate_channel_{channel_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🗑 Kanalni o'chirib tashlash", callback_data=f"delete_channel_{channel_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Kanallar ro'yxati", callback_data="manage_channels")])
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# Yangi kanal qo'shish
@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi kanal username ni kiriting (@ bilan):")
    await state.set_state(AdminForm.waiting_for_channel_username)
    await callback.answer()

@dp.message(AdminForm.waiting_for_channel_username)
async def add_channel_username(message: types.Message, state: FSMContext):
    channel_username = message.text.strip()
    
    # Username formatini tekshirish
    if not channel_username.startswith('@'):
        await message.answer("❌ Kanal username @ bilan boshlanishi kerak!\n\nQaytadan kiriting:")
        return
    
    await state.update_data(channel_username=channel_username)
    await message.answer("Kanal nomini kiriting:")
    await state.set_state(AdminForm.waiting_for_channel_name)

@dp.message(AdminForm.waiting_for_channel_name)
async def add_channel_finish(message: types.Message, state: FSMContext):
    channel_name = message.text.strip()
    data = await state.get_data()
    channel_username = data['channel_username']
    
    try:
        # Kanal mavjudligini tekshirish
        cursor.execute("INSERT INTO channels (channel_username, channel_name) VALUES (?, ?)", 
                      (channel_username, channel_name))
        conn.commit()
        
        await message.answer(f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
                           f"📢 Nomi: {channel_name}\n"
                           f"👤 Username: {channel_username}")
    except sqlite3.IntegrityError:
        await message.answer(f"❌ {channel_username} kanali allaqachon mavjud!")
    
    await state.clear()

# Kanalni faollashtirish/o'chirish
@dp.callback_query(F.data.startswith("deactivate_channel_"))
async def deactivate_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    
    cursor.execute("UPDATE channels SET is_active = 0 WHERE id = ?", (channel_id,))
    conn.commit()
    
    await callback.answer("✅ Kanal o'chirildi!")
    await manage_channels(callback)

@dp.callback_query(F.data.startswith("activate_channel_"))
async def activate_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    
    cursor.execute("UPDATE channels SET is_active = 1 WHERE id = ?", (channel_id,))
    conn.commit()
    
    await callback.answer("✅ Kanal yoqildi!")
    await manage_channels(callback)

Asadulloh Ibroximov, [12/26/25 1:47 AM]


# Kanalni o'chirib tashlash
@dp.callback_query(F.data.startswith("delete_channel_"))
async def delete_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split("_")[2])
    
    cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    
    await callback.answer("✅ Kanal o'chirib tashlandi!")
    await manage_channels(callback)

# Adminlar ro'yxati
@dp.callback_query(F.data == "list_admins")
async def list_admins(callback: types.CallbackQuery):
    cursor.execute("""
        SELECT user_id, username, full_name, phone, position, is_super_admin, created_at
        FROM admins 
        ORDER BY is_super_admin DESC, created_at
    """)
    admins = cursor.fetchall()
    
    if not admins:
        text = "⚠️ Hozircha hech qanday admin yo'q."
    else:
        text = "👨‍🏫 **Adminlar ro'yxati:**\n\n"
        
        for i, admin in enumerate(admins, 1):
            user_id, username, full_name, phone, position, is_super_admin, created_at = admin
            
            admin_type = "👑 Super Admin" if is_super_admin == 1 else "👨‍🏫 Admin"
            username_display = f"@{username}" if username else "Yo'q"
            phone_display = phone if phone else "Yo'q"
            position_display = position if position else "Yo'q"
            
            text += f"{i}. {admin_type}\n"
            text += f"   👤 Ism: {full_name}\n"
            text += f"   📱 ID: {user_id}\n"
            text += f"   🔗 Username: {username_display}\n"
            text += f"   📞 Telefon: {phone_display}\n"
            text += f"   💼 Lavozim: {position_display}\n"
            text += f"   📅 Qo'shilgan: {created_at[:10]}\n\n"
    
    keyboard = [[InlineKeyboardButton(text="🔙 Super admin", callback_data="super_admin_panel")]]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# Yangi super admin qo'shish
@dp.callback_query(F.data == "add_super_admin")
async def add_super_admin_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi adminning Telegram username ni kiriting (@ bilan):")
    await state.set_state(SuperAdminForm.waiting_for_admin_username)
    await callback.answer()

@dp.message(SuperAdminForm.waiting_for_admin_username)
async def process_admin_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    
    if not username.startswith('@'):
        await message.answer("❌ Username @ bilan boshlanishi kerak!\n\nQaytadan kiriting:")
        return
    
    await state.update_data(username=username)
    await message.answer("Adminning to'liq ismini kiriting:")
    await state.set_state(SuperAdminForm.waiting_for_admin_fullname)

@dp.message(SuperAdminForm.waiting_for_admin_fullname)
async def process_admin_fullname(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    await state.update_data(full_name=full_name)
    await message.answer("Adminning telefon raqamini kiriting:")
    await state.set_state(SuperAdminForm.waiting_for_admin_phone)

@dp.message(SuperAdminForm.waiting_for_admin_phone)
async def process_admin_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await message.answer("Adminning ish lavozimini kiriting:")
    await state.set_state(SuperAdminForm.waiting_for_admin_position)

Asadulloh Ibroximov, [12/26/25 1:47 AM]


@dp.message(SuperAdminForm.waiting_for_admin_position)
async def process_admin_position(message: types.Message, state: FSMContext):
    position = message.text.strip()
    data = await state.get_data()
    
    username = data['username']
    full_name = data['full_name']
    phone = data['phone']
    
    # Usernamedan @ ni olib tashlash
    clean_username = username.replace('@', '')
    
    text = f"📋 **Yangi admin ma'lumotlari:**\n\n"
    text += f"👤 Username: {username}\n"
    text += f"📛 Ism: {full_name}\n"
    text += f"📞 Telefon: {phone}\n"
    text += f"💼 Lavozim: {position}\n\n"
    text += "Adminni qo'shishni tasdiqlaysizmi?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, qo'shish", callback_data=f"confirm_add_admin_{clean_username}_{full_name}_{phone}_{position}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="super_admin_panel")]
    ])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await state.clear()

@dp.callback_query(F.data.startswith("confirm_add_admin_"))
async def confirm_add_admin(callback: types.CallbackQuery):
    data_parts = callback.data.split('_')[3:]
    username = data_parts[0]
    full_name = data_parts[1]
    phone = data_parts[2]
    position = "_".join(data_parts[3:])  # Bo'shliqlarni qayta tiklash
    
    # Admin ma'lumotlarini bazaga saqlash
    try:
        cursor.execute("""
            INSERT INTO admins (username, full_name, phone, position, is_super_admin) 
            VALUES (?, ?, ?, ?, ?)
        """, (f"@{username}", full_name, phone, position, 0))
        conn.commit()
        
        await callback.message.edit_text(f"✅ {full_name} admin sifatida qo'shildi!\n\n"
                                       f"📋 Ma'lumotlar bazaga saqlandi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik: {e}")
    
    await callback.answer()

# Adminlar uchun Excel fayl
@dp.callback_query(F.data == "admins_excel")
async def admins_excel(callback: types.CallbackQuery):
    cursor.execute("""
        SELECT user_id, username, full_name, phone, position, is_super_admin, created_at
        FROM admins 
        ORDER BY created_at DESC
    """)
    admins = cursor.fetchall()
    
    if not admins:
        await callback.answer("Hali hech qanday admin yo'q!")
        return
    
    # DataFrame yaratish
    df = pd.DataFrame(admins, columns=[
        'Telegram ID', 'Username', 'To\'liq ism', 'Telefon', 
        'Lavozim', 'Super admin', 'Qo\'shilgan vaqt'
    ])
    
    # Super admin ustunini o'zgartirish
    df['Super admin'] = df['Super admin'].map({1: 'Ha', 0: 'Yo\'q'})
    
    # Excel fayl yaratish
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Adminlar')
    
    output.seek(0)
    
    await callback.message.answer_document(
        types.BufferedInputFile(output.read(), filename="adminlar.xlsx"),
        caption="📊 Barcha adminlar ma'lumotlari"
    )
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


# To'liq statistika
@dp.callback_query(F.data == "full_stats")
async def full_stats(callback: types.CallbackQuery):
    # O'quvchilar statistikasi
    cursor.execute("SELECT COUNT(*) FROM users")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(registered_at) = DATE('now')")
    today_students = cursor.fetchone()[0]
    
    # Guruhlar statistikasi
    cursor.execute("SELECT COUNT(*) FROM groups")
    total_groups = cursor.fetchone()[0]
    
    # Adminlar statistikasi
    cursor.execute("SELECT COUNT(*) FROM admins")
    total_admins = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM admins WHERE is_super_admin = 1")
    super_admins = cursor.fetchone()[0]
    
    # Kanallar statistikasi
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM channels WHERE is_active = 1")
    active_channels = cursor.fetchone()[0]
    
    # Guruhlar bo'yicha statistika
    cursor.execute("""
        SELECT g.name, COUNT(u.id) 
        FROM groups g 
        LEFT JOIN users u ON g.id = u.group_id 
        GROUP BY g.id 
        ORDER BY COUNT(u.id) DESC
        LIMIT 5
    """)
    top_groups = cursor.fetchall()
    
    text = "📈 **To'liq statistika**\n\n"
    
    text += "👥 **O'quvchilar:**\n"
    text += f"   • Jami: {total_students}\n"
    text += f"   • Bugun: {today_students}\n\n"
    
    text += "🏫 **Guruhlar:**\n"
    text += f"   • Jami: {total_groups}\n\n"
    
    text += "👨‍🏫 **Adminlar:**\n"
    text += f"   • Jami: {total_admins}\n"
    text += f"   • Super adminlar: {super_admins}\n\n"
    
    text += "📢 **Kanallar:**\n"
    text += f"   • Jami: {total_channels}\n"
    text += f"   • Faol: {active_channels}\n\n"
    
    if top_groups:
        text += "🏆 **Eng ko'p o'quvchisi bo'lgan guruhlar (top 5):**\n"
        for group_name, count in top_groups:
            text += f"   • {group_name}: {count} ta\n"
    
    keyboard = [[InlineKeyboardButton(text="🔙 Super admin", callback_data="super_admin_panel")]]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# Kanal obunasini tekshirish (admin uchun)
@dp.callback_query(F.data == "check_channels")
async def check_channels_callback(callback: types.CallbackQuery):
    cursor.execute("SELECT channel_name, channel_username FROM channels WHERE is_active = 1")
    channels = cursor.fetchall()
    
    if not channels:
        text = "⚠️ Hech qanday kanal sozlanmagan."
    else:
        text = "📢 **Faol kanallar ro'yxati:**\n\n"
        for channel_name, channel_username in channels:
            text += f"• {channel_name}\n"
            text += f"  👉 {channel_username}\n\n"
        
        text += "Obuna bo'lishni tekshirish uchun:\n/start buyrug'ini yuboring."
    
    keyboard = [[InlineKeyboardButton(text="🔙 Admin panel", callback_data="back_to_admin")]]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# O'quvchi ma'lumotlarini to'ldirish (soddalashtirilgan versiya)
@dp.message(StudentForm.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(StudentForm.waiting_for_age)

Asadulloh Ibroximov, [12/26/25 1:47 AM]


@dp.message(StudentForm.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 5 or age > 60:
            await message.answer("Iltimos, to'g'ri yosh kiriting (5-60 oralig'ida):")
            return
        await state.update_data(age=age)
        await message.answer("Qayerdansiz? (Shahar/tuman):")
        await state.set_state(StudentForm.waiting_for_location)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")

@dp.message(StudentForm.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.answer("Ota-ona ismini kiriting:")
    await state.set_state(StudentForm.waiting_for_parent_name)

@dp.message(StudentForm.waiting_for_parent_name)
async def process_parent_name(message: types.Message, state: FSMContext):
    await state.update_data(parent_name=message.text)
    await message.answer("Ota-ona telefon raqamini kiriting:")
    await state.set_state(StudentForm.waiting_for_parent_phone)

@dp.message(StudentForm.waiting_for_parent_phone)
async def process_parent_phone(message: types.Message, state: FSMContext):
    await state.update_data(parent_phone=message.text)
    
    # Guruhlarni tanlash
    await message.answer("Guruhni tanlang:", reply_markup=get_groups_keyboard())
    await state.set_state(StudentForm.waiting_for_group)

@dp.callback_query(StudentForm.waiting_for_group, F.data.startswith("group_"))
async def process_group_selection(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    
    # Ma'lumotlarni bazaga saqlash
    try:
        cursor.execute('''
            INSERT INTO users (user_id, full_name, age, location, parent_name, parent_phone, group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (callback.from_user.id, data['full_name'], data['age'], data['location'], 
              data['parent_name'], data['parent_phone'], group_id))
        conn.commit()
        
        await callback.message.answer("✅ Ma'lumotlaringiz saqlandi! Rahmat!")
    except sqlite3.IntegrityError:
        await callback.message.answer("❌ Siz allaqachon ro'yxatdan o'tgansiz!")
    
    await state.clear()
    await callback.answer()

# Orqaga qaytish funksiyalari
@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    cursor.execute("SELECT is_super_admin FROM admins WHERE user_id = ?", (user_id,))
    admin_info = cursor.fetchone()
    
    if admin_info:
        is_super_admin = admin_info[0]
        if is_super_admin:
            await callback.message.edit_text("👑 Super Admin panelga xush kelibsiz!", reply_markup=get_super_admin_keyboard())
        else:
            await callback.message.edit_text("👨‍🏫 Admin panelga xush kelibsiz!", reply_markup=get_admin_keyboard())
    else:
        await callback.answer("Siz admin emassiz!", show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_super_admin")
async def back_to_super_admin(callback: types.CallbackQuery):
    await callback.message.edit_text("👑 Super Admin maxsus paneli", reply_markup=get_super_admin_panel_keyboard())
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


# Qo'shimcha zarur funksiyalar (soddalashtirilgan)
@dp.callback_query(F.data == "get_excel")
async def get_excel_file(callback: types.CallbackQuery):
    cursor.execute("""
        SELECT u.id, u.user_id, u.full_name, u.age, u.location, 
               u.parent_name, u.parent_phone, g.name as group_name, u.registered_at
        FROM users u
        LEFT JOIN groups g ON u.group_id = g.id
        ORDER BY u.registered_at DESC
    """)
    users = cursor.fetchall()
    
    if not users:
        await callback.answer("Hali hech qanday ma'lumot yo'q!")
        return
    
    # DataFrame yaratish
    df = pd.DataFrame(users, columns=[
        'ID', 'Telegram ID', 'To\'liq ism', 'Yosh', 'Manzil', 
        'Ota-ona ismi', 'Ota-ona telefoni', 'Guruh', 'Ro\'yxatdan o\'tgan vaqt'
    ])
    
    # Excel fayl yaratish
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='O\'quvchilar')
    
    output.seek(0)
    
    await callback.message.answer_document(
        types.BufferedInputFile(output.read(), filename="barcha_oquvchilar.xlsx"),
        caption="📊 Barcha o'quvchilar ma'lumotlari"
    )
    await callback.answer()

@dp.callback_query(F.data == "manage_groups")
async def manage_groups(callback: types.CallbackQuery):
    await callback.message.edit_text("📚 Guruhlar boshqaruvi", reply_markup=get_groups_list_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("group_detail_"))
async def group_detail(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    
    if not group:
        await callback.answer("Guruh topilmadi!")
        return
    
    group_name = group[0]
    
    # O'quvchilar sonini hisoblash
    cursor.execute("SELECT COUNT(*) FROM users WHERE group_id = ?", (group_id,))
    student_count = cursor.fetchone()[0]
    
    text = f"🏫 **{group_name}** guruhi\n\n"
    text += f"👥 O'quvchilar soni: {student_count}\n"
    text += f"🔗 Guruh ID: {group_id}\n\n"
    text += "Quyidagi amallardan birini tanlang:"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_group_detail_keyboard(group_id))
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


@dp.callback_query(F.data.startswith("list_group_"))
async def list_group_students(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    
    if not group:
        await callback.answer("Guruh topilmadi!")
        return
    
    group_name = group[0]
    
    # O'quvchilarni olish
    cursor.execute("""
        SELECT user_id, full_name, age, location, parent_name, parent_phone, registered_at
        FROM users 
        WHERE group_id = ?
        ORDER BY registered_at
    """, (group_id,))
    students = cursor.fetchall()
    
    if not students:
        text = f"🏫 **{group_name}** guruhi\n\n"
        text += "⚠️ Hozircha hech qanday o'quvchi yo'q."
        keyboard = [[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"group_detail_{group_id}")]]
        
        await callback.message.edit_text(text, parse_mode="Markdown", 
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await callback.answer()
        return
    
    # O'quvchilarni chiroyli formatda chiqarish
    text = f"🏫 **{group_name}** guruhi\n"
    text += f"📊 O'quvchilar soni: {len(students)}\n\n"
    text += "👥 **O'quvchilar ro'yxati:**\n\n"
    
    for i, student in enumerate(students, 1):
        user_id, full_name, age, location, parent_name, parent_phone, reg_date = student
        
        text += f"{i}. 👤 **{full_name}**\n"
        text += f"   📱 TG ID: `{user_id}`\n"
        text += f"   🎂 Yosh: {age}\n"
        text += f"   📍 {location}\n"
        text += f"   👨‍👩‍👧‍👦 {parent_name}\n"
        text += f"   📞 {parent_phone}\n"
        text += f"   📅 {reg_date[:10]}\n\n"
    
    keyboard = [
        [InlineKeyboardButton(text="📥 Excel yuklash", callback_data=f"excel_group_{group_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"group_detail_{group_id}")]
    ]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data.startswith("excel_group_"))
async def excel_group_students(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    
    if not group:
        await callback.answer("Guruh topilmadi!")
        return
    
    group_name = group[0]
    
    # O'quvchilarni olish
    cursor.execute("""
        SELECT user_id, full_name, age, location, parent_name, parent_phone, registered_at
        FROM users 
        WHERE group_id = ?
        ORDER BY registered_at
    """, (group_id,))
    students = cursor.fetchall()
    
    if not students:
        await callback.answer("Bu guruhda hali o'quvchi yo'q!")
        return
    
    # DataFrame yaratish
    df = pd.DataFrame(students, columns=[
        'Telegram ID', 'To\'liq ism', 'Yosh', 'Manzil', 
        'Ota-ona ismi', 'Ota-ona telefoni', 'Ro\'yxatdan o\'tgan vaqt'
    ])
    
    # Excel fayl yaratish
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=group_name[:31])
    
    output.seek(0)
    
    filename = f"{group_name.replace(' ', '_')}_oquvchilar.xlsx"
    
    await callback.message.answer_document(
        types.BufferedInputFile(output.read(), filename=filename),
        caption=f"📊 {group_name} guruhidagi o'quvchilar ma'lumotlari"
    )
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


@dp.callback_query(F.data == "get_stats")
async def get_stats(callback: types.CallbackQuery):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM groups")
    total_groups = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT g.name, COUNT(u.id) 
        FROM groups g 
        LEFT JOIN users u ON g.id = u.group_id 
        GROUP BY g.id 
        ORDER BY COUNT(u.id) DESC
    """)
    group_stats = cursor.fetchall()
    
    text = "📊 **Bot statistikasi**\n\n"
    text += f"👥 Jami o'quvchilar: {total_students}\n"
    text += f"🏫 Jami guruhlar: {total_groups}\n\n"
    
    if group_stats:
        text += "📈 **Guruhlar bo'yicha statistika:**\n"
        for group_name, count in group_stats:
            text += f"• {group_name}: {count} ta o'quvchi\n"
    
    keyboard = [[InlineKeyboardButton(text="🔙 Admin panel", callback_data="back_to_admin")]]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "add_group")
async def add_group_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi guruh nomini kiriting:")
    await state.set_state(AdminForm.waiting_for_group_name)
    await callback.answer()

@dp.message(AdminForm.waiting_for_group_name)
async def add_group_finish(message: types.Message, state: FSMContext):
    group_name = message.text.strip()
    
    if not group_name:
        await message.answer("Guruh nomi bo'sh bo'lishi mumkin emas!")
        return
    
    try:
        cursor.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
        conn.commit()
        await message.answer(f"✅ '{group_name}' guruhi muvaffaqiyatli yaratildi!")
    except sqlite3.IntegrityError:
        await message.answer(f"❌ '{group_name}' nomli guruh allaqachon mavjud!")
    
    await state.clear()

@dp.callback_query(F.data == "view_groups")
async def view_groups(callback: types.CallbackQuery):
    await callback.message.edit_text("📚 Guruhlar boshqaruvi", reply_markup=get_groups_list_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("deletegroup_"))
async def delete_group_confirm(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[1])
    
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    
    if not group:
        await callback.answer("Guruh topilmadi!")
        return
    
    group_name = group[0]
    
    # O'quvchilar borligini tekshirish
    cursor.execute("SELECT COUNT(*) FROM users WHERE group_id = ?", (group_id,))
    student_count = cursor.fetchone()[0]
    
    keyboard = []
    if student_count > 0:
        text = f"⚠️ **Diqqat!**\n\n"
        text += f"'{group_name}' guruhida {student_count} ta o'quvchi bor.\n"
        text += "Guruhni o'chirsangiz, bu o'quvchilarning guruhi o'chadi.\n\n"
        text += "Shundayam o'chirmoqchimisiz?"
        
        keyboard = [
            [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_{group_id}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"group_detail_{group_id}")]
        ]
    else:
        text = f"'{group_name}' guruhini o'chirmoqchimisiz?"
        
        keyboard = [
            [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_{group_id}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"group_detail_{group_id}")]
        ]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

Asadulloh Ibroximov, [12/26/25 1:47 AM]


@dp.callback_query(F.data.startswith("confirm_delete_"))
async def delete_group_final(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[2])
    
    cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
    group = cursor.fetchone()
    
    if group:
        group_name = group[0]
        
        # O'quvchilarning guruhini NULL qilish
        cursor.execute("UPDATE users SET group_id = NULL WHERE group_id = ?", (group_id,))
        
        # Guruhni o'chirish
        cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        conn.commit()
        
        text = f"✅ '{group_name}' guruhi o'chirildi!\n"
        text += f"⚠️ Ushbu guruhdagi o'quvchilarning guruhi o'chdi."
    else:
        text = "Guruh topilmadi!"
    
    keyboard = [[InlineKeyboardButton(text="🔙 Guruhlar ro'yxati", callback_data="manage_groups")]]
    
    await callback.message.edit_text(text, parse_mode="Markdown", 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# Asosiy funksiya
async def main():
    print("🚀 Bot yangi ma'lumotlar bazasi bilan ishga tushmoqda...")
    print(f"👑 Super Admin ID: {SUPER_ADMIN_ID}")
    print(f"📢 Asosiy kanal: {CHANNEL_USERNAME}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
