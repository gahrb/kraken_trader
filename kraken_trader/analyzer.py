class analyzer:

    def __init__(self,trader,account):
        self.trader = trader
        self.account = account

    def simulate(self):

        self.account.get_balance()
        balance = self.account.balance
        for pair in self.trader.pred:
            for i in self.trader.pred[pair]:
                buy = self.trader.get_sell_advice(i[0])

