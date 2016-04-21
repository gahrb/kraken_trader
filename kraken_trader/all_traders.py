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

        #Calculate the predicted change
        self.predict_price(0.595)

    def get_buy_advice(self):

        #return max(self.pred, key=self.pred[:][1].get)
        return self.pred

    def get_sell_advice(self):

        return self.pred

    def predict_price(self,alpha):

        self.pair_prediction = []
        for pair in self.pairs:
            cur = self.conn.cursor()
            cur.execute("SELECT modtime, ask_price, bid_price FROM "+ pair)
            res = cur.fetchall()
            cur.close()

            #TODO: put here the filter or whatever
            sval = res[0][1:]
            diff = []
            for i in range(1,len(res)):
                diff.append(np.subtract(res[i][1:],sval))
                sval_tmp1 = alpha*res[i][1]+(1-alpha)*sval[0]
                sval_tmp2 = alpha*res[i][2]+(1-alpha)*sval[1]
                sval = (sval_tmp1,sval_tmp2)

            abs_change = np.subtract(sval,res[-1][1:])
            #print "Abs_change: "+str(abs_change)
            rel_change = np.divide(abs_change,res[-1][1:])
            print "Rel_change: "+str(rel_change)
            self.pred.update({pair:rel_change})

