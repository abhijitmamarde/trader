'''Module docstring'''
import logging
from datetime import datetime
from math import sqrt
from upstox_api.api import TransactionType, OrderType, ProductType, DurationType
from ohlc import OHLC
from utils import round_off, ACTIONS, STATUS_TYPES, is_trade_active
from strategy import Strategy



class GannAngles(Strategy):
    '''Gann Angle strat'''
    def __init__(self, inst):
        super().__init__(inst)
        self.gann_angles = [0.02, 0.04, 0.08, 0.1, 0.15, 0.25, 0.35,
                       0.4, 0.42, 0.46, 0.48, 0.5, 0.67, 1.0]
        self.test = False
        self.init = False
        self.logger = None
        self.max_attempts = 5
        self.order_attempts = 0

        self.res_vals = []
        self.sup_vals = []
        self.res_trigger = 0.0
        self.sup_trigger = 0.0

        self.buy_orderid = 0
        self.stoploss_orderid = 0
        self.target_orderid = 0

        self.buy_placed = False
        self.sell_placed = False
        self.mod_placed = False

        self.setup_logger()


    def initialize(self, quote_info, test=False):
        '''Calculates buy/sell triggers.

        Automatically called by quote_update() if not initialized
        test argument currently unused.
        '''
        if isinstance(quote_info, OHLC):
            self.ohlc = quote_info
        else:
            self.ohlc = OHLC.fromquote(quote_info)

        self.test = test
        if is_trade_active():
            self.calc_resistance(self.ohlc.ltp)
            self.calc_support(self.ohlc.ltp)
            self.init = True
            self.logger.info('{} Gann Angle - on LTP {}, buy at {}'
                             .format(self.instrument.symbol,
                                     self.ohlc.ltp,
                                     self.res_trigger))


    def setup_logger(self):
        '''Creates logger with name gann_symbol.log'''
        self.logger = logging.getLogger('gann_{}'.format(self.instrument.symbol))
        self.logger.setLevel(logging.DEBUG)
        logname = 'Gann_{}'.format(self.instrument.symbol) \
                  + datetime.strftime(datetime.now(), '%d-%b-%y') \
                  + '.log'
        f = '{asctime}|{name}|{levelname} - {message}'
        formatter = logging.Formatter(fmt=f, style='{',
                                      datefmt='%H:%M:%S')
        fh = logging.FileHandler(logname)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)

        sh = logging.StreamHandler()
        sh.setLevel(logging.WARNING)
        sh.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(sh)
        self.logger.debug('Gann Angle logger initialised')


    def quote_update(self, quote_info):
        '''Main point of GannAngles execution'''
        if self.init is False:
            self.initialize(quote_info)
            return ACTIONS.none
        self.last_update = datetime.now()
        self.ohlc = OHLC.fromquote(quote_info)

        if self.buy_placed or self.order_attempts > self.max_attempts:
            return ACTIONS.none
        elif self.ohlc.ltp >= self.res_trigger and is_trade_active():
            self.buy_placed = True
            self.logger.debug('Buy Order attempt {}/{} for {}'
                              .format(self.order_attempts,
                                      self.max_attempts,
                                      self.ohlc.symbol))
            return ACTIONS.buy
        elif self.ohlc.ltp <= self.sup_trigger:
            if self.buy_orderid:
                return ACTIONS.sell
            else:
                self.calc_resistance(self.ohlc.ltp)
        return ACTIONS.none


    def order_update(self, order_info):
        '''Stores order IDs as they are processed by the server'''
        status = order_info['status']
        oid = order_info['order_id']
        txn = order_info['transaction_type']
        if txn == 'B':
            self.logger.debug('Buy order update - {sym} order {id} - {st}'
                              .format(sym=self.ohlc.symbol,
                                      id=oid,
                                      st=status))
            if status in STATUS_TYPES.positive:
                self.buy_orderid = oid
            elif status in STATUS_TYPES.negative:
                self.buy_placed = False
                self.order_attempts += 1
            elif status in STATUS_TYPES.processing:
                pass
            else:
                self.logger.debug('Unknown update type')
        else: # sell orders
            o_type = order_info['order_type']
            self.logger.debug('Sell order update - {sym} order {id} - {st}'
                              .format(sym=self.ohlc.symbol,
                                      id=oid,
                                      st=status))
            if status in STATUS_TYPES.positive:
                if o_type == 'Limit':
                    self.target_orderid = oid
                elif o_type == 'StopLoss':
                    self.stoploss_orderid = oid
                else:
                    self.logger.warning('Invalid sell order created by server')
                    self.logger.warning('Expected - {} | Created - {}'
                                        .format('Limit', o_type))
            elif status in STATUS_TYPES.processing:
                pass
            elif status in STATUS_TYPES.negative:
                self.logger.warning('Sell order failed! Reason: {}'
                                    .format(order_info['reason']))
            else:
                self.logger.debug('Unknown update type')
        self.orders.append(order_info)


    def trade_update(self, trade_info):
        if trade_info['transaction_type'] == 'S':
            self.order_attempts += 1
        self.trades.append(trade_info)


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
    10 - Stoploss as positive Difference between the purchase price and
         stop-loss target price
    11 - Square Off as positive Difference between purchase price and
         profit target price
    12 - Multiplier for 5 paise. Resultant no. is the flexibility
         given while placing orders.
    '''

    def get_buy_order(self):
        '''1x2 value with initialzing LTP as base value in Gann chart '''
        args = (TransactionType.Buy,
                self.instrument,
                75,
                OrderType.Limit,
                ProductType.Delivery,
                round_off(self.res_vals[4]),
                None,
                0,
                DurationType.DAY,
                None,
                None,
                None)
        return args


    def get_target_order(self):
        '''1x64 value on Gann Chart'''
        args = (TransactionType.Sell,
                self.instrument,
                75,
                OrderType.Limit,
                ProductType.Delivery,
                round_off(self.res_vals[-1]),
                0,
                0,
                DurationType.DAY,
                None,
                None,
                None
                )
        return args


    def get_sl_order(self):
        '''1x1 value on reverse direction in Gann Chart'''
        args = (TransactionType.Sell,
                self.instrument,
                75,
                OrderType.StopLoss,
                ProductType.Delivery,
                round_off(self.res_vals[4]),
                self.sup_vals[5],
                0,
                DurationType.DAY,
                None,
                None,
                None
                )
        return args


    def get_mod_order(self):
        sl = self.stoploss_orderid
        args = (sl['order_id'],
                self.sup_trigger)
        self.modifying = True
        return args


    def calc_resistance(self, price):
        resistance = []
        for x in self.gann_angles:
            tmp = (sqrt(price) + x)**2
            resistance.append(tmp)
        self.res_vals = resistance
        self.res_trigger = resistance[3]


    def calc_support(self, price):
        support = []
        for x in self.gann_angles:
            tmp = (sqrt(price) - x)**2
            support.append(tmp)
        self.sup_vals = support
        self.sup_trigger = support[5]
