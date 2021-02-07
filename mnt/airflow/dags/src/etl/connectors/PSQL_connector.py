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


