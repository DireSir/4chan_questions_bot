import os
import sqlite3
import json

config = json.load(open("config.json", "r"))
dialogue = json.load(open(config["files"]["dialogue_path"], "r"))
TOKEN = json.load(open(config["files"]["secrets_path"], "r"))["BOT_TOKEN"]
cursor = None
db_connection = None

def load_db():
  global db_connection
  global cursor
  db_file_path = config["files"]["db_file_path"]
  dir_ = os.path.dirname(db_file_path)
  if dir_: os.makedirs(dir_, exist_ok=True)
  db_connection = sqlite3.connect(db_file_path)
  cursor = db_connection.cursor()

def init_db():
  creating_primary_table = '''
    CREATE TABLE IF NOT EXISTS CHATS (
      chat_id TEXT PRIMARY KEY,
      interval INTEGER,
      last_sent TIMESTAMP
    )
  '''
  cursor.execute(creating_primary_table)
  db_connection.commit()

def add_chat(chat_id, timestamp, interval=config["default_interval"]):
  cursor.execute(
    "INSERT OR REPLACE INTO CHATS (chat_id, interval, last_sent) VALUES (?, ?, ?)",
    (chat_id, interval, timestamp)
  )
  db_connection.commit()

def remove_chat(chat_id):
  cursor.execute("DELETE FROM CHATS WHERE chat_id = ?", (chat_id,))
  db_connection.commit()

def update_interval(chat_id, interval):
  cursor.execute("UPDATE CHATS SET interval = ? WHERE chat_id = ?", (interval, chat_id))
  db_connection.commit()

def update_last_sent(chat_id, timestamp):
  cursor.execute("UPDATE CHATS SET last_sent = ? WHERE chat_id = ?", (timestamp, chat_id))
  db_connection.commit()

def get_chat_info(chat_id, serialise = False):
  cursor.execute("SELECT * FROM CHATS WHERE chat_id = ?", (chat_id,))
  line = cursor.fetchone()
  if not line:
    return None if not serialise else []
  if serialise:
    keys = ["chat_id", "interval", "last_sent"]
    return dict(zip(keys, line))
  return line

def get_all_chats_info(serialise = False):
  cursor.execute("SELECT * FROM CHATS")
  data = cursor.fetchall()
  if not data:
    return None if not serialise else []
  if serialise:
    keys = ["chat_id", "interval", "last_sent"]
    return [dict(zip(keys, row)) for row in data]
  return data

data = load_db()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CHATS';")
if not cursor.fetchone():
  init_db()
  db_connection.commit()