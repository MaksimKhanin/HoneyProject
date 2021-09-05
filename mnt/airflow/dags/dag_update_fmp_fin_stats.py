from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.python_operator import PythonOperator
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
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


def get_fmp_company_profiles():
    fmp_etl.etl_fmp_profiles()


def update_fmp_stat(stat, period):
    """
    stat: in {"income-statement", "balance-sheet-statement", "cash-flow-statement", "key-metrics"}
    period: in {"year", "quarter"}
    """
    fmp_etl.etl_fmp_stat(stat, period)


with DAG(dag_id="fmp_stat_update", schedule_interval="0 5 * * 6", default_args=default_args, catchup=False) as dag:
    
    fmp_profiles_getter = PythonOperator(
            task_id="get_fmp_profiles",
            python_callable=get_fmp_company_profiles
    )

    fmp_stat_income_q = PythonOperator(
            task_id="get_company_stat_income_q",
            python_callable=update_fmp_stat,
            op_kwargs={"stat": "income-statement", "period":"quarter"}
    )

    fmp_stat_balance_q = PythonOperator(
            task_id="get_company_stat_balance_q",
            python_callable=update_fmp_stat,
            op_kwargs={"stat": "balance-sheet-statement", "period":"quarter"}
    )

    fmp_stat_cash_q = PythonOperator(
            task_id="get_company_stat_cash_q",
            python_callable=update_fmp_stat,
            op_kwargs={"stat": "cash-flow-statement", "period":"quarter"}
    )

    fmp_stat_keys_q = PythonOperator(
            task_id="get_company_stat_keys_q",
            python_callable=update_fmp_stat,
            op_kwargs={"stat": "key-metrics", "period":"quarter"}
    )

    fmp_stat_income_y = PythonOperator(
        task_id="get_company_stat_income_y",
        python_callable=update_fmp_stat,
        op_kwargs={"stat": "income-statement", "period": "year"}
    )

    fmp_stat_balance_y = PythonOperator(
        task_id="get_company_stat_balance_y",
        python_callable=update_fmp_stat,
        op_kwargs={"stat": "balance-sheet-statement", "period": "year"}
    )

    fmp_stat_cash_y = PythonOperator(
        task_id="get_company_stat_cash_y",
        python_callable=update_fmp_stat,
        op_kwargs={"stat": "cash-flow-statement", "period": "year"}
    )

    fmp_stat_keys_y = PythonOperator(
        task_id="get_company_stat_keys_y",
        python_callable=update_fmp_stat,
        op_kwargs={"stat": "key-metrics", "period": "year"}
    )

    sending_slack_notification = SlackAPIPostOperator(
        task_id="sending_slack",
        channel=slack_channel,
        token=slack_token,
        username="airflow",
        text="DAG fmp_stat_update: DONE",
    )

    drop_fmp_x_tink_dict = PostgresOperator(
        task_id="drop_fmp_x_tink_dict",
        sql="DROP TABLE IF EXISTS fmp.tink_sec_x_fmp_prof;"
    )

    create_fmp_x_tink_dict = PostgresOperator(
        task_id="create_fmp_x_tink_dict",
        sql="""CREATE TABLE IF NOT EXISTS fmp.tink_sec_x_fmp_prof AS
                (
                    SELECT
                        figi,
                        ticker,
                        CASE 
                            WHEN currency = 'RUB' THEN ticker || '.ME' ELSE  ticker 
                        END AS fmp_symbol
                    FROM tink.security
                );"""
    )

    trigger_ml_update_weekly = TriggerDagRunOperator(
        task_id="trigger_ml_update_weekly",
        trigger_dag_id="ml_update_weekly"
    )

drop_fmp_x_tink_dict >> create_fmp_x_tink_dict >> fmp_profiles_getter

fmp_profiles_getter >> [fmp_stat_income_y, 
                        fmp_stat_balance_y, 
                        fmp_stat_cash_y, 
                        fmp_stat_keys_y, 
                        fmp_stat_income_q, 
                        fmp_stat_balance_q, 
                        fmp_stat_cash_q, 
                        fmp_stat_keys_q] >> trigger_ml_update_weekly >> sending_slack_notification

