import os

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters
from pytz import timezone
import datetime
import logging

import api
import helper
from analysis import GraphViewer
from common import CURRENCY_NOT_FOUND_ERROR, COMMAND_NOT_FOUND_ERROR, DEFAULT_SVC_CHARGE_RATE
from database import logic
from helper import is_command_in_text, RateParser, DataParser, ScheduleParser

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def help_handler(update: Update, context: CallbackContext):
    help_str = """
    Welcome to exchange rate bot! Here are some helpful commands~\n\n
    Get Exchange Rate of SGD to JPY:\n
    /getrate SGD-JPY\n\n
    Set exchange rate reminder for SGD-MYR at 3.6:\n
    /conditionalratealert SGD-MYR/3.6\n\n
    Set daily alerts for SGD-GBP at 9pm:\n
    /addratealert SGD-GBP/DAILY 21:00\n\n
    Gst & Service Charge calculator (Two-way):\n
    /start_gst
    """
    update.message.reply_text(help_str)
    return help_str


def get_exchange_rate(update: Update, context: CallbackContext):
    message_txt: str = update.message.text

    if not is_command_in_text(text=message_txt, command='/getrate'):
        return COMMAND_NOT_FOUND_ERROR

    data_txt = DataParser(text=message_txt, command='/getrate').parse_as_str()
    latest_exchg_rates, target_curr_mapping = get_rate_map(data_txt)

    print(target_curr_mapping)
    print(latest_exchg_rates)
    if target_curr_mapping['from'] not in api.valid_currencies:
        error_msg = CURRENCY_NOT_FOUND_ERROR.format('[FROM]')
        update.message.reply_text(text=error_msg)
        return error_msg

    if target_curr_mapping['to'] not in api.valid_currencies:
        error_msg = CURRENCY_NOT_FOUND_ERROR.format('[TO]')
        update.message.reply_text(text=error_msg)
        return error_msg

    # Manipulate data to get desired exchange rate
    result_str = f"Exchange rate of {data_txt} is 1 SGD - {latest_exchg_rates[target_curr_mapping['to']]}"
    update.message.reply_text(text=result_str)
    return result_str


def get_rate_map(data_txt, execute_get_exchg_rates=True):
    target_curr_mapping = RateParser(data=data_txt).parse_to_dict()
    if not execute_get_exchg_rates:
        return {}, target_curr_mapping
    latest_exchg_rates = api.get_latest_exchange_rates(
        base_currency=target_curr_mapping['from'], currencies=target_curr_mapping['to'])['data']
    return latest_exchg_rates, target_curr_mapping


# /addratealert SGD-JPY/DAILY 10:00
def turn_on_exchange_rate_alert(update: Update, context: CallbackContext):
    tz = timezone('Asia/Singapore')
    message_txt: str = update.message.text
    if not is_command_in_text(text=message_txt, command='/addratealert'):
        return COMMAND_NOT_FOUND_ERROR

    data_txt = DataParser(text=message_txt, command='/addratealert').parse_as_str()
    currency_str, freq_time_str = data_txt.split('/')

    # Handle freq and time
    freq, time_hh_mm_tuple = ScheduleParser.parse(data=freq_time_str)
    h, m = time_hh_mm_tuple
    target_time_to_run = datetime.time(hour=int(h), minute=int(m), tzinfo=tz)

    # Handle currency
    latest_exchg_rates, target_curr_mapping = get_rate_map(data_txt=currency_str, execute_get_exchg_rates=False)

    if update.effective_message is not None:
        chat_id = str(update.message.chat_id)
        context.job_queue.run_daily(get_exchange_rate_analysis, time=target_time_to_run, days=(0, 1, 2, 3, 4, 5, 6),
                                    name=str(chat_id),
                                    context={
                                        'target_curr_mapping': target_curr_mapping,
                                        'chat_id': chat_id
                                    })
        update.message.reply_text(f"Exchange Rate Alert enabled {freq.upper()} at {freq_time_str.strip()} for "
                                  f"{target_curr_mapping['from']}"
                                  f"-{target_curr_mapping['to']}")


def get_historical_rates(dates, curr_from, curr_to):
    result = {}
    for d in range(len(dates) - 1):
        historical_data = api.get_historical_data(base_currency=curr_from,
                                                  currencies=curr_to, date=dates[d])['data']
        result[dates[d]] = historical_data[dates[d]][curr_to]
    return result


def get_exchange_rate_analysis(context: CallbackContext):
    job = context.job
    if job is not None and job.context is not None:
        args_dict: object = job.context

        target_curr_mapping = args_dict['target_curr_mapping']
        curr_from = target_curr_mapping['from']
        curr_to = target_curr_mapping['to']
        latest_exchg_rates = api.get_latest_exchange_rates(
            base_currency=curr_from, currencies=curr_to)['data']

        result_str = f"Exchange rate of {curr_from}-{curr_to} is 1 {curr_from} - " \
                     f"{latest_exchg_rates[target_curr_mapping['to']]} {curr_to}"

        # Define the number of dates (50) and months to cover (6)
        num_dates = 10
        months_to_cover = 2

        # Get the current date
        now = datetime.datetime.now()

        # Calculate the start date of the period (3 months ago)
        start_date = now - datetime.timedelta(days=30 * months_to_cover)

        # Calculate the number of days between each date (rounded up)
        days_between = (now - start_date).days // (num_dates - 1)

        # Create an array to store the date strings
        date_str_array = []

        # Loop through the desired dates, adding them to the array
        for i in range(num_dates):
            date = start_date + datetime.timedelta(days=i * days_between)
            date_str_array.append(date.strftime("%Y-%m-%d"))
        tdy_date_str = now.strftime("%Y-%m-%d")
        date_str_array.append(tdy_date_str)

        # Find the last 5 peaks
        historical_rates_per_date_list = get_historical_rates(dates=date_str_array, curr_from=curr_from,
                                                              curr_to=curr_to)
        historical_rates_per_date_list[tdy_date_str] = latest_exchg_rates[target_curr_mapping['to']]

        # Render and send a graph of the peaks
        graph_img, caption = GraphViewer(data=historical_rates_per_date_list).get_n_peaks(5).generate_graph()
        caption += f"\n{result_str} today!"
        context.bot.send_photo(chat_id=args_dict['chat_id'], photo=graph_img, caption=caption)


def turn_on_conditional_rate_alert(update: Update, context: CallbackContext):
    # tz = timezone('Asia/Singapore')
    message_txt: str = update.message.text
    if not is_command_in_text(text=message_txt, command='/conditionalratealert'):
        return COMMAND_NOT_FOUND_ERROR

    data_txt = DataParser(text=message_txt, command='/conditionalratealert').parse_as_str()
    currency_str, target_rate_str = data_txt.split('/')

    # Handle currency
    _, target_curr_mapping = get_rate_map(data_txt=currency_str, execute_get_exchg_rates=False)
    # Add user's target currency
    target_curr_mapping['target'] = float(target_rate_str)

    if update.effective_message is not None:
        chat_id = str(update.message.chat_id)
        context.job_queue.run_repeating(get_exchange_rate_if_target,
                                        interval=int(os.environ.get("COND_RATE_CHECK_INTERVAL", 600)), name=str(chat_id),
                                        context={
                                            'target_curr_mapping': target_curr_mapping,
                                            'chat_id': chat_id
                                        })
        update.message.reply_text(f"Reminder enabled for {target_curr_mapping['from']}-{target_curr_mapping['to']} "
                                  f"at {target_rate_str}")


def get_exchange_rate_if_target(context: CallbackContext):
    time_now = datetime.datetime.now()
    if (not (9 < time_now.hour <= 19)) or (time_now.weekday() >= 5):
        if time_now.weekday() < 5:
            logger.info("get_exchange_rate_if_target -> Inactive Hours, No Triggers")
        else:
            logger.info("get_exchange_rate_if_target -> Weekends, No Triggers")
        return

    job = context.job
    if job is not None and job.context is not None:
        args_dict: object = job.context

        target_curr_mapping = args_dict['target_curr_mapping']
        curr_from = target_curr_mapping['from']
        curr_to = target_curr_mapping['to']
        latest_exchg_rates = api.get_latest_exchange_rates(
            base_currency=curr_from, currencies=curr_to)['data']

        logger.info("Executing Job...\n", latest_exchg_rates)

        latest_target_rate = latest_exchg_rates[target_curr_mapping['to']]

        user_target_to_notify = target_curr_mapping['target']
        if latest_target_rate >= user_target_to_notify:
            result_str = f"ALERT⚠️\nExchange rate of {curr_from}-{curr_to} is 1 {curr_from} - " \
                         f"{latest_target_rate} {curr_to} vs your set target of " \
                         f"{user_target_to_notify}"
            last_rate, last_update = logic.get_last_saved_exchange_rate(curr_to, latest_target_rate)
            if latest_target_rate > last_rate:
                logic.update_exchange_rate(curr_to, latest_target_rate)
            if latest_target_rate > last_rate and \
                    (abs(abs(60 - last_update.minute) - abs(60 - datetime.datetime.now().minute))
                     == int(os.environ.get("COND_RATE_REMIND_INTERVAL", 45))):
                logger.info("handlers.get_exchange_rate_if_target -> Interval reminder executed")
                logger.info((abs(abs(60 - last_update.minute) - abs(60 - datetime.datetime.now().minute))))
                chat_id = args_dict['chat_id']
                context.bot.send_message(chat_id, result_str)
            else:
                logger.info("handlers.get_exchange_rate_if_target -> Interval reminder did not execute")


CHOOSE_Forwards_Reverse, SET_COST, SET_SVC_CHARGE_RATE, DISPLAY_GST_SVC_RESULT = range(4)

reply_keyboard = [
    ["GST Only", "GST & Svc Charge"],
    ["Service Charge Only"],
]
choose_gst_svc_charge_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
reply_keyboard = [
    ["Forwards", "Reverse"]
]
choose_charge_direction_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def gst_service_charge_choice_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Hi, welcome to GST & Svc charge calculator!\nPlease select the your receipt type!",
                              reply_markup=choose_gst_svc_charge_markup)
    logger.info(f"Executed start_gst, moving on to CHOOSE_Forwards_Reverse")
    return CHOOSE_Forwards_Reverse


def gst_service_charge_direction_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please choose the direction of calculation!\n"
                              "Forward: Get Post GST and/or Svc Charge price\n"
                              "Reverse: Get the actual price before GST and/or Svc Charge",
                              reply_markup=choose_charge_direction_markup)
    context.user_data[f"gst_svc_options_{update.effective_user.id}"] = update.message.text
    logger.info(f"Saved: {update.message.text}, moving on to SET_COST")
    return SET_COST


def set_cost_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please input the total cost!")

    direction = update.message.text
    context.user_data[f"gst_svc_direction_{update.effective_user.id}"] = direction

    choice = context.user_data[f"gst_svc_options_{update.effective_user.id}"]
    if choice == "GST Only":
        logger.info(f"Choice: {choice}, Direction Saved: {direction}, Moving on to DISPLAY_GST_SVC_RESULT")
        return DISPLAY_GST_SVC_RESULT
    logger.info(f"Choice: {choice}, Direction Saved: {direction}, Moving on to SET_SVC_CHARGE_RATE")
    return SET_SVC_CHARGE_RATE


def set_svc_charge_rate(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter the service charge rate in decimal!")

    continue_get_cost = False
    try:
        if context.user_data[f"cost_{update.effective_user.id}"] == 0:
            continue_get_cost = True
    except Exception:
        continue_get_cost = True

    if not continue_get_cost:
        logger.info("Cost already found. Going to DISPLAY_GST_SVC_RESULT")
        return DISPLAY_GST_SVC_RESULT

    incoming_cost = update.message.text
    if not (helper.is_float(incoming_cost)):
        logger.warning(f"Incoming cost is not decimal, moving on back to CHOOSE_Forwards_Reverse")
        return CHOOSE_Forwards_Reverse
    context.user_data[f"cost_{update.effective_user.id}"] = float(incoming_cost)

    logger.info(f"Saved Cost: {incoming_cost}, Moving on to DISPLAY_GST_SVC_RESULT")
    return DISPLAY_GST_SVC_RESULT


def generic_info_received_handler(update: Update, context: CallbackContext):
    choice = context.user_data[f"gst_svc_options_{update.effective_user.id}"]
    direction = context.user_data[f"gst_svc_direction_{update.effective_user.id}"]
    cost = context.user_data[f"cost_{update.effective_user.id}"]
    if choice.upper() != "GST_ONLY" and not helper.is_float(update.message.text):
        logger.warning(f"Incoming cost is not decimal, moving on back to SET_SVC_CHARGE_RATE")
        update.message.reply_text(f"Svc Charge Rate is not decimal, Please try again!\n"
                                  f"Reply with something to proceed.")
        return SET_SVC_CHARGE_RATE

    number = float(update.message.text)
    if (not 0 <= number <= DEFAULT_SVC_CHARGE_RATE) and number != 'default':
        logger.warning(f"Incoming cost is not within 0 and 0.1, moving on back to SET_SVC_CHARGE_RATE")
        update.message.reply_text(f"Svc Charge Rate is not within 0 and 0.1, Please try again!\n"
                                  f"Reply with something to proceed.")
        return SET_SVC_CHARGE_RATE

    to_set = DEFAULT_SVC_CHARGE_RATE
    if number != 'default':
        to_set = number
    context.user_data[f"svc_charge_rate_{update.effective_user.id}"] = to_set

    svc_charge_rate = context.user_data[f"svc_charge_rate_{update.effective_user.id}"]
    calculator = helper.GSTSvcChargeCalculator(cost) \
        .set_direction(direction) \
        .set_svc_charge(svc_charge_rate) \
        .set_option(choice)

    result = calculator.get_result()
    update.message.reply_text(f"This is the result: ${result}")

    # Wipe the cost to prevent the error handling loop to occur.
    context.user_data[f"cost_{update.effective_user.id}"] = 0
    return ConversationHandler.END


def generic_done_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Thanks for using me, till next time! ☺️")
    return ConversationHandler.END


def gst_service_charge_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('start_gst', gst_service_charge_choice_handler)],
        states={
            CHOOSE_Forwards_Reverse: [
                MessageHandler(filters.Filters.text,
                               gst_service_charge_direction_handler)
            ],
            SET_COST: [
                MessageHandler(filters.Filters.text,
                               set_cost_handler)
            ],
            SET_SVC_CHARGE_RATE: [
                MessageHandler(filters.Filters.text,
                               set_svc_charge_rate)
            ],
            DISPLAY_GST_SVC_RESULT: [
                MessageHandler(filters.Filters.text, generic_info_received_handler)
            ]
        },
        fallbacks=[MessageHandler(filters.Filters.regex("^Done$"), generic_done_handler)]
    )
