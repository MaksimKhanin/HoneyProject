import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REQ_CANDLES = "/market/candles"
REQ_STOCKS = "/market/stocks"
REQ_PORTFOLIO = "/portfolio"
REQ_BASE_URL = 'https://api-invest.tinkoff.ru/openapi'


class TerminalConnector:

    def __init__(self, token, time_delta=3):
        self.token = token
        self.time_delta = time_delta
        self.header = {'Authorization': f"Bearer {token}"}

    def show_portfolio(self):
        response = self.requests_retry_session().get(REQ_BASE_URL + REQ_PORTFOLIO,
                                                         headers=self.header,
                                                         timeout=10)
        return response

    def show_stocks(self):
        response = self.requests_retry_session().get(REQ_BASE_URL + REQ_STOCKS,
                                                     headers=self.header,
                                                     timeout=10)
        # return requests.get(REQ_BASE_URL + REQ_STOCKS,
        #                     headers=self.header)
        return response

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

        response = self.requests_retry_session().get(REQ_BASE_URL + REQ_CANDLES,
                                                     params=params,
                                                     headers=self.header,
                                                     timeout=10)
        return response
        # return requests.get(REQ_BASE_URL + REQ_CANDLES,
        #                     params,
        #                     headers=self.header)

    def bool_status_return(self, answer_json):

        if answer_json["status"].upper() == "OK":
            return True
        else:
            return False

    @staticmethod
    def requests_retry_session(retries=3,backoff_factor=0.3,
                               status_forcelist=(500, 502, 504), session=None):

        session = session or requests.Session()
        retry = Retry(total=retries, read=retries, connect=retries,
                      backoff_factor=backoff_factor, status_forcelist=status_forcelist)

        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session


