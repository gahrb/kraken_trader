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
        self.get_local_assets()
        self.get_local_asset_pairs()
        if simulate:
            self.populate_balance()
        else:
            self.get_assetpairs()
            self.get_assets()
            # Load the key to perform private queries.
            self.k.load_key(keyfile)
            # Query private account information
            self.get_ledger_info()
            self.get_balance()
            self.get_trade_balance()
            self.get_open_orders()
        self.hf = hf.HelperFunctions(self.asset_pairs, self.dbq)

    def get_balance(self):
        local_bal = self.dbq.get_balances()
        currencies = self.dbq.get_columns()
        for idx in range(len(local_bal[-1])):
            cur = currencies[idx].lower()
            if not (cur=="modtime" or cur=="eq_bal"):
                self.balance[cur] = float(local_bal[-1][idx])

        # Find new currencies: They did not appear in the Balance query once, but ony via the asset_pairs
        for descr in self.asset_pairs.items():
            if not(str(descr[1]['quote']).lower() in self.balance):
                self.dbq.add_column_to_table('balance', str(descr[1]['quote']).lower())
                self.balance[str(descr[1]['quote']).lower()] = 0
            if not(str(descr[1]['base']).lower() in self.balance):
                self.dbq.add_column_to_table('balance', str(descr[1]['base']).lower())
                self.balance[str(descr[1]['base']).lower()] = 0

        # Check if some balance changed, i.e. manual transactions -> timestamp won't be correct
        # set fixed time, so not multiple rows get created
        time = dt.datetime.now()
        for currency, value in self.k.query_private('Balance')['result'].items():
            if self.balance[str(currency).lower()]!= float(value):
                self.balance[str(currency).lower()] = float(value)
                self.dbq.append_balance(currency=str(currency).lower(), time=time, value=float(value))

    def get_trade_balance(self):
        for key, balance in self.k.query_private('TradeBalance', {'Currency': 'ZEUR'})['result'].items():
            self.trade_balance[str(key).lower()] = float(balance)

    def get_local_asset_pairs(self):
        try:
            self.asset_pairs = self.dbq.get_asset_pairs()
        except:
            self.get_assetpairs()

    def get_local_assets(self):
        try:
            self.assets = self.dbq.get_assets()
        except:
            self.get_assets()

    def get_assets(self):
        query = self.k.query_public('Assets')
        if query['error']:
            print("Error querying Assets: " + query['error'])
            return
        self.assets = dict((k.lower(), v) for k,v in query['result'].items())
        self.dbq.assets2db(self.assets)

    def get_assetpairs(self):
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
        self.dbq.assetpairs2db(self.asset_pairs)

    def get_open_orders(self):
        self.open_orders = self.k.query_private('OpenOrders')['result']

    def get_ledger_info(self):
        self.ledger_info = self.k.query_private('Ledgers')['result']

    def place_orders(self, k, trades, trader):
        keep_amount = 0
        if "delta" in trader.constant:
            keep_amount = trader.constant["delta"]
        for action in trades:
            if action:
                for pair in trades[action]:
                    # TODO: check if for current pair other open orders are existing: if yes, stop, or cancle and
                    # replace them!
                    if action == "sell":
                        action_idx=2
                        amount = trades[action][pair]
                    elif action == "buy":
                        action_idx=1
                        #Guess the price to pay, and hence there is enough balance
                        amount = min(trades[action][pair],self.balance[pair[4:]]/trader.price[pair][-1][action_idx] - keep_amount)
                    else:
                        self.logger.warning("Got an unknown actions call: " + action)
                        return

                    if trades[action][pair] < 0.01:
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

        # Update balance after order was placed
        self.get_balance()

    def populate_balance(self):
        if not hasattr(self, "balance"):
            self.balance = dict()
        for asset in self.assets:
            self.balance[asset.lower()] = 1

    def account_dev(self):
        balances = self.dbq.get_balances()
        currencies = self.dbq.get_columns()
        eq_bal_idx = currencies.index('eq_bal')
        eq_bal = dict()
        for row in balances:
            time = row[0]
            eq_bal.update({time: row[eq_bal_idx]})
            if eq_bal[time] == 0:
                # the equivalent balance was not yet updated in the local db. recalculate it
                for cur in range(len(currencies)-1):  # first column is the timestamp
                    eq_bal[time] += self.hf.get_eq_bal(row[cur+1], currencies[cur+1].lower(), time, "zeur")
                # update db
                self.dbq.alter_value(table="balance", row=time, column='eq_bal', value=eq_bal[time])
            print(str(time) + ": " + str(eq_bal[time]))

        time = str(dt.datetime.now())
        eq_bal.update({time: 0})
        for cur in self.balance.keys():  # first column is the timestamp
            eq_bal[time] += self.hf.get_eq_bal(self.balance[cur], cur.lower(), time, "zeur")
        print("Current estimated equivalent Balance:")
        print(str(time) + ": " + str(eq_bal[time]))
