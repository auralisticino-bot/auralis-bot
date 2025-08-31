import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# === Config ===
load_dotenv("AuraLisKey.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)

# Limite messaggi per beta
MAX_MESSAGES = 15
user_usage = {}   # user_id -> count

# Link utili
WAITLIST_URL = "https://auralisbot.carrd.co"   # metti il tuo Carrd
FEEDBACK_URL = "https://forms.gle/..."         # metti il tuo Google Form

WELCOME = (
    "Ciao! Sono **AuraLis** 🌿 il tuo compagno digitale.\n"
    "Posso aiutarti con **stress**, **sonno** e **benessere quotidiano**.\n\n"
    "Scegli una prova rapida qui sotto o scrivimi liberamente.\n"
    "_Info generali, non è un consulto medico. In emergenza chiama il 144._"
)

SYSTEM = (
    "You are AuraLis, a warm, empathetic digital health companion for everyday wellbeing."
    " Be concise (<=120 words). Offer practical steps users can do now."
    " Never give diagnoses or drug dosages. Avoid medical claims."
    " Always end with: 'Info generali, non è un consulto medico. In emergenza chiama il 144.'"
    " Finish with a friendly follow-up question."
)

QUICK_SUGGESTIONS = [
    ["🧘 2-minute de-stress", "😴 Routine per dormire", "💨 Respirazione 4-7-8"],
    ["📋 Check-in stress", "⏱️ Pomodoro 25'", "💡 Abitudine micro-passo"]
]

def build_quick_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(t) for t in row] for row in QUICK_SUGGESTIONS],
        resize_keyboard=True, one_time_keyboard=False
    )

def cta_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔓 Ottieni accesso esteso", url=WAITLIST_URL)],
         [InlineKeyboardButton("📝 Lascia un feedback", url=FEEDBACK_URL)]]
    )

def inc_usage(user_id: int) -> int:
    user_usage[user_id] = user_usage.get(user_id, 0) + 1
    return user_usage[user_id]

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(WELCOME, reply_markup=build_quick_keyboard())

async def menu(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Scegli una prova rapida 👇", reply_markup=build_quick_keyboard())

async def info(update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "AuraLis è un *compagno digitale* che suggerisce pratiche semplici per stress, sonno e benessere."
        " Versione **beta** pubblica limitata a scopo di test.\n\n"
        f"🔗 Scopri di più / iscriviti: {WAITLIST_URL}\n"
        f"📝 Feedback: {FEEDBACK_URL}\n\n"
        "_Info generali, non è un consulto medico. In emergenza 144._"
    )
    await update.message.reply_markdown(txt, reply_markup=cta_keyboard())

async def feedback(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Grazie! Apri il modulo per dirci cosa ne pensi:", reply_markup=cta_keyboard())

def map_quick_intent(text: str) -> str | None:
    t = text.lower().strip()
    if "2-minute" in t or "2-minute" in t or "de-stress" in t or "stress" in t:
        return "Suggerisci un esercizio de-stress di 2 minuti da fare ora."
    if "routine per dormire" in t or "dormire" in t or "sonno" in t:
        return "Proponi una routine semplice pre-sonno di 10 minuti da fare stasera."
    if "4-7-8" in t or "4-7-8" in t or "respirazione" in t:
        return "Guida l'utente nella respirazione 4-7-8 passo passo per 4 cicli."
    if "check-in" in t or "check-in" in t:
        return "Fai un check-in stress in 3 domande brevi e suggerisci 1 azione pratica."
    if "pomodoro" in t or "25" in t:
        return "Spiega rapidamente la tecnica del Pomodoro con 1 ciclo da 25 minuti e 1 pausa da 5."
    if "abitudine" in t or "micro" in t:
        return "Aiuta a scegliere un micro-passo per costruire un'abitudine salutare."
    return None

async def handle_text(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text_in = update.message.text or ""

    # Limite beta
    used = inc_usage(user_id)
    if used > MAX_MESSAGES:
        await update.message.reply_text(
            f"⚠️ Hai raggiunto il limite della beta ({MAX_MESSAGES} messaggi). "
            "Grazie per aver provato AuraLis!",
            reply_markup=cta_keyboard()
        )
        return

    # Intenti rapidi dai bottoni
    quick = map_quick_intent(text_in)
    user_prompt = quick if quick else text_in

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=350,
            temperature=0.4,
        )
        answer = resp.choices[0].message.content
    except Exception:
        answer = ("Ops, non riesco a rispondere ora. Riprova tra poco. "
                  "Info generali, non è un consulto medico. In emergenza 144.")

    # Aggiungo un piccolo contatore visibile in basso
    footer = f"\n\n— Beta: messaggi usati {used}/{MAX_MESSAGES}"
    await update.message.reply_text(answer + footer)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ AuraLis Beta avviato. Premi Ctrl+C per fermarlo.")
    app.run_polling()

if __name__ == "__main__":
    main()