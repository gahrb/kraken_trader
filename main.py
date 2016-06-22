#!/usr/bin/python

import getopt
import logging
import os
import psycopg2
import sys
from datetime import datetime

import krakenex
from kraken_trader.account import kraken_account
from kraken_trader.all_traders import *
from kraken_trader.analyzer import *

simulate = False
realSim = False # uses the real balance from the account to simulate
conn = psycopg2.connect(database="kraken_crawler", user="kraken",  password="kraken")  # basic connection information for a local postgeSQL-DB, change this
FORMAT = '%(asctime)-5s [%(name)s] %(levelname)s: %(message)s'
logging.basicConfig(filename='/var/log/kraken/kraken_log.log',level=logging.INFO,format=FORMAT)
logger = logging.getLogger('kraken_crawler')


def main(argv):
    global simulate
    global realSim
    keyfile = os.path.expanduser('~') + '/.kraken/kraken.secret'
    try:
        opts, args = getopt.getopt(argv, 'ht:a:o:s')
    except getopt.GetoptError:
        print 'Invalid Usage: test.py -a [action]'  # -i <inputfile> -o <outputfile>'
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print "test.py -k <kraken.secret> -a [action]\n" \
                  "\tThe kraken.secret file contains in the first line the key and in the second the secret - " \
                  "nothing else. This is optional.\n" \
                  "\tThe action can be one of the followings:" \
                  "\t\"pupolateDB\" or \"-t <algorithm>\" \n\t\tadding the \"-s\" flag only simulates the algorithm"
            sys.exit()
        elif opt in ("-k", "--kfile"):
            keyfile = arg
        elif opt == "-s":
            simulate = True
        elif opt == "-r":
            realSim = True


    k = krakenex.API()
    k.load_key(keyfile)


    for opt, arg in opts:
        if opt == '-a' and arg == 'populateDB':
            logger = logging.getLogger('kraken_crawler')
            populate_db(k)
        elif opt == '-a' and arg == 'accountInfo':
            account = kraken_account(conn,k,simulate)
            print_account_info(account)
        elif opt == "-t":
            logger = logging.getLogger('kraken_trader')
            try:
                trader_class = eval(arg)
            except:
                print "Invalid trader class name!"
                logger.error("Invalid trader class name!")
                break
            print trader_class
            account = kraken_account(conn,k,simulate,logger)
            trader_class = trader_class(conn,k,account)

            if simulate:
                a = analyzer(trader_class,account)
                a.simulate()
            else:
                #account = kraken_account(conn,k,simulate)
                logger.info("Starting Trader...")
                print_account_info(account)
                trade = dict()
                logger.info("Getting Sell Advices...")
                trade["sell"] = trader_class.get_sell_advice(dt.datetime.now())
                logger.info("Getting Buy Advices...")
                trade["buy"] = trader_class.get_buy_advice(dt.datetime.now())
                if trade["sell"] or trade["buy"]:
                    print "---------------------\nPerforming Trades:\n---------------------"
                    logger.info("Performing Trades:")
                    account.place_orders(k,trade,trader_class)
                    account.get_open_orders()
                    print_orders(account)
                else:
                    print "---------------------\nNo trade orders received!\n---------------------"
                    logger.info("No trade orders received!")

        elif opt == "-o":
            account = kraken_account(conn,k,simulate)
            try:
                trader_class = eval(arg)
            except:
                print "Invalid trader class name!"
                logger.error("Invalid trader class name!")
                break
            print trader_class
            trader_class = trader_class(conn,k,account)
            a = analyzer(trader_class,account)
            a.optimize = True
            a.gradient()

def print_account_info(acc):
    print "Single Balances\n---------------------"
    for curr in acc.balance:
        print curr[1:] + ": " + str(acc.balance[curr])

    print "\nOverall Information\n---------------------"
    for tb in acc.trade_balance:
        print enum(tb) + ": " + str(acc.trade_balance[tb])
    print_orders(acc)

def print_orders(acc):
    print "\nOpen Orders\n---------------------"
    for oo in acc.open_orders['open']:
        timestr = datetime.fromtimestamp(int(acc.open_orders['open'][oo]['opentm'])).strftime('%Y-%m-%d %H:%M:%S')
        print timestr+": Volumen: "+acc.open_orders['open'][oo]['vol']
        print acc.open_orders['open'][oo]['descr']

def populate_db(k):

    for pair in get_asset_pairs(k):
        query = query_market(k, pair)
        if 'result' in query.keys() and len(query['result']):
            update_db(query['result'][pair], pair)
        else:
            logger.warning("Error querying pair: " + pair[1:4] +"-"+ pair[5:])
            logger.warning(query['error'])

def get_asset_pairs(k):
    pairs = k.query_public('AssetPairs')
    trade_pairs = []
    for pair in pairs['result']:
        #pair = pair.replace(".d", "")
        if not (pair.find(".d")>=0 or pair.find("CAD") >= 0 or pair.find("USD") >= 0 or pair.find(
                "GBP") >= 0 or pair.find("JPY") >= 0):
            trade_pairs.append(pair)

    return trade_pairs

def query_market(k, pair):
    return k.query_public('Ticker', {'pair': pair})

def update_db(res, pair):
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
    cur = conn.cursor()
    try:
        logger.info("Populating table " + pair)
        cur.execute(
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
        cur.close()
        conn.commit()
    except psycopg2.Error as e:
        if e.pgcode == '42P01':  # Table does not exist
            logger.info("Found new traid pair. Creating a new table...")
            cur = conn.cursor()
            cur.execute("rollback")
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
                cur.execute(query)
                cur.close()
                update_db(res, pair)
            except psycopg2.Error as e:
                logger.error("Could not create new table.")
                logger.error(pgcode)
                logger.error(e.pgerror)
        else:
            logger.error("Unable to insert new date into the table: " +pair)
            logger.warning(e.pgcode)
            logger.warning(e.pgerror)
    return

def enum(x):
    return {
        'tb': "Trade Balance",
        'eb': "Equivalent Balance",
        'm': "Margin Amount of Open Positions",
        'n': "Unrealized net profit/loss of open positions",
        'c': "Cost basis of open positions",
        'v': "Current floating valuation of open positions",
        'e': "Equity = trade balance + unrealized net profit/loss",
        'mf': "Free Margin = Equity - Initial Margin",
        'ml': "Margin level = (equity / initial margin) * 100",
    }.get(x, "unknown")

if __name__ == "__main__":
    main(sys.argv[1:])
