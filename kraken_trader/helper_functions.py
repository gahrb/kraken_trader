import json
import sys

filename = "traders.json"
sys.setrecursionlimit(9999)


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

def get_closest_elem(price,time,elem = 0):
    if elem+1 < len(price) and time > price[elem][0] and (time - price[elem+1][0] < time - price[elem][0]):
        return get_closest_elem(price,time,elem+1)
    return elem

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
        if bal!=reference_curr:
            pair = bal+reference_curr
            tmp_bal = balance[bal]
            buy = False
            if not(pair in self.account.asset_pair):
                if (reference_curr+bal in self.account.asset_pair):
                    pair = reference_curr+bal
                    buy = True
                else:
                    #Change it first to xxbt, then to reference curr
                    tmp_bal = xbal(self.trader.price["XXBT"+reference_curr],tmp_bal,time,True)
                    pair = bal+"XXBT"
            eq_bal += xbal(self.trader.price[pair],tmp_bal,time,buy)
    return eq_bal

def xbal(price,bal,time,action):
    # exchanges cur1 with cur2 at specific time
    elem = get_closest_elem(price,time)
    if action:
        return bal/price[elem][1]
    return bal*price[elem][2]

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

