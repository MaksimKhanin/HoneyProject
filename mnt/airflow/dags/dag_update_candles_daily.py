from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.python_operator import PythonOperator
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from datetime import datetime, timedelta
from src.etl import tink_etl

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


def get_all_stocks():
    tink_etl.etl_stock_list()


def get_candles_daily():
    tink_etl.etl_candles("day")


with DAG(dag_id="tink_daily_update", schedule_interval="0 3 * * *", default_args=default_args, catchup=False) as dag:
    
    terminal_stock_getter = PythonOperator(
            task_id="get_all_tink_stocks",
            python_callable=get_all_stocks
    )

    terminal_candles_daily = PythonOperator(
            task_id="get_candles_daily",
            python_callable=get_candles_daily
    )

    trigger_anl_update = TriggerDagRunOperator(
        task_id="trigger_anl_update",
        trigger_dag_id="anl_update_daily"
    )

    sending_slack_notification = SlackAPIPostOperator(
        task_id="sending_slack",
        channel=slack_channel,
        token=slack_token,
        username="honeySlackApp",
        text="DAG tink_daily_update: DONE",
    )
    

terminal_stock_getter >> terminal_candles_daily >> sending_slack_notification
terminal_candles_daily >> trigger_anl_update