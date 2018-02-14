'''Strategy.py by Shashwat'''
from datetime import datetime
from utils import ACTIONS


class Strategy():
    '''Base class for strategy classes. Contains some universal variables and

    methods expected to be present for usage'''
    def __init__(self, inst):
        self.instrument = inst
        self.orders = []
        self.trades = []
        self.start_time = datetime.now()
        self.last_update = None
        self.ohlc = None

    def quote_update(self, quote_info):
        '''To be overridden as required by subclass'''
        print(quote_info)
        self.last_update = datetime.now()
        return ACTIONS.none

    def order_update(self, order_info):
        '''To be overridden as required by subclass'''
        print(order_info)
        self.orders.append(order_info)
        return ACTIONS.NONE

    def trade_update(self, trade_info):
        '''To be overridden as required by subclass'''
        print(trade_info)
        self.trades.append(trade_info)
        return ACTIONS.none
