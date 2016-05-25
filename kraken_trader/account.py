class kraken_account:

    def __init__(self,conn,k):
        self.conn = conn
        self.k = k
        self.balance = dict()
        self.trade_balance = dict()
        self.simulate = True
        self.get_balance()

    def get_balance(self):

        all_balances = self.k.query_private('Balance')['result']
        for balance in all_balances:
            self.balance[str(balance)] = float(all_balances[balance])

        trade_balance = self.k.query_private('TradeBalance',{'Currency':'ZEUR'})['result']
        for balance in trade_balance:
            self.trade_balance[str(balance)] = float(trade_balance[balance])

    def get_assets(self):
        self.asset_pair = self.k.query_public('AssetPairs')['result']

    def get_orders(self):
        #TODO: get all open orders from account


    def place_orders(self,k):
        if not self.simulate:
            # TODO: implement the trading request
            res = k.query_private('AddOrder', {'pair': 'XXBTZEUR',
                                         'type': 'buy',
                                         'ordertype': 'limit',
                                         'price': '1',
                                         'volume': '1',
                                         'close[pair]': 'XXBTZEUR',
                                         'close[type]': 'sell',
                                         'close[ordertype]': 'limit',
                                         'close[price]': '9001',
                                         'close[volume]': '1'})
            print res
