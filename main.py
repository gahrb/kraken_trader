#!/usr/bin/python

import getopt
import os
import psycopg2
import sys
from datetime import datetime

import krakenex
from kraken_trader.account import kraken_account
from kraken_trader.all_traders import *
mod = __import__('kraken_trader.all_traders', fromlist=['standard_trader'])

simulate = True  # as long as this is under development, leave it on True
trade_pairs = ['XXBTZEUR', 'XETHZEUR', 'XLTCZEUR']  # basic set of asset pairs
conn = psycopg2.connect(database="kraken_crawler", user="kraken",
                        password="kraken")  # basic connection information for a local postgeSQL-DB, change this


def main(argv):
    keyfile = os.path.expanduser('~') + '/.kraken/kraken.secret'
    try:
        opts, args = getopt.getopt(argv, 'ht:a:')
    except getopt.GetoptError:
        print 'test.py -a [action]'  # -i <inputfile> -o <outputfile>'
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

    k = krakenex.API()
    k.load_key(keyfile)
    get_asset_pairs(k)

    for opt, arg in opts:
        if opt == '-a' and arg == 'populateDB':
            populate_db(k)
        elif opt == '-a' and arg == 'accountInfo':
            account_info = kraken_account(conn,k)
            print_account_info(account_info)
        elif opt == "-t":
            trader_class = advanced_trader(conn,k,trade_pairs)# TODO: get a class by the input argument getattr(mod, arg)
            print "Sell advice: " + str(trader_class.get_sell_advice())
            print "Buy advice: " + str(trader_class.get_buy_advice())
            place_order(k)

def print_account_info(acc):
    acc.get_balance()
    print "Single Balances\n---------------------"
    for curr in acc.balance:
        print curr[1:] + ": " + acc.balance[curr]

    print "\nOverall Information\n---------------------"
    for tb in acc.trade_balance:
        print enum(tb) + ": " + acc.trade_balance[tb]

def populate_db(k):

    for pair in trade_pairs:
        query = query_market(k, pair)
        if 'result' in query.keys() and len(query['result']):
            update_db(query['result'][pair], pair)
        else:
            print "Error querying pair: " + pair[1:4] +"-"+ pair[5:]
            print query['error']

def place_order(k):
    if not simulate:
        k.query_private('AddOrder', {'pair': 'XXBTZEUR',
                                     'type': 'buy',
                                     'ordertype': 'limit',
                                     'price': '1',
                                     'volume': '1',
                                     'close[pair]': 'XXBTZEUR',
                                     'close[type]': 'sell',
                                     'close[ordertype]': 'limit',
                                     'close[price]': '9001',
                                     'close[volume]': '1'})

def get_asset_pairs(k):
    pairs = k.query_public('AssetPairs')
    for pair in pairs['result']:
        pair = pair.replace(".d", "")
        if not (pair in trade_pairs or pair.find("CAD") >= 0 or pair.find("USD") >= 0 or pair.find(
                "GBP") >= 0 or pair.find("JPY") >= 0):
            print pair
            trade_pairs.append(pair)

    print trade_pairs

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
        print "Populating table " + pair
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
        print e.pgcode
        print e.pgerror
        if e.pgcode == '42P01':  # Table does not exist
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
                print "Creating table " + pair
                cur.execute(query)
                cur.close()
                update_db(res, pair)
            except psycopg2.Error as e:
                print "Could not create new table."
                print e.pgcode
                print e.pgerror
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
