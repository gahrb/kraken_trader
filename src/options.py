from enum import Enum


class ApplicationActions(Enum):
    NO_ACTION = 0
    POPULATE_DB = 1
    ACCOUNT_INFO = 2
    ACCOUNT_DEV = 3
    TRADE = 4


class ApplicationOptions(object):
    def __init__(self):
        self.simulate = False
        self.optimize = False
        self.start_date = -1
        self.action: ApplicationActions = ApplicationActions.NO_ACTION
        self.populate_db = False
        self.account_info = False
        self.account_dev = False
        self.trader_class = "mas_trader"
