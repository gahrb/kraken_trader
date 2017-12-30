import json
import sys

filename = "traders.json"
sys.setrecursionlimit(9999)


class HelperFunctions:

    def __init__(self, asset_pairs, dbq):
        self.dbq = dbq
        self.asset_pairs = asset_pairs

    def get_closest_elem(self, price, time, elem = 0):
        if elem+1 < len(price) and time > price[elem][0] and (time - price[elem+1][0] < time - price[elem][0]):
            return self.get_closest_elem(price,time,elem+1)
        return elem

    def get_eq_bal(self, amount, currency, time, reference_curr="xxbt"):
        """
        Calculate the equivalent balance (default: in XBT)
        """
        currency = currency.lower()
        reference_curr = reference_curr.lower()
        if currency==reference_curr or amount == 0.0:
            # Nothing to do here
            return amount

        # mult = False
        asset_pair, base = self.get_asset_pair(currency, reference_curr)
        if asset_pair is None and reference_curr != "xxbt":
            amount = self.get_eq_bal(amount, currency, time, reference_curr="xxbt")
            if amount == 0:
                return 0
            asset_pair, base = self.get_asset_pair("xxbt", reference_curr)
        if asset_pair is None:
            # The asset_pair was removed -> the currency is not tradable
            return 0

        price_row = self.dbq.closestelem(asset_pair, time)
        columns = self.dbq.get_columns()

        if base:
            price = price_row[0][columns.index('bid_price')]
            return amount*price
        price = price_row[0][columns.index('ask_price')]
        return amount/price

    def get_total_bal(self, time, ref='xxbt'):
        tot_bal = 0
        balance = self.dbq.get(table='balance', column="*", time=time)[0]
        curs = self.dbq.get_columns()
        for cur in curs:
            if cur != 'modtime' and cur != 'eq_bal':
                tot_bal += self.get_eq_bal(balance[curs.index(cur)], cur, time, ref)
        return tot_bal

    def xbal(self, price, bal, time, action):
        # exchanges cur1 with cur2 at specific time
        elem = self.get_closest_elem(price,time)
        if action:
            return bal/price[elem][1]
        return bal*price[elem][2]

    def get_base(self, pair):
        return self.asset_pairs[pair]['base'].lower()

    def get_quote(self, pair):
        return self.asset_pairs[pair]['quote'].lower()

    def get_asset_pair(self, cur1, cur2):
        """
        :param cur1: currency 1, which is assumed to be the 'base' currency
        :param cur2: currency 2, which is assumed to be the 'quote' currency
        :return: None -> no asset pair found or asset_pair and True is cur1 is 'base' or False if cur2 is 'quote'
        """
        for pair in self.asset_pairs:
            if cur1.lower() == self.asset_pairs[pair]['base'].lower() and\
                    cur2.lower() == self.asset_pairs[pair]['quote'].lower():
                return pair, True
            if cur2.lower() == self.asset_pairs[pair]['base'].lower() and\
                    cur1.lower() == self.asset_pairs[pair]['quote'].lower():
                return pair, False
        return None, None


def get_trader_config():
    json_data=open("./src/"+filename).read()
    return json.loads(json_data)


def get_tader_name(input_class):
    name_sidx = str(input_class).find("all_traders.")
    name_eidx = str(input_class).find(" instance")
    return str(input_class)[name_sidx+12:name_eidx]


def save_trader_config(data, trader_name):
    json_data = get_trader_config()
    # TODO: replace the config of the current trader with the new constants
    json_data[trader_name] = data
    with open("./kraken_trader/"+filename,mode='w') as outfile:
        json.dump(json_data, outfile,indent=4, sort_keys=True)


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

