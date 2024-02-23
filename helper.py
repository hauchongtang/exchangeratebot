def is_command_in_text(text: str, command: str):
    return command in text


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
