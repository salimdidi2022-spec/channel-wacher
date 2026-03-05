#!/usr/bin/env python3
import asyncio
import logging
import os
import sys

# إضافة src للمسار
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import Config
from handlers import start, handle_message, button_callback
from monitor import Monitor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        Config.validate()
    except SystemExit:
        sys.exit(1)
    
    print("🤖 تشغيل البوت...")
    print(f"📁 مجلد البيانات: {Config.DATA_DIR}")
    
    try:
        app = Application.builder().token(Config.BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        monitor = Monitor(app)
        app.bot_data['monitor'] = monitor
        
        asyncio.get_event_loop().create_task(monitor.start())
        
        print("✅ البوت يعمل الآن!")
        print("⏹️ اضغط Ctrl+C للإيقاف")
        
        app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف البوت من قبل المستخدم")
    except Exception as e:
        print(f"❌ خطأ: {e}")
        logger.error(f"خطأ في تشغيل البوت: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()