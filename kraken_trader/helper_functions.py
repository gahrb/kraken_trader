import numpy as np
import json


filename = "traders.json"


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

