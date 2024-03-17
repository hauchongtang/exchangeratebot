import os


def is_command_in_text(text: str, command: str):
    return command in text


def is_float(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False


class DataParser:
    def __init__(self, text: str, command: str):
        self.text = text
        self.command = command

    def parse_as_str(self):
        result = self.text.split(f"{self.command}")
        data_str = ''
        for i in range(1, len(result)):
            data_str += result[i]
        return data_str


class RateParser:
    def __init__(self, data: str = ''):
        self.data = data

    def parse_to_dict(self) -> dict:
        currencies = self.data.split('-')
        currency1: str = currencies[0].strip().upper()
        currency2: str = currencies[1].strip().upper()

        return {
            'from': currency1,
            'to': currency2
        }


class TimeParser:
    @staticmethod
    def parse(time_str: str):
        return time_str.split(':')


class ScheduleParser:
    @staticmethod
    def parse(data: str):
        freq_time_tuple = data.split(' ')
        assert len(freq_time_tuple) == 2

        freq_str, time_hh_mm_tuple = freq_time_tuple[0].strip().upper(), TimeParser.parse(freq_time_tuple[1].strip())
        if freq_str not in ('DAILY',):
            raise ValueError('Frequency not found. Only DAILY is applicable for now')
        return freq_str, time_hh_mm_tuple


class GSTSvcChargeCalculator:
    def __init__(self, cost: float):
        self.option = "GST & Svc Charge"
        self.cost = cost
        self.gst_rate = os.environ.get("GST_RATE", 0.09)
        self.svc_charge = os.environ.get("SVC_CHARGE", 0.1)
        self.direction = "Forwards"

    def set_direction(self, cal_dir: str):
        self.direction = cal_dir
        return self

    def set_svc_charge(self, svc_ch: float):
        self.svc_charge = svc_ch
        return self

    def set_gst_rate(self, rate: float):
        self.gst_rate = rate
        return self

    def set_option(self, option: str):
        self.option = option
        return self

    def get_result(self):
        option_str = self.option.upper().strip()
        if self.direction.upper().strip() == "FORWARDS":
            if option_str == "GST & SVC CHARGE":
                return self.gst_rate * self.svc_charge * self.cost
            if option_str == "GST ONLY":
                return self.gst_rate * self.cost
            if option_str == "SERVICE CHARGE ONLY":
                return self.svc_charge * self.cost
        else:
            if option_str == "GST & SVC CHARGE":
                return self.cost / (self.gst_rate * self.svc_charge)
            if option_str == "GST ONLY":
                return self.cost / self.gst_rate
            if option_str == "SERVICE CHARGE ONLY":
                return self.cost / self.svc_charge
        return "Error please try again! /Done"
