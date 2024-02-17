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
        currency1: str = currencies[0].upper()
        currency2: str = currencies[1].upper()

        return {
            'from': currency1,
            'to': currency2
        }
