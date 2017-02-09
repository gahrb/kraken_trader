import psycopg2
from datetime import datetime

from src.logger import logger
from src.kraken_api_wrapper import KrakenApiWrapper
from src.database_connection import get_database_connection


class KrakenCache(object):
    def __init__(self):
        self.krakenex_api = KrakenApiWrapper()
        self.database_connection = get_database_connection()

    def populate_db(self):
        for pair in self.krakenex_api.get_asset_pairs():
            query = self.krakenex_api.query_market(pair)
            if 'result' in query.keys() and len(query['result']):
                self._update_db(query['result'][pair], pair)
            else:
                logger.warning("Error querying pair: " + pair[1:4] + "-" + pair[5:])
                logger.warning(query['error'])

    def _update_db(self, res, pair):
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
        cursor = self.database_connection.cursor()
        try:
            logger.info("Populating table " + pair)
            cursor.execute(
                "INSERT INTO " + pair + " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                (datetime.now(),
                 res['a'][0], res['a'][1], res['a'][2],
                 res['b'][0], res['b'][1], res['b'][2],
                 res['c'][0], res['c'][1],
                 res['v'][0], res['v'][1],
                 res['p'][0], res['p'][1],
                 res['t'][0], res['t'][1],
                 res['l'][0], res['l'][1],
                 res['h'][0], res['h'][1],
                 res['o']))
            cursor.close()
            self.database_connection.commit()
        except psycopg2.Error as e:
            if e.pgcode == '42P01':  # Table does not exist
                logger.info("Found new traid pair. Creating a new table...")
                cursor = self.database_connection.cursor()
                cursor.execute("rollback")
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
                    cursor.execute(query)
                    cursor.close()
                    self._update_db(res, pair)
                except psycopg2.Error as e:
                    logger.error("Could not create new table.")
                    logger.error(e.pgcode)
                    logger.error(e.pgerror)
            else:
                logger.error("Unable to insert new date into the table: " + pair)
                logger.warning(e.pgcode)
                logger.warning(e.pgerror)
        return
