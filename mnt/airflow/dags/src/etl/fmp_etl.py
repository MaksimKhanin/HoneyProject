import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import time
from .connectors import FMP_Connector as fmp_con
from .connectors import PSQL_connector as db_con
from . import fmp_PSQL_queries as queryLib
from .logger.dag_logger import init_logger

############################
# Defining logger
############################

logger = init_logger("fmp_etl_logger")
logger.info("loading local .env")

############################
# Defining connectors
############################

load_dotenv()

############################
# Defining .env
############################
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]

FMP_TOKEN = os.environ["FMP_TOKEN"]

NM_TRIES = 3

############################
# Terminal global static vars
############################
DT_PERIOD_LIMITS_MAX = {
    "1min": timedelta(hours=23),
    "hour": timedelta(days=6),
    "day": timedelta(days=365)
}

DT_PERIOD_LIMITS_MIN = {
    "1min": timedelta(minutes=1),
    "hour": timedelta(minutes=50),
    "day": timedelta(hours=12)
}

EARNINGS_CALENDAR_RANGE = timedelta(days=30)

############################
# FMP global static vars
############################
DT_FIN_STAT_UPDATE_PER = timedelta(days=1)

INSERT_STAT_SQL_LIB = {
    "income-statement": queryLib.INSERT_INCOME_STATEMENT_JSON,
    "balance-sheet-statement": queryLib.INSERT_BALANCE_SHEET_JSON,
    "cash-flow-statement": queryLib.INSERT_CASH_FLOWS_JSON,
    "key-metrics": queryLib.INSERT_KEY_METRICS_JSON,
    "historical-price-full": queryLib.INSERT_FMP_CANDLE_JSON,
    "historical/earning_calendar": queryLib.INSERT_EARNINGS_CALENDAR,
    "earning_calendar": queryLib.INSERT_EARNINGS_CALENDAR,
    "historical-market-capitalization": queryLib.INSERT_MKT_CAP_HIST
}

FMP_INTERVAL_TO_STAT = {
    "day": "historical-price-full"
}


############################
# Defining connectors
############################

logger.info("Defining db connector")
db_con = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)
logger.info("Defining fmp connector")
fmp_con = fmp_con.FMP_Connector(FMP_TOKEN)


############################
# Defining static functions
############################

def _retry(func, retry_limit, *args, **kwargs):
    for n_try in range(retry_limit):
        try:
            output = func(*args, **kwargs)
            if output:
                return True
            logger.warning(f"Function {func} on {n_try} retry")
            time.sleep(30)
        except Exception as e:
            logger.error(f"Function {func} failed with error: {e}")
            continue
    logger.critical(f"Function {func} failed after {n_try} retries")
    return False

def round_prev_candle(timestamp, interval):
    return {
        '1min': timestamp.replace(microsecond=0, second=0),
        'hour': timestamp.replace(microsecond=0, second=0, minute=0),
        'day': timestamp.replace(hour=0, microsecond=0, second=0, minute=0)
    }[interval]


############################
# FMP etl functions block
############################

def update_company_profiles(fmp_connector, db_connector):
    logger.info(f"Update company fmp profile starts")
    ticker_array = db_connector.get_fetchAll(queryLib.GET_TINK_X_FMP_SYMBOLS_LIST)
    ticker_array = list(map(lambda x: x[0], ticker_array))
    #ticker_string = ",".join(ticker_array)
    for each_ticker in ticker_array:
        _retry(update_fmp_stat, NM_TRIES, fmp_connector, db_connector,
               stat="profile", ticker=each_ticker,
               insert_sql=queryLib.INSERT_COMPANY_PROFILE_JSON)
        logger.info(f"Update company fmp profile finished")

def upload_company_calendar(fmp_connector, db_connector, stat="historical/earning_calendar"):
    logger.info(f"Uploading companies' history calendars starts")
    ticker_array = db_connector.get_fetchAll(queryLib.GET_FMP_TICKERS_LIST)
    ticker_array = list(map(lambda x: x[0], ticker_array))
    for each_ticker in ticker_array:
        logger.info(f"Updating {each_ticker}")
        _retry(update_fmp_stat, NM_TRIES, fmp_connector, db_connector,
               stat=stat, ticker=each_ticker, insert_sql=INSERT_STAT_SQL_LIB[stat])


def update_earnings_calendar(fmp_connector, db_connector, stat="earning_calendar"):

    today = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
    fromdt = (today - EARNINGS_CALENDAR_RANGE).date()
    todt = (today + EARNINGS_CALENDAR_RANGE).date()
    kwargs = dict()
    kwargs["stat"] = stat
    kwargs["insert_sql"] = INSERT_STAT_SQL_LIB[stat]
    kwargs["from"] = fromdt
    kwargs["to"] = todt

    logger.info(f"Updating earnings_calendar from = {fromdt} todt = {todt}")
    _retry(update_fmp_stat, NM_TRIES, fmp_connector, db_connector, **kwargs)

def update_market_cap(fmp_connector, db_connector, stat="historical-market-capitalization"):

    logger.info(f"Update company {stat} starts")
    ticker_array = db_connector.get_fetchAll(queryLib.GET_FMP_TICKERS_LIST)
    ticker_array = list(map(lambda x: x[0], ticker_array))

    for each_ticker in ticker_array:
        logger.info(f"Updating {each_ticker}")
        last_update = db_connector.get_row(queryLib.GET_LAST_FIN_METRIC_UPDATE, (each_ticker, stat, "day",))[0]
        current_date = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

        if last_update is None or last_update < (current_date - DT_FIN_STAT_UPDATE_PER):
            _retry(update_fmp_stat, NM_TRIES, fmp_connector, db_connector,
                   stat=stat, ticker=each_ticker, insert_sql=INSERT_STAT_SQL_LIB[stat])
            db_connector.perform_query(queryLib.UPDATE_COMPANY_FIN_METRIC,
                                       (each_ticker, stat, "day", current_date.isoformat(),))
        else:
            logger.info(f"{each_ticker} was updated recently, so skipping")

def update_company_fin_stat(fmp_connector, db_connector, stat, period):
    logger.info(f"Update company fin stats {stat} for period {period} starts")
    ticker_array = db_connector.get_fetchAll(queryLib.GET_FMP_TICKERS_LIST)
    ticker_array = list(map(lambda x: x[0], ticker_array))

    period_x_table = {
        "year": "y",
        "quarter": "q"
    }

    for each_ticker in ticker_array:
        logger.info(f"Updating {each_ticker}")
        last_update = db_connector.get_row(queryLib.GET_LAST_FIN_METRIC_UPDATE, (each_ticker, stat, period,))[0]
        current_date = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

        if last_update is None or last_update < (current_date - DT_FIN_STAT_UPDATE_PER):
            _retry(update_fmp_stat, NM_TRIES, fmp_connector, db_connector,
                   stat=stat, ticker=each_ticker, period=period,
                   insert_sql=INSERT_STAT_SQL_LIB[stat].format(period=period_x_table[period]))

            db_connector.perform_query(queryLib.UPDATE_COMPANY_FIN_METRIC,
                                       (each_ticker, stat, period, current_date.isoformat(),))
        else:
            logger.info(f"{each_ticker} was updated recently, so skipping")


def parse_fmp_json(json_data, option="default"):
    if option == "historical-price-full":
        return json_data["historical"]
    else:
        return json_data


def update_fmp_stat(fmp_connector, db_connector, **kwargs):
    stat = kwargs["stat"]
    insert_sql = kwargs["insert_sql"]
    if "ticker" in kwargs:
        ticker = kwargs["ticker"]
    if "parse_option" in kwargs:
        parse_option = kwargs["parse_option"]
    else:
        parse_option = "default"
    if "ticker" in kwargs:
        logger.info(f"Requesting {stat} with tickers {ticker}")
    else:
        logger.info(f"Requesting {stat}")
    request = fmp_connector.get_finansials(**kwargs)
    if request.status_code != 200:
        logger.warning(f"FMP Returned bad code {request.status_code}")
        logger.warning(f"FMP Returned {request.head}")
        return False
    else:
        stat = parse_fmp_json(request.json(), option=parse_option)
        db_connector.perform_query(insert_sql, (json.dumps(stat),))
        return True


def etl_fmp_profiles():
    update_company_profiles(fmp_con, db_con)

def etl_earnings_calendar():
    update_earnings_calendar(fmp_con, db_con)


def etl_fmp_stat(stat, period):
    """
    stat: in {"income-statement", "balance-sheet-statement", "cash-flow-statement", "key-metrics"}
    period: in {"year", "quarter"}
    """
    update_company_fin_stat(fmp_con, db_con, stat, period)


def etl_fmp_candles(interval):
    logger.info(f"Candle update for {interval} from fmp starts")
    logger.info("Getting ticker list")
    ticker_array = db_con.get_fetchAll(queryLib.GET_FMP_SYMBOL_LIST)
    stat = "historical-price-full"
    for each_ticker_row in ticker_array:
        each_ticker = each_ticker_row[0]
        last_update = db_con.get_row(queryLib.GET_FMP_CANDLE_LAST_UPDATE,  (each_ticker, interval))[0]
        logger.info(f"Ticker precessing: {each_ticker}")
        current_date = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        if last_update is not None:
            logger.debug(f"Last update candle {interval} was in {last_update.isoformat()}")
            from_date = last_update
        else:
            from_date = (current_date - DT_PERIOD_LIMITS_MAX[interval])
            logger.debug(f"Last date not found in db {from_date.isoformat()} will be used instead")

        end_date = round_prev_candle(current_date, interval)
        from_dt = from_date.isoformat()
        end_dt = end_date.isoformat()
        logger.debug(f"Resulting period for quering - {from_dt} and {end_dt}")

        if DT_PERIOD_LIMITS_MIN[interval] < (end_date - from_date):
            logger.info(f"Quering candles for {each_ticker} from {from_dt} to {end_dt} and interval {interval}")
            _retry(update_fmp_stat, NM_TRIES, fmp_con, db_con,
                   stat=stat, ticker=f"{each_ticker}?from={from_date}&to={end_date}", period=None,
                   insert_sql=INSERT_STAT_SQL_LIB[stat].format(tf=interval, ticker=each_ticker), parse_option=stat)
            db_con.perform_query(queryLib.UPDATE_FMP_LAST_CANDLE_UPDATE, (each_ticker, interval, end_dt,))

