#!/usr/bin/env python
"""
jsthlmnAI — English Learning Telegram Bot
Powered by Google Gemini + python-telegram-bot
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Gemini setup ───────────────────────────────────────────────────────────
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are jsthlmnAI, a friendly and encouraging English learning assistant for Indonesian learners. You communicate in a mix of English and Bahasa Indonesia to make learning comfortable.

You have 6 learning modes:

1. TENSES QUIZ — Give the user ONE English sentence. Wrap the key verb phrase in asterisks like *has been studying*. Ask them to identify the tense. After they answer:
   - Reply ✅ Benar! or ❌ Belum tepat
   - Give the correct tense name
   - Explain briefly in Bahasa Indonesia
   - Show the grammar formula (e.g. has/have + been + V-ing)
   - End with: "Ketik /next untuk soal berikutnya atau /menu untuk kembali."

2. VOCAB CHALLENGE — Give ONE English word. Ask user to translate to Bahasa Indonesia. Give feedback with correct meaning + brief example. Track progress like "Kata 3 dari 10". After 10 words show a score summary. End each turn with: "Ketik /next untuk kata berikutnya."

3. VERB FORMS — Present a clean list of 10 verbs with V1 | V2 | V3. Mix regular and irregular verbs. Use a clean text table format. End with: "Ketik /quiz untuk kuis verb ini, atau /menu untuk kembali."

4. READING COMPREHENSION — Send a short paragraph (3-5 sentences). Ask 2 comprehension questions. Give clear feedback on answers.

5. WRITING PROMPT — Give a simple topic. Ask user to write 3-5 sentences. Give detailed feedback on grammar, vocabulary, and suggest improvements.

6. MY PROGRESS — Be encouraging. Ask what they've been practicing and give personalized tips.

Keep responses concise and conversational. Use emojis sparingly. Always be encouraging and patient.
When user makes a mistake, explain clearly why in Bahasa Indonesia.
Never use markdown headers (##). Use *bold* sparingly for key terms only.
Keep each message short enough to read comfortably on mobile."""

# Mode labels
MODES = {
    "tenses":  ("1️⃣ Tenses Quiz",         "Tebak tense dari kalimat nyata"),
    "vocab":   ("2️⃣ Vocab Challenge",      "10 kata, terjemahkan ke Bahasa Indonesia"),
    "verbs":   ("3️⃣ Verb Forms",           "Daftar V1, V2, V3 lengkap"),
    "reading": ("4️⃣ Reading Comprehension","Baca paragraf & jawab pertanyaan"),
    "writing": ("5️⃣ Writing Prompt",       "Tulis kalimat, dapat feedback AI"),
    "progress":("6️⃣ My Progress",          "Pantau semangat belajarmu"),
}

# ── Helpers ────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(MODES["tenses"][0],   callback_data="mode_tenses"),
         InlineKeyboardButton(MODES["vocab"][0],    callback_data="mode_vocab")],
        [InlineKeyboardButton(MODES["verbs"][0],    callback_data="mode_verbs"),
         InlineKeyboardButton(MODES["reading"][0],  callback_data="mode_reading")],
        [InlineKeyboardButton(MODES["writing"][0],  callback_data="mode_writing"),
         InlineKeyboardButton(MODES["progress"][0], callback_data="mode_progress")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_menu"),
        InlineKeyboardButton("▶️ Next",      callback_data="next_question"),
    ]])


def next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Next", callback_data="next_question"),
        InlineKeyboardButton("🏠 Menu", callback_data="back_menu"),
    ]])


def menu_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_menu"),
    ]])


async def ask_gemini(user_data: dict, user_message: str) -> str:
    """Send message to Gemini with full conversation history."""
    try:
        gemini_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        history = user_data.get("history", [])
        chat = gemini_model.start_chat(history=history)
        response = await chat.send_message_async(user_message)
        reply = response.text

        # Update history
        history.append({"role": "user",  "parts": [user_message]})
        history.append({"role": "model", "parts": [reply]})
        user_data["history"] = history

        return reply
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "Maaf, ada gangguan teknis. Coba lagi ya! 😅"


# ── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    context.user_data.clear()
    context.user_data["history"] = []

    text = (
        "Halo! 👋 Selamat datang di *jsthlmnAI* 🎓\n"
        "Your personal English trainer — siap belajar bareng kamu!\n\n"
        "Pilih mode belajar di bawah ini:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command."""
    context.user_data["mode"] = None
    await update.message.reply_text(
        "🏠 *Main Menu* — Pilih mode belajar kamu:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /next command — continue current mode."""
    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text(
            "Pilih mode dulu ya! 😊",
            reply_markup=main_menu_keyboard()
        )
        return

    mode_prompts = {
        "tenses":  "Berikan satu soal tenses baru. Tampilkan kalimat dengan verb yang ditandai *asterisks*.",
        "vocab":   "Berikan kata vocab berikutnya untuk diterjemahkan.",
        "verbs":   "Berikan daftar 10 verb baru dengan V1, V2, V3.",
        "reading": "Berikan paragraf baru untuk reading comprehension.",
        "writing": "Berikan writing prompt baru.",
        "progress":"Berikan tips motivasi belajar bahasa Inggris.",
    }

    prompt = mode_prompts.get(mode, "Lanjutkan sesi belajar.")
    await update.message.chat.send_action("typing")
    reply = await ask_gemini(context.user_data, prompt)
    await update.message.reply_text(reply, parse_mode="Markdown", reply_markup=next_keyboard())


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Back to menu ──
    if data == "back_menu":
        context.user_data["mode"] = None
        await query.edit_message_text(
            "🏠 *Main Menu* — Pilih mode belajar kamu:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    # ── Next question ──
    if data == "next_question":
        mode = context.user_data.get("mode")
        if not mode:
            await query.edit_message_text(
                "Pilih mode dulu ya! 😊",
                reply_markup=main_menu_keyboard()
            )
            return

        mode_prompts = {
            "tenses":  "Berikan satu soal tenses baru. Tampilkan kalimat dengan verb yang ditandai *asterisks*.",
            "vocab":   "Berikan kata vocab berikutnya untuk diterjemahkan. Pilih kata dari level A1, A2, B1, B2, atau C1 (CEFR).",
            "verbs":   "Berikan daftar 10 verb baru dengan V1, V2, V3.",
            "reading": "Berikan paragraf baru untuk reading comprehension.",
            "writing": "Berikan writing prompt baru.",
            "progress":"Berikan tips motivasi belajar bahasa Inggris.",
        }
        prompt = mode_prompts.get(mode, "Lanjutkan sesi belajar.")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.chat.send_action("typing")
        reply = await ask_gemini(context.user_data, prompt)
        await query.message.reply_text(reply, parse_mode="Markdown", reply_markup=next_keyboard())
        return

    # ── Mode selection ──
    if data.startswith("mode_"):
        mode = data.replace("mode_", "")
        context.user_data["mode"] = mode
        context.user_data["history"] = []  # fresh history per mode

        mode_starters = {
            "tenses": (
                "🎯 *Tenses Quiz*\n"
                "Baca kalimatnya dan tebak tense yang digunakan!\n\n"
                "Berikan satu soal tenses. Tampilkan kalimat dengan verb yang ditandai *asterisks*."
            ),
            "vocab": (
                "📚 *Vocab Challenge*\n"
                "Terjemahkan kata-kata berikut ke Bahasa Indonesia!\n\n"
                "Mulai vocab challenge set baru. Berikan kata pertama dari 10 kata. Pilih kata secara acak dari level A1, A2, B1, B2, atau C1 (CEFR), dan tampilkan levelnya di setiap soal."
            ),
            "verbs": (
                "📋 *Verb Forms*\n"
                "Pelajari V1, V2, V3 dari berbagai kata kerja!\n\n"
                "Tampilkan daftar 10 verb dengan V1, V2, V3 dalam format tabel teks yang rapi."
            ),
            "reading": (
                "📖 *Reading Comprehension*\n"
                "Baca paragraf dan jawab pertanyaan!\n\n"
                "Berikan paragraf pendek (3-5 kalimat) diikuti 2 pertanyaan pemahaman."
            ),
            "writing": (
                "✍️ *Writing Prompt*\n"
                "Tulis kalimat dan dapatkan feedback dari AI!\n\n"
                "Berikan satu writing prompt yang menarik. Minta user menulis 3-5 kalimat."
            ),
            "progress": (
                "📊 *My Progress*\n"
                "Yuk lihat semangat belajarmu!\n\n"
                "Berikan pesan motivasi yang menyemangati dan tanyakan apa yang sudah dipelajari user hari ini."
            ),
        }

        intro_and_prompt = mode_starters.get(mode, "Mulai sesi belajar.")
        parts = intro_and_prompt.split("\n\n", 1)
        intro = parts[0]
        gemini_prompt = parts[1] if len(parts) > 1 else intro

        # Show intro first
        await query.edit_message_text(intro, parse_mode="Markdown")

        # Get Gemini response
        await query.message.chat.send_action("typing")
        reply = await ask_gemini(context.user_data, gemini_prompt)

        keyboard = next_keyboard() if mode in ("tenses", "vocab", "verbs") else menu_only_keyboard()
        await query.message.reply_text(reply, parse_mode="Markdown", reply_markup=keyboard)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all free-text user messages."""
    mode = context.user_data.get("mode")
    user_text = update.message.text

    # No mode selected yet
    if not mode:
        await update.message.reply_text(
            "Pilih mode belajar dulu ya! 👇",
            reply_markup=main_menu_keyboard()
        )
        return

    await update.message.chat.send_action("typing")
    reply = await ask_gemini(context.user_data, user_text)

    keyboard = next_keyboard() if mode in ("tenses", "vocab", "verbs") else menu_only_keyboard()
    await update.message.reply_text(reply, parse_mode="Markdown", reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    text = (
        "🤖 *jsthlmnAI — Commands*\n\n"
        "/start — Mulai dari awal\n"
        "/menu  — Kembali ke main menu\n"
        "/next  — Soal/kata berikutnya\n"
        "/help  — Tampilkan bantuan ini\n\n"
        "Atau gunakan tombol inline di bawah setiap pesan!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("❌ TELEGRAM_TOKEN tidak ditemukan! Set environment variable dulu.")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("❌ GEMINI_API_KEY tidak ditemukan! Set environment variable dulu.")

    print("\n🎓 jsthlmnAI — Telegram Bot")
    print("=" * 40)
    print("✅ Bot is starting...")
    print("📱 Open Telegram and search your bot")
    print("=" * 40)
    print("Press Ctrl+C to stop\n")

    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("menu",   menu_command))
    app.add_handler(CommandHandler("next",   next_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
