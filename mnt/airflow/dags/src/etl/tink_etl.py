import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import time
from .connectors import Tink_Connector as t_con
from .connectors import PSQL_connector as db_con
from . import tink_PSQL_queries as queryLib
from .logger.dag_logger import init_logger

############################
# Defining logger
############################

logger = init_logger("tink_etl_logger")
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

T_TOKEN = os.environ["T_TOKEN"]

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

############################
# Defining connectors
############################

logger.info("Defining t_connector")
t_con = t_con.TerminalConnector(T_TOKEN)
logger.info("Defining db connector")
db_con = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)


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
        except:
            continue
    logger.error(f"Function {func} failed after {n_try} retries")
    return False



def round_prev_candle(timestamp, interval):
    return {
        '1min': timestamp.replace(microsecond=0, second=0),
        'hour': timestamp.replace(microsecond=0, second=0, minute=0),
        'day': timestamp.replace(hour=0, microsecond=0, second=0, minute=0)
    }[interval]


############################
# Terminal etl functions block
############################

def etl_portfolio():
    logger.info("Portfolio update starts")
    if _retry(update_portfolio_list, NM_TRIES, t_con, db_con):
        logger.info(f"Portfolio update was successful")
    else:
        logger.critical(f"Portfolio  update was unsuccessful")
        raise Exception(f"Portfolio  update was unsuccessful")

def update_portfolio_list(t_connector, db_connector):
    request = t_connector.show_portfolio()
    if request.status_code != 200:
        logger.warning(f"Terminal Returned bad code")
        return False
    else:
        portfolio = request.json()
    if t_connector.bool_status_return(portfolio):
        portfolio = portfolio["payload"]["positions"]
        db_connector.perform_query(queryLib.INSERT_PORTFOLIO_JSON, (json.dumps(portfolio),))
        return True
    else:
        logger.error(str(portfolio["payload"]["message"]))
        return False


def update_stock_list(t_connector, db_connector):
    request = t_connector.show_stocks()
    if request.status_code != 200:
        logger.warning(f"Terminal Returned bad code")
        return False
    else:
        stocks = request.json()
    if t_connector.bool_status_return(stocks):
        stocks = stocks["payload"]["instruments"]
        db_connector.perform_query(queryLib.INSERT_SECURITY_JSON, (json.dumps(stocks),))
        return True
    else:
        logger.error(str(stocks["payload"]["message"]))
        return False


def update_instr_candle_hist(figi, from_dt, end_dt, interval, t_connector, db_connector):
    request = t_connector.show_candle(figi, from_dt, end_dt, interval)

    if request.status_code != 200:
        logger.warning(f"Candles request for {figi} {from_dt} {end_dt} {interval} "
                       f"returned non-200 code {request.status_code}")
        time.sleep(10)
        return False
    else:
        logger.info(f"Candles request for {figi} {from_dt} {end_dt} {interval} "
                       f"returned correct code")
        candles = request.json()

    if t_connector.bool_status_return(candles):
        candles = candles["payload"]["candles"]
        db_connector.perform_query(queryLib.INSERT_CANDLE_JSON.format(tf=interval), (json.dumps(candles),))
        return True
    else:
        logger.error(str(candles["payload"]["message"]))
        return False


def etl_stock_list():
    logger.info("Stock list update starts")
    if _retry(update_stock_list, NM_TRIES, t_con, db_con):
        logger.info(f"Stock list update was successful")
    else:
        logger.critical(f"Stock list update was unsuccessful")
        raise Exception(f"Stock list update was unsuccessful")


def etl_candles(interval):
    logger.info(f"Candle update for the {interval} starts")
    logger.info("Getting figi list")
    figi_array = db_con.get_fetchAll(queryLib.GET_FIGI_LIST)
    for each_figi, each_ticker in figi_array:

        last_update = db_con.get_row(queryLib.GET_LAST_CANDLE_UPDATE,  (each_figi, each_ticker, interval))[0]
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
            if _retry(update_instr_candle_hist, NM_TRIES, each_figi, from_dt, end_dt, interval, t_con, db_con):
                logger.info(f"Got candles for {each_ticker}")
                db_con.perform_query(queryLib.UPDATE_TINK_LAST_CANDLE_UPDATE, (each_figi, each_ticker, interval, end_dt,))
                time.sleep(0.5)
            else:
                logger.error(f"Quering candles for {each_ticker} from {from_dt} to {end_dt} was unsuccessful")
                continue
