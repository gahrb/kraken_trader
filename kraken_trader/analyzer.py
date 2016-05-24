import numpy as np
import datetime as dt

class analyzer:

    def __init__(self,trader,account):
        self.trader = trader
        self.account = account
        self.iter_count = 0

    def simulate(self):
        """
        Simulates a trader's performance. creates new the variables eq_bal as equivalent balance
        (i.e. all values are transfered into Bitcoins (XBT) in order to compare them easily -
            be careful, this depends heavily on the exchange rates!!!)
        """

        # only query the sel. balance and populate the self.account.eq_bal, if not yet done.
        if len(self.account.balance)==0:
            self.account.get_balance()
            self.account.eq_bal = self.account.balance["XXBT"]
            for bal in self.account.balance:
                if bal!="XXBT":
                    try:
                        self.account.eq_bal = self.account.eq_bal + self.account.balance[bal]*self.trader.price[bal+"XXBT"][0][2]
                    except KeyError:
                        self.account.eq_bal = self.account.eq_bal + self.account.balance[bal]/self.trader.price["XXBT"+bal][0][2]
            print "Starting balance: "+ str(self.account.balance)
            print "Equivalent in XBT: " + str(self.account.eq_bal)

        self.trader.predict_change()
        balance = self.account.balance.copy()
        pair = self.trader.pred.iterkeys().next()
        now = dt.datetime.now()
        i=0
        for key in self.trader.pred[pair]:
            i=i+1
            #if key[0]< now-dt.timedelta(days=31): # restrict simulation to the last month -- speed reasons
                #continue
            #Sell action
            sell = self.trader.get_sell_advice(key[0])
            sellFX = sell[0][:4]
            buyFX = sell[0][4:]
            #Check if we buy/sell a new currency: (sell can happen, when the advice is: buy nothing)
            if not(balance.has_key(sellFX)):
                balance.update({sellFX:0.0})
            if not(balance.has_key(buyFX)):
                balance.update({buyFX:0.0})
            amountSell = min(balance[sellFX]*sell[1],balance[sellFX]) #Ensure, we're not selling more than we have

            elem = get_closest_elem(self.trader.price[sell[0]],key[0])
            # TODO: add transaction fees dependent on numbers of transaction (change 2nd last index)
            amountBuy = amountSell*self.trader.price[sell[0]][elem][2]*(1-self.account.asset_pair[sell[0]]['fees'][0][1]/100)
            balance[sellFX] = max(balance[sellFX] - amountSell,0)
            balance[buyFX] = balance[buyFX] + amountBuy

            # buy action
            buy = self.trader.get_buy_advice(key[0])
            buyFX = buy[0][:4]
            sellFX= buy[0][4:]
            #Check if we buy a new currency:
            if not(balance.has_key(sellFX)):
                balance.update({sellFX:0.0})
            if not(balance.has_key(buyFX)):
                balance.update({buyFX:0.0})
            amountSell = min(balance[sellFX]*buy[1],balance[sellFX]) #Ensure, we're not buying more than we can afford

            elem = get_closest_elem(self.trader.price[buy[0]],key[0])
            # TODO: add transaction fees dependent on numbers of transaction (change 2nd last index)
            amountBuy = amountSell/self.trader.price[buy[0]][elem][1]*(1-self.account.asset_pair[buy[0]]['fees'][0][1]/100)
            balance[sellFX] = max(balance[sellFX] - amountSell,0)
            balance[buyFX] = balance[buyFX] + amountBuy


            eq_bal = balance["XXBT"]
            for bal in balance:
                if bal!="XXBT":
                    pair = bal+"XXBT"
                    try:
                        try:
                            tmp =  balance[bal]*self.trader.price[pair][elem][2]
                        except KeyError:
                            pair = "XXBT"+bal
                            tmp =  balance[bal]/self.trader.price[pair][elem][2]
                    except IndexError:
                        elem = get_closest_elem(self.trader.price[pair],key[0])
                        if pair[0:4]=="XXBT":
                            tmp = balance[bal]/self.trader.price[pair][elem][2]
                        else:
                            tmp = balance[bal]/self.trader.price[pair][elem][2]
                    eq_bal = eq_bal + tmp
            # print "Balance: "+str(i)+", "+ str(balance)
            # print "Equivalent in XBT: "+str(i)+", " + str(eq_bal)
        return eq_bal


    def gradient(self,vec = np.empty([0])):
        """
        calculates the gradient of the trader with it's constants: alpha, beta, ...
        afterwards steepest descend/ascend can be applied
        """
        eps = pow(10,-4)
        if vec.size==0:
            for i in range(0,len(self.trader.constant)):
                vec = np.hstack((vec,self.trader.constant[constant_enum(i)]))
        f_x = self.simulate()
        #vec_eps = vec.copy()
        g = np.empty([len(self.trader.constant),1])
        for i in range(0,len(self.trader.constant)):
            #vec_eps[i] = vec[i] + eps
            #self.trader.constant[constant_enum(i)] = vec_eps[i]
            self.trader.constant[constant_enum(i)] = vec[i] + eps
            f_x_eps = self.simulate()
            g[i] = (f_x_eps - f_x)/eps
            #vec_eps[i] = vec[i]

        print "Starting adaptive stepsize algorithm"
        if np.linalg.norm(g)>0.5:
            g = g/np.linalg.norm(g)/1000  #reduce size of g

        if (self.stepsize(g,f_x,1.1) == g).all(): # i.e. no changes, as the gradient would lead to not allowed constant values
            print "Optimal Constants Found after "+str(self.iter_count)+" Iterations: "+str(self.trader.constant)
            self.trader.write_new_trader()
            return

        if self.iter_count < 100:
            self.iter_count = self.iter_count +1
            if np.linalg.norm(g) < eps: #avoid too small gradiants
                print "Stopping Optimization because of too small gradient"
                self.trader.write_new_trader()
            else:
                self.gradient()
        else:
            print "Optimal Constants After 99 Iterations: "+str(self.trader.constant)



    def stepsize(self,g,f_x,size):

        for i in range(0,len(g)):
            if self.trader.constant[constant_enum(i)] + float(g[i])>0 and self.trader.constant[constant_enum(i)] + float(g[i])<1:
                self.trader.constant[constant_enum(i)] = self.trader.constant[constant_enum(i)] + float(g[i])
            else:
                return g

        f_x_g = self.simulate()
        if f_x_g > f_x:
            print "Next adaptive stepsize: "+str(g*size).replace("\n","")
            print "Last optimal Equivalent Balance: "+str(f_x_g)
            g = self.stepsize(g*size,f_x_g,size)
        else:
            g = g/size #resetting g to the last optimizing state
            for i in range(0,len(g)):
                self.trader.constant[constant_enum(i)] = self.trader.constant[constant_enum(i)] - float(g[i])*size
        return g


def get_closest_elem(list,time):
    return np.argmin(np.abs(np.matrix(list)[:,0]-time))

def constant_enum(i):
    return {
        0:"alpha",
        1:"beta",
        2:"gamma",
        3:"delta",
        4:"eps",
        5:"zeta",
        6:"eta",
        7:"theta",
        8:"omega"
    }.get(i, "unknown")