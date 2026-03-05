#!/usr/bin/env python3
"""
ملف تشغيل البوت محلياً على الحاسوب
"""

import sys
import os

# إضافة مجلد src للمسار
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# استيراد من src
from bot import main

if __name__ == '__main__':
    main()