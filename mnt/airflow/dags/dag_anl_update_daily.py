from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
#from airflow.sensors.external_task_sensor import ExternalTaskSensor
from datetime import datetime, timedelta

from src.etl import fmp_etl

SLACK_CONN_ID = 'slack-honeyTradingTech'

slack_channel = BaseHook.get_connection(SLACK_CONN_ID).login
slack_token = BaseHook.get_connection(SLACK_CONN_ID).password

default_args = {
    "owner": "airflow",
    "start_date": datetime(2020, 1, 1),
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "email": "youremail@host.com",
    "retries": 5,
    "retry_delay": timedelta(minutes=10)
}

def update_earnings_calendar():
    fmp_etl.etl_earnings_calendar()

with DAG(dag_id="anl_update_daily", schedule_interval=None, default_args=default_args, catchup=False) as dag:

    # wait_ml_daily_update = ExternalTaskSensor(
    #     task_id="ml_update_daily"
    # )

    # wait_candle_daily_update = ExternalTaskSensor(
    #     task_id="tink_daily_update"
    # )

    create_dash_main_table = PostgresOperator(
        task_id="create_dash_main_table",
        sql="""
            CREATE TABLE IF NOT EXISTS anl.dash_main AS (
            SELECT
                    dr.timestamp, 
                    dr.date, 
                    dr.ticker, 
                    dr.open, 
                    dr.high, 
                    dr.low,
                    dr.close,
                    dr.daily_return,               
                    dr.currency,
                    dr.sector,
                    dr.industry,
                    dr.name,
                    cl.pca_loading_0,
                    cl.pca_loading_1,
                    cl.pca_loading_2,
                    cl.cluster,
                    dr.z_50_close,
                    trend.return_pred,
                    trend.prob_pred
                FROM anl.daily_return AS dr
                    LEFT JOIN anl.ml_ticker_clustering AS cl
                        ON dr.ticker = cl.ticker
                    LEFT JOIN ml.trend_locator AS trend
                        ON dr.ticker = trend.ticker AND dr.date = trend.date
                WHERE dr.date >= NOW() - INTERVAL '730 DAY'
                ORDER BY date ASC          
            );
        """
    )

    drop_dash_main_table = PostgresOperator(
        task_id="drop_dash_main_table",
        sql="DROP TABLE IF EXISTS anl.dash_main;"
    )

    earnings_calendar_update = PythonOperator(
        task_id="earnings_calendar_update",
        python_callable=update_earnings_calendar
    )

    anl_drop_calendar = PostgresOperator(
        task_id="anl_drop_calendar",
        sql="DROP TABLE IF EXISTS anl.earnings_calendar;"
    )

    anl_create_calendar = PostgresOperator(
        task_id="anl_create_calendar",
        sql="""
        CREATE TABLE IF NOT EXISTS anl.earnings_calendar AS (
            SELECT
                CAST(cal."date" AS DATE) AS date,
                cal."symbol",
                cal."time",
                cal."eps",
                cal."epsEstimated",
                cal."revenue",
                cal."revenueEstimated"
            FROM fmp.earnings_calendar AS cal
                INNER JOIN fmp.company_profile AS prof 
                    ON cal.symbol = prof.symbol
            WHERE CAST(cal."date" AS DATE) > NOW() - INTERVAL '730 DAY'
            ORDER BY date ASC  
        );
        """
    )

    drop_daily_return = PostgresOperator(
        task_id="drop_daily_return",
        sql="DROP TABLE IF EXISTS anl.daily_return;"
    )

    create_daily_return = PostgresOperator(
        task_id="create_daily_return",
        sql="""CREATE TABLE IF NOT EXISTS anl.daily_return AS (
                SELECT
                    EXTRACT(EPOCH FROM date) AS timestamp, 
                    DATE(date) AS date, 
                    ticker, 
                    open, 
                    high, 
                    low,
                    close,
                    ROUND((close /NULLIF(LAG(close, 1) OVER (
                                        PARTITION BY ticker
                                        ORDER BY date
                                        ), 0) - 1) * 100, 4) AS daily_return,               
                    currency,
                    sector,
                    industry,
                    name,
                    (close - ROLLING_MEAN_50_close) /  NULLIF(STD_50_close,0) AS z_50_close
                FROM (
                            SELECT
                                cndl.time AS date,
                                cndl.c AS close,
                                cndl.h AS high,
                                cndl.l AS low,
                                cndl.o AS open,
                                cndl.v AS volume,
                                sec.ticker,
                                sec.name,
                                sec.currency,                        
                                coalesce(prf.sector, 'other') AS sector,
                                coalesce(prf.industry, 'other') AS industry,
                                STDDEV_SAMP(cndl.c) OVER ticker_part_50 AS STD_50_close,
                                AVG(cndl.c) OVER ticker_part_50 AS ROLLING_MEAN_50_close                  
                            FROM tink.candles_day AS cndl
                                INNER JOIN tink.security AS sec 
                                    ON sec.figi = cndl.figi
                                INNER JOIN fmp.tink_sec_x_fmp_prof AS tink_x_fmp
                                    ON sec.ticker = tink_x_fmp.ticker
                                LEFT JOIN fmp.company_profile AS prf
                                    ON tink_x_fmp.fmp_symbol = prf.symbol
                            WINDOW ticker_part_50 AS (PARTITION BY sec.ticker ORDER BY cndl.time ROWS BETWEEN 50 PRECEDING AND CURRENT ROW)
                            UNION ALL
                            SELECT
                                fcndl.time as date,
                                fcndl.close,
                                fcndl.high,
                                fcndl.low,
                                fcndl.open,
                                fcndl.volume,
                                fcndl.ticker,
                                fsec.name,
                                fsec.currency,
                                'indicator' AS sector,
                                'indicator' AS industry,
                                STDDEV_SAMP(fcndl.close) OVER ticker_part_50 AS STD_50_close,
                                AVG(fcndl.close) OVER ticker_part_50 AS ROLLING_MEAN_50_close 
                            FROM fmp.candles_day AS fcndl
                                INNER JOIN fmp.security AS fsec
                                    ON fcndl.ticker = fsec.ticker 
                            WHERE fsec.type IN ('Fx', 'commodity')
                            WINDOW ticker_part_50 AS (PARTITION BY fcndl.ticker ORDER BY fcndl.time ROWS BETWEEN 50 PRECEDING AND CURRENT ROW)) AS stg
                );
            """
    )

    create_anl_ml_scores = PostgresOperator(
        task_id="create_anl_ml_scores",
        sql="""
        DROP TABLE IF EXISTS last_stmnt_score;
        CREATE TEMPORARY TABLE IF NOT EXISTS last_stmnt_score AS (
        SELECT
          main.symbol,
          main.statement_score
         FROM ml.stmnt_scores AS main
            INNER JOIN (
             SELECT
                 symbol,
                 MAX(date) AS date
             FROM ml.stmnt_scores
             GROUP BY symbol
             ) AS src ON src.symbol = main.symbol 
                AND src.date = main.date
    );

        DROP TABLE IF EXISTS anl.ml_scores;
        CREATE TABLE IF NOT EXISTS anl.ml_scores AS (
            SELECT
                dr.date, 
                dr.ticker,
                dr.name,					
                dr.sector,
                dr.industry,
                dr.z_50_close,
                cl.cluster,
                trend.return_pred - 1 AS return_pred,
                trend.prob_pred,
                ROUND(dr.close * trend.return_pred, 5) AS target_price,
                stmnt.statement_score 
            FROM anl.daily_return AS dr
                LEFT JOIN anl.ml_ticker_clustering AS cl
                    ON dr.ticker = cl.ticker
                LEFT JOIN ml.trend_locator AS trend
                    ON dr.ticker = trend.ticker AND dr.date = trend.date
                LEFT JOIN last_stmnt_score AS stmnt ON dr.ticker = stmnt.symbol
        ); 
            """
    )

    create_anl_strategy_signals = PostgresOperator(
        task_id="create_anl_strategy_signals",
        sql="""
        DROP TABLE IF EXISTS anl.create_anl_strategy_signals;
        CREATE TABLE IF NOT EXISTS anl.create_anl_strategy_signals AS (
        SELECT 
            *
        FROM (
            SELECT
                date,
                ticker,
                CASE WHEN 
                        REG_12_OPEN_SIGNAL = 1 AND PROB_12_OPEN_SIGNAL = 1 AND
                        (PREV_REG_12_OPEN_SIGNAL != 1 OR PREV_PROB_12_OPEN_SIGNAL != 1)
                        AND z_50_close < 2
                        THEN 'Signal_BUY'
                    WHEN 
                        REG_12_OPEN_SIGNAL = -1 AND PROB_12_OPEN_SIGNAL = -1 AND
                        (PREV_REG_12_OPEN_SIGNAL != -1 OR PREV_PROB_12_OPEN_SIGNAL != -1)
                        AND z_50_close > -2
                        THEN 'Signal_SELL' 
                    ELSE NULL
                    END AS SIGNAL,
                z_50_close,
                return_pred,
                prob_pred,
                statement_score,
                cluster
                FROM (
                    SELECT
                        date,
                        ticker,
                        z_50_close,
                        return_pred,
                        prob_pred,
                        statement_score,
                        cluster,
                        CASE 
                            WHEN return_pred >= 0.025 THEN 1
                            WHEN return_pred <= -0.025 THEN -1
                            ELSE 0 END AS REG_12_OPEN_SIGNAL,
                        CASE 
                            WHEN prob_pred >= 0.8 THEN 1
                            WHEN prob_pred <= 0.2 THEN -1
                            ELSE 0 END AS PROB_12_OPEN_SIGNAL,
                        LAG(
                            CASE 
                                WHEN return_pred >= 0.025 THEN 1
                                WHEN return_pred <= -0.025 THEN -1
                                ELSE 0 END,
                            1) OVER (PARTITION BY ticker ORDER BY date)
                            AS PREV_REG_12_OPEN_SIGNAL,
                        LAG(
                            CASE 
                                WHEN prob_pred >= 0.8 THEN 1
                                WHEN return_pred <= 0.2 THEN -1
                                ELSE 0 END,
                            1) OVER (PARTITION BY ticker ORDER BY date)
                            AS PREV_PROB_12_OPEN_SIGNAL				
                    FROM anl.ml_scores) AS src) AS src
        WHERE SIGNAL IS NOT NULL
        );
    """
    )
    create_anl_last_ml_scores = PostgresOperator(
        task_id="create_anl_last_ml_scores",
        sql="""
        DROP TABLE IF EXISTS anl.last_ml_scores;
        CREATE TABLE IF NOT EXISTS anl.last_ml_scores AS (
            SELECT dr.* FROM anl.ml_scores AS dr
            INNER JOIN (
                SELECT
                    ticker,
                    MAX(date) as date
                FROM anl.daily_return
                GROUP BY ticker 
                ) AS maxdt 
                    ON dr.date=maxdt.date AND dr.ticker=maxdt.ticker
            );
        """
    )

    sending_slack_notification = SlackAPIPostOperator(
        task_id="sending_slack",
        channel=slack_channel,
        token=slack_token,
        username="honeySlackApp",
        text="DAG anl_update_daily: DONE",
    )

drop_daily_return >> create_daily_return >> create_anl_ml_scores >> create_anl_strategy_signals

create_anl_ml_scores >> create_anl_last_ml_scores

earnings_calendar_update >> anl_drop_calendar >> anl_create_calendar

create_daily_return >> drop_dash_main_table >> create_dash_main_table



[anl_create_calendar, create_dash_main_table, create_anl_strategy_signals, create_anl_last_ml_scores] >> sending_slack_notification
