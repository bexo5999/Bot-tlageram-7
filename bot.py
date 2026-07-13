import random
import logging
import os
import json
import sqlite3
import asyncio
import io
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

# ============ تحميل البيانات ============
init_db()
RULES = load_rules()

waiting_for_rule = {}
waiting_for_import = {}
ADMIN_IDS = [8798182716, 8916460129]

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
    
    rules_count = len(RULES)
    
    await update.message.reply_text(
        f"🎲 *مرحباً بك في لعبة النرد!* 🎲\n\n"
        f"اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
        f"📜 عدد الأحكام المتاحة: *{rules_count}* حكم\n"
        f"💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ عرض النرد المتحرك ============
async def show_dice_animation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # تأثير الحركة (تغيير الإيموجي بسرعة)
    for _ in range(3):
        temp_dice = random.choice(list(DICE_EMOJIS.values()))
        await query.edit_message_text(
            f"🎲 *جاري رمي النرد...* 🎲\n\n"
            f"{temp_dice} {random.choice(list(DICE_EMOJIS.values()))} {random.choice(list(DICE_EMOJIS.values()))}",
            parse_mode='Markdown'
        )
        await asyncio.sleep(0.2)
    
    # رقم النرد (من 1 إلى 6 فقط للعرض)
    dice_number = random.randint(1, 6)
    dice_emoji = DICE_EMOJIS[str(dice_number)]
    
    # 🔥 الأهم: اختيار حكم عشوائي من جميع الأحكام (بغض النظر عن الرقم)
    all_rules_keys = list(RULES.keys())  # كل الأرقام (1 إلى 1000)
    rule_key = random.choice(all_rules_keys)  # اختيار رقم عشوائي
    rule = RULES[rule_key]  # الحكم
    
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

# ============ رمي النرد ============
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    rules_count = len(RULES)
    
    await query.edit_message_text(
        f"🎲 *مرحباً بك في لعبة النرد!* 🎲\n\n"
        f"اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
        f"📜 عدد الأحكام المتاحة: *{rules_count}* حكم\n"
        f"💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ تصدير الأحكام ============
async def export_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if int(user_id) not in ADMIN_IDS:
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
    
    if int(user_id) not in ADMIN_IDS:
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
    
    if int(user_id) not in ADMIN_IDS:
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
    
    if int(user_id) not in ADMIN_IDS:
        await query.edit_message_text("⛔ غير مصرح!")
        return
    
    if not RULES:
        await query.edit_message_text("📋 لا توجد أحكام لحذفها!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data="confirm_delete_all")],
        [InlineKeyboardButton("❌ لا، إلغاء", callback_data="settings")]
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
    
    if int(user_id) not in ADMIN_IDS:
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
            [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
        ]),
        parse_mode='Markdown'
    )

# ============ إضافة أحكام افتراضية ============
async def add_default_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if int(user_id) not in ADMIN_IDS:
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
                [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="settings")]
            ]),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "ℹ️ الأحكام الافتراضية موجودة مسبقاً!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للإعدادات", callback_data="settings")]
            ])
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
    
    if data == "confirm_delete_all":
        await confirm_delete_all(update, context)
        return
    
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
            [InlineKeyboardButton("📤 تصدير الأحكام (TXT)", callback_data="export_rules")],
            [InlineKeyboardButton("📥 استيراد أحكام (TXT)", callback_data="import_rules")],
            [InlineKeyboardButton("🗑️ حذف جميع الأحكام", callback_data="delete_all_rules")],
            [InlineKeyboardButton("📥 إضافة أحكام افتراضية", callback_data="add_default_rules")],
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

# ============ معالجة الرسائل ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if update.message.document:
        await handle_file_import(update, context)
        return
    
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
    
    await update.message.reply_text("❌ لا توجد عملية نشطة!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_count = len(RULES)
    
    await update.message.reply_text(
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
        f"⚙️ *للمشرفين:*\n"
        f"• استخدم 'الإعدادات' لإدارة الأحكام\n"
        f"• يمكنك إضافة أو حذف الأحكام بسهولة\n"
        f"• تصدير الأحكام كملف TXT\n"
        f"• استيراد أحكام من ملف TXT\n"
        f"• حذف جميع الأحكام دفعة واحدة",
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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    application.add_error_handler(error_handler)
    
    print("🤖 البوت يعمل...")
    print(f"📜 عدد الأحكام المحملة: {len(RULES)}")
    print(f"👑 عدد المشرفين: {len(ADMIN_IDS)}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
