from datetime import datetime, timedelta
from ohlc import OHLC
from OHLClogger import OHLCLog
import pickle
import requests
from requests.exceptions import HTTPError
import time
from upstox_api.api import *
from utils import print_l, print_s, Actions



class TradeCenter():

    def __init__(self):
        print_l("Initializing...")

        self._api_key = "sMc8FkcUOEm1n3zCooll9QZ3WMQHFgT7lLD4jihf"
        self._api_secret = "60s6wviia5"
        self._access_time= None
        self._access_token = ''
        self._token_file = "data.pkl"
        self._client = None

        self.condition = threading.Condition()
        self.indices = ['NSE_FO',]
        self.stock_dict = {}
        self.logger = OHLCLog()
        self.stockDB = StockDB()
        self.stockDB.initialize()
        self.OHLCqueue = []
        self.running = False
        self.trading = False

        self.quote_queue = []
        self.trade_queue = []
        self.order_queue = []

        try:
            with open(self._token_file, "rb") as f:
                self._access_token, self._access_time = pickle.load(f)
        except FileNotFoundError:
            self._access_token = None
            with open(self._token_file, "wb") as f:
                pass
        except EOFError:
            self._access_token = None


    def sign_in(self):
        '''Uses pickled tokens to sign in to server. May require user action.
           
           Requires new credentials every 24 hours. Unreliable error message
           formatting means the program will fail due to some or the other type
           of error.
           Returns-
           > 1 on successful login
           > 0 on failure to login
           > -1 for uncaptured error
        '''
        if self._client is not None:
            print("Already Logged in")
            return -1

        if self._access_token is None:
            self.get_new_tokens()

        try:
            self._client = Upstox(self._api_key, self._access_token)
        except HTTPError as e:
            err = e.args[0]
            print(err)
            # Need to get new security token and keys
            if 'Invalid' in err and '401' in err:
                self.get_new_tokens()
                return self.sign_in()
            else:
                raise
        except Exception as e:
            print_s()
            print_l("Unhandled Exception:")
            print_l(repr(e))
            print_s()
            return -1
        else:
            if self._client is not None:
                print_l("Signed in.")
                return 1
            else:
                print_l("Failed to Sign in. Please try again later")
                return 0
            print_s()


    def get_new_tokens(self):
        print_l("New access token required")
        sesh = Session(self._api_key)
        sesh.set_redirect_uri("https://upstox.com")
        sesh.set_api_secret(self._api_secret)
        print("\nOpen below link to login to Upstox:\n")
        url = sesh.get_login_url()
        print(url)
        auth_code = input("\nPlease enter the code from URL: ")
        sesh.set_code(auth_code)
        print_l("Authenticating...")
        self._access_token = str(sesh.retrieve_access_token())
        self._access_time = datetime.now()
        print("Access token - {0} \nreceived at {1}".\
              format(self._access_token, self._access_time))
        with open(self._token_file, 'wb') as f:
                    pickle.dump([self._access_token, self._access_time], f)


    def load_masters(self, masters):
        try:
            print_l("Loading Indices")
            for ind in masters:
                self._client.get_master_contract(ind)
            print_l('Indices loaded:')
            print_l(self._client.enabled_exchanges)
            self.indices = masters
            self._client.set_on_quote_update(self.quote_handler)
            self._client.set_on_order_update(self.order_handler)
            self._client.set_on_trade_update(self.trade_handler)
        except AttributeError:
            print_l("Masters preloaded/no valid masters provided")


    def add_stock(self, stock, symbol):
        try:
            self._client.subscribe(stock.instrument, LiveFeedType.Full)
        except HTTPError as e:
            # Already subscribed, resubscribing as fail-safe
            self._client.unsubscribe(stock.instrument, LiveFeedType.Full)
            self._client.subscribe(stock.instrument, LiveFeedType.Full)

        symbol = symbol.upper()
        self.stock_dict[symbol] = stock
        return True

    def init_listener(self):
        print_s()
        with self.condition :
            rep = input("Enable stock ordering?(y/n)")
            if rep.upper() == 'Y':
                self.trading = True
                print_s()
                print_l("Trading Enabled. Will place orders.")
            else:
                print_s()
                print_l("Trading Disabled. Listening only.")
            self.condition.notifyAll()

        self._client.start_websocket(True)
        self.running = True
        print_l("Receiving live feed updates")
        print_l("Press Ctrl+C to close program")
        print_s()

    def start_listener(self):
        while self.running:
            try:
                with self.condition:
                    self.condition.wait()
                if len(self.quote_queue) > 0:
                    self.quote_update(self.quote_queue.pop())
                if len(self.order_queue) > 0:
                    self.order_update(self.order_queue.pop())
                if len(self.trade_queue) > 0:
                    self.trade_update(self.trade_queue.pop())
                time.sleep(0.3)
            except KeyboardInterrupt:
                close_ops()
                return
            if not is_trade_active():
                close_ops()
                return


    def quote_handler(self, message):
        '''Addes message to queue for processing.
        '''
        with self.condition:
            self.quote_queue.append(message)
            self.condition.notify_all()


    def order_handler(self, message):
        '''Addes message to queue for processing.
        '''
        with self.condition:
            self.order_queue.append(message)
            self.condition.notify_all()

    def trade_handler(self, message):
        '''Addes message to queue for processing.
        '''
        with self.condition:
            self.trade_queue.append(message)
            self.condition.notify_all()

    def quote_update(self, message):
        '''Processes quotes from the queue.
        
        Implemented this way to keep function executions client-side as
        server(Upstox) executions do not give full debugging info.
        Message format:
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
        dat = OHLC.fromquote(message)
        order = ''
        try:
            if self.trading:
                action, args = self.stock_dict[sym].quote_update(message)
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
                    order = self._client.place_order(*args)
                    print_s('IN')
                    print_l('Response on place_order() - ')
                    print_l('Object of type - {}.'.format(type(order)))
                    print_l(order)
                    print_s('IN')
                elif action == Actions.mod_sl and args is not None:
                    print_s('OUT')
                    print_l("{} - modifying stoploss order".format(sym))
                    print_l("order_id = {}".format(args[0]))
                    order = self._client.modify_order(order_id=args[0],
                                                      trigger_price=args[1])
                if len(order) > 0:
                    print_s('IN')
                    print_l('Response on place_order() - ')
                    print_l('Object of type - {}.'.format(type(order)))
                    print_l(order)
                    print_s('IN')
        except Exception as e:
            print(e)


    def order_update(self, message):
        '''Processes orders from the queue.
        
        Implemented this way to keep function executions client-side as
        server(Upstox) executions do not give full debugging info.
        '''
        print("in order_update_handler")
        sym = message['symbol'].upper()
        try:
            self.stock_dict[sym].order_update(message)
            '''
        except KeyError as e:
            print_s('IN')
            print_l('Order info:')
            for key in message:
                print_l(message[key])
            print_s('IN')
            '''
        except Exception as e:
            print("Error in order_update_handler:")
            print(e)


    def trade_update(self, message):
        '''Processes trades from the queue.
        
        Implemented this way to keep function executions client-side as
        server(Upstox) executions do not give full debugging info.
        '''
        print("in trade_update_handler")
        sym = message['symbol'].upper()
        try:
            self.stock_dict[sym].order_update(message)
            '''
        except KeyError as e:
            print_s('IN')
            print_l('Trade info:')
            for key in message:
                print_l(message[key])
            print_s('IN')
            '''
        except Exception as e:
            print("Error in trade_update_handler:")
            print(e)


    def close_ops(self):
        print_s()
        print_l('Shutting Down')
        for sym, stock in self.stock_dict.items():
            self._client.unsubscribe(stock.instrument, LiveFeedType.Full)
        self.running = False
        with self.condition:
            self.condition.notifyAll()
        print_l('Shut Down Complete.')
        print_s()


class TradeStrategy():

    def __init__(self, inst):
        self.instrument = inst
        instrument = None
        orders = []
        trades = []
        start_time = datetime.now()
        last_update = None
        verbose = False

    def quote_update(self, quote_info):
        return Actions.none, None

    def order_update(self, order_info):
        return Actions.none, None

    def trade_update(self, trade_info):
        return Actions.none, None


