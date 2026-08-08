#!/usr/bin/env python3
"""
Duck le Quack bot skeleton.

Not a production bot. This is a placeholder for Phase 1.
Requires python-telegram-bot and a BOT_TOKEN env var.

Commands:
  /start  — welcome + disclaimer
  /quack  — random duck content
  /wallet — save a Solana wallet address for future fair-drop snapshot
  /about  — honest disclaimer
"""

import os
import random
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUACKS = [
    "🦆 Quack.",
    "🦆 A duck walked into a bar. The bartender said, 'What can I get you?' The duck said, 'Just put it on my bill.'",
    "🦆 What do you call a duck that steals? A robber ducky.",
    "🦆 Why did the duck join the band? Because he had the drumsticks.",
    "🦆 Duck fact: ducks can see in color.",
    "🦆 Duck fact: ducks have waterproof feathers.",
    "🦆 Duck fact: a group of ducks is called a paddling.",
    "🦆 Honk if you love ducks. Wait, that's geese. Quack.",
    "🦆 The only thing rarer than this duck is the whitepaper. There isn't one.",
    "🦆 Remember: this is a duck. Not a financial advisor.",
]


def require_token():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN environment variable.")
    return token


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦆 Welcome to Duck le Quack.\n\n"
        "This is a fun social experiment. There is no token yet.\n"
        "No presale. No team allocation. No profit promise.\n\n"
        "Commands:\n"
        "/quack — get a duck fact or joke\n"
        "/wallet <solana-address> — save your wallet for future fair-drop\n"
        "/about — the honest disclaimer"
    )


async def quack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(QUACKS))


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /wallet <solana-address>\n"
            "Save your Solana address for the future fair-drop snapshot."
        )
        return
    address = context.args[0]
    # TODO: validate Solana address, store in database, ensure one address per user.
    await update.message.reply_text(
        f"🦆 Got it: {address[:6]}...{address[-4:]}\n"
        "Saved for the future fair-drop snapshot. No token yet. Stay tuned."
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦆 Duck le Quack ($QUACK) is a planned social token on Solana.\n\n"
        "It is not a security. It is not an investment. It is not a product.\n"
        "It is a duck that people can send to each other for fun.\n\n"
        "Phase 1: bot + website + community.\n"
        "Phase 2: fair-drop. No presale. No team allocation.\n\n"
        "If you are here for profit, you are in the wrong pond."
    )


async def main():
    app = ApplicationBuilder().token(require_token()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quack", quack))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("about", about))
    logger.info("Duck le Quack bot starting...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
