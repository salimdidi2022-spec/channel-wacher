import json
import os
from config import Config

class Database:
    def __init__(self):
        os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    def load_users(self):
        if os.path.exists(Config.USERS_DB_FILE):
            try:
                with open(Config.USERS_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_users(self, data):
        with open(Config.USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_sent_links(self):
        if os.path.exists(Config.SENT_LINKS_DB):
            try:
                with open(Config.SENT_LINKS_DB, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_sent_links(self, links):
        with open(Config.SENT_LINKS_DB, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)