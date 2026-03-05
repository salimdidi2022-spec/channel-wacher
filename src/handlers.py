from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from utils import clean_message, extract_aliexpress_urls

db = Database()

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ إضافة قنوات"), KeyboardButton("📋 قائمة قنواتي")],
        [KeyboardButton("🗑️ حذف قنوات"), KeyboardButton("▶️ بدء المتابعة")],
        [KeyboardButton("⏹️ إيقاف المتابعة"), KeyboardButton("🔙 رجوع")]
    ], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ إلغاء")]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    users = db.load_users()
    if user_id not in users:
        users[user_id] = {"name": user_name, "channels": [], "active": False}
        db.save_users(users)
    
    await update.message.reply_text(
        f"👋 أهلاً بك {user_name}!\n\n"
        f"🤖 بوت متابعة AliExpress\n\n"
        f"⚡ فحص لحظي + حذف روابط Telegram\n\n"
        f"استخدم الأزرار 👇",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if text == "➕ إضافة قنوات":
        context.user_data['waiting'] = 'channels'
        await update.message.reply_text(
            "📥 أرسل روابط القنوات (كل رابط في سطر):\n"
            "• https://t.me/channel\n• @channel",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    elif text == "📋 قائمة قنواتي":
        await show_channels(update, context)
        return
    
    elif text == "🗑️ حذف قنوات":
        await delete_channels(update, context)
        return
    
    elif text == "▶️ بدء المتابعة":
        await start_monitoring(update, context)
        return
    
    elif text == "⏹️ إيقاف المتابعة":
        await stop_monitoring(update, context)
        return
    
    elif text in ["🔙 رجوع", "❌ إلغاء"]:
        context.user_data['waiting'] = None
        await update.message.reply_text("🔹 القائمة الرئيسية", reply_markup=get_main_keyboard())
        return
    
    if context.user_data.get('waiting') == 'channels':
        await add_channels(update, context)
        return

async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = db.load_users()
    user_data = users.get(user_id, {})
    channels = user_data.get('channels', [])
    
    if not channels:
        text = "📭 لا توجد قنوات"
    else:
        text = f"📋 قنواتك ({len(channels)}):\n\n"
        for i, ch in enumerate(channels, 1):
            status = "✅" if user_data.get('active') else "⏸️"
            text += f"{i}. {status} {ch}\n"
        text += f"\n{'🟢 نشط' if user_data.get('active') else '🔴 متوقف'}"
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def add_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    added = []
    for line in lines:
        if 't.me/' in line or line.startswith('@'):
            added.append(line)
    
    if not added:
        await update.message.reply_text("❌ لا توجد روابط صالحة", reply_markup=get_cancel_keyboard())
        context.user_data['waiting'] = None
        return
    
    users = db.load_users()
    if user_id not in users:
        users[user_id] = {"channels": [], "active": False}
    
    existing = set(users[user_id].get('channels', []))
    new_channels = [c for c in added if c not in existing]
    
    if not new_channels:
        await update.message.reply_text("⚠️ هذه القنوات مضافة مسبقاً", reply_markup=get_main_keyboard())
        context.user_data['waiting'] = None
        return
    
    users[user_id]['channels'].extend(new_channels)
    db.save_users(users)
    
    response = f"✅ تم إضافة {len(new_channels)} قناة:\n\n"
    response += "\n".join(f"• {c}" for c in new_channels)
    response += "\n\n⏳ جاري جلب المنشورات... (قد يستغرق دقيقة)"
    
    await update.message.reply_text(response, reply_markup=get_main_keyboard())
    context.user_data['waiting'] = None
    
    # جلب المنشورات - تمرير client المراقب
    from monitor import fetch_initial_posts
    monitor = context.application.bot_data.get('monitor')
    if monitor and monitor.client and monitor.client.is_connected():
        await fetch_initial_posts(user_id, new_channels, context.application, monitor.client)
    else:
        await context.application.bot.send_message(
            chat_id=int(user_id),
            text="⚠️ المراقب غير جاهز بعد، سيتم جلب المنشورات لاحقاً",
            reply_markup=get_main_keyboard()
        )

async def delete_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = db.load_users()
    channels = users.get(user_id, {}).get('channels', [])
    
    if not channels:
        await update.message.reply_text("📭 لا توجد قنوات", reply_markup=get_main_keyboard())
        return
    
    keyboard = [[InlineKeyboardButton(f"🗑️ {c[:40]}", callback_data=f"del_{i}")] 
                for i, c in enumerate(channels)]
    
    await update.message.reply_text("اختر للحذف:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = db.load_users()
    
    if not users.get(user_id, {}).get('channels'):
        await update.message.reply_text("❌ أضف قنوات أولاً", reply_markup=get_main_keyboard())
        return
    
    users[user_id]['active'] = True
    db.save_users(users)
    
    await update.message.reply_text("✅ تم بدء المتابعة!", reply_markup=get_main_keyboard())
    
    if 'monitor' in context.application.bot_data:
        await context.application.bot_data['monitor'].refresh()

async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = db.load_users()
    
    if user_id in users:
        users[user_id]['active'] = False
        db.save_users(users)
    
    await update.message.reply_text("⏹️ تم الإيقاف", reply_markup=get_main_keyboard())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if query.data.startswith('del_'):
        idx = int(query.data.split('_')[1])
        users = db.load_users()
        channels = users.get(user_id, {}).get('channels', [])
        
        if 0 <= idx < len(channels):
            deleted = channels.pop(idx)
            db.save_users(users)
            await query.edit_message_text(f"✅ تم حذف: {deleted}")
            await context.application.bot.send_message(
                chat_id=int(user_id),
                text="اختر إجراءً:",
                reply_markup=get_main_keyboard()
            )