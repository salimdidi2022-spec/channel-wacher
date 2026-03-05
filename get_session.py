from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("=" * 60)
print("🔐 الحصول على SESSION_STRING")
print("=" * 60)

api_id = input("API_ID: ")
api_hash = input("API_HASH: ")

print("\n⏳ جاري الاتصال...")
print("سيطلب منك إدخال رقم هاتفك وكود التحقق\n")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    session = client.session.save()
    
    print("\n" + "=" * 60)
    print("✅ تم الاتصال بنجاح!")
    print("=" * 60)
    print("\n📋 انسخ هذا السطر بالكامل:")
    print(f"\nSESSION_STRING={session}\n")
    
    print("📋 قنواتك (للحصول على CHANNEL_ID):")
    for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"  {dialog.name}: {dialog.id}")

input("\nاضغط Enter للخروج...")
