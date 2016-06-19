import logging


class kraken_account:

    def __init__(self,conn,k,simulate=True,logger=""):
        self.conn = conn
        self.k = k
        self.balance = dict()
        self.trade_balance = dict()
        self.simulate = simulate
        self.get_assets()
        if simulate:
            self.populate_balance()
        else:
            self.get_balance()
            self.get_trade_balance()
            self.get_open_orders()

        self.logger = logger


    def get_balance(self):
        all_balances = self.k.query_private('Balance')['result']
        for balance in all_balances:
            self.balance[str(balance)] = float(all_balances[balance])

    def get_trade_balance(self):
        trade_balance = self.k.query_private('TradeBalance',{'Currency':'ZEUR'})['result']
        for balance in trade_balance:
            self.trade_balance[str(balance)] = float(trade_balance[balance])

    def get_assets(self):
        self.asset_pair = self.k.query_public('AssetPairs')['result']
        for key in self.asset_pair.keys():
            if ( key.find(".d") >=0 or key.find("CAD") >=0 or  key.find("USD") >=0 or  key.find("JPY") >=0 or key.find("GBP") >=0 ):
                self.asset_pair.pop(key,None)

    def get_open_orders(self):
        self.open_orders = self.k.query_private('OpenOrders')['result']

    def place_orders(self,k,trades,trader):
        keepAmount = 0
        if trader.constant["delta"]:
            keepAmount = trader.constant["delta"]
        # TODO: implement the trading request
        for action in trades:
            if action:
                for pair in trades[action]:
                    # TODO: check if for current pair other open orders are existing: if yes, stop, or cancle and replace them!
                    if (trades[action][pair] < 0.01):
                        self.logger.info("Not trading "+pair+ ", due to insufficient balance. Action: "+action+" Pair: "+pair)
                        break
                    if action == "sell":
                        action_idx=2
                    elif action == "buy":
                        action_idx=1
                        #Guess the price to pay, and if there is enough balance
                        trades[action][pair] = min(trades[action][pair],self.balance[pair[4:]]/trader.price[pair][-1][action_idx] - keepAmount)

                    res = k.query_private("AddOrder",{'pair': pair,
                           'type': action,
                           'ordertype': 'limit',
                           'price': trader.price[pair][-1][action_idx],
                           'volume': trades[action][pair]*self.balance[pair[:4]]})

                    if res['error']:
                        self.logger.warning("Unable to perform a trade. Due to the error:")
                        self.logger.info(res['error'])
                        self.logger.info("Trade: "+str(action)+", "+str(pair)+", "+str(trades[action][pair]*self.balance[pair[:4]]))
                    else:
                        self.logger.info("Performed trade:")
                        self.logger.info(res['result'])

    def populate_balance(self):
        empty = False
        if not hasattr(self,"balance" ):
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
                    self.balance[pair[:4]] = 0
                else:
                    self.balance[pair[4:]] = 1

