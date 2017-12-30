#!/usr/bin/python3
import helper_functions as hf
import numpy as np
import datetime as dt
import db_queries
import db_queries as dbq


class ma_trader():
    """
    Returns sell/buy advices on the moving average, if a currency is under rated or overrated
    """
    def __init__(self, account):
        self.account = account
        self.queries = db_queries.DbQueries()
        self.pairs = account.asset_pair.keys()
        self.diff = dict()
        self.price = dict()

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = hf.get_tader_name(self)
        self.constant = hf.get_trader_config()[trader_name]

        self.keep = min(0.01,self.constant["delta"])

        # Calculate the predicted change
        self.run_trader()
        self.keep_back(dt.datetime.strptime("2016-01-01","%Y-%m-%d"))

    def write_new_trader(self):
        hf.save_trader_config(self.constant,hf.get_tader_name(self))

    def get_buy_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["ask"],time)
            if elem[pair] > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["ask"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            perform_trades = dict()
            for (pair, v) in allow_trade.items():
                change = (v-self.price[pair][elem[pair]][1])/v
                if v!=-1 and change >= self.constant["gamma"] and \
                        not pair[:4] in self.constant["donottrade"] and \
                        not pair[4:] in self.constant["donottrade"] and \
                        self.account.balance[pair[4:]]-self.keep[pair[4:]] > 0:
                    perform_trades[pair] = min(self.account.balance[pair[4:]] - self.keep[pair[4:]] , \
                            change *self.constant["beta"]*self.account.balance[pair[4:]] * self.price[pair][elem[pair]][2]) / \
                            self.price[pair][elem[pair]][1]

            if (perform_trades):
                self.keep_back(time)
                return perform_trades
        return []

    def get_sell_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["bid"],time)
            if elem[pair] > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["bid"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            perform_trades = dict()
            for (pair,v) in allow_trade.items():
                change = (self.price[pair][elem[pair]][2]-v)/v
                if v!=-1 and change >= self.constant["gamma"] and\
                        not pair[:4] in self.constant["donottrade"] and\
                        not pair[4:] in self.constant["donottrade"] and\
                        self.account.balance[pair[:4]]-self.keep[pair[:4]] > 0: #Ensures, that there is enough amount on this currency to trade
                    #Check if transaction does not exceed the self.keep amount
                    perform_trades[pair] = min(self.account.balance[pair[:4]]-self.keep[pair[:4]],\
                                            change*self.constant["beta"]*self.account.balance[pair[:4]])

            if (perform_trades):
                self.keep_back(time)
                return perform_trades
        return []

    def keep_back(self,time):
        reference_curr = "XXBT"
        balance = self.account.balance
        eq_bal = balance[reference_curr]
        elem = dict()
        for bal in balance:
            if bal!=reference_curr and not bal in self.constant["donottrade"]:
                pair = bal+reference_curr
                if self.price.has_key(pair):
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]*self.price[pair][elem[pair]][1]
                else: #not able to translate the currency directly to the reference currency...
                    pair = "XXBT"+bal
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]/self.price[pair][elem[pair]][2]

        self.keep = dict()
        self.keep["XXBT"] = eq_bal*self.constant["delta"]
        for pair in elem:
            if pair.find("XXBT")==0:
                self.keep[pair[4:]] = self.constant["delta"] * eq_bal * self.price[pair][elem[pair]][1]
            elif self.price[pair][elem[pair]][2] != 0:
                self.keep[pair[:4]] = self.constant["delta"] * eq_bal / self.price[pair][elem[pair]][2]
            else:
                self.keep[pair[:4]] = 0


    def run_trader(self):
        self.ma = dict()
        for pair in self.pairs:
            if not self.price.has_key(pair): #no new results shall be queried, when in the optimization loop!
                # cur = self.conn.cursor()
                # cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair +" order by modtime asc;")
                # res = cur.fetchall()
                # cur.close()

                self.price[pair] = res

            self.ma[pair] = dict()
            self.ma[pair]["ask"] = []
            self.ma[pair]["bid"] = []
            self.ma[pair]["ask"].append([self.price[pair][0][0],self.price[pair][0][1]])
            self.ma[pair]["bid"].append([self.price[pair][0][0],self.price[pair][0][2]])
            for i in range(1,len(self.price[pair])):
                lookback = min(int(self.constant["alpha"]),i)
                self.ma[pair]["ask"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,1])])
                self.ma[pair]["bid"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,2])])


class mas_trader():
    """
    Returns sell/buy advices on the moving average, if a currency is under rated or overrated
    """

    def __init__(self, k, account):
        self.k = k
        self.account = account
        self.pairs = account.asset_pair.keys()
        #self.pred = dict()
        self.diff = dict()
        self.price = dict()

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = 'mas_trader'
        self.constant = hf.get_trader_config()[trader_name]

        #Calculate the predicted change
        self.run_trader()

    def write_new_trader(self):
        hf.save_trader_config(self.constant,hf.get_tader_name(self))

    def get_buy_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["ask"],time)
            if elem[pair] > self.constant["window"]:
                allow_trade[pair]=self.ma[pair]["ask"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            perform_trades = dict()
            for (pair,v) in allow_trade.items():
                change = (v-self.price[pair][elem[pair]][1])/v
                if v!=-1 and change >= self.constant["x_thresh"]:
                    """
                    Things to take care of:
                    - predict amount to buy
                    - the buy amount does not exceed the max_vol amount
                    - enough balance to sell (incl. keep back amount),
                    """
                    # perform_trades[pair] = min(self.account.balance[pair[4:]], \
                    #         change *self.constant["trade_factor"]*self.account.balance[pair[4:]] * self.price[pair][elem[pair]][2]) / \
                    #         self.price[pair][elem[pair]][1]
                    # Get equivalent balance first, translate the pair currencies into the base

                    eq_bal,rel_bal = hf.get_eq_bal(self.account.balance,self.price,time,'XXBT')
                    if pair[:4] in self.constant['max_vol']:
                        max_vol = self.constant['max_vol'][pair[:4]]
                    else:
                        max_vol = self.constant['max_vol']['default']

                    if pair[4:] in self.constant['min_vol']:
                        min_vol = self.constant['min_vol'][pair[4:]]
                    else:
                        min_vol = self.constant['min_vol']['default']

                    #The max relative amount, which will be traded
                    fac = 0.0
                    sell_lim = 0
                    if pair[:4] in rel_bal and rel_bal[pair[:4]]:
                        fac = self.account.balance[pair[:4]]/rel_bal[pair[:4]]
                        sell_lim = max(rel_bal[pair[:4]]-min_vol,0)
                    else:
                        self.account.balance[str(pair[:4])] = 0
                    if not pair[4:] in rel_bal:
                        rel_bal[pair[4:]] = 0
                    buy_lim = max(max_vol - rel_bal[pair[:4]],0)
                    rel_amount = min(sell_lim, buy_lim)

                    #The max absolute amount, which will be bought
                    abs_amountBuy = min(rel_amount*fac, change*self.constant["trade_factor"]*self.account.balance[pair[:4]])

                    if abs_amountBuy>0.01: #Kraken's minimum amount to trade
                        perform_trades[pair] = abs_amountBuy

            if (perform_trades):
                self.check_max_vol(time)
                return perform_trades
        return []

    def get_sell_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["bid"],time)
            if elem[pair] > self.constant["window"]:
                allow_trade[pair]=self.ma[pair]["bid"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            perform_trades = dict()
            for (pair,v) in allow_trade.items():
                change = (self.price[pair][elem[pair]][2]-v)/v
                if v!=-1 and change >= self.constant["x_thresh"]:
                    """
                    Things to take care of:
                    - enough balance to sell (incl. the min_vol),
                    - bought balance does not exceed it's max_vol value
                    """
                    # Get equivalent balance first, translate the pair currencies into the base
                    eq_bal,rel_bal = hf.get_eq_bal(self.account.balance,self.price,time,'XXBT')
                    if pair[4:] in self.constant['max_vol']:
                        max_vol = self.constant['max_vol'][pair[4:]]
                    else:
                        max_vol = self.constant['max_vol']['default']

                    if pair[:4] in self.constant['min_vol']:
                        min_vol = self.constant['min_vol'][pair[:4]]
                    else:
                        min_vol = self.constant['min_vol']['default']

                    #The max relative amount, which will be traded
                    fac = 0.0
                    sell_lim = 0
                    if pair[:4] in rel_bal and rel_bal[pair[:4]]:
                        fac = self.account.balance[pair[:4]]/rel_bal[pair[:4]]
                        sell_lim = max(rel_bal[pair[:4]]-min_vol,0)
                    else:
                        self.account.balance[str(pair[:4])] = 0
                    if not pair[4:] in rel_bal:
                        rel_bal[str(pair[4:])] = 0
                    buy_lim = max(max_vol - rel_bal[pair[4:]],0)
                    rel_amount = min(sell_lim, buy_lim)
                    #The max absolute amount, which will be sold

                    abs_amountSell = min(rel_amount*fac, change*self.constant["trade_factor"]*self.account.balance[pair[:4]])

                    if abs_amountSell>0.01: #Kraken's minimum amount to trade
                        perform_trades[pair] = abs_amountSell



            if (perform_trades):
                self.check_max_vol(time)
                return perform_trades
        return []

    def check_max_vol(self,time):
        reference_curr = "XXBT"
        balance = self.account.balance
        eq_bal = balance[reference_curr]
        elem = dict()
        for bal in balance:
            if bal!=reference_curr:
                pair = bal+reference_curr
                if self.price.has_key(pair):
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]*self.price[pair][elem[pair]][1]
                else: #not able to translate the currency directly to the reference currency...
                    pair = "XXBT"+bal
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]/self.price[pair][elem[pair]][2]

        self.keep = dict()
        self.keep["XXBT"] = eq_bal*self.constant["x_thresh"]
        for pair in elem:
            if pair.find("XXBT")==0:
                self.keep[pair[4:]] = self.constant["x_thresh"] * eq_bal * self.price[pair][elem[pair]][1]
            else:
                self.keep[pair[:4]] = self.constant["x_thresh"] * eq_bal / self.price[pair][elem[pair]][2]


    def run_trader(self):
        self.ma = dict()
        for pair in self.pairs:
            if not self.price.has_key(pair): #no new results shall be queried, when in the optimization loop!
                cur = self.conn.cursor()
                cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair +" order by modtime asc;")
                res = cur.fetchall()
                cur.close()
                self.price[pair] = res

            self.ma[pair] = dict()
            self.ma[pair]["ask"] = []
            self.ma[pair]["bid"] = []
            self.ma[pair]["ask"].append([self.price[pair][0][0],self.price[pair][0][1]])
            self.ma[pair]["bid"].append([self.price[pair][0][0],self.price[pair][0][2]])
            for i in range(1,len(self.price[pair])):
                lookback = min(int(self.constant["window"]),i)
                self.ma[pair]["ask"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,1])])
                self.ma[pair]["bid"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,2])])


class MaDBTrader:
    """
    Returns sell/buy advices on the moving average, moves most of the logic to the DB
    """

    def __init__(self, account):
        self.account = account
        self.diff = dict()
        self.dbq = dbq.DbQueries()
        self.hf = hf.HelperFunctions(self.account.asset_pairs, self.dbq)

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = 'MaDBTrader'
        self.constant = hf.get_trader_config()[trader_name]

    def ma(self, pair, type, timestamp, window_len):
        series = self.dbq.get(table=pair, column=type, time=timestamp, limit=window_len, mode='smaller')
        if len(series) < window_len:
            return -1
        return np.array(series).mean()

    def write_new_trader(self):
        hf.save_trader_config(self.constant, hf.get_tader_name(self))

    def get_buy_advice(self, time):
        allow_trade = dict()
        for pair in self.account.asset_pairs:
            allow_trade[pair] = {'base': self.account.asset_pairs[pair]['base'].lower(),
                                 'quote': self.account.asset_pairs[pair]['quote'].lower(),
                                 'basevol': self.account.balance[self.account.asset_pairs[pair]['base'].lower()],
                                 'quotevol': self.account.balance[self.account.asset_pairs[pair]['quote'].lower()],
                                 'price': self.dbq.get(table=pair, column='bid_price', time=time)[0][0],
                                 'ma': self.ma(pair, "bid_price", time, self.constant["window"])}

        for (pair, v) in allow_trade.items():
            perform_trades = dict()
            if not (v['ma'] == -1 or v['price'] == 0):
                change = (v['ma'] - v['price']) / v['price']
                if v['ma'] != -1 and change >= self.constant["x_thresh"] and v['price'] > 0.0:
                    """
                    Things to take care of:
                    - enough balance to sell (incl. the min_vol),
                    - bought balance does not exceed it's max_vol value
                    """
                    # Get equivalent balance first, translate the pair currencies into the base
                    rel_base = self.hf.get_eq_bal(v['basevol'],
                                                  v['base'],
                                                  time,
                                                  'xxbt') / self.hf.get_total_bal(time, ref='xxbt')
                    rel_quote = self.hf.get_eq_bal(v['quotevol'],
                                                   v['quote'],
                                                   time,
                                                   'xxbt') / self.hf.get_total_bal(time, ref='xxbt')
                    # Wanted Trade Amount
                    wta = change * self.constant["trade_factor"]

                    # Maximum Buy Amount
                    if v['base'] in set(k.lower() for k in self.constant['max_vol']):
                        mba = self.constant['max_vol'][v['base'].upper()]
                    else:
                        mba = self.constant['max_vol']['default']

                    # Minimum Keep Amount
                    if v['quote'] in set(k.lower() for k in self.constant['max_vol']):
                        mka = self.constant['min_vol'][v['quote'].upper()]
                    else:
                        mka = self.constant['min_vol']['default']

                    # Maximum Sell Amount
                    rmsa = max(rel_quote - mka, 0)
                    # Relative Maximum Buy Amount
                    rmba = max(mba - rel_base, 0)
                    # Total Relative Trading Amount
                    trta = min(min(rmba, rmsa), wta)

                    # Transferred to absolute 'base' trading amount
                    absamount = trta * v['basevol'] / v['price']
                    if absamount > 0.01:  # Kraken's minimum amount to trade
                        perform_trades.update({pair: absamount})

            if perform_trades:
                # self.check_max_vol(time)
                return perform_trades
        return []

    def get_sell_advice(self, time):
        allow_trade = dict()
        for pair in self.account.asset_pairs:
            allow_trade[pair] = {'base': self.account.asset_pairs[pair]['base'].lower(),
                                 'quote': self.account.asset_pairs[pair]['quote'].lower(),
                                 'basevol': self.account.balance[self.account.asset_pairs[pair]['base'].lower()],
                                 'quotevol': self.account.balance[self.account.asset_pairs[pair]['quote'].lower()],
                                 'price': self.dbq.get(table=pair, column='ask_price', time=time)[0][0],
                                 'ma': self.ma(pair, "ask_price", time, self.constant["window"])}

        for (pair, v) in allow_trade.items():
            perform_trades = dict()
            if not (v['ma'] == -1 or v['price'] == 0):
                change = (-v['ma'] + v['price']) / v['price']
                if v['ma'] != -1 and change >= self.constant["x_thresh"] and v['price'] > 0.0:
                    """
                    Things to take care of:
                    - enough balance to sell (incl. the min_vol),
                    - bought balance does not exceed it's max_vol value
                    """
                    # Get equivalent balance first, translate the pair currencies into the base
                    rel_base = self.hf.get_eq_bal(v['basevol'],
                                                  v['base'],
                                                  time,
                                                  'xxbt') / self.hf.get_total_bal(time, ref='xxbt')
                    rel_quote = self.hf.get_eq_bal(v['quotevol'],
                                                   v['quote'],
                                                   time,
                                                   'xxbt') / self.hf.get_total_bal(time, ref='xxbt')
                    # Wanted Trade Amount
                    wta = change * self.constant["trade_factor"]

                    # Minimum Keep Amount
                    if v['base'] in set(k.lower() for k in self.constant['min_vol']):
                        mka = self.constant['min_vol'][v['base'].upper()]
                    else:
                        mka = self.constant['min_vol']['default']
                    # Maximum Buy Amount
                    if v['quote'] in set(k.lower() for k in self.constant['max_vol']):
                        mba = self.constant['max_vol'][v['quote'].upper()]
                    else:
                        mba = self.constant['max_vol']['default']

                    # Maximum Sell Amount
                    rmsa = max(rel_base - mka, 0)
                    # Relative Maximum Buy Amount
                    rmba = max(mba - rel_quote, 0)
                    # Total Relative Trading Amount
                    trta = min(min(rmba, rmsa), wta)

                    # Transferred to absolute 'base' trading amount
                    absamount = trta * v['quotevol'] * v['price']

                    if absamount > 0.01:  # Kraken's minimum amount to trade
                        perform_trades.update({pair: absamount})

            if perform_trades:
                # self.check_max_vol(time)
                return perform_trades
        return []
