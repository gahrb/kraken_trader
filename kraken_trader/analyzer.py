import numpy as np

class analyzer:

    def __init__(self,trader,account):
        self.trader = trader
        self.account = account

    def simulate(self):

        self.account.get_balance()
        balance = self.account.balance
        eq_bal = balance["ZEUR"]
        for bal in balance:
            if bal!="ZEUR":
                eq_bal = eq_bal + balance[bal]*self.trader.price[bal+"ZEUR"][0][2]
        print "Starting balance: "+ str(balance)
        print "Equivalent in EUR: " + str(eq_bal)
        pair = self.trader.pred.iterkeys().next()
        for key in self.trader.pred[pair]:
            sell = self.trader.get_sell_advice(key[0])
            sellFX = sell[0][:4]
            buyFX = sell[0][4:]
            #Check if we buy a new currency:
            if not(balance.has_key(sellFX)):
                balance.update({sellFX:0.0})
            amountSell = min(balance.get(sellFX)*sell[1],balance[sellFX]) #Ensure, we're not selling more than we have
            elem = np.argmin(np.abs(np.matrix(self.trader.price[sell[0]])[:,0]-key[0]))
            # TODO: add transaction fees
            amountBuy = amountSell*self.trader.price[sell[0]][elem][2]
            # TODO: update balance
            balance[sellFX] = balance[sellFX] - amountSell
            balance[buyFX] = balance[buyFX] + amountBuy
            # TODO: buy action
            buy = self.trader.get_buy_advice(key[0])
            sellFX = buy[0][:4]
            buyFX= buy[0][4:]
            #Check if we buy a new currency:
            if not(balance.has_key(buyFX)):
                balance.update({buyFX:0.0})
            amountSell = min(balance.get(sellFX)*buy[1],balance[sellFX]) #Ensure, we're not buying more than we can afford
            elem = np.argmin(np.abs(np.matrix(self.trader.price[buy[0]])[:,0]-key[0]))
            # TODO: add transaction fees
            buyAmount = amountSell/self.trader.price[buy[0]][elem][1]
            # TODO: update balance
            balance[sellFX] = balance[sellFX] - amountSell
            balance[buyFX] = balance[buyFX] + buyAmount


            eq_bal = balance["ZEUR"]
            for bal in balance:
                if bal!="ZEUR":
                    pair = bal+"ZEUR"
                    try:
                        tmp =  balance[bal]*self.trader.price[pair][elem][2]
                    except KeyError:
                        tmp =  balance[bal]*self.trader.price["XXBT"+bal][elem][2]
                        tmp = tmp*self.trader.price["XXBTZEUR"][elem][2]
                    eq_bal = eq_bal + tmp
            print "Starting balance: "+ str(balance)
            print "Equivalent in EUR: " + str(eq_bal)
        return eq_bal


    def gradient(self):
        """
        calculates the gradient of the trader with it's constants: alpha, beta, ...
        afterwards steepest descend/ascend can be applied
        """
        vec = []
        for i=0 in range(0,10):
            vec[i] = self.trader.enum(i)



