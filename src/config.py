import os
import sys
from dotenv import load_dotenv

# تحميل .env من المجلد الرئيسي (أب src)
current_dir = os.path.dirname(os.path.abspath(__file__))  # src/
parent_dir = os.path.dirname(current_dir)  # المجلد الرئيسي
env_path = os.path.join(parent_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ تم تحميل الإعدادات من: {env_path}")
else:
    load_dotenv()
    print("⚠️ لم يتم العثور على .env")

class Config:
    API_ID = int(os.getenv('API_ID', '0')) if os.getenv('API_ID') else 0
    API_HASH = os.getenv('API_HASH', '')
    SESSION_STRING = os.getenv('SESSION_STRING', '')
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    ALI_APP_KEY = os.getenv('ALI_APP_KEY', '')
    ALI_TRACKING_ID = os.getenv('ALI_TRACKING_ID', 'default')
    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
    
    # المجلد الرئيسي (أب src)
    BASE_DIR = parent_dir
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    
    USERS_DB_FILE = os.path.join(DATA_DIR, 'users_data.json')
    SENT_LINKS_DB = os.path.join(DATA_DIR, 'sent_links.json')
    
    @classmethod
    def validate(cls):
        required = {
            'API_ID': cls.API_ID,
            'API_HASH': cls.API_HASH,
            'SESSION_STRING': cls.SESSION_STRING,
            'BOT_TOKEN': cls.BOT_TOKEN
        }
        
        missing = [k for k, v in required.items() if not v]
        
        if missing:
            print("\n" + "="*60)
            print("❌ خطأ: إعدادات ناقصة في ملف .env!")
            print("="*60)
            print("\nالمتغيرات المطلوبة:")
            for item in missing:
                print(f"   • {item}")
            print("\n📁 الملف المطلوب:", env_path)
            print("="*60 + "\n")
            sys.exit(1)
        
        print("✅ جميع الإعدادات صحيحة!")
        return True