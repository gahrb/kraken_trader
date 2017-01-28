import krakenex


class KrakenApiWrapper(object):
    def __init__(self):
        self.krakenex_api = krakenex.API()

    def get_asset_pairs(self):
        pairs = self.krakenex_api.query_public('AssetPairs')
        trade_pairs = []
        for pair in pairs['result']:
            if not (pair.find(".d") >= 0 or pair.find("CAD") >= 0 or pair.find("USD") >= 0 or pair.find(
                    "GBP") >= 0 or pair.find("JPY") >= 0):
                trade_pairs.append(pair)

        return trade_pairs

    def query_market(self, pair):
        return self.krakenex_api.query_public('Ticker', {'pair': pair})
