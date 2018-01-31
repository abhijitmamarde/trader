from datetime import datetime
from collections import namedtuple
from math import sqrt

from ohlc import OHLC
from upstox_api.api import Instrument, TransactionType, OrderType, ProductType, DurationType
from utils import print_l, print_s, is_trade_active, round_off, Actions


from trader import TradeStrategy

class GannAngles(TradeStrategy):

    test = False
    gann_angles = [0.02, 0.04, 0.08, 0.1, 0.15, 0.25, 0.35,
                   0.4, 0.42, 0.46, 0.48, 0.5, 0.67, 1.0]
    res_vals = []
    sup_vals = []
    res_trigger = 0.0
    sup_trigger = 0.0
    init = False
    buy_orderid = 0
    stoploss_orderid = 0
    target_orderid = 0
    sell_orderid = 0
    ordered = False
    orders = []
    trades =[]

    def initialize(self, quote_info, test=False):
        print('in GA initialize')
        self.ohlc = OHLC().fromquote(quote_info)
        self.test = test
        if is_trade_active():
            self.calc_resistance(self.ohlc.ltp)
            self.calc_support(self.ohlc.ltp)
            self.init = True
            print_s()
            print_l('Gann Angle for {}'.format(self.instrument['symbol']))
            print_l('Calculated on ltp = {}'.format(self.ohlc.ltp))
            print_l('{} Buy Trigger = {}\n'.format(self.instrument.symbol,
                                                        self.res_trigger))
            print_l('{} Support Trigger = {}'.format(self.instrument.symbol,
                                                        self.sup_trigger))
            print_s()
        else:
            print_s()
            print_l("Waiting for Trade open..")
            print_s()

    def quote_update(self, quote_info):
        print('in GA qoute_update')
        if self.init == False:
            self.initialize(quote_info)
            return Actions.none, None
        self.last_update = datetime.now()

        self.ohlc.ltp = float(quote_info['ltp'])
        self.ohlc.atp = float(quote_info['atp'])
        self.ohlc.op = float(quote_info['open'])
        self.ohlc.hi = float(quote_info['high'])
        self.ohlc.lo = float(quote_info['low'])
        self.ohlc.cl = float(quote_info['close'])
        self.epoch = int(quote_info['timestamp'])/1000

        if self.ordered:
            return Actions.none, None
        elif self.ohlc.ltp >= self.res_trigger and is_trade_active():
            self.ordered = True
            return Actions.buy, self.buy_args()
        elif self.ohlc.ltp <= self.sup_trigger:
            self.calc_resistance(self.ohlc.ltp)
        return Actions.none, None

    def order_update(self, order_info):
        sym = order_info['symbol'].upper()
        if self.not_rejected(order_info['status']):
            if order_info['transaction_type'] == 'B':
                self.buy_orderid = order_info['order_id']
            elif order_info['trigger_price'] > 0:
                self.stoploss_orderid = order_info['order_id']
            else:
                self.target_orderid = order_info['order_id']
        else:
            self.ordered = False
        self.orders.append(order_info)

    def trade_update(self, trade_info):
        if trade_info['transaction_type'] == 'S':
            self.sell_orderid = trade_info['transaction_type']
        self.trades.append(trade_info)


    def calc_resistance(self, price):
        resistance = []
        for x in self.gann_angles:
            tmp = (sqrt(price)+x)**2
            resistance.append(tmp)
        self.res_vals = resistance
        self.res_trigger = resistance[3]


    def calc_support(self, price):
        support = []
        for x in self.gann_angles:
            tmp = (sqrt(price)-x)**2
            support.append(tmp)
        self.sup_vals = support
        self.sup_trigger = support[5]

    def buy_args(self):
        '''
        Place_order() Args List:
        1  - Buy/Sell
        2  - Instrument to buy
        3  - Quantity (for futures, it is multiples of 75)
        4  - Order Type - StopLossLimit(SL/Limit(L)/SLM(StoplossMarket/Market
        5  - Product Type - Intraday/Delivery/CO/OCO
        6  - Order price for purchase
        7  - Trigger Price for purchase to activate
        8  - Disclosed qt shown on NSE to other traders
        9  - Duration of trade(Use "DAY" only)
        10 - Stoploss as Difference between the purchase price and
             stop-loss target price
        11 - Square Off as Difference between purchase price and
             profit target price
        12 - Multiplier for 5 paise. Resultant no. is the flexibility
             given while placing orders.
        '''
        args = (TransactionType.Buy,
                self.instrument,
                75,
                OrderType.StopLossLimit,
                ProductType.OneCancelsOther,
                round_off(self.res_vals[4]),
                round_off(self.res_vals[3]),
                0,
                DurationType.DAY,
                round_off(self.res_vals[4] - self.sup_vals[5]),
                round_off(self.res_vals[-1] - self.res_vals[4]),
                None
                )

        return args

    def mod_sl_args(self):
        sl = self.stoploss_order
        args = (sl['order_id'],
            self.sup_trigger)
        self.modifying = True
        return args

    def not_rejected(self, status):
        if status == 'cancelled' or status == 'rejected':
            return False
        return True
