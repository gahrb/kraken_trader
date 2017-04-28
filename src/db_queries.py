import psycopg2


class DbQueries:

    def __init__(self):

        self.host = "localhost"
        self.database = "kraken_crawler"
        self.user = "kraken"
        self.password = "kraken"
        self.conn = psycopg2.connect(host=self.host, database=self.database, user=self.user,  password=self.password)
        self.cursor = self.conn.cursor()

    def execute(self, string):
        result = self.cursor.execute(string)
        return result.fetchall()

    def gettimeat(self, table, idx):
        querystring = "SELECT timestamp FROM " + table + " ORDER BY timestamp OFFSET " + idx + "LIMIT 1;"
        return self.execute(querystring)

    def closestelem(self, table, time):
        querystring = "SELECT * FROM " + table + " ORDER BY ABS(timestamp - " + time + ") LIMIT 1;"
        return self.execute(querystring)

    def close(self):
        self.cursor.close()

    def length(self, table):
        querystring = "SELECT COUNT(*) FROM " + table
        return self.execute(querystring)
