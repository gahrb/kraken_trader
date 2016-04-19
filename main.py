#!/usr/bin/python

import krakenex
import os
import sys, getopt


simulate = True

def main(argv):

    keyfile=os.path.expanduser('~')+'/.kraken/kraken.secret'
    try:
        opts, args = getopt.getopt(argv,"h:a:",["ifile=","ofile="])
    except getopt.GetoptError:
        print 'test.py -k <kraken.secret> -a [action]'# -i <inputfile> -o <outputfile>'

    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -k <kraken.secret> -a [action]\n' \
                '\tThe kraken.secret file contains in the first line the key and in the second the secret - nothing else. This is optional.\n'\
                '\tThe action can be one of the followings:'\
                '\t"pupolateDB" or "-t <algorithm>" \n\t\tadding the "-s" flag only simulates the algorithm'
            sys.exit()
        elif opt in ("-k", "--kfile"):
            keyfile = arg
        elif opt == "-s":
            Simulate = True

    k = krakenex.API()
    k.load_key(keyfile)

    for opt, arg in opts:
        if opt == '-a' and arg=='populateDB':
            query_market(k)
        elif opt == "-t":
            algorithm = arg
            print "Running the "+algorithm+" algorithm"
            place_order(k)


def place_order(k):
    if not simulate:
        k.query_private('AddOrder', {'pair': 'XXBTZEUR',
            'type': 'buy',
            'ordertype': 'limit',
            'price': '1',
            'volume': '1',
            'close[pair]': 'XXBTZEUR',
            'close[type]': 'sell',
            'close[ordertype]': 'limit',
            'close[price]': '9001',
            'close[volume]': '1'})

def query_market(k):
    ticker = k.query_public('Ticker', {'pair': 'XXBTZEUR'})
    print ticker
    ticker = k.query_public('Ticker', {'pair': 'XETHZEUR'})
    print ticker
    ticker = k.query_public('Ticker', {'pair': 'XLTCZEUR'})
    print ticker

if __name__ == "__main__":
    main(sys.argv[1:])
