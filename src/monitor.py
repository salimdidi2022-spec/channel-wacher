import asyncio
import logging
import os
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from urllib.parse import urlparse

from config import Config
from database import Database
from utils import clean_message, extract_aliexpress_urls

logger = logging.getLogger(__name__)
db = Database()


class Monitor:
    def __init__(self, application):
        self.application = application
        self.client = None
        self.handlers = []
        self.running = False
        
    async def start(self):
        try:
            self.client = TelegramClient(
                StringSession(Config.SESSION_STRING),
                Config.API_ID,
                Config.API_HASH
            )
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("SESSION_STRING غير صالح!")
                return
            
            logger.info("✅ Telethon متصل")
            self.running = True
            await self.refresh()
            
            while self.running:
                await asyncio.sleep(60)
                await self.refresh()
                
        except Exception as e:
            logger.error(f"خطأ في المراقب: {e}")
    
    async def refresh(self):
        for h in self.handlers:
            try:
                self.client.remove_event_handler(h)
            except:
                pass
        self.handlers = []
        
        users = db.load_users()
        
        for user_id, info in users.items():
            if not info.get('active'):
                continue
            
            for channel_link in info.get('channels', []):
                try:
                    entity = await self._resolve_channel(channel_link)
                    if not entity:
                        continue
                    
                    handler = self.client.add_event_handler(
                        self._make_handler(user_id),
                        events.NewMessage(chats=entity)
                    )
                    self.handlers.append(handler)
                    logger.info(f"👁️ مراقبة: {channel_link}")
                    
                except Exception as e:
                    logger.error(f"خطأ في {channel_link}: {e}")
        
        logger.info(f"🎯 المعالجات النشطة: {len(self.handlers)}")
    
    async def _resolve_channel(self, link):
        try:
            link = link.strip()
            
            if link.startswith('@'):
                return await self.client.get_entity(link)
            
            if 't.me/' in link:
                parsed = urlparse(link)
                path = parsed.path.strip('/')
                
                if path.startswith('+'):
                    hash_part = path[1:]
                    try:
                        result = await self.client(ImportChatInviteRequest(hash_part))
                        if result.chats:
                            return result.chats[0]
                    except:
                        check = await self.client(CheckChatInviteRequest(hash_part))
                        return check.chat if hasattr(check, 'chat') else None
                else:
                    username = path.split('/')[0]
                    return await self.client.get_entity(f"@{username}")
            
            return await self.client.get_entity(link)
            
        except Exception as e:
            logger.error(f"فشل حل {link}: {e}")
            return None
    
    def _make_handler(self, user_id):
        async def handler(event):
            await self._process_message(event, user_id)
        return handler
    
    async def _process_message(self, event, user_id):
        try:
            msg = event.message
            if not msg or not msg.message:
                return
            
            urls = extract_aliexpress_urls(msg.message)
            if not urls:
                return
            
            # ✅ إعادة نظام منع تكرار الروابط
            sent = db.load_sent_links()
            if urls[0] in sent:
                logger.info(f"⏭️ تم تجاهل منشور مكرر: {urls[0][:30]}...")
                return
            
            new_text = clean_message(msg.message)
            if not new_text.strip():
                new_text = "🔗 رابط منتج"
            
            from handlers import get_main_keyboard
            
            photo_path = None
            
            # ✅ إرسال للمستخدم بدون هيدر اسم القناة
            if msg.photo:
                photo_path = f"temp_{user_id}_{msg.id}_{int(time.time())}.jpg"
                await msg.download_media(photo_path)
                
                if os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        await self.application.bot.send_photo(
                            chat_id=int(user_id),
                            photo=f,
                            caption=new_text[:1024],  # بدون هيدر
                            parse_mode='HTML',
                            reply_markup=get_main_keyboard()
                        )
            else:
                await self.application.bot.send_message(
                    chat_id=int(user_id),
                    text=new_text,  # بدون هيدر
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            
            # ✅ الأرشفة مع هيدر alideals فقط (بدون اسم القناة الأصلية)
            if Config.CHANNEL_ID:
                try:
                    archive_text = f"📢 <b>alideals</b>\n➖➖➖➖➖➖➖➖➖\n\n{new_text}"
                    
                    if msg.photo and photo_path and os.path.exists(photo_path):
                        with open(photo_path, 'rb') as f:
                            await self.application.bot.send_photo(
                                chat_id=Config.CHANNEL_ID,
                                photo=f,
                                caption=archive_text[:1024],
                                parse_mode='HTML'
                            )
                    else:
                        await self.application.bot.send_message(
                            chat_id=Config.CHANNEL_ID,
                            text=archive_text,
                            parse_mode='HTML'
                        )
                except Exception as e:
                    logger.error(f"خطأ في الأرشفة: {e}")
            
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            
            # ✅ حفظ الرابط في قائمة الروابط المرسلة
            sent.append(urls[0])
            db.save_sent_links(sent)
            logger.info(f"📤 تم إرسال للمستخدم {user_id}")
            
        except Exception as e:
            logger.error(f"خطأ في المعالجة: {e}")


async def fetch_initial_posts(user_id, channels, application, monitor_client):
    """
    جلب المنشورات الأولية باستخدام نفس client المراقب
    """
    from handlers import get_main_keyboard
    
    logger.info(f"🔄 جلب منشورات للمستخدم {user_id}")
    
    if not monitor_client:
        logger.error("❌ لم يتم تمرير client المراقب")
        await application.bot.send_message(
            chat_id=int(user_id),
            text="❌ خطأ: المراقب غير متوفر",
            reply_markup=get_main_keyboard()
        )
        return
    
    if not monitor_client.is_connected():
        logger.error("❌ client المراقب غير متصل")
        await application.bot.send_message(
            chat_id=int(user_id),
            text="❌ خطأ في الاتصال، المراقب غير متصل",
            reply_markup=get_main_keyboard()
        )
        return
    
    client = monitor_client
    
    for link in channels:
        try:
            logger.info(f"🔍 معالجة: {link}")
            
            entity = None
            link = link.strip()
            
            if link.startswith('@'):
                entity = await client.get_entity(link)
            elif 't.me/' in link:
                parsed = urlparse(link)
                path = parsed.path.strip('/')
                
                if path.startswith('+'):
                    hash_part = path[1:]
                    try:
                        result = await client(ImportChatInviteRequest(hash_part))
                        entity = result.chats[0] if result.chats else None
                    except Exception as e:
                        logger.warning(f"محاولة الانضمام فشلت: {e}")
                        try:
                            check = await client(CheckChatInviteRequest(hash_part))
                            entity = check.chat if hasattr(check, 'chat') else None
                        except Exception as e2:
                            logger.error(f"فشل التحقق: {e2}")
                else:
                    username = path.split('/')[0]
                    entity = await client.get_entity(f"@{username}")
            
            if not entity:
                logger.error(f"❌ لا يمكن الوصول لـ {link}")
                await application.bot.send_message(
                    chat_id=int(user_id),
                    text=f"❌ لا يمكن الوصول لـ: {link}\nتأكد من عضويتك في القناة",
                    reply_markup=get_main_keyboard()
                )
                continue
            
            title = getattr(entity, 'title', link)
            chat_id = int(user_id)
            
            await application.bot.send_message(
                chat_id=chat_id,
                text=f"📡 <b>{title}</b>\n⏳ جاري فحص آخر 5 منشورات...",
                parse_mode='HTML'
            )
            
            count = 0
            async for msg in client.iter_messages(entity, limit=5):
                if not msg.message:
                    continue
                
                urls = extract_aliexpress_urls(msg.message)
                if not urls:
                    continue
                
                # ✅ التحقق من عدم تكرار الرابط في الجلب الأولي أيضاً
                sent = db.load_sent_links()
                if urls[0] in sent:
                    logger.info(f"⏭️ تم تخطي منشور مكرر في الجلب الأولي: {urls[0][:30]}...")
                    continue
                
                new_text = clean_message(msg.message)
                if not new_text.strip():
                    new_text = "🔗 رابط منتج AliExpress"
                
                photo_path = None
                
                # ✅ إرسال للمستخدم بدون هيدر
                if msg.photo:
                    photo_path = f"temp_{user_id}_{msg.id}_{int(time.time())}.jpg"
                    await msg.download_media(photo_path)
                    
                    if os.path.exists(photo_path):
                        with open(photo_path, 'rb') as f:
                            await application.bot.send_photo(
                                chat_id=chat_id,
                                photo=f,
                                caption=new_text[:1024],  # بدون هيدر
                                parse_mode='HTML',
                                reply_markup=get_main_keyboard()
                            )
                else:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=new_text,  # بدون هيدر
                        parse_mode='HTML',
                        reply_markup=get_main_keyboard()
                    )
                
                # ✅ الأرشفة مع هيدر alideals فقط
                if Config.CHANNEL_ID:
                    try:
                        archive_text = f"📢 <b>alideals</b>\n➖➖➖➖➖➖➖➖➖\n\n{new_text}"
                        
                        if msg.photo and photo_path and os.path.exists(photo_path):
                            with open(photo_path, 'rb') as f:
                                await application.bot.send_photo(
                                    chat_id=Config.CHANNEL_ID,
                                    photo=f,
                                    caption=archive_text[:1024],
                                    parse_mode='HTML'
                                )
                        else:
                            await application.bot.send_message(
                                chat_id=Config.CHANNEL_ID,
                                text=archive_text,
                                parse_mode='HTML'
                            )
                        logger.info(f"📁 تمت الأرشفة")
                    except Exception as e:
                        logger.error(f"❌ خطأ في الأرشفة: {e}")
                
                if photo_path and os.path.exists(photo_path):
                    os.remove(photo_path)
                
                # ✅ حفظ الرابط في الجلب الأولي أيضاً
                sent.append(urls[0])
                db.save_sent_links(sent)
                
                count += 1
                await asyncio.sleep(1)
            
            if count == 0:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=f"📡 <b>{title}</b>\n📭 لا توجد روابط AliExpress جديدة في آخر 5 منشورات",
                    reply_markup=get_main_keyboard(),
                    parse_mode='HTML'
                )
            else:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ تم جلب {count} منشور جديد من {title}",
                    reply_markup=get_main_keyboard()
                )
            
            logger.info(f"✅ تم جلب {count} منشور من {title}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة {link}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await application.bot.send_message(
                chat_id=int(user_id),
                text=f"❌ خطأ في {link}: {str(e)[:100]}",
                reply_markup=get_main_keyboard()
            )
    
    logger.info("✅ تم إنهاء جلب المنشورات")