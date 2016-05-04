class kraken_account:

    def __init__(self,conn,k):
        self.conn = conn
        self.k = k
        self.balance = dict()
        self.trade_balance = dict()

    def get_balance(self):

        all_balances = self.k.query_private('Balance')['result']
        for balance in all_balances:
            self.balance[str(balance)] = float(all_balances[balance])

        trade_balance = self.k.query_private('TradeBalance',{'Currency':'ZEUR'})['result']
        for balance in trade_balance:
            self.trade_balance[str(balance)] = float(trade_balance[balance])

        self.asset_pair = self.k.query_public('AssetPairs')['result']

