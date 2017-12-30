#!/usr/bin/python3

import getopt
import logging
import psycopg2
import sys
from datetime import datetime

import krakenex
from src.account import KrakenAccount
from src.all_traders import *
from src.analyzer import TraderAnalyzer
import src.db_queries as dbq
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

simulate = False
optimize = False
realSim = False # uses the real balance from the account to simulate
# try_host = "192.168.1.184"
# conn = psycopg2.connect(host="localhost",database="kraken_crawler", user="kraken",  password="kraken")  # basic connection information for a local postgeSQL-DB, change this
FORMAT = '%(asctime)-5s [%(name)s] %(levelname)s: %(message)s'
logging.basicConfig(filename='/var/log/kraken/kraken_log.log',level=logging.INFO,format=FORMAT,datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('kraken_crawler')
dbq = dbq.DbQueries()

def main(argv):
    global simulate
    global optimize
    global realSim
    Notify.init("kraken_trader")
    try:
        opts, args = getopt.getopt(argv, 'a:hskor')
    except getopt.GetoptError:
        print('Invalid Usage: ./kraken_trader.py -a [action] <options>\n'
              '\tFor more information try ./kraken_trader.py -h') # -i <inputfile> -o <outputfile>'
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print("./kraken_trader.py -a [action] <options>\n" 
                "The action can be one of the followings:\n" 
                "\t<algorithm-name>, \"accountInfo\", \"accountDev\" or \"populateDB\""
                "\n\t-k <path-to-key.file>:\t uses a specific kraken key-file"
                "\n\t-s:\t only simulates the algorithm"
                "\n\t-r:\t simulates the algorithm, with the current balance of the account"
                "\n\t-o:\t optimizes the constants of the algorithm")
            sys.exit()
        elif opt in ("-k", "--kfile"):
            keyfile = arg
        elif opt == "-s":
            simulate = True
        elif opt == "-r":
            realSim = True
        elif opt == "-o":
            optimize = True
            simulate = True

    k = krakenex.API()
    k.notify = Notify

    account = KrakenAccount(k, simulate)

    for opt, arg in opts:
        if opt == '-a' and arg == 'populateDB':
            # Gets only public information from kraken, no account needed
            logger = logging.getLogger('kraken_crawler')
            populate_db(k)

        elif opt == '-a' and arg == 'accountInfo':
            print_account_info(account)

        elif opt == '-a' and arg == 'accountDev':
            # trader_class = eval("ma_trader")
            account.account_dev()

        elif opt == "-a":
            logger = logging.getLogger('kraken_trader')
            try:
                trader_class = eval(arg)
            except:
                print("Invalid trader class name!")
                logger.error("Invalid trader class name!")
                break
            trader = trader_class(account)

            if optimize:
                a = TraderAnalyzer(trader, account)
                a.optimize=True
                a.gradient()
            elif simulate:
                a = TraderAnalyzer(trader, account)
                a.simulate(n=200)
            else:
                logger.info("Starting Trader '"+arg+"'...")
                print_account_info(account)
                trade = dict()
                logger.info("Getting Sell Advices...")
                trade["sell"] = trader_class.get_sell_advice(datetime.now())
                logger.info("Getting Buy Advices...")
                trade["buy"] = trader_class.get_buy_advice(datetime.now())
                if trade["sell"] or trade["buy"]:
                    print("---------------------\nPerforming Trades:\n---------------------")
                    logger.info("Performing Trades:")
                    account.place_orders(k,trade,trader_class)
                    account.get_open_orders()
                    print_orders(account)
                else:
                    print("---------------------\nNo trade orders received!\n---------------------")
                    logger.info("No trade orders received!")


def print_account_info(acc):
    print("Single Balances\n---------------------")
    for curr in acc.balance:
        print(curr + ": " + str(acc.balance[curr]))

    print("\nOverall Information\n---------------------")
    for tb in acc.trade_balance:
        print(enum(tb) + ": " + str(acc.trade_balance[tb]))
    print_orders(acc)


def print_orders(acc):
    print("\nOpen Orders\n---------------------")
    for oo in acc.open_orders['open']:
        timestr = datetime.fromtimestamp(int(acc.open_orders['open'][oo]['opentm'])).strftime('%Y-%m-%d %H:%M:%S')
        print(timestr+": Volumen: "+acc.open_orders['open'][oo]['vol'])
        print(acc.open_orders['open'][oo]['descr'])


def populate_db(k):
    for pair in get_asset_pairs(k):
        query = query_market(k, pair)
        if 'result' in query.keys() and len(query['result']):
            dbq.update_db(query['result'][pair], pair)
        else:
            logger.warning("Error querying pair: " + pair)
            logger.warning(query['error'])


def get_asset_pairs(k):
    pairs = k.query_public('AssetPairs')
    trade_pairs = []
    for pair in pairs['result']:
        if not (pair.find(".d")>=0 or pair.find("CAD") >= 0 or pair.find("USD") >= 0 or pair.find(
                "GBP") >= 0 or pair.find("JPY") >= 0):
            trade_pairs.append(pair)

    return trade_pairs


def query_market(k, pair):
    return k.query_public('Ticker', {'pair': pair})


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
