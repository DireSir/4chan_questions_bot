import asyncio
import logging #type:ignore
import time
import functions
from functions import TOKEN, dialogue, config
import online
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import BotCommand, Message
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramNetworkError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
socket_path = config["socket_path"]
running = False

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

class SettingsStates(StatesGroup):
  waiting_for_interval = State()

async def set_commands(bot) -> None | Exception:
  commands = [
    BotCommand(command="start", description="Print some bot info"),
    BotCommand(command="settings", description="Change bot's settings"),
    BotCommand(command="question", description="Get a random question"),
  ]
  try:
    await bot.set_my_commands(commands)
  except Exception:
    return Exception
    
@dp.message(CommandStart())
async def command_start_handler(message: Message):
  await message.answer(dialogue["start"])

@dp.message(Command("settings"))
async def settings(message: Message):
  if message.chat.type == "private":
    await message.reply(dialogue["settings"]["dms"])
    return
  # if is_admin:
  data = functions.get_chat_info(message.chat.id, True)
  interval = data["interval"] / 60
  boards = data["boards"] # THIS HERE TOO
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"{dialogue["settings"]["current_interval"]} {interval} minutes", callback_data="change_interval")],
    [InlineKeyboardButton(text=f"{dialogue["settings"]["current_boards"]} {boards}", callback_data="change_boards")],
    [InlineKeyboardButton(text=f"{dialogue["cancel"]}", callback_data="cancel")]
  ])
  await message.reply(text = dialogue["settings"]["main_menu"], reply_markup=keyboard)

@dp.message(Command("question"))
async def question(message: Message):
  chat_id = message.chat.id
  try:
    if message.chat.type != "private": 
      question = await online.question(functions.get_chat_info(chat_id, True)["boards"])
    else:
      question = await online.question(config["default_boards"])
    await message.reply(question)
  except TelegramBadRequest as e:
    print(f"Not enough rights to send the message to the {chat_id} chat!, {e}")
  except Exception as e:
    print(f"Either couldn't fetch a question or send it to the chat id {chat_id}, {e}")

@dp.callback_query()
async def callback_handler(callback: CallbackQuery, state: FSMContext):
  callback_data = callback.data
  if callback_data == "change_interval":
    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text=dialogue["cancel"], callback_data="cancel")]
    ])
    await callback.message.edit_text(
      text=dialogue["settings"]["new_interval"],
      reply_markup=new_keyboard
    )
    await state.set_state(SettingsStates.waiting_for_interval)
    await state.update_data(requester_id=callback.from_user.id)
    await callback.answer()
    return
  
  elif callback_data == "change_boards":
    boards = functions.get_chat_info(callback.message.chat.id, True)
    board_buttons = []
    for board, status in boards.items():
      board_buttons.append([board, status])
    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
      board_buttons,
      [InlineKeyboardButton(text=dialogue["cancel"], callback_data="cancel")],
    ])
    await callback.message.edit_text(
      text=dialogue["settings"]["change_boards"],
      reply_markup=new_keyboard
    )
    await state.set_state(SettingsStates.waiting_for_interval)
    await state.update_data(requester_id=callback.from_user.id)
    await callback.answer()
    return
  
  elif callback_data == "cancel":
    await state.clear()
    try:
      await callback.message.delete()
    except Exception:
      pass
    await callback.answer()
    return

  await callback.answer()

@dp.message(SettingsStates.waiting_for_interval)
async def interval_message_handler(message: Message, state: FSMContext):
  data = await state.get_data()
  if not message.chat.type == "private" or data.get("requester_id") and data["requester_id"] != message.from_user.id:
    try:
      minutes = float(message.text.strip())
      if minutes >= 1:
        interval =  minutes * 60
      else:
        await message.reply(dialogue["settings"]["interval_too_small"])
        return
    except ValueError:
      await message.reply(dialogue["settings"]["invalid_interval"])
      return

    functions.update_chat(message.chat.id, "interval", interval)

    await message.reply(f"{dialogue["settings"]["updated_interval"]} {interval / 60} {dialogue["minutes"]}.")
    await state.clear()

@dp.message()
async def message_handler(message: Message):
  if not message.chat.type == "private":
    chat_id = message.chat.id
    latest_message_time = time.time()
    chat_info = functions.get_chat_info(chat_id)
    if not chat_info:
      functions.add_chat(chat_id, latest_message_time)
    else:
      functions.update_chat(chat_id, "last_sent", latest_message_time)

async def _writeln(writer, text: str):
  writer.write((text + "\n").encode())
  await writer.drain()

async def console_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
  try:
    while True:
      await _writeln(writer, ">>>")
      data = await reader.readline()
      if not data:
        break
      line = data.decode().strip()
      if not line:
        continue
      parts = line.split()
      cmd = parts[0].lower()

      if cmd in ("quit", "exit"):
        await _writeln(writer, "closing connection.")
        break

      if cmd == "help":
        await _writeln(writer, "commands: help list send status stop quit update_commands")
        continue

      if cmd == "update_commands":
        if set_commands() == Exception: 
          await _writeln(writer, f"could not updated bot's commands, {Exception}")
        else:
          await _writeln(writer, "succssesfully updated bot's commands")

      if cmd == "list":
        try:
          data = functions.get_all_chats_info(True)
          if not data:
            await _writeln(writer, "no chats registered.")
            continue
          now = time.time()
          for c in data:
            cid = c.get("chat_id") or c.get("chat")
            interval_min = (c.get("interval") or 0) / 60
            last = c.get("last_sent") or 0
            age = int(now - last) if last else "never"
            await _writeln(writer, f"{cid}\tinterval={interval_min}min\tlast_sent_age={age}")
        except Exception as e:
          await _writeln(writer, f"error listing: {e}")
        continue

      if cmd == "send":
        if len(parts) < 3:
          await _writeln(writer, "usage: send <chat_id> <message...>")
          continue
        try:
          chat_id = int(parts[1])
        except ValueError:
          await _writeln(writer, "invalid chat_id")
          continue
        message_text = line.split(" ", 2)[2]
        try:
          await bot.send_message(chat_id, message_text)
          functions.update_chat(chat_id, "last_sent", time.time())
          await _writeln(writer, "sent")
        except Exception as e:
          await _writeln(writer, f"send error: {e}")
        continue

      if cmd == "stop":
        await _writeln(writer, "stopping bot.")
        global running
        running = False
        continue
      
      if cmd == "status":
        try:
          chats = functions.get_all_chats_info(True) or []
          await _writeln(writer, f"running={bool(running)} chats={len(chats)}")
        except Exception as e:
          await _writeln(writer, f"status error: {e}")
        continue

      await _writeln(writer, f"unknown command: {cmd}")
  except Exception as e:
    try:
      await _writeln(writer, f"console handler error: {e}")
    except Exception:
      pass
  finally:
    try:
      writer.close()
      await writer.wait_closed()
    except Exception:
      pass

async def main():
  if os.path.exists(socket_path):
    try:
      os.unlink(socket_path)
    except Exception as e:
      print({e})
  # server = await asyncio.start_unix_server(console_handler, path=socket_path)
  print(f"Console socket listening at {socket_path}")
  asyncio.create_task(dp.start_polling(bot))
  while running:
    try:
      data = functions.get_all_chats_info(True)
      for chat in data:
        if time.time() - chat["last_sent"] >= chat["interval"]:
          chat_id = chat["chat_id"]
          question = await online.question(functions.get_chat_info(chat_id, True)["boards"])
          await bot.send_message(chat, question)
          functions.update_chat(chat, "last_sent", time.time())
          print(f'Sent a "{question}" question to {chat}')   
      await asyncio.sleep(5)

    except TelegramForbiddenError:
      chat_id = chat["chat_id"]
      functions.remove_chat(chat_id)
      print(f"Removed chat {chat_id}")
    except TelegramRetryAfter as e:
      print(f"Flood limit, retry after {e.timeout} seconds")
      await asyncio.sleep(e.timeout + 2)
    except TelegramNetworkError:
      print("Network issue, retrying later")
      await asyncio.sleep(5)

if __name__ == "__main__":
  running = True
  # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  print("\nBot's running")
  try:
    asyncio.run(main())
  except TelegramNetworkError:
    print("Couldn't connect to telegram")