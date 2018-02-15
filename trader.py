'''Module docstring'''
import logging
import pickle
import time
import threading
from datetime import datetime, date
from gann import GannAngles
from ohlc import OHLC
from requests.exceptions import HTTPError
from stockdb import StockDB, TABLE_TYPES
from upstox_api.api import *
from utils import print_l, print_s, ACTIONS, is_trade_active

LOADED = []


class TradeCenter:
    '''Upstox client wrapper for convenience'''
    def __init__(self, config=None):
        self.client = None
        self.sesh = None
        self.condition = threading.Condition()
        self.indices = ['NSE_FO']
        self.stock_dict = {}
        self.listening = False
        self.trading = False
        self.logger = None
        # init db in listen() for thread compatibility
        self.db = None
        self.setup_logger()

        if config is None:
            self.logger.error('No config provided. Will be unable to sign in.')
        self.config = config
        self.quote_queue = []
        self.trade_queue = []
        self.order_queue = []


    def start_listener(self):
        '''Opens websocket to upstox server and starts listener daemon'''
        for key, value in self.stock_dict.items():
            try:
                self.client.unsubscribe(value.instrument, LiveFeedType.Full)
                resp = self.client.subscribe(value.instrument, LiveFeedType.Full)
                if resp['success'] == True:
                    self.logger.debug('Subbed to {}'.format(resp['symbol']))
            except HTTPError as e:
                self.logger.exception('message')
                self.client.unsubscribe(value.instrument.symbol, LiveFeedType.Full)
            
        try:
            self.logger.debug('Opening Websocket')
            self.client.start_websocket(True)
        except Exception as e:
            self.logger.exception('message')

        listener = threading.Thread(target=self.listen)
        try:
            listener.start()
            self.logger.info('Receiving updates from upstox...')
            self.listening = True
        except Exception as e:
            self.logger.exception('message')


    def listen(self):
        '''Checks update queues and calls the required update method'''
        self.db = StockDB()
        self.db.initialize('stock_db.sqlite')
        self.logger.debug('Trading = {}'.format(str(self.trading)))
        global LOADED
        for key in self.stock_dict:
            if self.db.create_table(key, TABLE_TYPES.ohlc):
                self.logger.debug('Table verified for: ' + str(key))
                LOADED.append(key)
        while self.listening:
            try:
                with self.condition:
                    self.condition.wait()
                if len(self.quote_queue) > 0:
                    for q in self.quote_queue:
                        o = OHLC.fromquote(q)
                        print(o)
                        self.db.add_data(q['symbol'], TABLE_TYPES.ohlc, o)
                        self.quote_update(q)
                    del self.quote_queue[:]

                if len(self.order_queue) > 0:
                    for q in self.order_queue:
                        self.order_update(q)
                    del self.order_queue[:]

                if len(self.trade_queue) > 0:
                    for q in self.trade_queue:
                        self.trade_update(q)
                    del self.trade_queue[:]
                time.sleep(0.2)
            except KeyboardInterrupt as e:
                self.logger.critical('Program interrupted by user.')
                self.close_ops()


    def register_masters(self, masters=["nse_fo", 'nse_index']):
        'Boilerplate for adding exchanges'
        try:
            print_s()
            print_l("Registering Indices")
            for ind in masters:
                num = len(self.client.get_master_contract(ind))
                self.logger.debug('{} - downloaded {} scrips'.format(ind, num))
        except AttributeError as e:
            self.logger.debug("Masters preloaded/no valid masters provided")
        except HTTPError as e:
            self.logger.error('Unable to load master contract')
            self.logger.exception('message')


    def register_handlers(self):
        'Registers quote, order and trade handlers for Upstox updates'
        try:
            print_s()
            self.logger.debug('Registering handlers')
            self.client.set_on_quote_update(self.quote_handler)
            self.client.set_on_order_update(self.order_handler)
            self.client.set_on_trade_update(self.trade_handler)
        except Exception as e:
            self.logger.error('Unable to register handlers - ')
            self.logger.exception('message')

    def register_stocks(self, sym=None):
        '''Subscribes to stocks for live feed.'''
        inst = None
        try:
            inst = self.client.get_instrument_by_symbol('NSE_FO', sym)
            self.logger.debug('Added {} to stock_dict'.format(inst.symbol))
        except Exception as e:
            # TODO Figure out exceptions
            self.logger.exception('message')

        

        self.stock_dict[sym.upper()] = GannAngles(inst)
        self.logger.debug('Current stock dict:')
        for key, value in self.stock_dict.items():
            self.logger.debug('{} -> {}'.format(key, type(value)))


    def remove_stocks(self, sym=None):
        '''Unsubscribe and remove strategy for a live feed'''
        unsub = None
        self.logger.warning('Removing {} from list.'.format(sym))
        try:
            unsub = self.stock_dict.pop(sym)
        except KeyError as e:
            self.logger.debug('{} has no GannAngles obj associated.'.format(sym))
            return

        try:
            self.logger.warning('Unsubscribing {}. Will no longer receive updates'
                    .format(sym))
            self.client.unsubscribe(unsub.instrument, LiveFeedType.Full)
            unsub = None
        except TypeError as e:
            self.logger.error('Already unsubbed')
        except Exception as e:
            self.logger.exception('message')
            # TODO figure out exceptions
            pass


    def quote_handler(self, message):
        '''Addes message to queue for processing.
        
        This handler runs on the Upstox websocket thread.
        '''
        with self.condition:
            self.quote_queue.append(message)
            self.condition.notify_all()


    def order_handler(self, message):
        '''Addes message to queue for processing.
        
        This handler runs on the Upstox websocket thread.
        '''
        with self.condition:
            self.order_queue.append(message)
            self.condition.notify_all()


    def trade_handler(self, message):
        '''Addes message to queue for processing.
        
        This handler runs on the Upstox websocket thread.
        '''
        with self.condition:
            self.trade_queue.append(message)
            self.condition.notify_all()


        '''
        Message object:
        {'bids': [{'orders': 2, 'price': 97.5, 'quantity': 150},],
        'high': 111.85,
        'asks': [{'orders': 2, 'price': 97.75, 'quantity': 225}],
        'vtt': 3107850.0,
        'open': 100.0,
        'timestamp': '1517377333000',
        'ltp': 97.85,
        'total_buy_qty': 651975,
        'spot_price': 11019.55,
        'oi': 2665875.0,
        'upper_circuit': 229.55,
        'symbol': 'NIFTY18FEB11200CE',
        'yearly_low': None,
        'lower_circuit': 1.95,
        'exchange': 'NSE_FO',
        'low': 95.0,
        'instrument': namedtuple Instrument,
        'close': 115.75,
        'ltt': 1517377332000,
        'total_sell_qty': 221775,
        'atp': 103.58}
        '''
    def quote_update(self, message):
        '''Processes quotes from the queue.
        
        Implemented this way to keep function executions client-side whenever
        possible.
        '''
        sym = message['symbol']
        
        try:
            action = self.stock_dict[sym].quote_update(message)
        except KeyError:
            self.logger.debug('{} Not in subscribed stock list'.format(sym))
            action = ACTIONS.none

        order = ''
        args = None
        if action == ACTIONS.none:
            pass
        elif action == ACTIONS.buy:
            args = self.stock_dict[sym].get_buy_order()
            print('Place buy order:')
            print('Instrument:    {}'.format(args[1].symbol))
            print('Order Price:   {}'.format(args[5]))
            print('Quantity:      {}'.format(args[2]))
            print('OUT')
            if self.trading:
                try:
                    self.logger.debug('Attempted to place  for {} at Rs.{}'
                                      .format(args[1].symbol, args[5]))
                    order = self.client.place_order(*args)
                    if order:
                        self.logger.debug('Buy order received by server. Ref={}'
                                          .format(order['order_id']))
                except Exception as e:
                    self.logger.exception('message')
        elif action == ACTIONS.modify:
            args = self.stock_dict[sym].get_mod_order()
            self.logger.info('Modifying {} stoploss - ID: {}'
                             .format(sym, args[0]))
            try:
                order = self.client.modify_order(order_id=args[0],
                                                 trigger_price=args[1])
                if order:
                        self.logger.debug('Modify request received by server. Ref= {}'
                                          .format(order['order_id']))
            except Exception as e:
                self.logger.exception('message')
        else:
            if action == ACTIONS.sell_target:
                args = self.stock_dict[sym].get_target_order()
            elif action == ACTIONS.sell_sl:
                args = self.stock_dict[sym].get_sl_order()
            if self.trading:
                try:
                    self.logger.debug('Placing Sell-{otype} order for {sym} at Rs.{rs}'
                                      .format(otype=args[3],
                                              sym=args[1].symbol,
                                              rs=args[5]))
                    order = self.client.place_order(*args)
                    if order:
                        self.logger.debug('Sell order received by server. Ref= {}'
                                          .format(order['order_id']))
                except Exception as e:
                    self.logger.exception('message')


    def order_update(self, message):
        '''Processes items from the order queue.
        
        Updates the relevant TradeStrategy object in stock_dict with the order info
        '''
        sym = message['symbol'].upper()
        self.logger.info('Order update for {} - ID: {}'
                         .format(sym, message['order_id']))
        print(message)
        with open('messages.txt', 'a') as f:
            for field, val in message.items():
                f.write(field)
        try:
            self.logger.info(str(message['status']))
            self.stock_dict[sym].order_update(message)
        except KeyError:
            self.logger.info('Order update received for external order')
        except Exception as e:
            self.logger.exception('message')


    def trade_update(self, message):
        '''Processes items from the trade queue.
        
        Updates the relevant TradeStrategy object in stock_dict with the trade info
        '''
        sym = message['symbol'].upper()
        self.logger.info('Trade update for {} - ID: {}'
                         .format(sym, message['order_id']))
        self.logger.info(str(message['status']))
        try:
            self.stock_dict[sym].order_update(message)
        except KeyError:
            self.logger.info('Trade update received for external order')
        except Exception as e:
            self.logger.exception('message')


    def setup_logger(self):
        '''Creates logger for Tradecenter messages'''
        self.logger = logging.getLogger('tradecenter')
        self.logger.setLevel(logging.DEBUG)
        logname = 'center' + datetime.strftime(datetime.now(), '%d-%b-%y') + '.log'
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
        
        self.logger.debug('Logger initialised')


    def sign_in(self):
        '''Login to Upstox.'''
        #
        token_file = 'data.pkl'
        #
        token = ''
        client = None
        try:
            self.logger.debug('Checking for stored credentials')
            with open(token_file, "rb") as f:
                token = pickle.load(f)
        except FileNotFoundError:
            self.logger.debug('Credentials file not found. Creating new file...')
            with open(token_file, "wb") as f:
                pass
        except EOFError:
            self.logger.debug('Data file empty.')
        finally:
            if not token:
                return False

        try:
            self.logger.info('Attempting login with stored credentials')
            client = Upstox(self.config['api_key'], token)
        except HTTPError as e:
            err = e.args[0]
            # Similar error messages for incorrect and expired token.
            # 'Invalid'  is common word between them
            if 'Invalid' in err:
                self.logger.critical('Invalid token entered')
            else:
                raise
        finally:
            if client is not None:
                self.logger.info('Signed in to upstox.')
                self.client = client
                return True
            return False


    def save_new_token(self, auth_code):
        if self.sesh is None:
            return False
        self.sesh.set_code(auth_code)
        self.logger.debug("Authenticating...")
        access_token = str(self.sesh.retrieve_access_token())
        access_time = datetime.now()
        self.logger.debug('Access token received')
        with open('data.pkl', 'wb') as f:
            pickle.dump(access_token, f)
            pickle.dump(access_time, f)
        return True


    def get_session_url(self):
        self.logger.debug('Getting new session URL')
        self.sesh = Session(self.config['api_key'])
        self.sesh.set_redirect_uri("https://upstox.com")
        self.sesh.set_api_secret(self.config['api_secret'])
        try:
            url = self.sesh.get_login_url()
            return url
        except HTTPError as e:
            # No errors encountered yet...
            self.logger.exception('message')
            return None


    def close_ops(self):
        '''Unsubscribe from upstox scrips and closes other threads'''
        self.logger.warning('Closing program')
        with self.condition:
            self.logger.debug('notifying threads')
            self.listening = False
            self.condition.notify_all()
        for sym, stock in self.stock_dict.items():
            self.logger.debug('Unsubbing {}'.format(stock.instrument.symbol))
            self.client.unsubscribe(stock.instrument, LiveFeedType.Full)
        self.logger.debug('Finished all exit tasks.')
