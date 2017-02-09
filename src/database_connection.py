import psycopg2


def get_database_connection():
    return psycopg2.connect(
        host="127.0.0.1",
        database="kraken_trader",
        user="kraken_trader",
        password="trader")
