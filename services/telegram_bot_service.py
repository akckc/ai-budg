import asyncio
import logging
import os
from datetime import date

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from db import get_db
from services.forecast_service import get_active_recurring_events, get_occurrences_in_window
from services.projection_service import calculate_two_week_projection

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(amount: float) -> str:
    """Format a dollar amount: $1,234.56 or -$234.56."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def _fmt_date(d) -> str:
    """'Mon Apr 21' — cross-platform (no %-d)."""
    return d.strftime("%a %b ") + str(d.day)


def _allowed(update: Update) -> bool:
    """Return True if the message is from the permitted chat (or no restriction set)."""
    if TELEGRAM_CHAT_ID and str(update.effective_chat.id) != str(TELEGRAM_CHAT_ID):
        return False
    return True


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.message.reply_text(
        "Budget Bot is running.\n\n"
        "/summary — 14-day forecast with upcoming bills and safe-to-spend"
    )


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return

    try:
        projection = calculate_two_week_projection()
    except Exception as exc:
        logger.exception("Projection failed")
        await update.message.reply_text(f"Error fetching forecast: {exc}")
        return

    # Fetch upcoming bills directly from recurring events
    today = date.today()
    upcoming = []
    conn = get_db()
    try:
        events = get_active_recurring_events(conn)
        for event in events:
            for occ in get_occurrences_in_window(event, today, window_days=14):
                upcoming.append((occ, event['name'], event['amount']))
    finally:
        conn.close()

    upcoming.sort(key=lambda x: x[0])

    lines = [
        "*Budget Summary*",
        f"Current balance:  {_fmt(projection.starting_balance)}",
        f"Safe to spend:    {_fmt(projection.safe_to_spend)}",
        "",
        "*Upcoming bills — next 14 days:*",
    ]

    if upcoming:
        for occ_date, name, amount in upcoming:
            lines.append(f"  {_fmt_date(occ_date)}  {name}  {_fmt(amount)}")
    else:
        lines.append("  None scheduled")

    end_balance = projection.timeline[-1].projected_balance if projection.timeline else projection.starting_balance
    lines += [
        "",
        f"Projected balance ({_fmt_date(projection.end_date)}):  {_fmt(end_balance)}",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Entry point (called from a daemon thread)
# ---------------------------------------------------------------------------

def start_bot() -> None:
    """Drive the bot manually via asyncio — safe to call from a non-main thread."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")
        return

    async def run() -> None:
        try:
            application = ApplicationBuilder().token(token).build()
            application.add_handler(CommandHandler("start", cmd_start))
            application.add_handler(CommandHandler("summary", cmd_summary))

            async with application:
                await application.initialize()
                await application.start()
                await application.updater.start_polling(drop_pending_updates=True)
                logger.info("Telegram bot polling started.")
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            logger.exception(f"Bot run() raised an exception: {e}")
            raise

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(run())
        except Exception as e:
            logger.exception(f"Bot crashed, restarting in 10 seconds: {e}")
            loop.run_until_complete(asyncio.sleep(10))
