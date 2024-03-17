from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters
from pytz import timezone
import datetime

import api
import helper
from analysis import GraphViewer
from common import CURRENCY_NOT_FOUND_ERROR, COMMAND_NOT_FOUND_ERROR
from helper import is_command_in_text, RateParser, DataParser, ScheduleParser
from main import logger


def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


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
        context.job_queue.run_repeating(get_exchange_rate_if_target, interval=3600 * 3, name=str(chat_id),
                                        context={
                                            'target_curr_mapping': target_curr_mapping,
                                            'chat_id': chat_id
                                        })
        update.message.reply_text(f"Reminder enabled for {target_curr_mapping['from']}-{target_curr_mapping['to']} "
                                  f"at {target_rate_str}")


def get_exchange_rate_if_target(context: CallbackContext):
    job = context.job
    if job is not None and job.context is not None:
        args_dict: object = job.context

        target_curr_mapping = args_dict['target_curr_mapping']
        curr_from = target_curr_mapping['from']
        curr_to = target_curr_mapping['to']
        latest_exchg_rates = api.get_latest_exchange_rates(
            base_currency=curr_from, currencies=curr_to)['data']

        user_target_to_notify = target_curr_mapping['target']
        if latest_exchg_rates[target_curr_mapping['to']] >= user_target_to_notify:
            result_str = f"ALERT⚠️\nExchange rate of {curr_from}-{curr_to} is 1 {curr_from} - " \
                         f"{latest_exchg_rates[target_curr_mapping['to']]} {curr_to} vs your set target of " \
                         f"{user_target_to_notify}"
            context.bot.send_message(result_str)


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
    update.message.reply_text("Hi, welcome to GST & Svc charge calculator!\nPlease select the options !",
                              reply_markup=choose_gst_svc_charge_markup)
    context.user_data["gst_svc_options"] = update.message.text
    logger.info(f"Selected: {update.message.text}, moving on to CHOOSE_Forwards_Reverse")
    return CHOOSE_Forwards_Reverse


def gst_service_charge_direction_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please choose the direction !", reply_markup=choose_charge_direction_markup)
    context.user_data["gst_svc_direction"] = update.message.text
    logger.info(f"Selected: {update.message.text}, moving on to SET_COST")
    return SET_COST


def set_cost_handler(update: Update, context: CallbackContext):
    update.message.reply_text("Please input the cost !")
    try:
        number = float(update.effective_message.text)
        if number <= 0:
            raise ValueError
        context.user_data["cost"] = number
    except ValueError:
        update.effective_message.reply_text("I am sorry, you need to send me a number like _.__, nothing else")
        return CHOOSE_Forwards_Reverse
    choice = context.user_data["gst_svc_options"]
    if choice == "GST Only":
        logger.info(f"Selected: {number}, moving on to DISPLAY_GST_SVC_RESULT")
        return DISPLAY_GST_SVC_RESULT
    logger.info(f"Selected: {number}, moving on to SET_SVC_CHARGE_RATE")
    return SET_SVC_CHARGE_RATE


def set_svc_charge_rate(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter the service charge rate !\nEnter 'default' to choose default of 10%")
    try:
        number = float(update.effective_message.text)
        if not 0 <= number <= 0.1 or number != 'default':
            raise ValueError
        to_set = 0.1
        if number != 'default':
            to_set = number
        context.user_data["svc_charge_rate"] = to_set
    except ValueError:
        update.effective_message.reply_text("I am sorry, you need to send me a number like _.__ "
                                            "between 0 and 0.1 (both inclusive), nothing else")
        logger.info(f"Selected: {ValueError}, moving back to SET_SVC_CHARGE_RATE")
        return SET_SVC_CHARGE_RATE
    logger.info(f"Selected: {to_set}, moving on to DISPLAY_GST_SVC_RESULT")
    return DISPLAY_GST_SVC_RESULT


def generic_info_received_handler(update: Update, context: CallbackContext):
    choice = context.user_data["gst_svc_options"]
    direction = context.user_data["gst_svc_direction"]
    cost = context.user_data["cost"]
    svc_charge_rate = context.user_data["svc_charge_rate"]
    calculator = helper.GSTSvcChargeCalculator(cost) \
        .set_direction(direction)\
        .set_svc_charge(svc_charge_rate)\
        .set_option(choice)

    result = calculator.get_result()
    update.message.reply_text(f"This is the result: ${result}")
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
