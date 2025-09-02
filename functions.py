import os
import sqlite3
import json

config = json.load(open("config.json", "r"))
dialogue = json.load(open(config["files"]["dialogue_path"], "r"))
TOKEN = json.load(open(config["files"]["secrets_path"], "r"))["BOT_TOKEN"]
cursor = None
db_connection = None
keys = ["chat_id", "interval", "boards", "last_sent"]

def load_db() -> None: # I don't think we need error handling here because if something here doesn't work, we're fucked anyway
  global db_connection
  global cursor
  db_file_path = config["files"]["db_file_path"]
  dir_ = os.path.dirname(db_file_path)
  if dir_: os.makedirs(dir_, exist_ok=True)
  db_connection = sqlite3.connect(db_file_path)
  cursor = db_connection.cursor()

def init_db() -> None:
  """
  ### Initializes a new database with pre-defined collumns. 
  I'm just testing stuff btw.
  """
  creating_primary_table = '''
    CREATE TABLE IF NOT EXISTS CHATS (
      chat_id TEXT PRIMARY KEY,
      interval INTEGER,
      boards TEXT,
      last_sent TIMESTAMP
    )
  '''
  cursor.execute(creating_primary_table)
  db_connection.commit()

def add_chat(chat_id, timestamp, boards=config["default_boards"], interval=config["default_interval"]) -> bool:
  try:
    cursor.execute(
      "INSERT OR REPLACE INTO CHATS (chat_id, interval, boards, last_sent) VALUES (?, ?, ?, ?)",
      (chat_id, interval, str(boards), timestamp)
    )
    db_connection.commit()
    return True
  except Exception as e:
    print(f"Could not add a chat, {e}")
    return False

def update_chat(chat_id, column, value) -> bool:
  try:
    cursor.execute(f"UPDATE CHATS SET {column} = ? WHERE chat_id = ?", (value, chat_id))
    db_connection.commit()
    return True
  except Exception as e:
    print(f"Could not update {column} of chat {chat_id}, {e}")
    return False

def get_chat_info(chat_id, serialise = False) -> tuple | dict:
  try:
    cursor.execute("SELECT * FROM CHATS WHERE chat_id = ?", (chat_id,))
    line = cursor.fetchone()
    if line is None:
      return {} if serialise else ()
    if serialise:
      result = dict(zip(keys, line))
      if "boards" in result and isinstance(result["boards"], str):
        result["boards"] = [b.strip(" '") for b in result["boards"].strip("[]").split(",")]
      return result
    return line
  
  except KeyError:
    print(f"The {chat_id} chat is not in the database!")
  except Exception as e:
    print(f"Could not fetch {"" if not serialise else "serialized "}info for the {chat_id} chat, {e}")
  return () if not serialise else []

def get_all_chats_info(serialise = False) -> tuple | list:
  try:
    cursor.execute("SELECT * FROM CHATS")
    try:
      data = cursor.fetchall()
    except Exception as e:
      print(e)
      data = []
    if serialise:
      data = []
      for row in data:
        row_dict = dict(zip(keys, row))
        if "boards" in row_dict and isinstance(row_dict["boards"], str):
          row_dict["boards"] = [b.strip(" '") for b in row_dict["boards"].strip("[]").split(",")]
        data.append(row_dict)
      print(data) # Remove this ~~in production~~
    return data
  
  except Exception as e:
    print(f"Could not fetch {"" if not serialise else "serialized "}info for all chats, {e}")
  return () if not serialise else []

def fix_chats() -> None:
  defaults = {"last_sent": 0, "interval": config["default_interval"],"boards": config["default_boards"]}
  data = get_all_chats_info(True)
  for chat in data:
    for column, default_value in defaults.items():
      if chat.get(column) is None:
        update_chat(chat['chat_id'], column, default_value)

data = load_db()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CHATS';")
if not cursor.fetchone():
  init_db()
fix_chats()