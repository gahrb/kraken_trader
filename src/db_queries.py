#!/usr/bin/python3

import psycopg2
import psycopg2.extras
import logging
from psycopg2.extensions import AsIs
from datetime import datetime
FORMAT = '%(asctime)-5s [%(name)s] %(levelname)s: %(message)s'
logging.basicConfig(filename='/var/log/kraken/kraken_log.log',level=logging.INFO,format=FORMAT,datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('kraken_crawler')

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
        self.dict_cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def fetchall(self, string):
        self.execute(string)
        return self.cursor.fetchall()

    def dict_fetch(self, string):
        self.execute(string)
        return self.dict_cursor.fetchall()

    def execute(self, string):
        return self.cursor.execute(string)

    def get_last(self, string):
        return self.fetchall(string + " ORDER BY modtime DESC LIMIT 1;")

    def gettimeat(self, table, idx):
        querystring = "SELECT modtime FROM " + table + " ORDER BY modtime OFFSET " + str(idx) + "LIMIT 1;"
        return self.fetchall(querystring)[0][0]

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
        return self.fetchall(querystring)[0][0]

    def alter_value(self, table, column, row, value):
        querystring = "UPDATE " + table + " SET " + column + "=" + str(value) + " WHERE modtime='" + str(row) + "';"
        self.execute(querystring)
        self.commit()

    def add_column_to_table(self, table, column):
        query = "ALTER TABLE " + table.lower() + " ADD COLUMN " + str(column).lower() + " double precision default 0;"
        self.execute(query)
        self.commit()

    def inser_into(self, table, columns, values):
        # Inserts new values into table, make sure that the order of the columns and values are the same
        values = [str(i) for i in values]
        idx = columns.index('modtime')
        values[idx] = "'" + values[idx] + "'"
        query = "INSERT INTO " + table + " (" + ",".join(columns) + ") VALUES (" + ",".join(values) + ");"
        self.execute(query)
        self.commit()

    def append_balance(self, currency, time, value):
        # Check if row with timestamp already exists -> only alter_value
        row = list(self.closestelem(table='balance', time=time)[0])
        currencies = self.get_columns()
        if row[0] == time:
            return self.alter_value(table='balance', column=currency.lower(), row=time, value=value)

        # Take values from last row to copy all values but the new one
        row[0] = time
        idx = currencies.index(currency)
        row[idx] = value
        return self.inser_into(table='balance', columns=currencies, values=row)

    def get(self, table, column, time, limit=1, mode='closest'):
        time_cond = " ORDER BY ABS(extract(epoch from modtime - '" + str(time) + "'))"
        if mode == 'greater':
            time_cond = " WHERE modtime > '" + str(time) +\
                        "' ORDER BY extract(epoch from modtime) ASC"
        elif mode == 'smaller':
            time_cond = " WHERE modtime < '" + str(time) +\
                        "' ORDER BY extract(epoch from modtime) DESC"
        elif mode == 'dist':
            time_cond = " WHERE modtime > '" + str(time) +\
                        "' ORDER BY ABS(extract(epoch from modtime - '" + str(time) + "'))"
        query = "SELECT " + column + " FROM " + table + time_cond + " LIMIT " + str(limit) + ";"
        return self.fetchall(query)

    def timestamps(self, table, limit=-1):
        if not limit==-1:
            limit_str = "SELECT modtime FROM " + table + " ORDER BY modtime DESC LIMIT " + str(limit)
            query = "SELECT * FROM (" + limit_str + ") AS tmp ORDER BY modtime ASC;"
        else:
            query = "SELECT modtime FROM " + table + ";"
        return self.fetchall(query)

    def update_db(self, res, pair):
        """
        a = ask array(<price>, <whole lot volume>, <lot volume>),
        b = bid array(<price>, <whole lot volume>, <lot volume>),
        c = last trade closed array(<price>, <lot volume>),
        v = volume array(<today>, <last 24 hours>),
        p = volume weighted average price array(<today>, <last 24 hours>),
        t = number of trades array(<today>, <last 24 hours>),
        l = low array(<today>, <last 24 hours>),
        h = high array(<today>, <last 24 hours>),
        o = today's opening price
        """
        try:
            logger.info("Populating table " + pair)
            query = str("INSERT INTO " + pair +
                        " VALUES ('" +
                        str(datetime.now()) + "', " +
                        str(res['a'][0]) + ", " + str(res['a'][1]) + ", " + str(res['a'][2]) + ", " +
                        str(res['b'][0]) + ", " + str(res['b'][1]) + ", " + str(res['b'][2]) + ", " +
                        str(res['c'][0]) + ", " + str(res['c'][1]) + ", " +
                        str(res['v'][0]) + ", " + str(res['v'][1]) + ", " +
                        str(res['p'][0]) + ", " + str(res['p'][1]) + ", " +
                        str(res['t'][0]) + ", " + str(res['t'][1]) + ", " +
                        str(res['l'][0]) + ", " + str(res['l'][1]) + ", " +
                        str(res['h'][0]) + ", " + str(res['h'][1]) + ", " +
                        str(res['o'])) + ")"
            self.execute(query)
            self.commit()
        except psycopg2.Error as e:
            if e.pgcode == '42P01':  # Table does not exist
                logger.info("Found new traid pair. Creating a new table...")
                self.execute("rollback")
                try:
                    query = "CREATE TABLE " + pair + " (modtime timestamp," \
                                                     "ask_price double precision," \
                                                     "ask_volume double precision," \
                                                     "ask_lot_volume double precision," \
                                                     "bid_price double precision," \
                                                     "bid_volume double precision," \
                                                     "bid_lot_volume double precision," \
                                                     "closed_price double precision," \
                                                     "closed_colume double precision," \
                                                     "volume double precision," \
                                                     "volume_24h double precision," \
                                                     "volume_weighted double precision," \
                                                     "volume_weighted_24h double precision," \
                                                     "num_trades integer," \
                                                     "num_trades_24h integer," \
                                                     "low double precision," \
                                                     "low_24h double precision," \
                                                     "high double precision," \
                                                     "high_24h double precision," \
                                                     "opened double precision )"
                    logger.info("Creating table " + pair)
                    self.execute(query)
                    self.commit()
                    self.update_db(res, pair)
                except psycopg2.Error as e:
                    logger.error("Could not create new table.")
                    logger.error(pgcode)
                    logger.error(e.pgerror)
            else:
                logger.error("Unable to insert new date into the table: " +pair)
                logger.warning(e.pgcode)
                logger.warning(e.pgerror)
        return

    def get_assets(self):
        query = "SELECT * FROM assets;"
        res = self.fetchall(query)
        cols = self.get_columns()
        assets = dict()
        for row in res:
            tmp_dict = dict()
            for col in cols:
                if col != 'asset':
                    tmp_dict.update({col: row[cols.index(col)]})
            assets.update({row[cols.index('asset')]: tmp_dict})
        return assets

    def get_asset_pairs(self):
        query = "SELECT * FROM asset_pairs;"
        res = self.fetchall(query)
        cols = self.get_columns()
        asset_pairs = dict()
        for row in res:
            tmp_dict = dict()
            for col in cols:
                if col != 'asset':
                    tmp_dict.update({col: row[cols.index(col)]})
            asset_pairs.update({row[cols.index('asset')]: tmp_dict})
        return asset_pairs

    def assets2db(self, assets):
        for asset in assets:
            columns = list(assets[asset].keys())
            values = [assets[asset][column] for column in columns]
            str_values = [str(assets[asset][column]).lower() for column in columns]
            columns.insert(0, 'asset')
            str_values.insert(0, asset)
            insert_statement = 'INSERT INTO assets (' +\
                               ", ".join(columns) +\
                               ") VALUES ('" +\
                               "', '".join(str_values) +\
                               "');"
            try:
                self.execute(insert_statement)
                self.commit()
            except psycopg2.Error as e:
                if e.pgcode == '42P01' or e.pgcode == '25P02':  # Table does not exist
                    logger.info("Assets table does not yet exist. Creating a new table...")
                    types = [self.psql_type(type(v)) for v in values]
                    types.insert(0, 'varchar')
                    query = "CREATE TABLE assets (" +\
                            "".join([str(columns[i]) + " " + types[i] + ", " for i in range(len(columns)-1)]) +\
                            columns[-1] + " " + types[-1] + " );"
                    logger.info("Creating table.")
                    self.execute("rollback")
                    self.execute(query)
                    self.commit()

    def assetpairs2db(self, asset_pairs):
        for asset in asset_pairs:
            columns = list(asset_pairs[asset].keys())
            values = [asset_pairs[asset][column] for column in columns]
            str_values = [str(asset_pairs[asset][column]).lower() for column in columns]
            columns.insert(0, 'asset')
            str_values.insert(0, asset)
            insert_statement = 'insert into asset_pairs (' + ", ".join(columns) + ") values ('" + "', '".join(str_values) + "');"
            try:
                self.execute(insert_statement)
                self.commit()
            except psycopg2.Error as e:
                if e.pgcode == '42P01' or e.pgcode == '25P02':  # Table does not exist
                    logger.info("Assets table does not yet exist. Creating a new table...")
                    types = [self.psql_type(type(v)) for v in values]
                    types.insert(0, 'varchar')
                    query = "CREATE TABLE asset_pairs (" +\
                            "".join([str(columns[i]) + " " + types[i] + ", " for i in range(len(columns)-1)]) +\
                            columns[-1] + " " + types[-1] + " );"
                    logger.info("Creating table.")
                    self.execute("rollback")
                    self.execute(query)
                    self.commit()

    def psql_type(self, ptype):
        if ptype == str:
            return 'varchar'
        elif ptype == float:
            return 'double precision'
        elif ptype == datetime:
            return 'timestamp'
        elif ptype == bool:
            return 'bool'
        elif ptype == int:
            return 'integer'
        else:
            return 'text'