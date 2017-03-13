import krakenex
import datetime

from src.options import ApplicationOptions, ApplicationActions
from src.kraken_cache import KrakenCache
from src.database_connection import get_database_connection
from src.account import KrakenAccount
from src.logger import logger
from src.analyzer import Analyzer
from src.all_traders import ma_trader, mas_trader


class KrakenTraderApplication(object):
    def __init__(self, application_options=ApplicationOptions()):
        self.application_options = application_options
        self.kraken_cache = KrakenCache()

    def start(self):
        action_functions = {
            ApplicationActions.POPULATE_DB: self._populate_db,
            ApplicationActions.ACCOUNT_INFO: self._print_account_info,
            ApplicationActions.ACCOUNT_DEV: self._print_account_dev
        }

        action_function = action_functions.get(self.application_options.action, self._no_action)
        action_function()

    def _no_action(self):
        print('No action selected')
        logger.info('No action selected')

    def _populate_db(self):
        self.kraken_cache.populate_db()

    def _print_account_info(self):
        kraken_api = krakenex.API()
        account = KrakenAccount(get_database_connection(), kraken_api, self.application_options.simulate)
        print(account.account_info_str())

    def _print_account_dev(self):
        kraken_api = krakenex.API()
        account = KrakenAccount(get_database_connection(), kraken_api, self.application_options.simulate)
        trader_class = eval(self.application_options.trader_class)
        account.account_dev(trader_class(get_database_connection(), kraken_api, account))

    def _run_trader(self):
        kraken_api = krakenex.API()
        try:
            trader_class = eval(self.application_options.trader_class)
        except:
            print("Invalid trader class name!")
            logger.error('Invalid trader class name!')
            return

        database_connection = get_database_connection()
        account = KrakenAccount(database_connection,
                                kraken_api,
                                self.application_options.simulate,
                                logger)
        trader = trader_class(database_connection, kraken_api, account)

        analyzer = Analyzer(trader, account)
        analyzer.optimize = self.application_options.optimize

        if self.application_options.optimize:
            analyzer.gradient(self.application_options.start_date)
        elif self.application_options.simulate:
            analyzer.simulate(self.application_options.start_date)
        else:
            self._start_trader(kraken_api, account, trader)

    def _start_trader(self, kraken_api, account, trader):
        logger.info('Starting trader {}'.format(trader.trader_name))
        trade = dict()
        logger.info('Getting sell advices...')
        now = datetime.datetime.now()
        trade['sell'] = trader.get_sell_advice(now)
        trade['buy'] = trader.get_buy_advice(now)

        if trade:
            print("---------------------\nPerforming Trades:\n---------------------")
            logger.info("Performing Trades:")
            account.place_orders(kraken_api, trade, trader)
            account.get_open_orders()
            print(account.orders_info_str())
        else:
            print("---------------------\nNo trade orders received!\n---------------------")
            logger.info("No trade orders received!")

