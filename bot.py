# bot.py
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from models import init_db, SessionLocal, User, Farm, Animal, Reminder

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is required")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_ANIMALS, GET_FARM_NAME, GET_COUNT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Mol", "Qo'y", "Tovuq"], ["Echki", "Boshqa"]]
    await update.message.reply_text(
        "Assalomu alaykum! Ferma boshqaruv botiga xush kelibsiz.\n"
        "Boshlash uchun nima boqayotganingizni tanlang (yoki yozing):",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_ANIMALS

async def choosing_animals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['animals_text'] = update.message.text
    await update.message.reply_text("Ferma nomini kiriting (yoki 'skip' deb yozing):")
    return GET_FARM_NAME

async def get_farm_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    farm_name = update.message.text
    context.user_data['farm_name'] = farm_name if farm_name.lower() != 'skip' else None
    await update.message.reply_text("Taxminiy hayvonlar sonini yozing (masalan: 10):")
    return GET_COUNT

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count_text = update.message.text
    try:
        count = int(count_text)
    except ValueError:
        await update.message.reply_text("Iltimos son kiriting (raqam).")
        return GET_COUNT

    animals_text = context.user_data.get('animals_text', '')
    farm_name = context.user_data.get('farm_name')

    db = SessionLocal()
    tg_user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
    if not tg_user:
        tg_user = User(telegram_id=update.effective_user.id, name=update.effective_user.full_name)
        db.add(tg_user); db.commit(); db.refresh(tg_user)

    farm = Farm(user_id=tg_user.id, name=farm_name or "Mening fermam")
    db.add(farm); db.commit(); db.refresh(farm)

    animal = Animal(farm_id=farm.id, types=animals_text, count=count)
    db.add(animal)
    db.commit()

    await update.message.reply_text(f"Rahmat! {animals_text} — {count} ta qilib fermangizga qo‘shildi.")
    db.close()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Onboarding bekor qilindi.")
    return ConversationHandler.END

# Simple /addreminder: format -> /addreminder 2026-08-13 17:00 Emlash: 10 qo'y, 1 qo'chqor
async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Foydalanish: /addreminder YYYY-MM-DD HH:MM Xabar matni\n"
            "Masalan: /addreminder 2026-08-13 17:00 10 ta qora qoyni emlash kerak"
        )
        return
    date_str = args[0]
    time_str = args[1]
    message = " ".join(args[2:])
    try:
        scheduled_at = datetime.fromisoformat(f"{date_str}T{time_str}")
    except Exception:
        await update.message.reply_text("Sana/vaqt formatida xatolik. YYYY-MM-DD HH:MM ni ishlating.")
        return

    db = SessionLocal()
    r = Reminder(telegram_id=update.effective_user.id, message=message, scheduled_at=scheduled_at)
    db.add(r)
    db.commit()
    db.close()
    await update.message.reply_text(f"Eslatma qo‘shildi: {scheduled_at} -> {message}")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    rems = db.query(Reminder).filter(Reminder.telegram_id == update.effective_user.id).order_by(Reminder.scheduled_at).all()
    if not rems:
        await update.message.reply_text("Sizda hech qanday eslatma yo‘q.")
        db.close()
        return
    lines = []
    for r in rems:
        lines.append(f"{r.id}. {r.scheduled_at} -> {r.message} (sent={r.sent})")
    await update.message.reply_text("\n".join(lines))
    db.close()

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Foydalanish: /cancelreminder <id>")
        return
    try:
        rid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Iltimos haqiqiy id kiriting.")
        return
    db = SessionLocal()
    r = db.query(Reminder).filter(Reminder.id == rid, Reminder.telegram_id == update.effective_user.id).first()
    if not r:
        await update.message.reply_text("Bunday eslatma topilmadi.")
        db.close()
        return
    db.delete(r)
    db.commit()
    db.close()
    await update.message.reply_text("Eslatma o‘chirildi.")

# Job to check DB for due reminders
async def job_check_reminders(context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    now = datetime.utcnow()
    due = db.query(Reminder).filter(Reminder.scheduled_at <= now, Reminder.sent == False).all()
    for r in due:
        try:
            await context.bot.send_message(chat_id=r.telegram_id, text=f"Eslatma: {r.message}")
            r.sent = True
            db.add(r)
            db.commit()
        except Exception as e:
            logger.exception("Failed to send reminder %s: %s", r.id, e)
    db.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Onboarding\n"
        "/addreminder YYYY-MM-DD HH:MM Xabar - eslatma qo'shish\n"
        "/listreminders - eslatmalar ro'yxati\n"
        "/cancelreminder <id> - eslatmani o'chirish\n"
        "/help - yordam"
    )

def main():
    init_db()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ANIMALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, choosing_animals)],
            GET_FARM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_farm_name)],
            GET_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("addreminder", add_reminder))
    application.add_handler(CommandHandler("listreminders", list_reminders))
    application.add_handler(CommandHandler("cancelreminder", cancel_reminder))
    application.add_handler(CommandHandler("help", help_command))

    # Run a repeating job every 30 seconds to check reminders (adjust as needed)
    application.job_queue.run_repeating(job_check_reminders, interval=30, first=10)

    application.run_polling()

if __name__ == '__main__':
    main()
