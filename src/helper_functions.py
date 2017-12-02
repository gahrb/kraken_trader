import json
import sys

filename = "traders.json"
sys.setrecursionlimit(9999)


class HelperFunctions:

    def __init__(self, asset_pairs, dbq):
        self.dbq = dbq
        self.asset_pairs = asset_pairs

    def get_trader_config(self):
        json_data=open("./src/"+filename).read()
        return json.loads(json_data)

    def save_trader_config(self, data, trader_name):
        json_data = self.get_trader_config()
        # TODO: replace the config of the current trader with the new constants
        json_data[trader_name] = data
        with open("./kraken_trader/"+filename,mode='w') as outfile:
            json.dump(json_data, outfile,indent=4, sort_keys=True)



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

        if currency==reference_curr:
            # Nothing to do here
            return amount

        mult = False
        if currency+reference_curr in self.asset_pairs:
            asset_pair = currency+reference_curr
            mult = True
        elif reference_curr+currency in self.asset_pairs:
            asset_pair = reference_curr+currency
        else:
            # If there is no asset_pair towards the reference currency, go via xxbt
            if reference_curr+"xxbt" in self.asset_pairs:
                asset_pair = reference_curr+"xxbt"
            elif "xxbt"+reference_curr in self.asset_pairs:
                mult = True
                asset_pair = "xxbt"+reference_curr
            else:
                # No asset pair found. Return 0
                # self.logger.warn("Asset pair not found: " + reference_curr + ", " + currency)
                return 0
            amount = self.get_eq_bal(amount, currency, time, reference_curr="xxbt")

        price_row = self.dbq.closestelem(asset_pair, time)
        columns = self.dbq.get_columns()

        if mult:
            price = price_row[0][columns.index('bid_price')]
            return amount*price
        price = price_row[0][columns.index('ask_price')]
        return amount/price


        # rel_bal = dict()
        # for bal in balance:
        #     if bal!=reference_curr:
        #         pair = bal+reference_curr
        #         tmp_bal = balance[bal]
        #         buy = False
        #         if not(pair in price):
        #             if (reference_curr+bal in price):
        #                 pair = reference_curr+bal
        #                 buy = True
        #             else:
        #                 #Change it first to xxbt, then to reference curr
        #                 tmp_bal = xbal(price[bal+"XXBT"],tmp_bal,time,buy)
        #                 pair = "XXBT"+reference_curr
        #                 if not(pair in price):
        #                     pair = reference_curr+"XXBT"
        #                     buy = True
        #         rel_bal[bal] = xbal(price[pair],tmp_bal,time,buy)
        #         eq_bal += rel_bal[bal]
        #     else:
        #         rel_bal[bal] = balance[bal]
        # for bal in rel_bal:
        #     rel_bal[bal] = rel_bal[bal]/eq_bal
        # return (eq_bal,rel_bal)

    def xbal(self, price, bal, time, action):
        # exchanges cur1 with cur2 at specific time
        elem = self.get_closest_elem(price,time)
        if action:
            return bal/price[elem][1]
        return bal*price[elem][2]


def get_tader_name(self, input_class):
    name_sidx = str(input_class).find("all_traders.")
    name_eidx = str(input_class).find(" instance")
    return str(input_class)[name_sidx+12:name_eidx]


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

