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
        "🎲 مرحباً بك في لعبة النرد!\n\n"
        "اختر نوع اللعب:\n"
        "• 🎲 فردي: العب مع نفسك\n"
        "• 🎮 زوجي: العب مع صديق\n\n"
        "💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup
    )

# ============ اللعب الفردي ============
async def roll_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dice_number = random.choice(list(RULES.keys()))
    rule = RULES[dice_number]
    
    message = f"🎲 رقم النرد: {dice_number}\n\n📜 الحكم: {rule}"
    
    keyboard = [
        [InlineKeyboardButton("🎲 أعد الرمي", callback_data="roll_single")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

# ============ إنشاء غرفة لعبة جديدة ============
async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"🎮 تم إنشاء غرفة اللعبة!\n\n"
        f"🆔 معرف الغرفة: {game_id}\n"
        f"👤 منشئ الغرفة: @{username}\n\n"
        f"📌 للدعوة:\n"
        f"أرسل هذا الرابط لأصدقائك:\n"
        f"/join_{game_id}\n\n"
        f"🎯 اضغط على 'رمي النرد' للبدء!",
        reply_markup=reply_markup
    )

# ============ الانضمام للعبة ============
async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or user_id
    
    text = update.message.text
    game_id = text.replace("/join_", "").strip()
    
    if game_id not in GAMES:
        await update.message.reply_text(f"❌ الغرفة {game_id} غير موجودة!")
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
        f"✅ تم الانضمام للغرفة بنجاح!\n\n"
        f"🎮 معرف الغرفة: {game_id}\n"
        f"👤 اللاعبين:\n" + 
        "\n".join([f"• @{name}" for name in game["players_names"]]) +
        f"\n\n🎯 انتظر دورك للعب!"
    )

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
        f"🎲 رمية جديدة!\n\n"
        f"🎲 رقم النرد: {dice_number}\n"
        f"📜 الحكم: {rule}\n\n"
        f"👤 اللاعب: @{game['players_names'][(game['current_turn'] - 1) % len(game['players'])]}\n"
        f"⭐ +1 نقطة\n\n"
        f"📊 النتيجة:\n{players_info}\n\n"
        f"🔄 الدور الآن: @{next_player}",
        reply_markup=reply_markup
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
        f"📊 نتائج اللعبة\n\n"
        f"🆔 معرف الغرفة: {game_id}\n\n"
        f"👥 اللاعبين:\n{players_info}",
        reply_markup=reply_markup
    )

# ============ مشاركة رابط اللعبة ============
async def share_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"🔗 رابط الدعوة للغرفة\n\n"
        f"انسخ هذا الرابط وأرسله لصديقك:\n"
        f"/join_{game_id}\n\n"
        f"👤 انتظر حتى ينضم لاعب آخر للبدء",
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
        f"🏆 انتهت اللعبة!\n\n"
        f"🎉 الفائز: @{winner}\n"
        f"⭐ النقاط: {max_score}\n\n"
        f"📊 النتيجة النهائية:\n" +
        "\n".join([f"• @{name}: {game['scores'].get(pid, 0)} نقطة" 
                   for name, pid in zip(game["players_names"], game["players"])]) +
        f"\n\n🔄 ابدأ لعبة جديدة بـ /start"
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
        "🎲 مرحباً بك في لعبة النرد!\n\n"
        "اختر نوع اللعب:\n"
        "• 🎲 فردي: العب مع نفسك\n"
        "• 🎮 زوجي: العب مع صديق\n\n"
        "💡 الأحكام تظهر فقط عند اللعب!",
        reply_markup=reply_markup
    )

# ============ بقية الكود (الإعدادات، معالجة الرسائل...) ============
# ... (باقي الكود كما هو)
