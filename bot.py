import random
import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# تفعيل التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
ADMIN_IDS = ["8798182716"]  # ضع معرفات المشرفين هنا

# أمر /start
def start(update, context):
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rules_text = "\n".join([f"{k}: {v}" for k, v in RULES.items()])
    
    update.message.reply_text(
        f"🎲 مرحباً بك في لعبة النرد!\n"
        f"اضغط على الزر لرمي النرد ومعرفة الحكم.\n\n"
        f"📜 الأحكام الحالية:\n{rules_text}",
        reply_markup=reply_markup
    )

# معالجة ضغط الأزرار
def button_handler(update, context):
    query = update.callback_query
    query.answer()
    
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
        
        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "settings":
        if user_id not in ADMIN_IDS:
            query.edit_message_text(
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
        
        query.edit_message_text(
            "⚙️ *لوحة التحكم*\n\nاختر الإجراء الذي تريده:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "add_rule":
        if user_id not in ADMIN_IDS:
            query.edit_message_text("⛔ غير مصرح!")
            return
        
        waiting_for_rule[user_id] = "waiting_for_rule_number"
        
        query.edit_message_text(
            "✏️ *إضافة حكم جديد*\n\n"
            "أرسل رقم الحكم أولاً (مثال: 7)\n"
            "ثم سأطلب منك كتابة الحكم.\n\n"
            "🔙 لإلغاء العملية أرسل /cancel",
            parse_mode='Markdown'
        )
    
    elif data == "delete_rule":
        if user_id not in ADMIN_IDS:
            query.edit_message_text("⛔ غير مصرح!")
            return
        
        keyboard = []
        for num, rule in RULES.items():
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {num}: {rule[:20]}...", 
                callback_data=f"del_{num}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🗑️ *اختر الحكم الذي تريد حذفه:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data.startswith("del_"):
        if user_id not in ADMIN_IDS:
            query.edit_message_text("⛔ غير مصرح!")
            return
        
        rule_num = data.replace("del_", "")
        if rule_num in RULES:
            del RULES[rule_num]
            save_rules(RULES)
            query.edit_message_text(
                f"✅ تم حذف الحكم رقم {rule_num} بنجاح!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back")]
                ])
            )
        else:
            query.edit_message_text("❌ الحكم غير موجود!")
    
    elif data == "view_rules":
        if not RULES:
            query.edit_message_text("📋 لا توجد أحكام حالياً!")
            return
        
        rules_text = "\n".join([f"• {k}: {v}" for k, v in sorted(RULES.items())])
        query.edit_message_text(
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
        
        rules_text = "\n".join([f"{k}: {v}" for k, v in RULES.items()])
        
        query.edit_message_text(
            f"🎲 مرحباً بك في لعبة النرد!\n"
            f"اضغط على الزر لرمي النرد ومعرفة الحكم.\n\n"
            f"📜 الأحكام الحالية:\n{rules_text}",
            reply_markup=reply_markup
        )

# معالجة الرسائل النصية
def handle_message(update, context):
    user_id = str(update.message.from_user.id)
    
    if user_id not in ADMIN_IDS:
        return
    
    if user_id not in waiting_for_rule:
        return
    
    state = waiting_for_rule[user_id]
    text = update.message.text.strip()
    
    if state == "waiting_for_rule_number":
        if not text.isdigit():
            update.message.reply_text("❌ الرجاء إدخال رقم صحيح!")
            return
        
        context.user_data['rule_number'] = text
        waiting_for_rule[user_id] = "waiting_for_rule_text"
        
        update.message.reply_text(
            f"✅ تم استلام الرقم *{text}*\n\n✏️ الآن أرسل نص الحكم:",
            parse_mode='Markdown'
        )
    
    elif state == "waiting_for_rule_text":
        rule_number = context.user_data.get('rule_number')
        
        if rule_number in RULES:
            update.message.reply_text(
                f"❌ الحكم رقم {rule_number} موجود مسبقاً!\nالحكم الحالي: {RULES[rule_number]}"
            )
            del waiting_for_rule[user_id]
            return
        
        RULES[rule_number] = text
        save_rules(RULES)
        
        del waiting_for_rule[user_id]
        context.user_data.clear()
        
        update.message.reply_text(
            f"✅ *تم إضافة الحكم بنجاح!*\n\n"
            f"📌 الرقم: {rule_number}\n"
            f"📜 الحكم: {text}",
            parse_mode='Markdown'
        )

# أمر /cancel
def cancel(update, context):
    user_id = str(update.message.from_user.id)
    if user_id in waiting_for_rule:
        del waiting_for_rule[user_id]
        context.user_data.clear()
        update.message.reply_text("✅ تم إلغاء العملية!")
    else:
        update.message.reply_text("❌ لا توجد عملية نشطة!")

# أمر /help
def help_command(update, context):
    rules_text = "\n".join([f"{k}: {v}" for k, v in sorted(RULES.items())])
    update.message.reply_text(
        f"🎲 *كيفية اللعب:*\n"
        f"اضغط على زر 'ارمي النرد' وسيظهر لك رقم وحكم.\n\n"
        f"📜 *الأحكام الحالية:*\n{rules_text}",
        parse_mode='Markdown'
    )

# الدالة الرئيسية
def main():
    TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # إنشاء التطبيق بالطريقة القديمة (متوافقة)
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # إضافة المعالجات
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # بدء البوت
    print("🤖 البوت يعمل...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
