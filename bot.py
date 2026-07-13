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

# ملفات حفظ البيانات
RULES_FILE = "rules.json"
GAMES_FILE = "games.json"

# تحميل الأحكام
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

def save_rules(rules):
    with open(RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

# تحميل وحفظ الألعاب
def load_games():
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_games(games):
    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

RULES = load_rules()
GAMES = load_games()

waiting_for_rule = {}
ADMIN_IDS = ["8798182716", "8916460129"]

# ============ دالة /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll_single")],
        [InlineKeyboardButton("🎮 لعبة زوجية", callback_data="multiplayer")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎲 *مرحباً بك في لعبة النرد!*\n\n"
        f"اختر نوع اللعب:\n"
        f"• 🎲 فردي: العب مع نفسك\n"
        f"• 🎮 زوجي: العب مع صديق\n\n"
        f"💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ اللعب الفردي ============
async def roll_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dice_number = random.choice(list(RULES.keys()))
    rule = RULES[dice_number]
    
    message = f"🎲 رقم النرد: *{dice_number}*\n\n📜 الحكم: {rule}"
    
    keyboard = [
        [InlineKeyboardButton("🎲 أعد الرمي", callback_data="roll_single")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ إنشاء غرفة لعبة جديدة (للجميع) ============
async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق من أن المستخدم مشرف أو أي مستخدم عادي
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    username = query.from_user.username or user_id
    
    game_id = str(random.randint(1000, 9999))
    
    GAMES[game_id] = {
        "creator": user_id,
        "creator_name": username,
        "players": [user_id],
        "players_names": [username],
        "current_turn": 0,
        "scores": {user_id: 0},
        "active": True
    }
    save_games(GAMES)
    
    keyboard = [
        [InlineKeyboardButton("🎲 رمي النرد", callback_data=f"roll_game_{game_id}")],
        [InlineKeyboardButton("📋 عرض النتائج", callback_data=f"scores_{game_id}")],
        [InlineKeyboardButton("🔗 مشاركة الرابط", callback_data=f"share_{game_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎮 *تم إنشاء غرفة اللعبة!*\n\n"
        f"🆔 معرف الغرفة: `{game_id}`\n"
        f"👤 منشئ الغرفة: @{username}\n\n"
        f"📌 *للدعوة:*\n"
        f"أرسل هذا الرابط لأصدقائك:\n"
        f"`/join_{game_id}`\n\n"
        f"🎯 اضغط على 'رمي النرد' للبدء!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ الانضمام للعبة ============
async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or user_id
    
    text = update.message.text
    if text.startswith("/join_"):
        game_id = text.replace("/join_", "").strip()
    else:
        await update.message.reply_text("❌ استخدام خاطئ! استخدم /join_[رقم الغرفة]")
        return
    
    if game_id not in GAMES:
        await update.message.reply_text(
            f"❌ الغرفة `{game_id}` غير موجودة!\n"
            f"تأكد من الرقم وأعد المحاولة.",
            parse_mode='Markdown'
        )
        return
    
    game = GAMES[game_id]
    
    if not game["active"]:
        await update.message.reply_text("❌ هذه اللعبة انتهت!")
        return
    
    if user_id in game["players"]:
        await update.message.reply_text("ℹ️ أنت بالفعل في هذه الغرفة!")
        return
    
    if len(game["players"]) >= 2:
        await update.message.reply_text("❌ الغرفة ممتلئة! (حد أقصى 2 لاعبين)")
        return
    
    game["players"].append(user_id)
    game["players_names"].append(username)
    game["scores"][user_id] = 0
    
    if len(game["players"]) == 2:
        game["current_turn"] = 0
    
    save_games(GAMES)
    
    await update.message.reply_text(
        f"✅ *تم الانضمام للغرفة بنجاح!*\n\n"
        f"🎮 معرف الغرفة: `{game_id}`\n"
        f"👤 اللاعبين:\n" + 
        "\n".join([f"• @{name}" for name in game["players_names"]]) +
        f"\n\n🎯 انتظر دورك للعب!",
        parse_mode='Markdown'
    )
    
    # إرسال إشعار لمنشئ الغرفة
    try:
        creator_id = game["creator"]
        await context.bot.send_message(
            chat_id=creator_id,
            text=f"👤 *انضم لاعب جديد!*\n\n"
                 f"@{username} انضم للغرفة `{game_id}`\n"
                 f"الآن يمكنك البدء باللعب!",
            parse_mode='Markdown'
        )
    except:
        pass

# ============ رمي النرد في اللعبة الزوجية ============
async def roll_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if game_id not in GAMES:
        await query.edit_message_text("❌ الغرفة غير موجودة!")
        return
    
    game = GAMES[game_id]
    
    if not game["active"]:
        await query.edit_message_text("❌ هذه اللعبة انتهت!")
        return
    
    if user_id not in game["players"]:
        await query.edit_message_text("❌ أنت لست في هذه اللعبة!")
        return
    
    current_player_id = game["players"][game["current_turn"]]
    if user_id != current_player_id:
        current_name = game["players_names"][game["current_turn"]]
        await query.edit_message_text(
            f"⛔ ليس دورك!\nدور اللاعب @{current_name} الآن."
        )
        return
    
    dice_number = random.choice(list(RULES.keys()))
    rule = RULES[dice_number]
    
    game["scores"][user_id] = game["scores"].get(user_id, 0) + 1
    game["current_turn"] = (game["current_turn"] + 1) % len(game["players"])
    next_player = game["players_names"][game["current_turn"]]
    
    save_games(GAMES)
    
    players_info = ""
    for i, name in enumerate(game["players_names"]):
        pid = game["players"][i]
        score = game["scores"].get(pid, 0)
        current = " 👈" if i == game["current_turn"] else ""
        players_info += f"• @{name}: {score} نقطة{current}\n"
    
    keyboard = [
        [InlineKeyboardButton("🎲 رمي النرد", callback_data=f"roll_game_{game_id}")],
        [InlineKeyboardButton("📋 عرض النتائج", callback_data=f"scores_{game_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎲 *رمية جديدة!*\n\n"
        f"🎲 رقم النرد: *{dice_number}*\n"
        f"📜 الحكم: {rule}\n\n"
        f"👤 اللاعب: @{game['players_names'][(game['current_turn'] - 1) % len(game['players'])]}\n"
        f"⭐ +1 نقطة\n\n"
        f"📊 *النتيجة:*\n{players_info}\n\n"
        f"🔄 الدور الآن: @{next_player}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ عرض النتائج ============
async def show_scores(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    query = update.callback_query
    await query.answer()
    
    if game_id not in GAMES:
        await query.edit_message_text("❌ الغرفة غير موجودة!")
        return
    
    game = GAMES[game_id]
    
    players_info = ""
    for i, name in enumerate(game["players_names"]):
        pid = game["players"][i]
        score = game["scores"].get(pid, 0)
        players_info += f"• @{name}: {score} نقطة\n"
    
    keyboard = [
        [InlineKeyboardButton("🎲 متابعة اللعب", callback_data=f"roll_game_{game_id}")],
        [InlineKeyboardButton("🔄 إنهاء اللعبة", callback_data=f"end_{game_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 *نتائج اللعبة*\n\n"
        f"🆔 معرف الغرفة: `{game_id}`\n\n"
        f"👥 *اللاعبين:*\n{players_info}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ مشاركة رابط اللعبة ============
async def share_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    query = update.callback_query
    await query.answer()
    
    bot_username = (await context.bot.get_me()).username
    
    await query.edit_message_text(
        f"🔗 *رابط الدعوة للغرفة*\n\n"
        f"انسخ هذا الرابط وأرسله لصديقك:\n"
        f"`/join_{game_id}`\n\n"
        f"أو استخدم هذا الرابط المباشر:\n"
        f"https://t.me/{bot_username}?start=join_{game_id}\n\n"
        f"👤 انتظر حتى ينضم لاعب آخر للبدء",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 العودة للعبة", callback_data=f"roll_game_{game_id}")]
        ])
    )

# ============ إنهاء اللعبة ============
async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    query = update.callback_query
    await query.answer()
    
    if game_id not in GAMES:
        await query.edit_message_text("❌ الغرفة غير موجودة!")
        return
    
    game = GAMES[game_id]
    game["active"] = False
    save_games(GAMES)
    
    max_score = -1
    winner = ""
    for i, pid in enumerate(game["players"]):
        score = game["scores"].get(pid, 0)
        if score > max_score:
            max_score = score
            winner = game["players_names"][i]
    
    await query.edit_message_text(
        f"🏆 *انتهت اللعبة!*\n\n"
        f"🎉 الفائز: @{winner}\n"
        f"⭐ النقاط: {max_score}\n\n"
        f"📊 *النتيجة النهائية:*\n" +
        "\n".join([f"• @{name}: {game['scores'].get(pid, 0)} نقطة" 
                   for name, pid in zip(game["players_names"], game["players"])]) +
        f"\n\n🔄 ابدأ لعبة جديدة بـ /start",
        parse_mode='Markdown'
    )

# ============ العودة للقائمة الرئيسية ============
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎲 ارمي النرد", callback_data="roll_single")],
        [InlineKeyboardButton("🎮 لعبة زوجية", callback_data="multiplayer")],
        [InlineKeyboardButton("⚙️ الإعدادات (للمشرفين)", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎲 *مرحباً بك في لعبة النرد!*\n\n"
        f"اختر نوع اللعب:\n"
        f"• 🎲 فردي: العب مع نفسك\n"
        f"• 🎮 زوجي: العب مع صديق\n\n"
        f"💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ معالجة بدء اللعبة عبر الرابط ============
async def start_with_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if " " in text:
        args = text.split(" ", 1)
        if len(args) > 1 and args[1].startswith("join_"):
            game_id = args[1].replace("join_", "").strip()
            update.message.text = f"/join_{game_id}"
            await join_game(update, context)
            return
    
    await start(update, context)

# ============ معالجة الأزرار الرئيسية ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    # معالجة اللعب الفردي (للجميع)
    if data == "roll_single":
        await roll_single(update, context)
        return
    
    # معالجة اللعب الزوجي (للجميع - بدون شرط المشرف)
    if data == "multiplayer":
        await create_game(update, context)
        return
    
    # معالجة أزرار اللعبة
    if data.startswith("roll_game_"):
        game_id = data.replace("roll_game_", "")
        await roll_game(update, context, game_id)
        return
    
    if data.startswith("scores_"):
        game_id = data.replace("scores_", "")
        await show_scores(update, context, game_id)
        return
    
    if data.startswith("share_"):
        game_id = data.replace("share_", "")
        await share_game(update, context, game_id)
        return
    
    if data.startswith("end_"):
        game_id = data.replace("end_", "")
        await end_game(update, context, game_id)
        return
    
    if data == "back_to_main":
        await back_to_main(update, context)
        return
    
    # ============ الإعدادات (للمشرفين فقط) ============
    if data == "settings":
        if user_id not in ADMIN_IDS:
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
        return
    
    if data == "delete_rule":
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
        return
    
    if data.startswith("del_"):
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
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ العودة للإعدادات", callback_data="settings")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
            ])
        )
        return

# ============ معالجة الرسائل النصية ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    if text.startswith("/join_"):
        await join_game(update, context)
        return
    
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
        f"🎲 *لعبة النرد*\n\n"
        f"📌 *الأوامر:*\n"
        f"/start - القائمة الرئيسية\n"
        f"/join_[رقم] - الانضمام لغرفة (مثال: /join_1234)\n"
        f"/help - عرض المساعدة\n"
        f"/cancel - إلغاء العملية\n\n"
        f"🎮 *طريقة اللعب الزوجي:*\n"
        f"1️⃣ اختر 'لعبة زوجية'\n"
        f"2️⃣ شارك الرابط مع صديقك\n"
        f"3️⃣ يتناوب اللاعبون على رمي النرد\n"
        f"4️⃣ كل رمية تعطي حكم + نقطة\n"
        f"5️⃣ الفائز من يحصل على أكبر عدد من النقاط",
        parse_mode='Markdown'
    )

# ============ الدالة الرئيسية ============
def main():
    TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: لم يتم العثور على توكن البوت!")
        print("الرجاء إضافة متغير بيئي باسم BOT_TOKEN")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_with_join))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
