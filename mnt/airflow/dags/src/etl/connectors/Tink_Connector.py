import requests

REQ_CANDLES = "/sandbox/market/candles"
REQ_STOCKS = "/sandbox/market/stocks"
REQ_BASE_URL = 'https://api-invest.tinkoff.ru/openapi'


class TerminalConnector:

    def __init__(self, token, time_delta=3):
        self.token = token
        self.time_delta = time_delta
        self.header = {'Authorization': f"Bearer {token}"}

    def show_stocks(self):
        return requests.get(REQ_BASE_URL + REQ_STOCKS,
                            headers=self.header)

    def show_candle(self, figi, from_dt, end_dt, interval):

        """
        :param figi: string
        :param from_dt: string
            exmaple: 2019-08-19T18:38:33.131642+03:00
        :param end_dt: string
            exmaple: 2019-08-19T18:38:33.131642+03:00
        :param interval: string
            Available values : 1min, 2min, 3min, 5min, 10min, 15min, 30min, hour, day, week, month
        :return: list(json)
        """

        params = {
            "figi": figi,
            "from": from_dt,
            "to": end_dt,
            "interval": interval,
        }

        return requests.get(REQ_BASE_URL + REQ_CANDLES,
                            params,
                            headers=self.header)

    def bool_status_return(self, answer_json):

        if answer_json["status"].upper() == "OK":
            return True
        else:
            return False

