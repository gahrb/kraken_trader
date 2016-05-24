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

    def predict_change(self):

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
        self.pred = dict()
        self.diff = dict()
        self.price = dict()

        # Get Configuration Values for Trader from JSON File
        # This is required in case, we want ot optimize the algorithms later on.
        trader_name = get_tader_name(self)
        self.constant = get_trader_config()[trader_name]

        #Calculate the predicted change
        self.calc_ma()



def write_new_trader(self):

    save_trader_config(self.constant,get_tader_name(self))

    def get_buy_advice(self,time):

        return (self.pred.get(0),0)

    def get_sell_advice(self,time):

        return (self.pred.get(0),0)

    def calc_ma(self):
        return 0




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
