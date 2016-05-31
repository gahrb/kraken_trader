import numpy as np
import datetime as dt

class analyzer:

    def __init__(self,trader,account):
        self.trader = trader
        self.account = account
        self.iter_count = 0
        self.optimize = False
        self.reference_curr = "ZEUR"

    def simulate(self,n=-1):
        """
        Simulates a trader's performance. creates new the variables eq_bal as equivalent balance
        (i.e. all values are transfered into Bitcoins (XBT) in order to compare them easily -
            be careful, this depends heavily on the exchange rates!!!)
        """

        balance = self.account.balance
        if not self.optimize:
            s_balance = balance.copy()
        pair = self.trader.price.iterkeys().next()
        i=0
        if n==-1:
            n = len(self.trader.price[pair])

        start_time = self.trader.price[pair][len(self.trader.price[pair])-n][0]
        end_time = dt.datetime.now()
        start_bal = self.get_eq_bal(balance,start_time)
        end_bal = self.get_eq_bal(balance,end_time)

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

            eq_bal = self.get_eq_bal(balance,key[0])


            if not self.optimize:
                if sold or bought:
                    print "-----\nPerformed trade ($): sell: "+str(sold)+" buy: "+str(bought)
                s_eq_bal = self.get_eq_bal(s_balance,key[0])
                print str(key[0])+" "+str(i)+", Equivalent in "+self.reference_curr+": " + str(round(eq_bal,2))+", Compared to market: " + str(round((eq_bal-s_eq_bal)/s_eq_bal*100,2))+"%"

        print "Start balance: "+str(start_bal)
        print "Market adjusted end balance: "+str(end_bal)
        print "Return: "+str(eq_bal/start_bal*100-100)+"%"
        print "-----------------------\nSingle Positions:"
        for bal in balance:
            print str(bal) + ": "+str(balance[bal])
        return eq_bal


    def get_eq_bal(self,balance,time,toXBT=False):
        """
        Calculate the equivalent balance in XBTs
        """
        if toXBT:
            reference_curr = "XXBT"
        else:
            reference_curr = self.reference_curr
        eq_bal = balance[reference_curr]
        for bal in balance:
            if bal!=reference_curr and not bal in self.trader.constant["donottrade"]:
                pair = bal+reference_curr
                buy = True
                if not(pair in self.account.asset_pair):
                    pair = reference_curr+bal
                    buy = False
                try:
                    elem = get_closest_elem(self.trader.price[pair],time)
                except KeyError: #not able to translate the currency directly to the reference currency...
                    elem = get_closest_elem(self.trader.price["XXBT"+bal],time)
                    eq_xbt = balance[bal]/self.trader.price["XXBT"+bal][elem][1]
                    elem = get_closest_elem(self.trader.price["XXBT"+reference_curr],time)
                    eq_bal += eq_xbt*self.trader.price["XXBT"+reference_curr][elem][2]
                    continue
                if buy:
                    eq_bal +=  balance[bal]*self.trader.price[pair][elem][1]
                else:
                    eq_bal +=  balance[bal]/self.trader.price[pair][elem][2]
        return eq_bal

    def gradient(self,vec = np.empty([0])):
        """
        calculates the gradient of the trader with it's constants: alpha, beta, ...
        afterwards steepest descend/ascend can be applied
        """
        sim_length = -1
        eps = pow(10,-5)
        if vec.size==0:
            for i in self.trader.constant["float"]:
                vec = np.hstack((vec,self.trader.constant[i]))
        print "Current constants: "+str(vec)
        self.account.populate_balance() #set balance back to all = 1
        self.trader.run_trader()
        f_x = self.simulate(sim_length)
        print "-----------------\nEquivalent optimized balance: "+str(f_x)+"\n-----------------"
        g = np.empty([len(self.trader.constant["float"]),1])
        for i in range(len(g)):
            for j in range(len(g)):
                if j==i:
                    self.trader.constant[self.trader.constant["float"][i]] = vec[i] + eps
                else:
                    self.trader.constant[self.trader.constant["float"][i]] = vec[i]
            self.account.populate_balance() #set balance back to all = 1
            self.trader.run_trader()
            f_x_eps = self.simulate(sim_length)
            g[i] = (f_x_eps - f_x)/eps
        print "Current gradient: "+str(g)

        print "Starting adaptive stepsize algorithm"
        if np.linalg.norm(g)>0.5:
            g = g/np.linalg.norm(g)/1000  #reduce size of g

        if (self.stepsize(g,f_x,1.1,sim_length) == g).all(): # i.e. no changes, as the gradient would lead to not allowed constant values
            print "Optimal Constants Found after "+str(self.iter_count)+" Iterations: "+str(self.trader.constant)
            self.trader.write_new_trader()
            return

        if self.iter_count < 100:
            self.iter_count = self.iter_count +1
            print str(self.iter_count)+" Iterations: "+str(self.trader.constant)
            #self.trader.write_new_trader()
            if np.linalg.norm(g) < eps: #avoid too small gradiants
                print "Stopping Optimization because of too small gradient"
            else:
                self.gradient()
        else:
            print "Optimal Constants After 99 Iterations: "+str(self.trader.constant)



    def stepsize(self,g,f_x,size,sim_length=-1):

        for i in range(len(g)):
            if self.trader.constant[self.trader.constant["float"][i]] + float(g[i])>0:# and self.trader.constant[constant_enum(i)] + float(g[i])<1:
                self.trader.constant[self.trader.constant["float"][i]] = self.trader.constant[self.trader.constant["float"][i]] + float(g[i])
            else:
                return g

        self.account.populate_balance() #set balance back to all = 1
        self.trader.run_trader()
        f_x_g = self.simulate(sim_length)
        if f_x_g > f_x:
            print "Next adaptive stepsize: "+str(g*size).replace("\n","")
            print "Last optimal Equivalent Balance: "+str(f_x_g)
            g = self.stepsize(g*size,f_x_g,size,sim_length)
        else:
            g = g/size #resetting g to the last optimizing state
            for i in range(0,len(g)):
                self.trader.constant[self.trader.constant["float"][i]] = self.trader.constant[self.trader.constant["float"][i]]- float(g[i])*size
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