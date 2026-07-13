import random
import logging
import os
import json
import sqlite3
import asyncio
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ============ إعدادات القناة الإجبارية ============
FORCED_CHANNEL = "@Bexo50"  # اسم القناة
CHANNEL_LINK = "https://t.me/Bexo50"  # رابط القناة

# ============ قاعدة البيانات (SQLite) ============
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  number TEXT UNIQUE,
                  text TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (group_id TEXT PRIMARY KEY,
                  group_name TEXT,
                  enabled INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_admins
                 (group_id TEXT,
                  user_id TEXT,
                  PRIMARY KEY (group_id, user_id))''')
    conn.commit()
    conn.close()

# ============ دوال الأحكام ============
def load_rules():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT number, text FROM rules ORDER BY CAST(number AS INTEGER)")
    rows = c.fetchall()
    conn.close()
    
    if rows:
        return {str(row[0]): row[1] for row in rows}
    else:
        default_rules = {
            "1": "رئيج بيه",
            "2": "😂 اضحك بصوت عالٍ لمدة 10 ثوانٍ",
            "3": "💃 ارقص لمدة 30 ثانية",
            "4": "📖 احكي نكتة مضحكة",
            "5": "🤝 صافح أقرب شخص إليك بحرارة",
            "6": "🌶️ اشرب ماء حار أو تناول شيئاً حاراً"
        }
        save_rules(default_rules)
        return default_rules

def save_rules(rules):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM rules")
    for number, text in rules.items():
        c.execute("INSERT INTO rules (number, text) VALUES (?, ?)", (number, text))
    conn.commit()
    conn.close()

# ============ دوال المجموعات ============
def is_group_enabled(group_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT enabled FROM groups WHERE group_id = ?", (str(group_id),))
    row = c.fetchone()
    conn.close()
    if row:
        return bool(row[0])
    return True

def set_group_enabled(group_id, enabled):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (group_id, enabled) VALUES (?, ?)", 
              (str(group_id), 1 if enabled else 0))
    conn.commit()
    conn.close()

def save_group_info(group_id, group_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups (group_id, group_name, enabled) VALUES (?, ?, COALESCE((SELECT enabled FROM groups WHERE group_id = ?), 1))", 
              (str(group_id), group_name, str(group_id)))
    conn.commit()
    conn.close()

def add_group_admin(group_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO group_admins (group_id, user_id) VALUES (?, ?)", 
              (str(group_id), str(user_id)))
    conn.commit()
    conn.close()

def remove_group_admin(group_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM group_admins WHERE group_id = ? AND user_id = ?", 
              (str(group_id), str(user_id)))
    conn.commit()
    conn.close()

def is_group_admin_user(group_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM group_admins WHERE group_id = ? AND user_id = ?", 
              (str(group_id), str(user_id)))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_group_admins(group_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM group_admins WHERE group_id = ?", (str(group_id),))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ============ تحميل البيانات ============
init_db()
RULES = load_rules()

waiting_for_rule = {}
waiting_for_import = {}
waiting_for_admin_add = {}

# ============ المشرفين الأساسيين (صلاحية كاملة) ============
MASTER_ADMINS = [8798182716]

# ============ إيموجي النرد حسب الرقم ============
DICE_EMOJIS = {
    "1": "⚀",
    "2": "⚁",
    "3": "⚂",
    "4": "⚃",
    "5": "⚄",
    "6": "⚅"
}

# ============ التحقق من الاشتراك في القناة ============
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من اشتراك المستخدم في القناة الإجبارية"""
    user_id = update.effective_user.id
    
    # المشرفين الأساسيين لا يحتاجون اشتراك
    if is_master_admin(user_id):
        return True
    
    try:
        chat_member = await context.bot.get_chat_member(FORCED_CHANNEL, user_id)
        if chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"خطأ في التحقق من الاشتراك: {e}")
        return True

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة الاشتراك الإجباري"""
    keyboard = [
        [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ *عذراً!*\n\n"
        f"يجب عليك الاشتراك في قناتنا أولاً لتتمكن من استخدام البوت.\n\n"
        f"📌 القناة: {FORCED_CHANNEL}\n\n"
        f"🔽 اضغط على الزر أدناه للاشتراك، ثم اضغط 'تحقق من الاشتراك'.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if is_master_admin(user_id):
        await query.edit_message_text("👑 أنت مشرف أساسي، لا تحتاج للاشتراك!")
        return
    
    try:
        chat_member = await context.bot.get_chat_member(FORCED_CHANNEL, user_id)
        if chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await query.edit_message_text(
                "✅ *تم التحقق من اشتراكك!*\n\n"
                "🎲 مرحباً بك في لعبة النرد!\n"
                "اضغط على /start للبدء.",
                parse_mode='Markdown'
            )
            # عرض القائمة الرئيسية
            await start(update, context)
        else:
            keyboard = [
                [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
                [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚠️ *لم يتم العثور على اشتراكك!*\n\n"
                f"يجب عليك الاشتراك في قناتنا أولاً:\n"
                f"📌 {FORCED_CHANNEL}\n\n"
                f"🔽 اضغط على الزر أدناه للاشتراك، ثم 'تحقق من الاشتراك'.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logging.error(f"خطأ في التحقق من الاشتراك: {e}")
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚠️ *حدث خطأ أثناء التحقق!*\n\n"
            f"تأكد من اشتراكك في القناة:\n"
            f"📌 {FORCED_CHANNEL}\n\n"
            f"ثم اضغط 'تحقق من الاشتراك' مرة أخرى.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# ============ التحقق من الصلاحيات ============
def is_master_admin(user_id):
    """التحقق من أن المستخدم مشرف أساسي"""
    return int(user_id) in MASTER_ADMINS

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من أن المستخدم مشرف أو مالك في المجموعة"""
    if not update.effective_chat:
        return False
    if update.effective_chat.type == "private":
        return True
    
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]:
            return True
        if is_group_admin_user(chat_id, user_id):
            return True
        return False
    except Exception as e:
        logging.error(f"خطأ في التحقق من صلاحيات المشرف: {e}")
        return False

# ============ دالة /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title or "خاص"
    user_id = update.effective_user.id
    
    # التحقق من الاشتراك في القناة (للمستخدمين العاديين في الخاص)
    if chat_type == "private" and not is_master_admin(user_id):
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
    
    if chat_type != "private":
        save_group_info(chat_id, chat_name)
    
    rules_count = len(RULES)
    
    # أزرار اللعب للجميع
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")],
    ]
    
    # أزرار الإعدادات فقط للمشرفين
    if chat_type == "private":
        if is_master_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="master_settings")])
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")])
    else:
        if await is_group_admin(update, context):
            keyboard.append([InlineKeyboardButton("⚙️ إعدادات المجموعة", callback_data="group_settings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if chat_type == "private":
        msg = f"🎲 *مرحباً بك في لعبة النرد!* 🎲\n\nاضغط على الزر لرمي النرد والحصول على حكمك.\n\n📜 عدد الأحكام المتاحة: *{rules_count}* حكم\n💡 الأحكام تظهر فقط عند اللعب!"
    else:
        msg = f"🎲 *لعبة النرد في المجموعة!* 🎲\n\nاضغط على الزر لرمي النرد والحصول على حكمك.\n\n📜 عدد الأحكام المتاحة: *{rules_count}* حكم\n💡 الأحكام تظهر فقط عند اللعب!\n\n👥 يمكن للجميع اللعب!"
    
    await update.message.reply_text(
        msg,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ عرض النرد المتحرك ============
async def show_dice_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    chat_type = update.effective_chat.type
    
    # التحقق من الاشتراك في القناة (للمستخدمين العاديين في الخاص)
    if chat_type == "private" and not is_master_admin(user_id):
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
    
    if chat_type != "private":
        if not is_group_enabled(chat_id):
            await query.edit_message_text("⛔ البوت معطل في هذه المجموعة!\nتواصل مع المشرف لتفعيله.")
            return
    
    # تأثير الحركة
    for _ in range(3):
        temp_dice = random.choice(list(DICE_EMOJIS.values()))
        await query.edit_message_text(
            f"🎲 *جاري رمي النرد...* 🎲\n\n"
            f"{temp_dice} {random.choice(list(DICE_EMOJIS.values()))} {random.choice(list(DICE_EMOJIS.values()))}",
            parse_mode='Markdown'
        )
        await asyncio.sleep(0.2)
    
    # رقم النرد
    dice_number = random.randint(1, 6)
    dice_emoji = DICE_EMOJIS[str(dice_number)]
    
    # اختيار حكم عشوائي
    all_rules_keys = list(RULES.keys())
    rule_key = random.choice(all_rules_keys)
    rule = RULES[rule_key]
    
    # اسم المستخدم
    user_name = query.from_user.first_name or "لاعب"
    if query.from_user.username:
        user_name = f"@{query.from_user.username}"
    
    message = (
        f"🎲 *رقم النرد: {dice_number}* {dice_emoji}\n\n"
        f"📜 *الحكم:* {rule}\n\n"
        f"👤 اللاعب: {user_name}\n"
        f"💫 حظ سعيد!"
    )
    
    # أزرار اللعب للجميع
    keyboard = [
        [InlineKeyboardButton("🎲 أعد الرمي 🎲", callback_data="roll")],
    ]
    
    # أزرار الإعدادات فقط للمشرفين
    if chat_type == "private":
        if is_master_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="master_settings")])
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")])
    else:
        if await is_group_admin(update, context):
            keyboard.append([InlineKeyboardButton("⚙️ إعدادات المجموعة", callback_data="group_settings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ رمي النرد ============
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_dice_animation(update, context)

# ============ العودة للقائمة الرئيسية ============
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_type = update.effective_chat.type
    user_id = query.from_user.id
    rules_count = len(RULES)
    
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")],
    ]
    
    if chat_type == "private":
        if is_master_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="master_settings")])
            keyboard.append([InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")])
    else:
        if await is_group_admin(update, context):
            keyboard.append([InlineKeyboardButton("⚙️ إعدادات المجموعة", callback_data="group_settings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if chat_type == "private":
        msg = f"🎲 *مرحباً بك في لعبة النرد!* 🎲\n\nاضغط على الزر لرمي النرد والحصول على حكمك.\n\n📜 عدد الأحكام المتاحة: *{rules_count}* حكم"
    else:
        msg = f"🎲 *لعبة النرد في المجموعة!* 🎲\n\nاضغط على الزر لرمي النرد والحصول على حكمك.\n\n📜 عدد الأحكام المتاحة: *{rules_count}* حكم"
    
    await query.edit_message_text(
        msg,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ إعدادات المجموعة ============
async def group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = str(update.effective_chat.id)
    chat_name = update.effective_chat.title or "المجموعة"
    
    if not await is_group_admin(update, context):
        await query.edit_message_text(
            "⛔ عذراً، هذا الأمر للمشرفين فقط!\n\n"
            "💡 يمكنك فقط استخدام زر '🎲 ارمي النرد' للعب.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")]
            ])
        )
        return
    
    enabled = is_group_enabled(chat_id)
    status = "🟢 مفعل" if enabled else "🔴 معطل"
    is_admin = is_master_admin(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🔄 تفعيل/تعطيل البوت", callback_data=f"toggle_group_{chat_id}")],
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("➕ إضافة مشرف للمجموعة", callback_data=f"add_group_admin_{chat_id}")])
        keyboard.append([InlineKeyboardButton("🗑️ حذف مشرف من المجموعة", callback_data=f"remove_group_admin_{chat_id}")])
    
    keyboard.append([InlineKeyboardButton("📋 عرض المشرفين", callback_data=f"view_group_admins_{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admins = get_group_admins(chat_id)
    admin_list = "\n".join([f"• {admin}" for admin in admins]) if admins else "لا يوجد مشرفين معينين"
    
    await query.edit_message_text(
        f"⚙️ *إعدادات المجموعة*\n\n"
        f"📌 *المجموعة:* {chat_name}\n"
        f"🆔 المعرف: {chat_id}\n"
        f"📌 حالة البوت: {status}\n\n"
        f"👑 *مشرفي البوت في المجموعة:*\n{admin_list}\n\n"
        f"اختر الإجراء الذي تريده:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ تبديل حالة المجموعة ============
async def toggle_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("toggle_group_"):
        return
    
    chat_id = data.replace("toggle_group_", "")
    
    if not await is_group_admin(update, context):
        await query.edit_message_text(
            "⛔ عذراً، هذا الأمر للمشرفين فقط!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة", callback_data="group_settings")]
            ])
        )
        return
    
    current = is_group_enabled(chat_id)
    new_status = not current
    set_group_enabled(chat_id, new_status)
    
    status = "🟢 مفعل" if new_status else "🔴 معطل"
    
    await query.edit_message_text(
        f"✅ *تم تحديث حالة البوت!*\n\n"
        f"📌 الحالة الجديدة: {status}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="group_settings")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
        ]),
        parse_mode='Markdown'
    )

# ============ عرض مشرفي المجموعة ============
async def view_group_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("view_group_admins_"):
        return
    
    chat_id = data.replace("view_group_admins_", "")
    
    admins = get_group_admins(chat_id)
    admin_list = "\n".join([f"• {admin}" for admin in admins]) if admins else "لا يوجد مشرفين معينين"
    
    await query.edit_message_text(
        f"👑 *مشرفي البوت في المجموعة*\n\n{admin_list}\n\n"
        f"📌 *ملاحظة:* مالك المجموعة ومشرفي التلغرام لديهم صلاحيات تلقائياً.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="group_settings")]
        ]),
        parse_mode='Markdown'
    )

# ============ إضافة مشرف للمجموعة ============
async def add_group_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ هذا الأمر للمشرفين الأساسيين فقط!")
        return
    
    data = query.data
    if not data.startswith("add_group_admin_"):
        return
    
    chat_id = data.replace("add_group_admin_", "")
    
    waiting_for_admin_add[str(user_id)] = chat_id
    
    await query.edit_message_text(
        "➕ *إضافة مشرف للمجموعة*\n\n"
        "أرسل معرف المستخدم (ID) الذي تريد إضافته كمشرف.\n\n"
        "📌 *كيفية الحصول على ID:*\n"
        "1️⃣ أضف البوت @userinfobot\n"
        "2️⃣ أرسل /start ثم أعد توجيه رسالة المستخدم\n"
        "3️⃣ ستحصل على المعرف (ID)\n\n"
        "🔙 لإلغاء العملية أرسل /cancel",
        parse_mode='Markdown'
    )

# ============ حذف مشرف من المجموعة ============
async def remove_group_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ هذا الأمر للمشرفين الأساسيين فقط!")
        return
    
    data = query.data
    if not data.startswith("remove_group_admin_"):
        return
    
    chat_id = data.replace("remove_group_admin_", "")
    
    admins = get_group_admins(chat_id)
    if not admins:
        await query.edit_message_text(
            "📋 لا يوجد مشرفين لحذفهم!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="group_settings")]
            ])
        )
        return
    
    keyboard = []
    for admin in admins:
        keyboard.append([InlineKeyboardButton(f"🗑️ {admin}", callback_data=f"remove_admin_{chat_id}_{admin}")])
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="group_settings")])
    
    await query.edit_message_text(
        "🗑️ *اختر المشرف الذي تريد حذفه:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ تنفيذ حذف مشرف ============
async def remove_admin_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    data = query.data
    if not data.startswith("remove_admin_"):
        return
    
    parts = data.split("_")
    if len(parts) < 3:
        return
    
    chat_id = parts[2]
    admin_id = parts[3] if len(parts) > 3 else None
    
    if not admin_id:
        await query.edit_message_text("❌ حدث خطأ!")
        return
    
    remove_group_admin(chat_id, admin_id)
    
    await query.edit_message_text(
        f"✅ تم حذف المشرف {admin_id} بنجاح!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="group_settings")]
        ])
    )

# ============ معالجة إضافة مشرف ============
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id not in waiting_for_admin_add:
        return
    
    chat_id = waiting_for_admin_add[user_id]
    admin_id = update.message.text.strip()
    
    if not admin_id.isdigit():
        await update.message.reply_text("❌ الرجاء إدخال معرف صحيح (أرقام فقط)!")
        return
    
    add_group_admin(chat_id, admin_id)
    
    del waiting_for_admin_add[user_id]
    
    await update.message.reply_text(
        f"✅ *تم إضافة المشرف بنجاح!*\n\n"
        f"🆔 المعرف: {admin_id}\n"
        f"📌 المجموعة: {chat_id}\n\n"
        f"يمكنه الآن إدارة إعدادات البوت في هذه المجموعة.",
        parse_mode='Markdown'
    )

# ============ الإعدادات ============
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ هذا الأمر للمشرفين الأساسيين فقط!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة حكم جديد", callback_data="add_rule")],
        [InlineKeyboardButton("🗑️ حذف حكم", callback_data="delete_rule")],
        [InlineKeyboardButton("📋 عرض جميع الأحكام", callback_data="view_rules")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rules_count = len(RULES)
    
    await query.edit_message_text(
        f"⚙️ *لوحة التحكم*\n\n"
        f"📜 عدد الأحكام: *{rules_count}*\n\n"
        f"اختر الإجراء الذي تريده:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ الإعدادات المتقدمة ============
async def master_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ هذا الأمر للمشرفين الأساسيين فقط!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة حكم جديد", callback_data="add_rule")],
        [InlineKeyboardButton("🗑️ حذف حكم", callback_data="delete_rule")],
        [InlineKeyboardButton("📋 عرض جميع الأحكام", callback_data="view_rules")],
        [InlineKeyboardButton("📤 تصدير الأحكام (TXT)", callback_data="export_rules")],
        [InlineKeyboardButton("📥 استيراد أحكام (TXT)", callback_data="import_rules")],
        [InlineKeyboardButton("🗑️ حذف جميع الأحكام", callback_data="delete_all_rules")],
        [InlineKeyboardButton("📥 إضافة أحكام افتراضية", callback_data="add_default_rules")],
        [InlineKeyboardButton("📊 عرض إحصائيات البوت", callback_data="bot_stats")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rules_count = len(RULES)
    
    await query.edit_message_text(
        f"⚙️ *لوحة التحكم المتقدمة*\n\n"
        f"📜 عدد الأحكام: *{rules_count}*\n"
        f"👑 صلاحياتك: *مشرف أساسي*\n\n"
        f"اختر الإجراء الذي تريده:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ إحصائيات البوت ============
async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_master_admin(user_id):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM rules")
    rules_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM groups")
    groups_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM groups WHERE enabled = 1")
    active_groups = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM group_admins")
    group_admins = c.fetchone()[0]
    
    conn.close()
    
    await query.edit_message_text(
        f"📊 *إحصائيات البوت*\n\n"
        f"📜 عدد الأحكام: *{rules_count}*\n"
        f"👥 عدد المجموعات: *{groups_count}*\n"
        f"🟢 مجموعات مفعلة: *{active_groups}*\n"
        f"👑 مشرفي المجموعات: *{group_admins}*\n\n"
        f"🤖 البوت يعمل بكفاءة!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للإعدادات المتقدمة", callback_data="master_settings")]
        ]),
        parse_mode='Markdown'
    )

# ============ تصدير الأحكام ============
async def export_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    if not RULES:
        await query.edit_message_text("📋 لا توجد أحكام لتصديرها!")
        return
    
    content = "📜 قائمة الأحكام\n"
    content += "=" * 40 + "\n\n"
    
    for num, text in sorted(RULES.items(), key=lambda x: int(x[0])):
        content += f"{num}: {text}\n"
    
    content += f"\nإجمالي الأحكام: {len(RULES)}"
    
    file = io.BytesIO(content.encode('utf-8'))
    file.name = f"rules_export_{len(RULES)}.txt"
    
    await query.edit_message_text("📤 جاري تصدير الأحكام...")
    
    await context.bot.send_document(
        chat_id=user_id,
        document=file,
        filename=f"rules_export_{len(RULES)}.txt",
        caption=f"✅ تم تصدير {len(RULES)} حكم بنجاح!"
    )
    
    await query.delete_message()

# ============ استيراد الأحكام ============
async def import_rules_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    waiting_for_import[user_id] = True
    
    await query.edit_message_text(
        "📥 *استيراد الأحكام من ملف TXT*\n\n"
        "أرسل ملف TXT يحتوي على الأحكام.\n"
        "صيغة الملف:\n"
        "1: نص الحكم الأول\n"
        "2: نص الحكم الثاني\n"
        "3: نص الحكم الثالث\n\n"
        "🔙 لإلغاء العملية أرسل /cancel",
        parse_mode='Markdown'
    )

# ============ معالجة استيراد الملف ============
async def handle_file_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if not is_master_admin(int(user_id)):
        return
    
    if user_id not in waiting_for_import:
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ الرجاء إرسال ملف TXT!")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ الرجاء إرسال ملف بصيغة TXT فقط!")
        return
    
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    
    try:
        text = file_content.decode('utf-8')
        lines = text.strip().split('\n')
        
        new_rules = {}
        errors = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if ':' in line:
                parts = line.split(':', 1)
                num = parts[0].strip()
                rule_text = parts[1].strip()
                
                if num.isdigit() and rule_text:
                    new_rules[num] = rule_text
                else:
                    errors.append(line)
            else:
                errors.append(line)
        
        if not new_rules:
            await update.message.reply_text(
                "❌ لم يتم العثور على أحكام صالحة!\n"
                "تأكد من الصيغة: رقم: نص الحكم"
            )
            del waiting_for_import[user_id]
            return
        
        added = 0
        for num, rule_text in new_rules.items():
            if num not in RULES:
                RULES[num] = rule_text
                added += 1
        
        save_rules(RULES)
        
        result_msg = f"✅ *تم استيراد الأحكام بنجاح!*\n\n"
        result_msg += f"📥 تم إضافة *{added}* حكم جديد\n"
        result_msg += f"📊 إجمالي الأحكام: *{len(RULES)}*\n\n"
        
        if errors:
            result_msg += f"⚠️ *تم تخطي {len(errors)} سطر غير صالح*\n"
        
        await update.message.reply_text(result_msg, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء قراءة الملف: {str(e)}")
    
    del waiting_for_import[user_id]

# ============ حذف جميع الأحكام ============
async def delete_all_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    if not RULES:
        await query.edit_message_text("📋 لا توجد أحكام لحذفها!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="confirm_delete_all")],
        [InlineKeyboardButton("❌ لا، إلغاء", callback_data="master_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ *تحذير!*\n\n"
        f"أنت على وشك حذف جميع الأحكام (*{len(RULES)}* حكم)\n\n"
        f"هل أنت متأكد؟",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ تأكيد حذف الكل ============
async def confirm_delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    global RULES
    RULES = {}
    save_rules(RULES)
    
    await query.edit_message_text(
        "🗑️ *تم حذف جميع الأحكام بنجاح!*\n\n"
        "📊 إجمالي الأحكام: 0\n\n"
        "يمكنك إضافة أحكام جديدة من خلال الإعدادات.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للإعدادات المتقدمة", callback_data="master_settings")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
        ]),
        parse_mode='Markdown'
    )

# ============ إضافة أحكام افتراضية ============
async def add_default_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    default_rules = {
        "1": "رئيج بيه",
        "2": "😂 اضحك بصوت عالٍ لمدة 10 ثوانٍ",
        "3": "💃 ارقص لمدة 30 ثانية",
        "4": "📖 احكي نكتة مضحكة",
        "5": "🤝 صافح أقرب شخص إليك بحرارة",
        "6": "🌶️ اشرب ماء حار أو تناول شيئاً حاراً"
    }
    
    added = 0
    for num, text in default_rules.items():
        if num not in RULES:
            RULES[num] = text
            added += 1
    
    if added > 0:
        save_rules(RULES)
        await query.edit_message_text(
            f"✅ *تم إضافة {added} حكم افتراضي!*\n\n"
            f"📊 إجمالي الأحكام: *{len(RULES)}*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للإعدادات المتقدمة", callback_data="master_settings")]
            ]),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "ℹ️ الأحكام الافتراضية موجودة مسبقاً!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للإعدادات المتقدمة", callback_data="master_settings")]
            ])
        )

# ============ إضافة حكم جديد ============
async def add_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    waiting_for_rule[user_id] = "waiting_for_rule_number"
    
    await query.edit_message_text(
        "✏️ *إضافة حكم جديد*\n\n"
        "أرسل رقم الحكم أولاً (مثال: 7)\n"
        "ثم سأطلب منك كتابة الحكم.\n\n"
        "🔙 لإلغاء العملية أرسل /cancel",
        parse_mode='Markdown'
    )

# ============ حذف حكم ============
async def delete_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if not is_master_admin(int(user_id)):
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    if not RULES:
        await query.edit_message_text("📋 لا توجد أحكام لحذفها!")
        return
    
    keyboard = []
    for num, rule in sorted(RULES.items(), key=lambda x: int(x[0])):
        keyboard.append([InlineKeyboardButton(
            f"🗑️ {num}: {rule[:25]}...", 
            callback_data=f"del_{num}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑️ *اختر الحكم الذي تريد حذفه:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ عرض الأحكام ============
async def view_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not RULES:
        await query.edit_message_text("📋 لا توجد أحكام حالياً!")
        return
    
    rules_text = "\n".join([f"• {k}: {v}" for k, v in sorted(RULES.items(), key=lambda x: int(x[0]))])
    
    if len(rules_text) > 4000:
        rules_text = rules_text[:4000] + "\n\n... (تم اختصار القائمة)"
    
    await query.edit_message_text(
        f"📋 *قائمة الأحكام:*\n\n{rules_text}\n\n📊 الإجمالي: {len(RULES)} حكم",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
        ]),
        parse_mode='Markdown'
    )

# ============ معالجة الأزرار ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    chat_type = update.effective_chat.type
    
    # ======== زر التحقق من الاشتراك ========
    if data == "check_subscription":
        await check_subscription_button(update, context)
        return
    
    # ======== أزرار اللعب للجميع ========
    if data == "roll":
        await roll_dice(update, context)
        return
    
    if data == "back_to_main":
        await back_to_main(update, context)
        return
    
    # ======== التحقق من الصلاحيات ========
    if chat_type == "private":
        if not is_master_admin(user_id):
            await query.edit_message_text(
                "⛔ عذراً، هذا الأمر للمشرفين الأساسيين فقط!\n\n"
                "💡 يمكنك فقط استخدام زر '🎲 ارمي النرد' للعب.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")]
                ])
            )
            return
    
    if chat_type != "private":
        if not await is_group_admin(update, context):
            await query.edit_message_text(
                "⛔ عذراً، هذا الأمر للمشرفين فقط!\n\n"
                "💡 يمكنك فقط استخدام زر '🎲 ارمي النرد' للعب.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")]
                ])
            )
            return
    
    # ======== باقي الأزرار ========
    if data == "settings":
        await settings(update, context)
        return
    
    if data == "master_settings":
        await master_settings(update, context)
        return
    
    if data == "bot_stats":
        await bot_stats(update, context)
        return
    
    if data == "add_rule":
        await add_rule(update, context)
        return
    
    if data == "delete_rule":
        await delete_rule(update, context)
        return
    
    if data == "view_rules":
        await view_rules(update, context)
        return
    
    if data == "export_rules":
        await export_rules(update, context)
        return
    
    if data == "import_rules":
        await import_rules_start(update, context)
        return
    
    if data == "delete_all_rules":
        await delete_all_rules(update, context)
        return
    
    if data == "add_default_rules":
        await add_default_rules(update, context)
        return
    
    if data == "confirm_delete_all":
        await confirm_delete_all(update, context)
        return
    
    if data == "group_settings":
        await group_settings(update, context)
        return
    
    if data.startswith("toggle_group_"):
        await toggle_group(update, context)
        return
    
    if data.startswith("view_group_admins_"):
        await view_group_admins(update, context)
        return
    
    if data.startswith("add_group_admin_"):
        await add_group_admin_start(update, context)
        return
    
    if data.startswith("remove_group_admin_"):
        if data.startswith("remove_admin_"):
            await remove_admin_execute(update, context)
            return
        await remove_group_admin_start(update, context)
        return
    
    if data.startswith("del_"):
        rule_num = data.replace("del_", "")
        if rule_num in RULES:
            del RULES[rule_num]
            save_rules(RULES)
            await query.edit_message_text(
                f"✅ تم حذف الحكم رقم {rule_num} بنجاح!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ])
            )
        else:
            await query.edit_message_text("❌ الحكم غير موجود!")
        return

# ============ معالجة الرسائل ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if update.message.document:
        await handle_file_import(update, context)
        return
    
    if user_id in waiting_for_admin_add:
        await handle_add_admin(update, context)
        return
    
    if not is_master_admin(int(user_id)):
        return
    
    if user_id not in waiting_for_rule:
        return
    
    state = waiting_for_rule[user_id]
    text = update.message.text.strip()
    
    if state == "waiting_for_rule_number":
        if not text.isdigit():
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
            return
        
        if text in RULES:
            await update.message.reply_text(f"❌ الحكم رقم {text} موجود مسبقاً!")
            return
        
        context.user_data['rule_number'] = text
        waiting_for_rule[user_id] = "waiting_for_rule_text"
        
        await update.message.reply_text(
            f"✅ تم استلام الرقم *{text}*\n\n✏️ الآن أرسل نص الحكم:",
            parse_mode='Markdown'
        )
    
    elif state == "waiting_for_rule_text":
        rule_number = context.user_data.get('rule_number')
        
        if rule_number in RULES:
            await update.message.reply_text(f"❌ الحكم رقم {rule_number} موجود مسبقاً!")
            del waiting_for_rule[user_id]
            return
        
        RULES[rule_number] = text
        save_rules(RULES)
        
        del waiting_for_rule[user_id]
        context.user_data.clear()
        
        await update.message.reply_text(
            f"✅ *تم إضافة الحكم بنجاح!*\n\n"
            f"📌 الرقم: {rule_number}\n"
            f"📜 الحكم: {text}\n\n"
            f"📊 إجمالي الأحكام: *{len(RULES)}*",
            parse_mode='Markdown'
        )

# ============ أوامر البوت ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id in waiting_for_rule:
        del waiting_for_rule[user_id]
        context.user_data.clear()
        await update.message.reply_text("✅ تم إلغاء إضافة الحكم!")
        return
    
    if user_id in waiting_for_import:
        del waiting_for_import[user_id]
        await update.message.reply_text("✅ تم إلغاء استيراد الملف!")
        return
    
    if user_id in waiting_for_admin_add:
        del waiting_for_admin_add[user_id]
        await update.message.reply_text("✅ تم إلغاء إضافة المشرف!")
        return
    
    await update.message.reply_text("❌ لا توجد عملية نشطة!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_count = len(RULES)
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    
    msg = (
        f"🎲 *لعبة النرد*\n\n"
        f"📌 *الأوامر:*\n"
        f"/start - بدء اللعبة\n"
        f"/help - عرض المساعدة\n"
        f"/cancel - إلغاء العملية\n\n"
        f"🎮 *طريقة اللعب:*\n"
        f"1️⃣ اضغط على 'ارمي النرد'\n"
        f"2️⃣ شاهد النرد يتحرك!\n"
        f"3️⃣ سيظهر لك رقم (1-6) وحكم عشوائي من {rules_count} حكم\n"
        f"4️⃣ استمتع باللعب!\n\n"
    )
    
    if chat_type == "private":
        if is_master_admin(user_id):
            msg += (
                f"👑 *أنت مشرف أساسي*\n"
                f"• لديك صلاحية كاملة على البوت\n"
                f"• يمكنك إدارة الأحكام والمجموعات\n\n"
            )
    else:
        if await is_group_admin(update, context):
            msg += (
                f"⚙️ *أنت مشرف في هذه المجموعة*\n"
                f"• يمكنك تفعيل/تعطيل البوت\n"
                f"• استخدم زر 'إعدادات المجموعة'\n\n"
            )
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ معالج الأخطاء ============
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"خطأ: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ حدث خطأ! يرجى المحاولة مرة أخرى.")
    except:
        pass

# ============ الدالة الرئيسية ============
def main():
    TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: لم يتم العثور على توكن البوت!")
        print("الرجاء إضافة متغير بيئي باسم BOT_TOKEN")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    application.add_error_handler(error_handler)
    
    print("🤖 البوت يعمل...")
    print(f"📜 عدد الأحكام المحملة: {len(RULES)}")
    print(f"👑 عدد المشرفين الأساسيين: {len(MASTER_ADMINS)}")
    print(f"📢 القناة الإجبارية: {FORCED_CHANNEL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
