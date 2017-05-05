import psycopg2


class DbQueries:

    def __init__(self):

        self.host = "localhost"
        self.database = "kraken_crawler"
        self.user = "kraken"
        self.password = "kraken"
        try:
            self.conn = psycopg2.connect(host=self.host, database=self.database, user=self.user,  password=self.password)
        except:
            return
        self.cursor = self.conn.cursor()


    def fetchall(self, string):
        return self.execute(string).fetchall()

    def execute(self, string):
        return self.cursor.execute(string)

    def get_last(self, string):
        return self.fetchall(string + " ORDER BY timestamp DESC LIMIT 1;")

    def gettimeat(self, table, idx):
        querystring = "SELECT timestamp FROM " + table + " ORDER BY timestamp OFFSET " + idx + "LIMIT 1;"
        return self.execute(querystring)

    def closestelem(self, table, time):
        querystring = "SELECT * FROM " + table + " ORDER BY ABS(timestamp - " + time + ") LIMIT 1;"
        return self.execute(querystring)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()

    def length(self, table):
        querystring = "SELECT COUNT(*) FROM " + table
        return self.execute(querystring)
