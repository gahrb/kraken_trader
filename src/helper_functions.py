import json
import sys
import numpy as np
import datetime as dt
import os

filename = "traders.json"
path = os.path.expanduser('~') + "/.kraken/"
sys.setrecursionlimit(99999)


def get_trader_config():
    json_data = open(path + filename).read()
    return json.loads(json_data)


def save_trader_config(data, trader_name):
    json_data = get_trader_config()
    # TODO: replace the config of the current trader with the new constants
    json_data[trader_name] = data
    with open(path + filename, mode='w') as outfile:
        json.dump(json_data, outfile, indent=4, sort_keys=True)


def get_tader_name(trader):
    return type(trader).__name__


def get_closest_elem(price, time, elem=0):
    if not elem or abs(time - price[elem][0]) > dt.timedelta(
            1):  # if no initial elem is given or the delta is too big, search with numpy
        return np.argmin(np.abs(np.matrix(price)[:, 0] - time))
    elif elem + 1 < len(price) and time > price[elem][0] and (
                abs(time - price[elem + 1][0]) < abs(time - price[elem][0])):  # Step forward
        return get_closest_elem(price, time, elem + 1)
    elif elem - 1 >= 0 and time < price[elem][0] and (
                abs(time - price[elem - 1][0]) < abs(time - price[elem][0])):  # Step backward
        return get_closest_elem(price, time, elem - 1)
    return elem


def get_eq_bal(balance, price, time, reference_curr="XXBT", elem=dict()):
    """
    Calculate the equivalent balance (default: in XBT)
    """
    eq_bal = balance[reference_curr]
    rel_bal = dict()
    for bal in balance:
        tmp_elem = 0
        if bal != reference_curr:
            pair = bal + reference_curr
            tmp_bal = balance[bal]
            buy = False
            removed_curr = False
            if not (pair in price):
                if (reference_curr + bal in price):
                    pair = reference_curr + bal
                    buy = True
                elif (bal + "XXBT" in price):
                    if pair in elem:
                        tmp_elem = elem[pair]
                    # Change it first to xxbt, then to reference curr
                    tmp_bal, elem[pair] = xbal(price[bal + "XXBT"], tmp_bal, time, buy, tmp_elem)
                    pair = "XXBT" + reference_curr
                    if not (pair in price):
                        pair = reference_curr + "XXBT"
                        buy = True
                else:
                    removed_curr = True  # currency is no longer available (c.f. XDAO end of Dec.'16)
            if not removed_curr:
                if pair in elem:
                    tmp_elem = elem[pair]
                rel_bal[bal], elem[pair] = xbal(price[pair], tmp_bal, time, buy, tmp_elem)
                eq_bal += rel_bal[bal]
            else:
                rel_bal[bal] = 0
        else:
            rel_bal[bal] = balance[bal]
    for bal in rel_bal:
        rel_bal[bal] = rel_bal[bal] / eq_bal
    return (eq_bal, rel_bal, elem)


def xbal(price, bal, time, action, elem=0):
    # exchanges cur1 with cur2 at specific time
    elem = get_closest_elem(price, time, elem)
    if action:
        return bal / price[elem][1], elem
    return bal * price[elem][2], elem


def constant_enum(i):
    return {
        0: "alpha",
        1: "beta",
        2: "gamma",
        3: "delta",
        4: "eps",
        5: "zeta",
        6: "eta",
        7: "theta",
        8: "omega"
    }.get(i, "unknown")
