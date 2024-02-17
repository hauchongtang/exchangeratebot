from telegram import Update
from telegram.ext import Updater, CallbackContext

import api
from common import CURRENCY_NOT_FOUND_ERROR, COMMAND_NOT_FOUND_ERROR
from helper import is_command_in_text, RateParser, DataParser
from main import logger


def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def get_exchange_rate(update: Update, context: CallbackContext):
    message_txt: str = update.message.text

    if not is_command_in_text(text=message_txt, command='/getrate'):
        return COMMAND_NOT_FOUND_ERROR

    data_txt = DataParser(text=message_txt, command='/getrate').parse_as_str()
    target_curr_mapping = RateParser(data=data_txt).parse_to_dict()
    latest_exchg_rates = api.get_latest_exchange_rates(base_currency='SGD')['data']  # TODO: Feature to allow set base

    if target_curr_mapping['from'] not in latest_exchg_rates:
        error_msg = CURRENCY_NOT_FOUND_ERROR.format('[FROM]')
        update.message.reply_text(text=error_msg)
        return error_msg

    if target_curr_mapping['to'] not in latest_exchg_rates:
        error_msg = CURRENCY_NOT_FOUND_ERROR.format('[TO]')
        update.message.reply_text(text=error_msg)
        return error_msg

    # Manipulate data to get desired exchange rate
    result_str = f"Exchange rate of {data_txt} is 1 SGD - 111 JPY"
    update.message.reply_text(result_str)
    return result_str
