class kraken_account:

    def __init__(self,conn,k):
        self.conn = conn
        self.k = k

    def get_balance(self):

        self.balance = self.k.query_private('Balance')['result']
        self.trade_balance = self.k.query_private('TradeBalance',{'Currency':'ZEUR'})['result']
