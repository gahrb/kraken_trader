import numpy as np


class standard_trader():

    def __init__(self,conn,k):
        self.conn = conn
        self.k = k

    def get_buy_advice(self):

        return 0

    def get_sell_advice(self):

        return 0

class advanced_trader():

    def __init__(self,conn,k,pairs):
        self.conn = conn
        self.k = k
        self.pairs = pairs
        self.pred = dict()
        self.diff = dict()

        #Calculate the predicted change
        self.predict_price(0.895)

    def get_buy_advice(self):

        #return max(self.pred, key=self.pred[:][1].get)
        return self.diff

    def get_sell_advice(self):

        return self.pred

    def predict_price(self,alpha):

        self.pair_prediction = []
        for pair in self.pairs:
            cur = self.conn.cursor()
            cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair)
            res = cur.fetchall()
            cur.close()

            #TODO: put here the filter, strategy or whatever
            self.pred[pair] = []
            self.diff[pair] = []
            self.pred[pair].append(np.array(res[0][1:]))
            self.diff[pair].append(np.array(res[0][1:]))
            for i in range(1,len(res)):
                self.diff[pair].append(np.array(res[i][1:]))
                self.pred[pair].append(np.add(alpha*np.array(res[i][1:]),(1-alpha)*np.array(self.pred[pair][-1])))

            abs_change = np.subtract(self.pred[pair][-1],res[-1][1:])
            #print "Abs_change: "+str(abs_change)
            self.rel_change = np.divide(abs_change,res[-1][1:])
            print "Rel_change: "+str(self.rel_change)

