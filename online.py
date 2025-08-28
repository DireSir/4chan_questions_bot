import json
import html
import aiohttp
import asyncio
import re
import random
from bs4 import BeautifulSoup

async def fetch_a_4chan_json(board: str):
  url = f"https://a.4cdn.org/{board}/catalog.json"
  async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
      data = await resp.json()
      return data

def extract_questions(raw_html: str):
  soup = BeautifulSoup(raw_html, "html.parser")

  for br in soup.find_all("br"):
    br.replace_with("\n")

  for quote in soup.find_all("span", class_="quote"):
    quote.decompose()

  text = html.unescape(soup.get_text())
  text = re.sub(r'https?://\S+', '', text)
  sentences = re.split(r'(?<=[.?!])\s+', text)
  questions = [s.strip() for s in sentences if '?' in s]

  return questions

async def get_a_question(data) -> str:
  all_questions = []
  for page in data:
    for thread in page.get("threads", []):
      op = thread.get("com", "")
      if op:
        all_questions.extend(extract_questions(op))
      for reply in thread.get("last_replies", []):
        text = reply.get("com", "")
        if text:
          all_questions.extend(extract_questions(text))
    if all_questions:
      break

  if all_questions:
    return random.choice(all_questions)
  return None

async def question():
  data = await fetch_a_4chan_json("pol")
  question = await get_a_question(data)
  return question