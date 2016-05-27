class kraken_account:

    def __init__(self,conn,k,simulate=True):
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

    def place_orders(self,k,trades=False):
        # TODO: implement the trading request
        print trades
        if not self.simulate and not type(trades) is bool:
            for trade in trades:
                print trade
                res = trades[trade]
                # res = k.query_private('AddOrder', {'pair': 'XXBTZEUR',
                #                          'type': 'buy',
                #                          'ordertype': 'limit',
                #                          'price': '1',
                #                          'volume': '1',
                #                          'close[pair]': 'XXBTZEUR',
                #                          'close[type]': 'sell',
                #                          'close[ordertype]': 'limit',
                #                          'close[price]': '9001',
                #                          'close[volume]': '1'})
                print res

    def populate_balance(self):
        self.balance = dict()
        for pair in self.asset_pair.keys():
            if not(pair[:4] in self.balance):
                self.balance[pair[:4]] = 1
            if not(pair[4:] in self.balance):
                self.balance[pair[4:]] = 1

