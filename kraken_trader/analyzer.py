import numpy as np
import datetime as dt

class analyzer:

    def __init__(self,trader,account):
        self.trader = trader
        self.account = account
        self.iter_count = 0

    def simulate(self,n=-1):
        """
        Simulates a trader's performance. creates new the variables eq_bal as equivalent balance
        (i.e. all values are transfered into Bitcoins (XBT) in order to compare them easily -
            be careful, this depends heavily on the exchange rates!!!)
        """

        # only query the sel. balance and populate the self.account.eq_bal, if not yet done.
#             self.account.get_balance()
#             self.account.eq_bal = self.account.balance["XXBT"]
#             for bal in self.account.balance:
#                 if bal!="XXBT":
#                     try:
#                         self.account.eq_bal = self.account.eq_bal + self.account.balance[bal]*self.trader.price[bal+"XXBT"][0][2]
#                     except KeyError:
#                         self.account.eq_bal = self.account.eq_bal + self.account.balance[bal]/self.trader.price["XXBT"+bal][0][2]
#             print "Starting balance: "+ str(self.account.balance)
#             print "Equivalent in XBT: " + str(self.account.eq_bal)

        self.trader.run_trader()
        balance = self.account.balance.copy()
        pair = self.trader.price.iterkeys().next()
        now = dt.datetime.now()
        i=0
        if n==-1:
            n = len(self.trader.price[pair])
        for key in self.trader.price[pair][len(self.trader.price[pair])-n:]:
            i=i+1
            #if key[0]< now-dt.timedelta(days=31): # restrict simulation to the last month -- speed reasons
                #continue
            #Sell action
            sell_advice = self.trader.get_sell_advice(key[0])
            sold = dict()
            # TODO: add reserved amount for trading, to avoid trading with money which is already in use.
            credit_item = dict((key,0) for key in balance)
            if not type(sell_advice) is bool:
                for sellPair in sorted(sell_advice, key=lambda key: sell_advice[key],reverse=True):
                    sellFX = sellPair[:4]
                    buyFX = sellPair[4:]
                    #Check if we buy/sell a new currency: (sell can happen, when the advice is: buy nothing)
                    if not(balance.has_key(sellFX)):
                        balance.update({sellFX:0.0})
                    if not(balance.has_key(buyFX)):
                        balance.update({buyFX:0.0})
                    amountSell = min(sell_advice[sellPair],1)*balance[sellFX] # Ensure, we're not selling more than we have or have spent on previous transactions

                    #Minimal amount required by kraken
                    elem = get_closest_elem(self.trader.price[sellPair],key[0])
                    # TODO: add transaction fees dependent on numbers of transaction (change 2nd last index)
                    amountBuy = amountSell*self.trader.price[sellPair][elem][2]*(1-self.account.asset_pair[sellPair]['fees'][0][1]/100)
                    if amountSell > 0.01 and amountBuy > 0.01:
                        balance[sellFX] -= amountSell
                        credit_item[buyFX] += amountBuy
                        sold[sellPair] = [amountSell, amountBuy]

            # buy action
            buy_advice = self.trader.get_buy_advice(key[0])
            bought = dict()
            if not type(buy_advice) is bool:
                for buyPair in sorted(buy_advice, key=lambda key: buy_advice[key],reverse=True):
                    buyFX = buyPair[:4]
                    sellFX= buyPair[4:]
                    #Check if we buy a new currency:
                    if not(balance.has_key(sellFX)):
                        balance.update({sellFX:0.0})
                    if not(balance.has_key(buyFX)):
                        balance.update({buyFX:0.0})
                    amountSell = min(1,buy_advice[buyPair])*balance[sellFX] #Ensure, we're not buying more than we can afford

                    elem = get_closest_elem(self.trader.price[buyPair],key[0])
                    #Minimal amount required by kraken
                    # TODO: add transaction fees dependent on numbers of transaction (change 2nd last index)
                    amountBuy = amountSell/self.trader.price[buyPair][elem][1]*(1-self.account.asset_pair[buyPair]['fees'][0][1]/100)
                    if amountSell > 0.01 and amountBuy > 0.01:
                        balance[sellFX] -= amountSell
                        credit_item[buyFX] += amountBuy
                        bought[buyPair] = [amountBuy, amountSell]

            # Write credit items to the account balance
            if credit_item:
                for curr in credit_item:
                    balance[curr] += credit_item[curr]


            eq_bal = balance["XXBT"]
            for bal in balance:
                if bal!="XXBT":
                    pair = bal+"XXBT"
                    try:
                        try:
                            elem = get_closest_elem(self.trader.price[pair],key[0])
                            tmp =  balance[bal]*self.trader.price[pair][elem][2]
                        except KeyError:
                            pair = "XXBT"+bal
                            elem = get_closest_elem(self.trader.price[pair],key[0])
                            tmp =  balance[bal]/self.trader.price[pair][elem][2]
                    except IndexError:
                        if pair[0:4]=="XXBT":
                            tmp = balance[bal]/self.trader.price[pair][elem][2]
                        else:
                            tmp = balance[bal]/self.trader.price[pair][elem][2]
                    eq_bal += tmp
            # print "Balance: "+str(i)+", "+ str(balance)
            # if not type(buy_advice) is bool or not type(sell_advice) is bool:
            #     # for bal in balance:
            #     #     print str(bal) + ": "+str(balance[bal])
            #     print "Trade advice (%): sell: "+str(sell_advice)+" buy: "+str(buy_advice)
            if sold or bought:
                print "Performed trade ($): sell: "+str(sold)+" buy: "+str(bought)
            print str(key[0])+" "+str(i)+", Equivalent in XBT: " + str(eq_bal)
        print "Final Balance"
        for bal in balance:
            print str(bal) + ": "+str(balance[bal])
        return eq_bal



    def gradient(self,vec = np.empty([0])):
        """
        calculates the gradient of the trader with it's constants: alpha, beta, ...
        afterwards steepest descend/ascend can be applied
        """
        sim_length = 1500
        eps = pow(10,-5)
        if vec.size==0:
            for i in range(0,len(self.trader.constant)):
                vec = np.hstack((vec,self.trader.constant[constant_enum(i)]))
        f_x = self.simulate(sim_length)
        print "-----------------\nStarting with eq_balance: "+str(f_x)+"\n-----------------"
        #vec_eps = vec.copy()
        g = np.empty([len(self.trader.constant),1])
        for i in range(0,len(self.trader.constant)):
            #vec_eps[i] = vec[i] + eps
            #self.trader.constant[constant_enum(i)] = vec_eps[i]
            self.trader.constant[constant_enum(i)] = vec[i] + eps
            f_x_eps = self.simulate(sim_length)
            g[i] = (f_x_eps - f_x)/eps
            #vec_eps[i] = vec[i]

        print "Starting adaptive stepsize algorithm"
        if np.linalg.norm(g)>0.5:
            g = g/np.linalg.norm(g)/1000  #reduce size of g

        if (self.stepsize(g,f_x,1.1,sim_length) == g).all(): # i.e. no changes, as the gradient would lead to not allowed constant values
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



    def stepsize(self,g,f_x,size,sim_length=-1):

        for i in range(0,len(g)):
            if self.trader.constant[constant_enum(i)] + float(g[i])>0:# and self.trader.constant[constant_enum(i)] + float(g[i])<1:
                self.trader.constant[constant_enum(i)] = self.trader.constant[constant_enum(i)] + float(g[i])
            else:
                return g

        f_x_g = self.simulate(sim_length)
        if f_x_g > f_x:
            print "Next adaptive stepsize: "+str(g*size).replace("\n","")
            print "Last optimal Equivalent Balance: "+str(f_x_g)
            g = self.stepsize(g*size,f_x_g,size,sim_length)
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