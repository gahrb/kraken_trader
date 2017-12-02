#!/usr/bin/python3

import datetime as dt
import helper_functions as hf
import os
import psycopg2
import db_queries as dbq
import logging

keyfile = os.path.expanduser('~') + '/.kraken/kraken.secret'


class KrakenAccount:

    def __init__(self, k, simulate=True, logger=logging.getLogger('KrakenAccount')):
        self.logger = logger
        self.dbq = dbq.DbQueries()
        self.k = k
        self.balance = dict()
        self.trade_balance = dict()
        self.asset_pairs = dict()
        self.simulate = simulate
        self.get_assets()
        if simulate:
            self.populate_balance()
        else:
            # Load the key to perform private queries.
            self.k.load_key(keyfile)
            # Query private account information
            # self.get_ledger_info()
            self.get_balance()
            self.get_trade_balance()
            self.get_open_orders()
            # Check if local database needs an update
            # self.db_updatecheck()
        self.hf = hf.HelperFunctions(self.asset_pairs, self.dbq)

    def get_balance(self):

        for currency, value in self.get_local_balance().items():
            self.balance[str(currency).lower()] = float(value[0][0])

        for currency, value in self.k.query_private('Balance')['result'].items():
            if not str(currency).lower() in self.balance:
                self.add_todb(str(currency).lower())
                self.balance[str(currency).lower()] = float(value)

        for descr in self.asset_pairs.items():
            if not(str(descr[1]['quote']).lower() in self.balance):
                self.add_todb(str(descr[1]['quote']).lower())
                self.balance[str(descr[1]['quote']).lower()] = 0
            if not(str(descr[1]['base']).lower() in self.balance):
                self.add_todb(str(descr[1]['base']).lower())
                self.balance[str(descr[1]['base']).lower()] = 0

    def get_local_balance(self):
        local_bal = dict()
        query = "select * from balance;"
        self.dbq.execute(query)
        for desc in self.dbq.cursor.description:
            currency = desc[0]
            if currency != 'modtime' and currency != 'eq_bal':
                query = "SELECT " + currency + " FROM balance"
                try:
                    local_bal[currency] = self.dbq.get_last(query)
                except:
                    local_bal[currency] = 0
        return local_bal

    def add_todb(self, currency):
        query = "ALTER TABLE balance ADD COLUMN " + str(currency).lower() + " double precision default 0;"
        self.dbq.execute(query)
        self.dbq.commit()

    def balance_to_db(self):
        query = "select column_name from information_schema.columns where table_name='balance';"
        try:
            cols = self.dbq.execute(query)
        except psycopg2.Error as e:
            self.logger.error("Could not query the balance table schema.")
            self.logger.error(e.pgcode)
            self.logger.error(e.pgerror)

        missing =  set(map(str.lower,self.balance))-set([ seq[0] for seq in cols ])
        if missing:
            query = "ALTER TABLE balance "
            for miss in missing:
                self.logger.info("Adding new column "+miss+" to the account table.")
                query += "ADD COLUMN "+miss+" double precision default 0, "
            query = query[0:-2]
            self.cur.execute(query+";")

        dbString = "INSERT INTO balance ("
        nameString = "modtime"
        valueString = "%s"
        values = (dt.datetime.now(),)
        for balance in self.balance:
            nameString += ", "+balance.lower()
            valueString += ", %s"
            values += (self.balance[balance],)

        dbString += nameString+") VALUES ("+valueString+");"
        self.cur.execute(dbString,values)
        self.cur.close()
        self.conn.commit()

    def get_trade_balance(self):
        for key, balance in self.k.query_private('TradeBalance', {'Currency': 'ZEUR'})['result'].items():
            self.trade_balance[str(key).lower()] = float(balance)

    def get_assets(self):
        self.asset_pairs = self.k.query_public('AssetPairs')['result']
        tmp_dict = dict()
        for key in self.asset_pairs.keys():
            if not(key.find(".d") >= 0 or
                           key.find("CAD") >= 0 or
                           key.find("USD") >= 0 or
                           key.find("JPY") >= 0 or
                           0 <= key.find("GBP")):
                tmp_dict.update({key.lower(): self.asset_pairs[key]})
                # self.asset_pairs.pop(key,None)
        self.asset_pairs = tmp_dict

    def get_open_orders(self):
        self.open_orders = self.k.query_private('OpenOrders')['result']

    def get_ledger_info(self):
        self.ledger_info = self.k.query_private('Ledgers')['result']

    def place_orders(self, k, trades, trader):
        keepAmount = 0
        if "delta" in trader.constant:
            keepAmount = trader.constant["delta"]
        # TODO: implement the trading request
        for action in trades:
            if action:
                for pair in trades[action]:
                    # TODO: check if for current pair other open orders are existing: if yes, stop, or cancle and
                    # replace them!
                    amount = 0
                    if action == "sell":
                        action_idx=2
                        amount = trades[action][pair]
                    elif action == "buy":
                        action_idx=1
                        #Guess the price to pay, and hence there is enough balance
                        amount = min(trades[action][pair],self.balance[pair[4:]]/trader.price[pair][-1][action_idx] - keepAmount)

                    if (trades[action][pair] < 0.01):
                        self.logger.info("Not trading "+pair+ ", due to insufficient balance. Action: "+action+" Pair: "+pair)
                        break
                    res = k.query_private("AddOrder",{'pair': pair,
                           'type': action,
                           'ordertype': 'limit',
                           'price': format(trader.price[pair][-1][action_idx],'.10f'),
                           'volume': amount})

                    if res['error']:
                        self.logger.warning("Unable to perform a trade. Due to the error:")
                        self.logger.info(res['error'])
                        self.logger.info("Trade: "+str(action)+", "+str(pair)+", "+str(trades[action][pair]*self.balance[pair[:4]]))
                        k.notify.Notification.new("Transaction Error","Trade: "+str(action)+", "+str(pair)+", "+str(trades[action][pair]*self.balance[pair[:4]])+ "\nReason: "+res['error'][0]).show()
                    else:
                        self.logger.info("Performed trade:")
                        self.logger.info(res['result'])
                        k.notify.Notification.new("New Transaction",str(res['result'])).show()

        self.balance_to_db()

    def populate_balance(self):
        empty = False
        if not hasattr(self,"balance"):
            self.balance = dict()
            emtpy = True
        for pair in self.asset_pair.keys():
            if self.simulate or not(pair[:4] in self.balance):
                if empty:
                    self.balance[pair[:4]] = 0
                else:
                    self.balance[pair[:4]] = 1
            if self.simulate or not(pair[4:] in self.balance):
                if empty:
                    self.balance[pair[4:]] = 0
                else:
                    self.balance[pair[4:]] = 1

    def db_updatecheck(self):
        # TODO: compare local balance vs. kraken_account balance renew local database
        # I think everything below here is bad and has to be rewritten totally...
        query = "SELECT "
        for currency in self.balance.keys():
            query += currency + ", "
        query = query.rstrip(", ") + " FROM balance order by modtime desc limit 1;"

        self.dbq.execute(query)
        balance = self.dbq.cursor.fetchall()[0]
        for it in balance: # -1 because the first row is 'modtime' --> add below +1
            bal = self.cur.description[it+1][0].lower()
            if bal in self.balance.keys() and self.balance[bal] != balance[0][it+1]:
                self.balance_to_db()
                break

    def accountDev(self):
        balances = self.dbq.get_balances()
        currencies = self.dbq.get_columns()
        tot_eq_bal = dict()
        for row in balances:
            time = row[0]
            tot_eq_bal.update({time: 0})
            for cur in range(len(currencies)-1):  # first column is the timestamp
                balance = row[cur+1]
                eq_bal = self.hf.get_eq_bal(balance, currencies[cur+1].lower(), time, "zeur")
                tot_eq_bal[time] += eq_bal
            print(str(time) + ": " + str(tot_eq_bal[time]))

        # Neglect current value for the moment
        # time = dt.datetime.now()
        # balance = dict()
        # for it in range(len(self.cur.description)-1): # -1 because the first row is 'modtime' --> add below +1
        #     bal = self.cur.description[it+1][0].lower()
        #     balance[bal] = DBbalance[-1][it+1]
        # eq_bal,rel_bal = self.hf.get_eq_bal(balance, self.dbq.closestelem(row[1]+"zeur",time), time, "ZEUR")
        # print("Current equivalent Balance estimated:[ZEUR]")
        # print(str(time) + ": " + str(eq_bal)+\
        #     "\nRelative balances[%]: "+str(sorted(rel_bal.items(), key=lambda x: x[1], reverse=True)))


