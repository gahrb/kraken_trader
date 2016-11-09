import datetime as dt
import helper_functions as hf
import os
import psycopg2

keyfile = os.path.expanduser('~') + '/.kraken/kraken.secret'

class kraken_account:

    def __init__(self,conn,k,simulate=True,logger=""):
        self.logger = logger
        self.conn = conn
        self.cur = conn.cursor()
        self.k = k
        self.balance = dict()
        self.trade_balance = dict()
        self.simulate = simulate
        self.get_assets()
        if simulate:
            self.populate_balance()
        else:
            # Load the key to perform private queries.
            self.k.load_key(keyfile)

            # Query private account information
            #self.get_ledger_info()
            self.get_balance()
            self.get_trade_balance()
            self.get_open_orders()
            self.DBupdatecheck()

    def get_balance(self):

        for pair in self.asset_pair.keys():
            if not(str(pair[:4]) in self.balance):
                self.balance[str(pair[:4])] = 0
            if not(str(pair[4:]) in self.balance):
                self.balance[str(pair[4:])] = 0

        all_balances = self.k.query_private('Balance')['result']
        for balance in all_balances:
            self.balance[str(balance)] = float(all_balances[balance])

    def balance_to_db(self):
        query = "select column_name from information_schema.columns where table_name='balance';"
        try:
            self.cur.execute(query)
            cols = self.cur.fetchall()
        except psycopg2.Error as e:
            logger.error("Could not query the balance table schema.")
            logger.error(pgcode)
            logger.error(e.pgerror)

        missing =  set(map(str.lower,self.balance))-set([ seq[0] for seq in cols ])
        if missing:
            query = "ALTER TABLE balance "
            for miss in missing:
                self.logger.info("Adding new column "+miss+" to the account table.")
                query += "ADD COLUMN "+miss+" double precision default 0, "
            query = query[0:-2]
            self.cur.execute(query+";")

        dbString = "INSERT INTO balance ("
        nameString = "modtime"
        valueString = "%s"
        values = (dt.datetime.now(),)
        for balance in self.balance:
            nameString += ", "+balance.lower()
            valueString += ", %s"
            values += (self.balance[balance],)

        dbString += nameString+") VALUES ("+valueString+");"
        self.cur.execute(dbString,values)
        self.cur.close()
        self.conn.commit()

    def get_trade_balance(self):
        trade_balance = self.k.query_private('TradeBalance',{'Currency':'ZEUR'})['result']
        for balance in trade_balance:
            self.trade_balance[str(balance)] = float(trade_balance[balance])

    def get_assets(self):
        self.asset_pair = self.k.query_public('AssetPairs')['result']
        for key in self.asset_pair.keys():
            if ( key.find(".d") >=0 or key.find("CAD") >=0 or  key.find("USD") >=0 or  key.find("JPY") >=0 or key.find("GBP") >=0 ):
                self.asset_pair.pop(key,None)

    def get_open_orders(self):
        self.open_orders = self.k.query_private('OpenOrders')['result']


    def get_ledger_info(self):
        self.ledger_info = self.k.query_private('Ledgers')['result']

    def place_orders(self,k,trades,trader):
        keepAmount = 0
        if "delta" in trader.constant:
            keepAmount = trader.constant["delta"]
        # TODO: implement the trading request
        for action in trades:
            if action:
                for pair in trades[action]:
                    # TODO: check if for current pair other open orders are existing: if yes, stop, or cancle and replace them!
                    amount = 0
                    if action == "sell":
                        action_idx=2
                        amount = trades[action][pair]
                    elif action == "buy":
                        action_idx=1
                        #Guess the price to pay, and hence there is enough balance
                        amount = min(trades[action][pair],self.balance[pair[4:]]/trader.price[pair][-1][action_idx] - keepAmount)

                    if (trades[action][pair] < 0.01):
                        self.logger.info("Not trading "+pair+ ", due to insufficient balance. Action: "+action+" Pair: "+pair)
                        break

                    res = k.query_private("AddOrder",{'pair': pair,
                           'type': action,
                           'ordertype': 'limit',
                           'price': format(trader.price[pair][-1][action_idx],'.10f'),
                           'volume': amount})

                    if res['error']:
                        self.logger.warning("Unable to perform a trade. Due to the error:")
                        self.logger.info(res['error'])
                        self.logger.info("Trade: "+str(action)+", "+str(pair)+", "+str(trades[action][pair]*self.balance[pair[:4]]))
                        k.notify.Notification.new("Transaction Error","Trade: "+str(action)+", "+str(pair)+", "+str(trades[action][pair]*self.balance[pair[:4]])+ "\nReason: "+res['error'][0]).show()
                    else:
                        self.logger.info("Performed trade:")
                        self.logger.info(res['result'])
                        k.notify.Notification.new("New Transaction",str(res['result']['descr']['order'])).show()

        self.balance_to_db()

    def populate_balance(self):
        empty = False
        if not hasattr(self,"balance"):
            self.balance = dict()
            emtpy = True
        for pair in self.asset_pair.keys():
            if self.simulate or not(pair[:4] in self.balance):
                if empty:
                    self.balance[pair[:4]] = 0
                else:
                    self.balance[pair[:4]] = 1
            if self.simulate or not(pair[4:] in self.balance):
                if empty:
                    self.balance[pair[4:]] = 0
                else:
                    self.balance[pair[4:]] = 1

    def DBupdatecheck(self):
        self.cur.execute("SELECT * FROM balance order by modtime desc limit 1;")
        dBbalance = self.cur.fetchall()
        for it in range(len(self.cur.description)-1): # -1 because the first row is 'modtime' --> add below +1
            bal = self.cur.description[it+1][0].upper()
            if bal in self.balance.keys() and self.balance[bal] != dBbalance[0][it+1]:
                self.balance_to_db()
                break

    def accountDev(self,trader):
        self.cur.execute("SELECT * FROM balance order by modtime asc;")
        DBbalance = self.cur.fetchall()
        for row in DBbalance:
            time = row[0]
            balance = dict()
            for it in range(len(self.cur.description)-1): # -1 because the first row is 'modtime' --> add below +1
                bal = self.cur.description[it+1][0].upper()
                balance[bal] = row[it+1]
            eq_bal,_ = hf.get_eq_bal(balance,trader.price,time,"ZEUR")
            print str(time) + ": " + str(eq_bal)

        time = dt.datetime.now()
        balance = dict()
        for it in range(len(self.cur.description)-1): # -1 because the first row is 'modtime' --> add below +1
            bal = self.cur.description[it+1][0].upper()
            balance[bal] = DBbalance[-1][it+1]
        eq_bal,rel_bal = hf.get_eq_bal(balance,trader.price,time,"ZEUR")

        print "Current equivalent Balance estimated:[ZEUR]"
        print str(time) + ": " + str(eq_bal)

        for val in sorted(rel_bal.items(), key=lambda x: x[1],reverse=True):
            print str(val[0]) + ": " + str(round(val[1]*100,2))


