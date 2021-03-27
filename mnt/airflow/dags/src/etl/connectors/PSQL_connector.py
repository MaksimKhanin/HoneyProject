import psycopg2


class PostgresConnector:

    def __init__(self, host, password, port, user):
        self.connection = psycopg2.connect(host=host,
                                           password=password,
                                           port=port,
                                           user=user)

    def perform_query(self, query, params=None):
        connection = self.connection
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    def get_row(self, query, params=None):
        connection = self.connection
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                print(params)
                return cursor.fetchone()

    def get_fetchAll(self, query, params=None, withColumns=False):
        connection = self.connection
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                if withColumns:
                    columns = [desc[0] for desc in cursor.description]
                    data = cursor.fetchall()
                    return (columns, data)
                else:
                    return cursor.fetchall()

    # Define function using cursor.executemany() to insert the dataframe
    def insert_many(self, dataframe, table):
        connection = self.connection
        tpls = [tuple(x) for x in dataframe.to_numpy()]
        cols = ','.join(list(dataframe.columns))
        values_tmplt = "%s,"*len(dataframe.columns)
        sql = "INSERT INTO %s(%s) VALUES(%s)" % (table, cols, values_tmplt[:-1])
        with connection:
            with connection.cursor() as cursor:
                cursor.executemany(sql, tpls)
