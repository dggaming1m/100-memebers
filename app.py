import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

# Bot token from BotFather
BOT_TOKEN = "7627604218:AAFzDC763QEHCyU6dXW-cHSu1k6h9SA_cMM"

# Group details
GROUP_LINK = "https://t.me/freefirelikesbot655"
GROUP_ID = -1002535466570  # Group ID provided

# Admin ID (set your admin Telegram user ID here)
ADMIN_ID = 5670174770  # Replace with actual admin ID

# Custom reply keyboard with emojis
def get_custom_keyboard():
    keyboard = [
        ["💰 Balance", "👥 Invite"],
        ["💼 Wallet", "🎁 Bonus", "💸 Withdraw"],
        ["📊 Statistics"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Initialize database
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    referrals INTEGER DEFAULT 0,
                    invited_by INTEGER,
                    channel_link TEXT,
                    has_joined INTEGER DEFAULT 0,
                    last_bonus TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
                    total_users INTEGER,
                    total_withdrawals INTEGER
                )''')
    # Initialize stats if not exists
    c.execute("INSERT OR IGNORE INTO stats (total_users, total_withdrawals) VALUES (0, 0)")
    conn.commit()
    conn.close()

# Helper to get/set user data
def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, referrals, has_joined, last_bonus) VALUES (?, 0, 0, ?)", (user_id, None))
        c.execute("UPDATE stats SET total_users = total_users + 1")
        conn.commit()
    conn.close()
    return user

def update_referrals(user_id, referrals):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET referrals = referrals + ? WHERE user_id = ?", (referrals, user_id))
    conn.commit()
    conn.close()

def mark_user_joined(user_id):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET has_joined = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_channel_link(user_id, channel_link):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET channel_link = ? WHERE user_id = ?", (channel_link, user_id))
    conn.commit()
    conn.close()

def update_bonus_time(user_id, timestamp):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (timestamp, user_id))
    conn.commit()
    conn.close()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)

    # Check if the user was invited via a referral link
    if context.args:
        try:
            invited_by = int(context.args[0].replace("Bot", ""))
            if invited_by != user_id:
                user = get_user(invited_by)
                if user and user[4] == 1:
                    update_referrals(invited_by, 1)  # 1 point per referral
        except (IndexError, ValueError):
            pass

    # Inline keyboard with group link
    keyboard = [
        [InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)],
        [InlineKeyboardButton("✅ JOINED", callback_data="joined")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "🚫 Must Join Our Group\n\n✅ After Joining, Click on JOINED"
    await update.message.reply_text(message, reply_markup=reply_markup)

# Joined button handler with group join verification
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "joined":
        user_id = query.from_user.id
        user = get_user(user_id)

        if user[4] == 1:
            channel_link = user[3] if user[3] else "Not set"
            await query.message.reply_text(f"✅ You Have Already Joined The Group!\n\n✏️ Your Channel Link: {channel_link}\n💸 It will be used for future withdrawals!", reply_markup=get_custom_keyboard())
            return

        try:
            chat_member = await context.bot.get_chat_member(chat_id=GROUP_ID, user_id=user_id)
            if chat_member.status in ["member", "administrator", "creator"]:
                mark_user_joined(user_id)
                channel_link = user[3] if user[3] else "Not set"
                await query.message.reply_text(f"✅ Joined\n\n✏️ Your Channel Link: {channel_link}\n💸 It will be used for future withdrawals!", reply_markup=get_custom_keyboard())
            else:
                await query.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        except Exception as e:
            await query.message.reply_text(f"⚠️ Error verifying your membership. Please ensure you have joined the group.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
            print(f"Error: {e}")

    elif query.data in ["balance", "invite", "withdraw"]:
        await context.bot.send_message(chat_id=user_id, text=f"Please use the command /{query.data} to proceed.", reply_markup=get_custom_keyboard())

# Handle custom keyboard input
async def handle_keyboard_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text

    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return

    if text == "💰 Balance":
        await balance(update, context)
    elif text == "👥 Invite":
        await invite(update, context)
    elif text == "💼 Wallet":
        if not user[3]:  # Only prompt for link if not set
            await update.message.reply_text("✏️ Please send your channel or group link to set it for withdrawals.", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"✅ Your Channel Link is already set to: {user[3]}\n💸 It will be used for future withdrawals!", reply_markup=get_custom_keyboard())
    elif text == "🎁 Bonus":
        await bonus(update, context)
    elif text == "💸 Withdraw":
        await withdraw(update, context)
    elif text == "📊 Statistics":
        await statistics(update, context)

# Handle channel link submission after "Wallet"
async def handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text

    # Check if the user is in the process of setting a channel link
    if user[4] == 1 and not user[3]:  # User has joined but no channel link set
        if text.startswith("https://t.me/") or text.startswith("http://t.me/"):
            update_channel_link(user_id, text)
            await update.message.reply_text(f"✅ Channel link set to: {text}\n💸 It will be used for all future withdrawals!", reply_markup=get_custom_keyboard())
        else:
            await update.message.reply_text("⚠️ Please send a valid Telegram channel or group link (e.g., https://t.me/yourchannel).", reply_markup=ReplyKeyboardRemove())

# Balance command
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    referrals = user[1] if user else 0
    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return
    await update.message.reply_text(f"👥 Referrals = {referrals} points", reply_markup=get_custom_keyboard())

# Invite command
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return

    invite_link = f"https://t.me/freemembersoo?start=Bot{user_id}"
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE invited_by = ?", (user_id,))
    total_refs = c.fetchone()[0]
    conn.close()

    message = (f"👥 TOTAL REFERRALS = {total_refs} User(s)\n\n"
               f"👥 YOUR INVITE LINK = {invite_link}\n\n"
               "💸 INVITE TO EARN 1 POINT PER INVITE (100 MEMBERS = 100 REFERRALS)")
    await update.message.reply_text(message, reply_markup=get_custom_keyboard())

# Withdraw command
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return

    referrals = user[1] if user else 0
    if referrals < 10:
        await update.message.reply_text("⚠️ MUST HAVE AT LEAST 10 POINTS TO MAKE WITHDRAWAL (10 POINTS = 100 MEMBERS)", reply_markup=get_custom_keyboard())
        return

    if not user[3]:
        await update.message.reply_text("⚠️ Please set your channel link using 💼 Wallet first!", reply_markup=get_custom_keyboard())
        return

    update_referrals(user_id, -10)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE stats SET total_withdrawals = total_withdrawals + 1")
    conn.commit()
    conn.close()

    channel_link = user[3]
    await update.message.reply_text(f"💸 Withdrawal successful! 100 members will be added to your channel: {channel_link}", reply_markup=get_custom_keyboard())

# Bonus command (weekly bonus)
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return

    last_bonus = user[5]
    current_time = datetime.now()
    if last_bonus and (current_time - datetime.fromisoformat(last_bonus)).days < 7:
        await update.message.reply_text("⚠️ You can claim your bonus only once every week!", reply_markup=get_custom_keyboard())
        return

    update_referrals(user_id, 1)
    update_bonus_time(user_id, current_time.isoformat())
    await update.message.reply_text("🎁 Bonus of 1 point added to your balance!", reply_markup=get_custom_keyboard())

# Admin commands
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    for user_id in [user[0] for user in users]:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")
    await update.message.reply_text("📢 Broadcast sent to all users!")

async def add_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /bonus <number_of_points>")
        return
    points = int(context.args[0])
    user_id = update.effective_user.id
    update_referrals(user_id, points)
    await update.message.reply_text(f"🎁 {points} bonus points added to your balance!")

async def botstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT total_withdrawals FROM stats")
    total_withdrawals = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 Bot Status:\n- Total Users: {total_users}\n- Total Withdrawals: {total_withdrawals}")

async def resetstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE stats SET total_users = 0, total_withdrawals = 0")
    conn.commit()
    conn.close()
    await update.message.reply_text("🔄 Statistics reset successfully!")

async def banuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠️ Usage: /banuser <user_id>")
        return
    user_id = int(context.args[0])
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"🚫 User {user_id} has been banned!")

# Statistics command
async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user[4] == 0:
        await update.message.reply_text(f"⚠️ You must join the group first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]]))
        return

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT total_users, total_withdrawals FROM stats")
    stats = c.fetchone()
    conn.close()

    total_users, total_withdrawals = stats
    message = (f"📊 BOT LIVE STATS 📊\n\n"
               f"📤 TOTAL WITHDRAWALS: {total_withdrawals} (x100 MEMBERS)\n\n"
               f"💡 TOTAL USERS: {total_users} User(s)\n\n"
               f"🤘 CODES MAKER: @dg_gaming_1m")
    await update.message.reply_text(message, reply_markup=get_custom_keyboard())

# Main function to run the bot
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("bonus", bonus))
    app.add_handler(CommandHandler("statistics", statistics))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("bonus", add_bonus))  # Admin bonus command
    app.add_handler(CommandHandler("botstatus", botstatus))
    app.add_handler(CommandHandler("resetstats", resetstats))
    app.add_handler(CommandHandler("banuser", banuser))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.Regex(r"https?://t\.me/.*")  # raw string to avoid escape warning) & ~filters.COMMAND, handle_channel_link))  # Handle only valid links
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_input))  # Handle keyboard input

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
