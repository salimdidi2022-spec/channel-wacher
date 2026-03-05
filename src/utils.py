import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from config import Config

def is_aliexpress_url(url):
    if not url:
        return False
    return 'aliexpress.com' in url.lower()

def extract_urls(text):
    if not text:
        return []
    pattern = r'https?://[^\s<>"{}|\\^`\[\]\n\r]+'
    urls = re.findall(pattern, text)
    return [u.rstrip('.,;:!?)]}>"\'') for u in urls if len(u) > 10]

def extract_aliexpress_urls(text):
    return [u for u in extract_urls(text) if is_aliexpress_url(u)]

def convert_to_affiliate(url):
    if not Config.ALI_APP_KEY or not is_aliexpress_url(url):
        return url
    try:
        parsed = urlparse(url.strip())
        params = parse_qs(parsed.query)
        params['aff_fcid'] = [f'{Config.ALI_APP_KEY}::{Config.ALI_TRACKING_ID}']
        new_query = urlencode(params, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                          parsed.params, new_query, parsed.fragment))
    except:
        return url

def clean_message(text):
    if not text:
        return ""
    
    # استخراج روابط AliExpress أولاً
    ali_urls = extract_aliexpress_urls(text)
    if not ali_urls:
        return text
    
    # تقسيم النص إلى أسطر
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # تجاهل الأسطر الفارغة
        if not line_stripped:
            continue
            
        # ✅ تجاهل أي سطر يحتوي على t.me/ بأي صيغة (مع أو بدون https)
        if 't.me/' in line_stripped or 't.me/' in line_stripped.replace('https://', '').replace('http://', ''):
            # إذا كان فيه رابط علي في نفس السطر، نحتفظ بالنص فقط
            if 'aliexpress' in line_stripped.lower():
                cleaned_line = re.sub(r'https?://t\.me/\S+', '', line_stripped).strip()
                cleaned_line = re.sub(r't\.me/\S+', '', cleaned_line).strip()
                if cleaned_line and len(cleaned_line) > 3:
                    filtered_lines.append(cleaned_line)
                continue
            else:
                continue
        
        # ✅ تجاهل أي سطر يحتوي على @ (ذكر حسابات/بوتات)
        if '@' in line_stripped and 'aliexpress' not in line_stripped.lower():
            continue
            
        # ✅ تجاهل الأسطر التي تدعو للانضمام لقناة أو بوت (بأي صيغة)
        if any(x in line_stripped for x in [
            '🔸 قناتنا', '🔸 البوت', 'بوت يساعدك', 'البوت', 'بوت للحصول',
            'قناتنا على تلغرام', 'قناتنا على التليجرام', 'قناتنا على telegram',
            'قناتنا', 'القناة', 'انضم لقناتنا', 'اشترك في القناة',
            '🛑قناتنا', '📌قناتنا', '👇', '⬇️', '🔗',
            'بوت تتبع', 'تتبع طرود', 'تتبع الطرود', 'تتبع الشحن',
            '✨📦بوت', '📦بوت', 'بوت التتبع', 'بوت تتبع',
            '🤖', '🤖 t.me', '🤖t.me',
            # ✅ الجمل الجديدة المضافة:
            '📌رابط بوت', 'رابط بوت', 'بوت لخصم', 'بوت لخصم سعر',
            'تخفيض المنتوجات', 'بوت تخفيض', 'بوت تخفيض المنتوجات',
            'تابعوا قناتنا', 'تابعوا قناتنا على', 'تابعوا قناتنا على تليغرام',
            'تابعوا قناتنا على التليجرام', 'تابعوا قناتنا على تلغرام',
            'لأفضل سعر', 'لأفضل سعر استخدم', 'لأفضل سعر استخدم البوت',
            '🟡', '📌', '👌', 'خصم سعر', 'خصم سعر اي منتج',
            'خاص بالعملات', 'بوت خاص بالعملات'
        ]) and 'aliexpress' not in line_stripped.lower():
            continue
            
        filtered_lines.append(line_stripped)
    
    # إعادة بناء النص
    text = '\n'.join(filtered_lines)
    
    # ✅ إزالة الأسطر الأخيرة إذا كانت فارغة أو تحتوي على سهام/رموز فقط
    lines_final = text.split('\n')
    while lines_final and (
        not lines_final[-1].strip() or 
        lines_final[-1].strip() in ['👇', '⬇️', '🔗', '👆', '⬆️', '...', '…', '✨', '📦', '✨📦', '🤖', '🟡', '📌', '👌']
    ):
        lines_final.pop()
    
    text = '\n'.join(lines_final)
    
    # معالجة الروابط: الاحتفاظ بـ AliExpress فقط وتحويله للأفلييت
    all_urls = extract_urls(text)
    new_text = text
    for url in all_urls:
        if is_aliexpress_url(url):
            new_text = new_text.replace(url, convert_to_affiliate(url))
        else:
            new_text = new_text.replace(url, '')
    
    # تنظيف الفراغات المتعددة
    new_text = re.sub(r'\n\s*\n+', '\n\n', new_text)
    new_text = '\n'.join(line.strip() for line in new_text.split('\n') if line.strip())
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)
    new_text = new_text.strip()
    
    return new_text