from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import logging
import windfinder
import os
import datetime

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
chat_id = os.getenv("chat_id")

location = "weston_southampton"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def windfinderBot(context: CallbackContext):
    job = context.job
    text = windfinder.produceForecastText(location)
    context.bot.send_message(job.context, text=text)


def remove_job(name: str, context: CallbackContext):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    for job in current_jobs:
        job.schedule_removal()


def stop(update: Update, context: CallbackContext):
    # chat_id = update.message.chat_id
    remove_job(str(chat_id), context)

    update.message.reply_text("Stopping")


def main():
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("stop", stop))

    updater.job_queue.run_daily(windfinderBot, datetime.time(hour=8), context=chat_id, name=str(chat_id))  # Windfinder
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
