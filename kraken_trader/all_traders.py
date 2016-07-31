import helper_functions as hf
import numpy as np
import datetime as dt

filename = "traders.json"

class basic_trader():
    """
    Returns the most increasing FX to buy and the most decreasing to sell
    """

    def __init__(self,conn,k,account):
        self.conn = conn
        self.k = k
        self.pairs = account.asset_pair.keys()
        self.pred = dict()
        self.diff = dict()
        self.price = dict()
        self.simulate = True

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = hf.get_tader_name(self)
        self.constant = hf.get_trader_config()[trader_name]

        #Calculate the predicted change
        self.predict_change()

    def write_new_trader(self):

        hf.save_trader_config(self.constant,hf.get_tader_name(self))

    def get_buy_advice(self,time):

        ask_list_pred = dict()
        for key in self.pred:
            # TODO: check if time is not larger
            elem = np.argmin(np.abs(np.matrix(self.pred.get(key))[:,0]-time))
            if elem < 100: #avoid prediciton on untrained data
                continue
            ask_list_pred.update({key:self.pred.get(key)[elem][1]})
        if len(ask_list_pred)==0:
            return (key,0)
        return (max(ask_list_pred,key=ask_list_pred.get),max(min(self.constant["beta"],1),0))

    def get_sell_advice(self,time):

        bid_list_pred = dict()
        for key in self.pred:
            # TODO: check if time is not larger
            elem = np.argmin(np.abs(np.matrix(self.pred.get(key))[:,0]-time))
            if elem < 100: #avoid prediciton on untrained data
                continue
            bid_list_pred.update({key:self.pred.get(key)[elem][2]})
        if len(bid_list_pred)==0:
            return (key,0)
        return (min(bid_list_pred, key=bid_list_pred.get),max(min(self.constant["beta"],1),0))

    def run_trader(self):

        for pair in self.pairs:
            cur = self.conn.cursor()
            cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair +" order by modtime asc;")
            res = cur.fetchall()
            cur.close()

            #TODO: put here the filter, strategy or whatever
            self.pred[pair] = []
            self.price[pair] = []
            self.pred[pair].append(np.array(res[0]))
            self.price[pair].append(np.array(res[0]))
            for i in range(1,len(res)):
                alpha = max(min(self.constant["alpha"],1),0)
                pred_val = np.add(alpha*np.array(res[i][1:]), (1-alpha)*np.array(res[i-1][1:]))
                abs_change = np.subtract(pred_val,res[i][1:])
                #TODO: check if correct this way...
                self.pred[pair].append(np.insert(res[i][0],1,np.divide(abs_change,res[i][1:])))
                #Important for the later analysis, so that we have the actual price
                self.price[pair].append(np.array(res[i]))

class ma_trader():
    """
    Returns sell/buy advices on the moving average, if a currency is under rated or overrated
    """

    def __init__(self,conn,k,account):
        self.conn = conn
        self.k = k
        self.account = account
        self.pairs = account.asset_pair.keys()
        #self.pred = dict()
        self.diff = dict()
        self.price = dict()

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = hf.get_tader_name(self)
        self.constant = hf.get_trader_config()[trader_name]

        self.keep = min(0.01,self.constant["delta"])

        #Calculate the predicted change
        self.run_trader()
        self.keep_back(dt.datetime.strptime("2016-01-01","%Y-%m-%d"))



    def write_new_trader(self):
        hf.save_trader_config(self.constant,hf.get_tader_name(self))

    def get_buy_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["ask"],time)
            if elem[pair] > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["ask"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            performTrades = dict()
            for (pair,v) in allow_trade.items():
                change = (v-self.price[pair][elem[pair]][1])/v
                if v!=-1 and change >= self.constant["gamma"] and \
                        not pair[:4] in self.constant["donottrade"] and \
                        not pair[4:] in self.constant["donottrade"] and \
                        self.account.balance[pair[4:]]-self.keep[pair[4:]] > 0:
                    performTrades[pair] = min(self.account.balance[pair[4:]] - self.keep[pair[4:]] , \
                            change *self.constant["beta"]*self.account.balance[pair[4:]] * self.price[pair][elem[pair]][2]) / \
                            self.price[pair][elem[pair]][1]

            if (performTrades):
                self.keep_back(time)
                return performTrades
        return []

    def get_sell_advice(self,time):

        allow_trade = dict()
        elem = dict()
        for pair in self.pairs:
            elem[pair] = hf.get_closest_elem(self.ma[pair]["bid"],time)
            if elem[pair] > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["bid"][elem[pair]][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            performTrades = dict()
            for (pair,v) in allow_trade.items():
                change = (self.price[pair][elem[pair]][2]-v)/v
                if v!=-1 and change >= self.constant["gamma"] and\
                        not pair[:4] in self.constant["donottrade"] and\
                        not pair[4:] in self.constant["donottrade"] and\
                        self.account.balance[pair[:4]]-self.keep[pair[:4]] > 0: #Ensures, that there is enough amount on this currency to trade
                    #Check if transaction does not exceed the self.keep amount
                    performTrades[pair] = min(self.account.balance[pair[:4]]-self.keep[pair[:4]],\
                                            change*self.constant["beta"]*self.account.balance[pair[:4]])

            if (performTrades):
                self.keep_back(time)
                return performTrades
        return []

    def keep_back(self,time):
        reference_curr = "XXBT"
        balance = self.account.balance
        eq_bal = balance[reference_curr]
        elem = dict()
        for bal in balance:
            if bal!=reference_curr and not bal in self.constant["donottrade"]:
                pair = bal+reference_curr
                if self.price.has_key(pair):
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]*self.price[pair][elem[pair]][1]
                else: #not able to translate the currency directly to the reference currency...
                    pair = "XXBT"+bal
                    elem[pair] = hf.get_closest_elem(self.price[pair],time)
                    eq_bal +=  balance[bal]/self.price[pair][elem[pair]][2]

        self.keep = dict()
        self.keep["XXBT"] = eq_bal*self.constant["delta"]
        for pair in elem:
            if pair.find("XXBT")==0:
                self.keep[pair[4:]] = self.constant["delta"] * eq_bal * self.price[pair][elem[pair]][1]
            else:
                self.keep[pair[:4]] = self.constant["delta"] * eq_bal / self.price[pair][elem[pair]][2]


    def run_trader(self):
        self.ma = dict()
        for pair in self.pairs:
            if not self.price.has_key(pair): #no new results shall be queried, when in the optimization loop!
                cur = self.conn.cursor()
                cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair +" order by modtime asc;")
                res = cur.fetchall()
                cur.close()
                self.price[pair] = res

            self.ma[pair] = dict()
            self.ma[pair]["ask"] = []
            self.ma[pair]["bid"] = []
            self.ma[pair]["ask"].append([self.price[pair][0][0],self.price[pair][0][1]])
            self.ma[pair]["bid"].append([self.price[pair][0][0],self.price[pair][0][2]])
            for i in range(1,len(self.price[pair])):
                lookback = min(int(self.constant["alpha"]),i)
                self.ma[pair]["ask"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,1])])
                self.ma[pair]["bid"].append([self.price[pair][i][0],np.mean(np.array(self.price[pair][i-lookback:i])[:,2])])

