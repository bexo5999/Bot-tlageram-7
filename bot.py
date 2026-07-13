import random
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تفعيل التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# قائمة الأحكام حسب الرقم
RULES = {
    1: "⚠️ اطلب من شخص أن يغني أغنية طفولية",
    2: "😂 اضحك بصوت عالٍ لمدة 10 ثوانٍ",
    3: "💃 ارقص لمدة 30 ثانية",
    4: "📖 احكي نكتة مضحكة",
    5: "🤝 صافح أقرب شخص إليك بحرارة",
    6: "🌶️ اشرب ماء حار أو تناول شيئاً حاراً"
}

# متغير لتخزين حالة اللاعبين (اختياري)
user_data = {}

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎲 مرحباً بك في لعبة النرد!\n"
        "اضغط على الزر لرمي النرد ومعرفة الحكم.\n\n"
        "📜 الأحكام:\n"
        "1: ⚠️ اطلب من شخص أن يغني أغنية طفولية\n"
        "2: 😂 اضحك بصوت عالٍ لمدة 10 ثوانٍ\n"
        "3: 💃 ارقص لمدة 30 ثانية\n"
        "4: 📖 احكي نكتة مضحكة\n"
        "5: 🤝 صافح أقرب شخص إليك بحرارة\n"
        "6: 🌶️ اشرب ماء حار أو تناول شيئاً حاراً",
        reply_markup=reply_markup
    )

# معالجة ضغط الزر
async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # رمي النرد (رقم عشوائي من 1 إلى 6)
    dice_number = random.randint(1, 6)
    rule = RULES[dice_number]
    
    # عرض النتيجة
    message = f"🎲 رقم النرد: *{dice_number}*\n\n📜 الحكم: {rule}"
    
    # إضافة زر للعب مرة أخرى
    keyboard = [[InlineKeyboardButton("🎲 أعد الرمي", callback_data="roll")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# أمر /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 *كيفية اللعب:*\n"
        "اضغط على زر 'ارمي النرد' وسيظهر لك رقم وحكم.\n\n"
        "📜 *الأحكام:*\n"
        "1: ⚠️ اطلب من شخص أن يغني أغنية طفولية\n"
        "2: 😂 اضحك بصوت عالٍ لمدة 10 ثوانٍ\n"
        "3: 💃 ارقص لمدة 30 ثانية\n"
        "4: 📖 احكي نكتة مضحكة\n"
        "5: 🤝 صافح أقرب شخص إليك بحرارة\n"
        "6: 🌶️ اشرب ماء حار أو تناول شيئاً حاراً",
        parse_mode='Markdown'
    )

# الدالة الرئيسية
def main():
    # استخدم توكن البوت الخاص بك
    
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(roll_dice, pattern="roll"))
    
    # بدء البوت
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
