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
        self.execute(string)
        return self.cursor.fetchall()

    def execute(self, string):
        return self.cursor.execute(string)

    def get_last(self, string):
        return self.fetchall(string + " ORDER BY modtime DESC LIMIT 1;")

    def gettimeat(self, table, idx):
        querystring = "SELECT modtime FROM " + table + " ORDER BY modtime OFFSET " + idx + "LIMIT 1;"
        return self.execute(querystring)

    def closestelem(self, table, time):
        if not type(time) == str:
            time = str(time)
        querystring = "SELECT * FROM " + table + " ORDER BY ABS(extract(epoch from modtime - '" + time + "')) LIMIT 1;"
        return self.fetchall(querystring)

    def get_balances(self):
        querystring = "SELECT * FROM balance order by modtime asc;"
        return self.fetchall(querystring)

    def get_columns(self):
        columns = []
        for col in self.cursor.description:
            columns.append(col.name)
        return columns

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()

    def length(self, table):
        querystring = "SELECT COUNT(*) FROM " + table
        return self.execute(querystring)
