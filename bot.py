import random
import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ملف لحفظ الأحكام
RULES_FILE = "rules.json"

# تحميل الأحكام من الملف
def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
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

# حفظ الأحكام في الملف
def save_rules(rules):
    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

# تحميل الأحكام
RULES = load_rules()

# متغير لتخزين حالة انتظار إضافة حكم
waiting_for_rule = {}

# معرف المشرف
# معرف المشرفين (يمكنك إضافة أكثر من مشرف)
ADMIN_IDS = ["8798182716", "8916460129"]  # ضع معرفات المشرفين هنا  # ضع معرفات المشرفين هنا

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎲 *مرحباً بك في لعبة النرد!*\n\n"
        f"اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
        f"💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# معالجة ضغط الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data == "roll":
        # رمي النرد
        dice_number = random.choice(list(RULES.keys()))
        rule = RULES[dice_number]
        
        message = f"🎲 رقم النرد: *{dice_number}*\n\n📜 الحكم: {rule}"
        
        keyboard = [
            [InlineKeyboardButton("🎲 أعد الرمي", callback_data="roll")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "settings":
        if user_id not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ عذراً، هذا الأمر للمشرفين فقط!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 العودة", callback_data="back")]
                ])
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة حكم جديد", callback_data="add_rule")],
            [InlineKeyboardButton("🗑️ حذف حكم", callback_data="delete_rule")],
            [InlineKeyboardButton("📋 عرض جميع الأحكام", callback_data="view_rules")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *لوحة التحكم*\n\nاختر الإجراء الذي تريده:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "add_rule":
        if user_id not in ADMIN_IDS:
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
    
    elif data == "delete_rule":
        if user_id not in ADMIN_IDS:
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
    
    elif data.startswith("del_"):
        if user_id not in ADMIN_IDS:
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
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back")]
                ])
            )
        else:
            await query.edit_message_text("❌ الحكم غير موجود!")
    
    elif data == "view_rules":
        if not RULES:
            await query.edit_message_text("📋 لا توجد أحكام حالياً!")
            return
        
        rules_text = "\n".join([f"• {k}: {v}" for k, v in sorted(RULES.items(), key=lambda x: int(x[0]))])
        await query.edit_message_text(
            f"📋 *قائمة الأحكام:*\n\n{rules_text}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back")]
            ])
        )
    
    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll")],
            [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎲 *مرحباً بك في لعبة النرد!*\n\n"
            f"اضغط على الزر لرمي النرد والحصول على حكمك.\n\n"
            f"💡 الأحكام تظهر فقط عند اللعب!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# معالجة الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if user_id not in ADMIN_IDS:
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

# أمر /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in waiting_for_rule:
        del waiting_for_rule[user_id]
        context.user_data.clear()
        await update.message.reply_text("✅ تم إلغاء العملية!")
    else:
        await update.message.reply_text("❌ لا توجد عملية نشطة!")

# أمر /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎲 *كيفية اللعب:*\n\n"
        f"1️⃣ اضغط على زر '🎲 ارمي النرد'\n"
        f"2️⃣ سيظهر لك رقم وحكم عشوائي\n"
        f"3️⃣ استمتع باللعب!\n\n"
        f"⚙️ *للمشرفين:*\n"
        f"• استخدم زر 'الإعدادات' لإدارة الأحكام\n"
        f"• يمكنك إضافة أو حذف الأحكام بسهولة\n\n"
        f"📌 *الأوامر المتاحة:*\n"
        f"/start - بدء اللعبة\n"
        f"/help - عرض المساعدة\n"
        f"/cancel - إلغاء العملية الجارية",
        parse_mode='Markdown'
    )

# الدالة الرئيسية
def main():
    TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: لم يتم العثور على توكن البوت!")
        print("الرجاء إضافة متغير بيئي باسم BOT_TOKEN")
        return
    
    # إنشاء التطبيق بالطريقة الحديثة
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # بدء البوت
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
