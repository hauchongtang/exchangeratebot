import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

import handlers

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


class ExchangeRateBot:
    def __init__(self, token: str, domain: str):
        self.domain = domain
        self.token = token
        self.PORT = int(os.environ.get('PORT', '8443'))
        self.updater = Updater(token=self.token, use_context=True)

        # Dispatcher to register handlers
        self.dp: Updater.dispatcher = self.updater.dispatcher

    def register_handlers(self):
        self.dp.add_handler(CommandHandler('getrate', handlers.get_exchange_rate))
        return self

    def start(self):
        self.updater.start_webhook(
            listen='0.0.0.0',
            port=int(self.PORT),
            url_path=self.token,
            webhook_url=f"{self.domain}{self.token}"
        )
        self.updater.idle()


if __name__ == '__main__':
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    webhook_domain = os.environ.get('DOMAIN', '')
    ExchangeRateBot(token=TOKEN, domain=webhook_domain)\
        .register_handlers()\
        .start()
