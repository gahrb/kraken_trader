import numpy as np
import json
import datetime as dt

filename = "traders.json"

class standard_trader():

    def __init__(self,conn,k):
        self.conn = conn
        self.k = k

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = get_tader_name(self)
        filename = "traders.json"
        json_data=open("./kraken_trader/"+filename).read()
        data = json.loads(json_data)
        self.constant = data[trader_name]

    def get_buy_advice(self):

        return (0,1)

    def get_sell_advice(self):

        return (0,1)

class basic_trader():
    """
    Returns the most increasing FX to buy and the most decreasing to sell
    """

    def __init__(self,conn,k,pairs):
        self.conn = conn
        self.k = k
        self.pairs = pairs
        self.pred = dict()
        self.diff = dict()
        self.price = dict()
        self.simulate = True

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = get_tader_name(self)
        self.constant = get_trader_config()[trader_name]

        #Calculate the predicted change
        self.predict_change()

    def write_new_trader(self):

        save_trader_config(self.constant,get_tader_name(self))

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
            cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair)
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

    def __init__(self,conn,k,pairs):
        self.conn = conn
        self.k = k
        self.pairs = pairs
        #self.pred = dict()
        self.diff = dict()
        self.price = dict()

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = get_tader_name(self)
        self.constant = get_trader_config()[trader_name]

        #Calculate the predicted change
        self.run_trader()



    def write_new_trader(self):
        save_trader_config(self.constant,get_tader_name(self))

    def get_buy_advice(self,time):

        allow_trade = dict()
        for pair in self.pairs:
            elem = get_closest_elem(self.ma[pair]["ask"],time)
            if elem > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["ask"][elem][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            performTrades = dict()
            for (k,v) in allow_trade.items():
                elem = get_closest_elem(self.price[k],time)
                change = (v-self.price[k][elem][1])/v
                if v!=-1 and change >= self.constant["gamma"]:
                    performTrades[k] = change *self.constant["beta"]
            # This is ugly... iknow...
            # allow_trade = dict((k,(v-self.price[k][get_closest_elem(self.price[k],time)][1])/v * self.constant["beta"]) \
            #     for k, v in allow_trade.items() \
            #     if v!=-1 and (v-self.price[k][get_closest_elem(self.price[k],time)][1])/v >= self.constant["gamma"]) # the price must be over gamma-% of the average

            if (performTrades):
                return performTrades
        return False

    def get_sell_advice(self,time):

        allow_trade = dict()
        for pair in self.pairs:
            elem = get_closest_elem(self.ma[pair]["bid"],time)
            if elem > self.constant["alpha"]:
                allow_trade[pair]=self.ma[pair]["bid"][elem][1]
            else:
                allow_trade[pair]=-1

        if not all(val==-1 for val in allow_trade.values()):
            # This is ugly... iknow...
            performTrades = dict()
            for (k,v) in allow_trade.items():
                elem = get_closest_elem(self.price[k],time)
                change = (self.price[k][elem][2]-v)/v
                if v!=-1 and change >= self.constant["gamma"]:
                    performTrades[k] = change *self.constant["beta"]

            # This is ugly... iknow...
            # allow_trade = dict((k,(self.price[k][get_closest_elem(self.price[k],time)][2]-v)/v * self.constant["beta"]) \
            #         for k, v in allow_trade.items() \
            #         if v!=-1 and (self.price[k][get_closest_elem(self.price[k],time)][2]-v)/v >= self.constant["gamma"]) # the price must be over gamma-% of the average

            if (performTrades):
                return performTrades
        return False

    def run_trader(self):
        self.ma = dict()
        for pair in self.pairs:
            cur = self.conn.cursor()
            cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair)
            res = cur.fetchall()
            cur.close()
            self.price[pair] = []
            self.price[pair].append(np.array(res[0]))

            self.ma[pair] = dict()
            self.ma[pair]["ask"] = []
            self.ma[pair]["bid"] = []
            self.ma[pair]["ask"].append([res[0][0],res[0][1]])
            self.ma[pair]["bid"].append([res[0][0],res[0][2]])
            for i in range(1,len(res)):
                lookback = min(int(self.constant["alpha"]),i)
                self.ma[pair]["ask"].append([res[i][0],np.mean(np.array(res[i-lookback:i])[:,1])])
                self.ma[pair]["bid"].append([res[i][0],np.mean(np.array(res[i-lookback:i])[:,2])])
                self.price[pair].append(np.array(res[i]))


def get_trader_config():
    json_data=open("./kraken_trader/"+filename).read()
    return json.loads(json_data)

def save_trader_config(data,trader_name):
    json_data = get_trader_config()
    # TODO: replace the config of the current trader with the new constants
    json_data[trader_name] = data
    with open("./kraken_trader/"+filename,mode='w') as outfile:
        json.dump(json_data, outfile)


def get_tader_name(input_class):
    name_sidx = str(input_class).find("all_traders.")
    name_eidx = str(input_class).find(" instance")
    return str(input_class)[name_sidx+12:name_eidx]

def get_closest_elem(list,time):
    return np.argmin(np.abs(np.matrix(list)[:,0]-time))