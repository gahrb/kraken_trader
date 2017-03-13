import logging

FORMAT = '%(asctime)-5s [%(name)s] %(levelname)s: %(message)s'
logging.basicConfig(filename='/var/log/kraken/kraken_log.log', level=logging.INFO, format=FORMAT,
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('kraken_trader')
