from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from src.ml import trendLocator

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


def update_trend_locator():
    trendLocator.upload_trend_scores("trend_locator_12_reg", "trend_locator_12_class")

with DAG(dag_id="ml_update_daily", schedule_interval=None, default_args=default_args, catchup=False) as dag:

    truncate_trendlocator = PostgresOperator(
        task_id="truncate_trendlocator",
        sql="TRUNCATE ml.trend_locator;"
    )

    trendLocator_update = PythonOperator(
        task_id="trendLocator_update",
        python_callable=update_trend_locator
    )

    trigger_anl_update_daily = TriggerDagRunOperator(
        task_id="trigger_anl_update_daily",
        trigger_dag_id="anl_update_daily"
    )

truncate_trendlocator >> trendLocator_update >> trigger_anl_update_daily