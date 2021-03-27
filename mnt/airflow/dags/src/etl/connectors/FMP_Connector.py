import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

REQ_BASE_URL = "https://financialmodelingprep.com/api/v3"

class FMP_Connector:

    def __init__(self, token):
        self.token = token

    def get_finansials(self, stat, ticker=None, **kwargs):

        """
        stat is in
            "profile",
            "income-statement",
            "balance-sheet-statement",
            "cash-flow-statement",
            "income-statement-growth",
            "balance-sheet-statement-growth",
            "cash-flow-statement-growth",
            "enterprise-values",
            "key-metrics",
            "financial-growth",
            "historical-market-capitalization",
            "earning_calendar",
            "historical-market-capitalization"
        """
        kwargs_allowed = {"limit", "period", "from", "to"}
        params = {"apikey": self.token}

        for kwarg in kwargs:
            if kwarg in kwargs_allowed:
                params[kwarg] = kwargs[kwarg]

        if ticker:
            url = f"{REQ_BASE_URL}/{stat}/{ticker}"
        else:
            url = f"{REQ_BASE_URL}/{stat}/"

        response = self.requests_retry_session().get(url, params=params, timeout=10)

        return response

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
