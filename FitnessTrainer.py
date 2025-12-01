import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

load_dotenv()

# ---------- Настройки API ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("API_KEY_YANDEX")
PROJECT = os.getenv("PROJECT_YANDEX")

client = OpenAI(
    base_url="https://llm.api.cloud.yandex.net/v1",
    api_key=API_KEY,
)

MODEL = f"gpt://{PROJECT}/gpt-oss-20b/latest"
SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ---------- Ассистент ----------
class Assistant:
    def __init__(self, instructions, model=MODEL):
        self.model = model
        self.instructions = instructions

    def load_session(self, session_id):
        path = f"{SESSIONS_DIR}/{session_id}.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return [{"role": "system", "content": self.instructions}]

    def save_session(self, session_id, history):
        path = f"{SESSIONS_DIR}/{session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def ask(self, user_input, session_id):
        history = self.load_session(session_id)
        history.append({"role": "user", "content": user_input})
        history_to_send = [m for m in history if m.get("content")][-20:]

        res = client.chat.completions.create(
            model=self.model,
            messages=history_to_send,
            temperature=0.1,
            max_tokens=500
        )

        answer = getattr(res.choices[0].message, "content", None) or getattr(res.choices[0], "text", None)
        if not answer:
            answer = "Бот пока не может ответить"

        history.append({"role": "assistant", "content": answer})
        self.save_session(session_id, history)
        return answer

# ---------- Промпт ----------
instructions = """
Ты — профессиональный фитнес-ассистент. Отвечай как энергичный молодой человек. 
Общайся в позитивном тоне. Говори как человек, короткими фразами, избегая перечислений и списков. 
Спроси сначала про противопоказания занятия спортом. 
Если пользователь задает вопросы не по теме фитнеса, то напомни ему о своем функционале. 
Если общение идет в одном диалоге, то не нужно приветствовать пользователя.
"""
assistant = Assistant(instructions)

# ---------- Обработчики ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name  # только имя
    await update.message.reply_text(
        f"Привет, {user_name}! Я твой фитнес-ассистент. Моя цель - помочь тебе достигнуть поставленной цели в спорте. Расскажи мне, у тебя есть противопоказания занятием спорта?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_text = update.message.text
    answer = assistant.ask(user_text, session_id=user_id)
    await update.message.reply_text(answer)

# ---------- Запуск бота ----------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Бот запущен...")
app.run_polling()