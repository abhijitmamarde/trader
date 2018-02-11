'''Module docstring'''
import logging
import pickle
import time
import threading
from datetime import datetime, date
from gann import GannAngles
from ohlc import OHLC
from requests.exceptions import HTTPError
from stockdb import StockDB, table_types
from upstox_api.api import *
from utils import print_l, print_s, Actions, is_trade_active

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

        if config is None:
            print('No config provided. Will be unable to sign in.')
        self.config = config

        self.setup_logger()

        self.quote_queue = []
        self.trade_queue = []
        self.order_queue = []


    def start_listener(self):
        try:
            print_l('Opening Websocket to Upstox server')
            self.client.start_websocket(True)
        except Exception as e:
            print_l('Error while starting websocket - ')
            print_l(e.args[0])

        listener = threading.Thread(target=self.listen)
        try:
            listener.start()
            self.listening = True
        except Exception as e:
            print_s()
            print_l('Unexpected error')
            print_l(e)
            print_s()


    def listen(self):
        'Checks update queues and calls the required update method'
        self.db = StockDB()
        self.db.initialize('stock_db.sqlite')
        global LOADED
        for key in self.stock_dict:
            if self.db.create_table(key, table_types.ohlc):
                print_l('Table verified for: ' + str(key))
                LOADED.append(key)
        print_l('Receiving updates...')
        while self.listening:
            try:
                with self.condition:
                    self.condition.wait()
                if len(self.quote_queue) > 0:
                    for q in self.quote_queue:
                        o = OHLC.fromquote(q)
                        if o.symbol in LOADED:
                            self.db.add_data(q['symbol'], table_types.ohlc, o)
                        else:
                            self.db.create_table(o.symbol, table_types.ohlc)
                            LOADED.append(o.symbol)
                        self.quote_update(q)
                        self.quote_queue.remove(q)

                if self.order_queue > 0:
                    self.order_update(self.order_queue.pop())
                if self.trade_queue > 0:
                    self.trade_update(self.trade_queue.pop())
                time.sleep(0.2)
            except KeyboardInterrupt as e:
                self.listening = False
            if not is_trade_active():
                self.listening = False


    def register_masters(self, masters=["nse_fo", 'nse_index']):
        'Boilerplate for adding exchanges to enable stock data subscriptions'
        try:
            print_s()
            print_l("Registering Indices")
            for ind in masters:
                print(len(self.client.get_master_contract(ind)))
        except AttributeError:
            print_l("Masters preloaded/no valid masters provided")
        except HTTPError as e:
            print_s()
            print_l('Server error - ')
            print_l(e.args[0])
            print_s()


    def register_handlers(self):
        'Registers quote, order and trade handlers for Upstox updates'
        try:
            print_s()
            print_l('Registering handlers')
            self.client.set_on_quote_update(self.quote_handler)
            self.client.set_on_order_update(self.order_handler)
            self.client.set_on_trade_update(self.trade_handler)
        except Exception as e:
            print_l('Unable to register handlers - ')
            print_l(e.args[0])


    def register_stocks(self, sym=None):
        '''Subscribes to stocks for live feed.'''
        inst = None
        try:
            inst = self.client.get_instrument_by_symbol('NSE_FO', sym)
        except Exception as e:
            # TODO Figure out exceptions
            print(e)

        try:
            self.client.subscribe(inst, LiveFeedType.Full)
            self.client.subscribe(inst, LiveFeedType.Full)
        except HTTPError as e:
            self.client.unsubscribe(inst, LiveFeedType.Full)

        self.stock_dict[sym.upper()] = GannAngles(inst)


    def remove_stocks(self, sym=None):
        '''Unsubscribe from a live feed'''
        unsub = None
        try:
            unsub = self.stock_dict.pop(sym)
        except KeyError as e:
            print('Stock not tracked by program.')
            return

        try:
            self.client.unsubscribe(unsub.instrument, LiveFeedType.Full)
        except TypeError as e:
            print('No such stock to unsub from')
        except Exception as e:
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


    def quote_update(self, message):
        '''Processes quotes from the queue.
        
        Implemented this way to keep function executions client-side whenever
        possible.
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

        sym = message['symbol']

        try:
            action, args = self.stock_dict[sym].quote_update(message)
        except KeyError:
            print('{} Not in subscribed stock list'.format(sym))

        order = ''
        if action == Actions.buy and args is not None:
            print_l('')
            print_s('OUT')
            print_l('Placing order:')
            print_l('Instrument:    {}'.format(args[1].symbol))
            print_l('Order Price:   {}'.format(args[5]))
            print_l('Trigger price: {}'.format(args[6]))
            print_l('Sell Target:   {}'.format(args[5] + args[10]))
            print_l('Stoploss:      {}'.format(args[5] - args[9]))
            print_l('Quantity:      {}'.format(args[2]))
            print_s('OUT')
            print_l('')

            if self.trading:
                try:
                    order = self.client.place_order(*args)
                except Exception as e:
                    print_s()
                    print_l('Error while placing order!')
                    print_l('order args:')
                    print_l(args)
                    print_l(e.args[0])
                    print_s()
        elif action == Actions.mod_sl and args is not None:
            print_s('OUT')
            print_l("{} - modifying stoploss order".format(sym))
            print_l("order_id = {}".format(args[0]))
            try:
                order = self.client.modify_order(order_id=args[0],
                                                 trigger_price=args[1])
            except Exception as e:
                print_s()
                print_l('Exception while modifying order!')
                print_l(e.args[0])
                print_s()

            if len(order) > 0:
                print_s('IN')
                print_l('Response on place_order() - ')
                print_l('Object of type - {}.'.format(type(order)))
                print_l(order)
                print_s('IN')


    def order_update(self, message):
        '''Processes items from the order queue.
        
        Updates the relevant TradeStrategy object in stock_dict with the order info
        '''
        sym = message['symbol'].upper()
        print_s('IN')
        try:
            self.stock_dict[sym].order_update(message)
        except KeyError as e:
            print_l('Update received for unregistered stock')
        except Exception as e:
            print_l("Unhandled Error in order_update:")
            print_l(e)

        print_s('IN')


    def trade_update(self, message):
        '''Processes items from the trade queue.
        
        Updates the relevant TradeStrategy object in stock_dict with the trade info
        '''
        sym = message['symbol'].upper()
        print_s('IN')
        try:
            self.stock_dict[sym].order_update(message)
        except KeyError as e:
            print_l('Update received for unregistered stock')
        except Exception as e:
            print("Error in trade_update_handler:")
            print(e)
        print_l('Trade info received:')
        for key in message:
            print_l(message[key])
        print_s('IN')


    def make_reports(self):
        ''' Currently testing.
        
        Saves the day's total trades and orders in a
        text file'''
        orders = self.client.get_order_history()
        sorted_orders = []
        print_l("Generating order book")
        for order in orders:
            if order['product'] == 'D':
                continue
            if order['transaction_type'] == 'B':
                if order['status'] != 'rejected' and \
                   order['status'] != 'cancelled':
                    sorted_orders.append(order)
                    p_id = order['order_id']
                    for order in orders:
                        if order['parent_order_id'] == p_id and \
                           order['transaction_type'] == 'S':
                            sorted_orders.append(order)

        print_keys = ['symbol',
                      'product',
                      'order_type',
                      'transaction_type',
                      'status',
                      'price',
                      'trigger_price',
                      'order_id',
                      'parent_order_id',
                      'exchange_time']
        dmy = date.today().strftime('%d%m%y')
        with open('orders{}.txt'.format(dmy), 'w') as f:
            f.write('Orders placed ----\n')
            for order in sorted_orders:
                for key in print_keys:
                    f.write("{} :: {}\n".format(key, order[key]))
                f.write("\n----------------------------------\n")
        print_l("Generating trade book")
        trades = self.client.get_trade_book()
        with open('trades{}.txt'.format(dmy), 'w') as f:
            f.write('Trades Completed ----\n')
            for trade in trades:
                for key, val in trade.items():
                    f.write("{} :: {}\n".format(key, val))
                    f.write("\n-----------------\n")


    def setup_logger(self):

        logger = logging.getLogger('tradecenter')
        logger.setLevel(logging.DEBUG)
        logname = 'debug.log'
        formatter = logging.Formatter(style='{')

        fh = logging.FileHandler(logname)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)

        # TODO - Continue here



    def sign_in(self):
        '''Login to Upstox.'''
        #
        token_file = 'data.pkl'
        #
        token = ''
        client = None
        try:
            print_l('Loading previous credentials')
            with open(token_file, "rb") as f:
                token = pickle.load(f)
        except FileNotFoundError:
            print_l('Data file not found. Creating new file...')
            with open(token_file, "wb") as f:
                pass
        except EOFError:
            print_l('Data file empty. New credentials needed.')
        finally:
            if not token:
                return False

        try:
            client = Upstox(self.config['api_key'], token)
        except HTTPError as e:
            err = e.args[0]
            # Similar error messages for incorrect and expired token. 'Invalid'
            # is common word between them
            if 'Invalid':
                print('Invalid token entered')
            else:
                raise
        finally:
            if client is not None:
                print_l('Logged in successfully.')
                self.client = client
                return True
            return False


    def save_new_token(self, auth_code):
        if self.sesh is None:
            return False
        self.sesh.set_code(auth_code)
        print_l("Authenticating...")
        access_token = str(self.sesh.retrieve_access_token())
        access_time = datetime.now()
        print('Access token received')
        with open('data.pkl', 'wb') as f:
            pickle.dump(access_token, f)
            pickle.dump(access_time, f)
        return True


    def get_session_url(self):
        print(self.config)
        self.sesh = Session(self.config['api_key'])
        self.sesh.set_redirect_uri("https://upstox.com")
        self.sesh.set_api_secret(self.config['api_secret'])
        try:
            url = self.sesh.get_login_url()
            return url
        except HTTPError as e:
            # No errors encountered yet...
            print(e.args[0])
            return None


    def close_ops(self):
        'Unsubscribe from upstox scrips and closes other threads'
        print_s()
        print_l('Shutting Down')
        for sym, stock in self.stock_dict.items():
            self.client.unsubscribe(stock.instrument, LiveFeedType.Full)
        print_l('Shut Down Complete.')
        print_s()
        with self.condition:
            self.listening = False
            self.condition.notify_all()
