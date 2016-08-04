import helper_functions as hf
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

        pair = "XETHXXBT" #self.trader.price.iterkeys().next()
        i=0
        if n==-1:
            n = len(self.trader.price[pair])

        elem = dict()

        start_time = self.trader.price[pair][len(self.trader.price[pair])-n][0]
        end_time = dt.datetime.now()

        self.starting_balance(start_time)

        balance = self.account.balance # Important: this copys only the pointer. changing balance will change self.account.balance
        if not self.optimize:
            s_balance = self.account.balance.copy()

        start_bal,_ = hf.get_eq_bal(balance,self.trader.price,start_time,'ZEUR')
        end_bal,_ = hf.get_eq_bal(balance,self.trader.price,end_time,'ZEUR')

        for key in self.trader.price[pair][len(self.trader.price[pair])-n:]:
            i=i+1
            #Sell action
            advice = self.trader.get_sell_advice(key[0])
            sold = dict()
            credit_item = dict((key,0) for key in balance)
            if not type(advice) is bool:
                for sellPair in sorted(advice, key=lambda key: advice[key],reverse=True):
                    if not elem.has_key(sellPair):
                        elem[sellPair] = 0
                    sellFX = sellPair[:4]
                    buyFX = sellPair[4:]
                    elem[sellPair] = hf.get_closest_elem(self.trader.price[sellPair],key[0],elem[sellPair])
                    #Check if sufficient funds
                    # TODO: add transaction fees dependent on numbers of transaction (change 2nd last index)
                    amountBuy = advice[sellPair]*self.trader.price[sellPair][elem[sellPair]][2]*(1-self.account.asset_pair[sellPair]['fees'][0][1]/100)
                    if advice[sellPair] > min(self.trader.keep,0.01) :
                        balance[sellFX] -= advice[sellPair]
                        credit_item[buyFX] += amountBuy
                        sold[sellPair] = [advice[sellPair], amountBuy, self.trader.price[sellPair][elem[sellPair]][2]]

            # buy action
            advice = self.trader.get_buy_advice(key[0])
            bought = dict()
            if not type(advice) is bool:
                for buyPair in sorted(advice, key=lambda key: advice[key],reverse=True):
                    if not elem.has_key(buyPair):
                        elem[buyPair] = 0
                    buyFX = buyPair[:4]
                    sellFX= buyPair[4:]
                    elem[buyPair] = hf.get_closest_elem(self.trader.price[buyPair],key[0],elem[buyPair])
                    sellAmount = advice[buyPair]*self.trader.price[buyPair][elem[buyPair]][1]*(1-self.account.asset_pair[buyPair]['fees'][0][1]/100)
                    #Chek if enough money is left to buy
                    if advice[buyPair] > 0.01 :
                        balance[sellFX] -= sellAmount
                        credit_item[buyFX] += advice[buyPair]
                        bought[buyPair] = [sellAmount, advice[buyPair], self.trader.price[buyPair][elem[buyPair]][1]]

            # Write credit items to the account balance
            if credit_item:
                for curr in credit_item:
                    balance[curr] += credit_item[curr]

            eq_bal,rel_bal = hf.get_eq_bal(balance,self.trader.price,key[0],'ZEUR')


            if not self.optimize:
                if sold or bought:
                    print "-----\nPerformed trade ($): sell: "+str(sold)+" buy: "+str(bought)
                s_eq_bal,_ = hf.get_eq_bal(s_balance,self.trader.price,key[0],'ZEUR')
                for bal in rel_bal:
                    rel_bal[bal] = round(rel_bal[bal]*100,1)
                print str(key[0])+" "+str(i)+", Equivalent in "+self.reference_curr+": " + str(round(eq_bal,2))+\
                    ",\n\t Compared to market ("+str(round(s_eq_bal,2))+"): " + str(round((eq_bal/s_eq_bal-1)*100,2))+\
                    "%,\n\t Compared to start ("+str(round(start_bal,2))+"): " + str(round((eq_bal/start_bal-1)*100,2))+"%."+\
                    "\nRelative balances[%]: "+str(sorted(rel_bal.items(), key=lambda x: x[1], reverse=True))

        print "Start balance: "+str(start_bal)
        print "Market adjusted end balance: "+str(end_bal)
        print "Return: "+str(eq_bal/start_bal*100-100)+"%"
        print "-----------------------\nSingle Positions:"
        for bal in balance:
            print str(bal) + ": "+str(balance[bal])
        return eq_bal


    def gradient(self,vec = np.empty([0])):
        """
        calculates the gradient of the trader with it's constants: alpha, beta, ...
        afterwards steepest descend/ascend can be applied
        """
        sim_length = 5000
        eps = pow(10,-5)
        if vec.size==0:
            for i in self.trader.constant["float"]:
                vec = np.hstack((vec,self.trader.constant[i]))
        print "Current constants: "+str(vec)
        self.account.populate_balance() #set balance back to all = 1
        f_x = self.simulate(sim_length)
        print "-----------------\nEquivalent optimized balance: "+str(f_x)+"\n-----------------"
        g = np.empty([len(self.trader.constant["float"]),1])
        for i in range(len(g)):
            #set balance back to all = 1
            self.account.populate_balance()
            for j in range(len(g)):
                if j==i:
                    self.trader.constant[self.trader.constant["float"][i]] = vec[i] + eps
                else:
                    self.trader.constant[self.trader.constant["float"][i]] = vec[i]
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
            self.iter_count = self.iter_count+1
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
            if self.trader.constant[self.trader.constant["float"][i]] + float(g[i])>0:
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

    def starting_balance(self,time):
        ref = "XXBT"
        start_factor = 0.1
        for bal in self.account.balance:
            if not bal == ref:
                pair = bal+ref
                if pair in self.trader.price:
                    elem = hf.get_closest_elem(self.trader.price[pair],time)
                    self.account.balance[bal] = start_factor/self.trader.price[pair][elem][1]
                else:
                    pair = ref+bal
                    elem = hf.get_closest_elem(self.trader.price[pair],time)
                    self.account.balance[bal] = start_factor*self.trader.price[pair][elem][2]
            else:
                self.account.balance[bal] = 1*start_factor


