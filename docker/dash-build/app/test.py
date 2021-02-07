# import pandas as pd
# import src.PSQL_queries as querylib
# from src.connectors import PSQL_connector as db_con
#
# DB_USER='khanin'
# DB_PASSWORD='Zx129132Aa'
# DB_HOST='45.156.21.247'
# DB_PORT=5432
#
# ticker = 'AAPL'
# DB_CON = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)
# def get_data_from_db(query, params=None):
#     cols, data = DB_CON.get_fetchAll(query, withColumns=True, params=params)
#     df = pd.DataFrame(data, columns=cols)
#     return df.to_json()
#
# print(get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT, params=(ticker,)))