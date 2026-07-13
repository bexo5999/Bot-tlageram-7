import random
import logging
import os
import json
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ============ قاعدة البيانات (SQLite) ============
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rules
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  number TEXT UNIQUE,
                  text TEXT)''')
    conn.commit()
    conn.close()

# ============ دوال الأحكام ============
def load_rules():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT number, text FROM rules")
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
            "6": "🌶️ اشرب ماء حار أو تناول شيئاً حاراً",
            "7": "😈 قول أمنية مستحيلة",
            "8": "🎤 غني أغنية من اختيارك",
            "9": "🤪 اعمل وجه مضحك لمدة 10 ثواني",
            "10": "💪 اعمل 10 تمارين ضغط",
            "11": "📞 اتصل بصديق وقل له نكتة",
            "12": "🕺 ارقص على أنغام وهمية"
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

# ============ تحميل البيانات ============
init_db()
RULES = load_rules()

waiting_for_rule = {}
ADMIN_IDS = [8798182716, 8916460129]  # معرفات المشرفين

# ============ إيموجي النرد حسب الرقم ============
DICE_EMOJIS = {
    "1": "⚀",
    "2": "⚁",
    "3": "⚂",
    "4": "⚃",
    "5": "⚄",
    "6": "⚅"
}

# ============ دالة /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎲 *مرحباً بك في لعبة النرد!* 🎲\n\n"
        "اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
        "💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ عرض النرد المتحرك ============
async def show_dice_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إظهار النرد المتحرك"""
    query = update.callback_query
    await query.answer()
    
    # إرسال ملصق النرد المتحرك (إيموجي النرد)
    dice_message = await query.edit_message_text(
        "🎲 *جاري رمي النرد...* 🎲\n\n"
        "⚀ ⚁ ⚂ ⚃ ⚄ ⚅",
        parse_mode='Markdown'
    )
    
    # تأثير الحركة (تغيير الإيموجي بسرعة)
    for _ in range(3):
        temp_dice = random.choice(list(DICE_EMOJIS.values()))
        await query.edit_message_text(
            f"🎲 *جاري رمي النرد...* 🎲\n\n"
            f"{temp_dice} {random.choice(list(DICE_EMOJIS.values()))} {random.choice(list(DICE_EMOJIS.values()))}",
            parse_mode='Markdown'
        )
        await asyncio.sleep(0.2)
    
    # اختيار الرقم النهائي
    dice_number = random.choice(list(RULES.keys()))
    rule = RULES[dice_number]
    
    # إيموجي النرد المناسب
    dice_emoji = DICE_EMOJIS.get(dice_number, "🎲")
    
    # عرض النتيجة النهائية
    message = (
        f"🎲 *رقم النرد: {dice_number}* {dice_emoji}\n\n"
        f"📜 *الحكم:* {rule}\n\n"
        f"💫 حظ سعيد!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎲 أعد الرمي 🎲", callback_data="roll")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ رمي النرد (بدون حركة - النسخة البسيطة) ============
async def roll_dice_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نسخة بسيطة بدون حركة (احتياطي)"""
    query = update.callback_query
    await query.answer()
    
    dice_number = random.choice(list(RULES.keys()))
    rule = RULES[dice_number]
    dice_emoji = DICE_EMOJIS.get(dice_number, "🎲")
    
    message = (
        f"🎲 *رقم النرد: {dice_number}* {dice_emoji}\n\n"
        f"📜 *الحكم:* {rule}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎲 أعد الرمي 🎲", callback_data="roll")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ رمي النرد (مع حركة) ============
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الدالة الرئيسية لرمي النرد مع حركة"""
    await show_dice_animation(update, context)

# ============ العودة للقائمة الرئيسية ============
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد 🎲", callback_data="roll")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎲 *مرحباً بك في لعبة النرد!* 🎲\n\n"
        "اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
        "💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ معالجة الأزرار ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data == "roll":
        await roll_dice(update, context)
        return
    
    if data == "back_to_main":
        await back_to_main(update, context)
        return
    
    # ============ الإعدادات (للمشرفين فقط) ============
    if data == "settings":
        if int(user_id) not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ عذراً، هذا الأمر للمشرفين فقط!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
                ])
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة حكم جديد", callback_data="add_rule")],
            [InlineKeyboardButton("🗑️ حذف حكم", callback_data="delete_rule")],
            [InlineKeyboardButton("📋 عرض جميع الأحكام", callback_data="view_rules")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *لوحة التحكم*\n\nاختر الإجراء الذي تريده:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    if data == "add_rule":
        if int(user_id) not in ADMIN_IDS:
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
        return
    
    if data == "delete_rule":
        if int(user_id) not in ADMIN_IDS:
            await query.edit_message_text("⛔ غير مصرح!")
            return
        
        keyboard = []
        for num, rule in sorted(RULES.items(), key=lambda x: int(x[0])):
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {num}: {rule[:20]}...", 
                callback_data=f"del_{num}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ *اختر الحكم الذي تريد حذفه:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    if data.startswith("del_"):
        if int(user_id) not in ADMIN_IDS:
            await query.edit_message_text("⛔ غير مصرح!")
            return
        
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
    
    if data == "view_rules":
        if not RULES:
            await query.edit_message_text("📋 لا توجد أحكام حالياً!")
            return
        
        rules_text = "\n".join([f"• {k}: {v}" for k, v in sorted(RULES.items(), key=lambda x: int(x[0]))])
        await query.edit_message_text(
            f"📋 *قائمة الأحكام:*\n\n{rules_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        return

# ============ معالجة الرسائل النصية ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if int(user_id) not in ADMIN_IDS:
        return
    
    if user_id not in waiting_for_rule:
        return
    
    state = waiting_for_rule[user_id]
    text = update.message.text.strip()
    
    if state == "waiting_for_rule_number":
        if not text.isdigit():
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
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
            await update.message.reply_text(
                f"❌ الحكم رقم {rule_number} موجود مسبقاً!\nالحكم الحالي: {RULES[rule_number]}"
            )
            del waiting_for_rule[user_id]
            return
        
        RULES[rule_number] = text
        save_rules(RULES)
        
        del waiting_for_rule[user_id]
        context.user_data.clear()
        
        await update.message.reply_text(
            f"✅ *تم إضافة الحكم بنجاح!*\n\n"
            f"📌 الرقم: {rule_number}\n"
            f"📜 الحكم: {text}",
            parse_mode='Markdown'
        )

# ============ أوامر البوت ============
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in waiting_for_rule:
        del waiting_for_rule[user_id]
        context.user_data.clear()
        await update.message.reply_text("✅ تم إلغاء العملية!")
    else:
        await update.message.reply_text("❌ لا توجد عملية نشطة!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *لعبة النرد*\n\n"
        "📌 *الأوامر:*\n"
        "/start - بدء اللعبة\n"
        "/help - عرض المساعدة\n"
        "/cancel - إلغاء العملية\n\n"
        "🎮 *طريقة اللعب:*\n"
        "1️⃣ اضغط على 'ارمي النرد'\n"
        "2️⃣ شاهد النرد يتحرك!\n"
        "3️⃣ سيظهر لك رقم وحكم عشوائي\n"
        "4️⃣ استمتع باللعب!\n\n"
        "⚙️ *للمشرفين:*\n"
        "• استخدم 'الإعدادات' لإدارة الأحكام\n"
        "• يمكنك إضافة أو حذف الأحكام بسهولة",
        parse_mode='Markdown'
    )

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
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
