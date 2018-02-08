from datetime import datetime
from utils import Actions


class Strategy():

    def __init__(self, inst):
        self.instrument = inst
        self.orders = []
        self.trades = []
        self.start_time = datetime.now()
        self.last_update = None

    def quote_update(self, quote_info):
        return Actions.none, None

    def order_update(self, order_info):
        return Actions.none, None

    def trade_update(self, trade_info):
        return Actions.none, None
