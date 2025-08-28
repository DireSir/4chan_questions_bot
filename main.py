import asyncio
import logging
import time
import functions
from functions import TOKEN
from functions import dialogue
from functions import config
import online

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import BotCommand
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramNetworkError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

class SettingsStates(StatesGroup):
  waiting_for_interval = State()

async def set_commands(bot):
  commands = [
    BotCommand(command="settings", description="z"),
    BotCommand(command="question", description="Get a random question"),
  ]
  await bot.set_my_commands(commands)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
  await message.answer(dialogue["start"])

@dp.message(Command("settings"))
async def settings(message: Message) -> None:
  if message.chat.type == "private":
    await message.reply(dialogue["settings"]["dms"])
    return
  data = functions.get_chat_info(message.chat.id, True)
  interval = data["interval"] / 60
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"{dialogue["settings"]["current_interval"]} {interval} minutes", callback_data="change_interval")],
    [InlineKeyboardButton(text=f"{dialogue["cancel"]}", callback_data="cancel")]
  ])
  await message.reply(text = dialogue["settings"]["main_menu"], reply_markup=keyboard)

@dp.message(Command("question"))
async def question(message: Message) -> None:
  question = await online.question()
  try:
    await message.reply(question)
  except TelegramBadRequest:
    print("Not enough rights to send the message!")

@dp.callback_query()
async def callback_handler(callback: CallbackQuery, state: FSMContext):
  if callback.data == "change_interval":
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
  
  if callback.data == "cancel":
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
  if message.chat.type == "private":
    return

  data = await state.get_data()
  if data.get("requester_id") and data["requester_id"] != message.from_user.id:
    return

  try:
    text = float(message.text.strip())
    if text >= 1:
      interval =  text * 60
    else:
      await message.reply(dialogue["settings"]["interval_too_small"])
      return
  except ValueError:
    await message.reply(dialogue["settings"]["invalid_interval"])
    return

  functions.update_interval(message.chat.id, interval)

  await message.reply(f"Interval updated to {interval / 60} minutes.")
  await state.clear()

@dp.message()
async def message_handler(message: Message) -> None:
  if message.chat.type == "private":
    return
  chat_id = message.chat.id
  latest_message_time = time.time()
  chat_info = functions.get_chat_info(chat_id)
  if not chat_info:
    functions.add_chat(chat_id, latest_message_time)
  else:
    functions.update_last_sent(chat_id, latest_message_time)

async def main():
  await set_commands(bot)
  asyncio.create_task(dp.start_polling(bot))
  while running:
    try:
      data = functions.get_all_chats_info(True)
      for chat in data:
        if time.time() - chat["last_sent"] >= chat["interval"]:
          chat = chat["chat_id"]
          question = await online.question()
          await bot.send_message(chat, question)
          functions.update_last_sent(chat, time.time())
          print(f'Sent a "{question}" question to {chat}')   
      await asyncio.sleep(5)

    except TelegramForbiddenError:
      chat_id = chat["chat_id"]
      functions.remove_chat(chat_id)
      print(f"Removed chat {chat_id}")
    except TelegramRetryAfter as e:
      print(f"Flood limit, retry after {e.timeout} seconds")
      await asyncio.sleep(e.timeout)
    except TelegramNetworkError:
      print("Network issue, retrying later")


running = 0

if __name__ == "__main__":
  running = 1
  # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  print("\nBot's running")
  asyncio.run(main())