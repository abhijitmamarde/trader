from datetime import datetime, timedelta
from gann import GannAngles
from ohlc import OHLC, OHLClog
import pickle
import requests
from requests.exceptions import HTTPError
from stockdb import StockDB, table_types
import time
from upstox_api.api import *
from utils import print_l, print_s, Actions, is_trade_active
from utils import TradeStrategy



class TradeCenter():

    def __init__(self, config=None):
        print_l("Initializing...")
        self.client = None
        self.condition = threading.Condition()
        self.indices = ['NSE_FO',]
        self.stock_dict = {}
        self.running = False
        self.trading = False
        self.ohlc_logger = OHLCLog()
        # init db in listen() for thread compatibility
        self.db = None

        if config is None:
            print_s()
            print_l('No config provided. Will be unable to sign in.')
        self.config = config

        self.quote_queue = []
        self.trade_queue = []
        self.order_queue = []


    def run(self, offline=False):
        '''Executes boilerplate
        
        Initiates listener for updates on a separate thread'''

        if self.config == None:
            print_s()
            print_l("No config provided. Unable to sign in.")
            return
        self.sign_in()
        self.register_masters()
        self.register_handlers()
        self.register_stocks()

        if offline:
            self.make_reports()
            return

        print_s()
        rep = input("Enable stock ordering?(y/n)")
        if rep.upper() == 'Y':
            self.trading = True
            print_l("Trading Enabled. Will place orders.")
        else:
            print_l("Trading Disabled. Listening only.")

        print_s()
        try:
            print_l('Opening Websocket to Upstox server')
            self.client.start_websocket(True)
        except Exception as e:
            print_l('Error while starting websocket - ')
            print_l(e.args[0])

        self.running = True
        listener = threading.Thread(target=self.listen)
        try:
            listener.start()
        except Exception as e:
            print_s()
            print_l('Unexexpted error')
            print_l(e)

            print_s()
        input("Press enter to close program\n")
        with self.condition:
            self.running = False
            self.condition.notify_all()


    def sign_in(self):
        '''Login to Upstox.'''
        #
        #
        token_file = 'data.pkl'
        #
        #
        print_s()
        token = ''
        access_time = ''
        try:
            print_l('Loading previous credentials')
            with open(token_file, "rb") as f:
                token = pickle.load(f)
                access_time =  pickle.load(f)
        except FileNotFoundError:
            print_l('Data file not found. Creating new file...')
            with open(token_file, "wb") as f:
                pass
        except EOFError:
            print_l('Data file empty. New credentials needed.')
            token = self.save_new_tokens(self.config['api_key'],
                                         self.config['api_secret'])

        print_s()
        print_l("Signing in to upstox-")

        max_tries = 5
        tries = 1
        client = None
        while tries <= max_tries:
            print_l('Attempt {}/{}'.format(tries, max_tries))
            try:
                client = Upstox(self.config['api_key'], token)
            except HTTPError as e:
                err = e.args[0]
                # Need to get new security token and keys
                if 'Invalid' in err and '401' in err:
                    print_s()
                    print_l("Credentials expired")
                    token = self.save_new_tokens(self.config['api_key'],
                                                 self.config['api_secret'])
                else:
                    raise
            except Exception as e:
                print_s()
                print_l("Unhandled Exception:")
                print_l(e.args[0])
                print_s()
            finally:
                if client is not None:
                    print_l('Logged in successfully.')
                    self.client = client
                    return
                tries += 1
        else:
            print_l("Unable to login to upstox. Quitting...")
            return None


    def save_new_tokens(self, key, secret):
        'Gets and saves new credentials fom Upstox server'
        print_l("New access token required")
        sesh = Session(key)
        sesh.set_redirect_uri("https://upstox.com")
        sesh.set_api_secret(secret)
        print("\nOpen below link to login to Upstox:\n")
        url = sesh.get_login_url()
        print(url)
        auth_code = input("\nPlease enter the code from URL: ")
        sesh.set_code(auth_code)
        print_l("Authenticating...")
        access_token = str(sesh.retrieve_access_token())
        access_time = datetime.now()
        print("Access token - {0} \nreceived at {1}".\
              format(access_token, access_time))
        with open('data.pkl', 'wb') as f:
            pickle.dump(access_token, f)
            pickle.dump(access_time, f)
        return access_token


    def listen(self):
        'Checks update queues and calls the required update method'
        #Extra sleep so main thread can finish print statements
        time.sleep(1.0)

        # DB init here for thread compatibility.
        self.db = StockDB()
        self.db.initialize('stock_db.sqlite')

        for key in self.stock_dict:
            if self.db.create_table(key, table_types.ohlc):
                print_l('Table verified for: '+ str(key))

        print_l('Receiving updates...')
        while self.running:
            try:
                with self.condition:
                    self.condition.wait()
                if len(self.quote_queue) > 0:
                    for q in self.quote_queue:
                        o = OHLC.fromquote(q)
                        self.db.add_data(q['symbol'], table_types.ohlc, o)
                        self.quote_update(q)
                        self.quote_queue.remove(q)
                    
                if len(self.order_queue) > 0:
                    self.order_update(self.order_queue.pop())
                if len(self.trade_queue) > 0:
                    self.trade_update(self.trade_queue.pop())
                time.sleep(0.2)
            except KeyboardInterrupt as e:
                self.running = False

            if not is_trade_active():
                self.running = False
        else:
            self.close_ops()


    def register_masters(self, masters=["nse_fo"]):
        'Boilerplate for adding exchanges to enable stock data subscriptions'
        try:
            print_s()
            print_l("Registering Indices")
            for ind in masters:
               print(len(self.client.get_master_contract(ind)))
            indices = masters
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


    def register_stocks(self):
        '''Subscribes to stocks for live feed.
        
        Additionally creates a logger for each stock subscribed in
        self.loggers[symbol]
        '''
        stocks = []
        insts = []
        ym = '18FEB'
        stocks.append(('NSE_FO', "NIFTY" + ym + str(10800) + 'CE'))
        stocks.append(('NSE_FO', "NIFTY" + ym + str(10900) + 'PE'))
        print_s()
        print_l('Registering stocks')
        print_s()
        print_l('Loading instruments...')
        for stock in stocks:
            try:
                insts.append(self.client.get_instrument_by_symbol(stock[0],
                                                                  stock[1]))
            except Exception as e:
                print(e)
        print_s()
        for inst in insts:
            try:
                print_l("Subscribing to {} - {}".format(inst.exchange,
                                                        inst.symbol))
                self.client.subscribe(inst, LiveFeedType.Full)
            except Exception as e:
                print(e)

        print_s()
        print_l('Setting up logger...')
        for inst in insts:
            # Create a OHLC logger for the stock
            sym = inst.symbol.upper()
            self.ohlc_logger.create_ohlc_file(sym)
            # Temporary stock addition
            self.stock_dict[sym] = GannAngles(inst)

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

        dat = OHLC.fromquote(message)
        self.ohlc_logger.logohlc(dat.as_dict)

        order = ''
        if not self.trading:
            print_l('Quote update received')
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
        "Saves the day's total trades and orders in a text file"
        orders = self.client.get_order_history()
        sorted_orders = []
        print_l("Generating order book")
        for order in orders:
            if order['product'] == 'D':
                continue
            if order['transaction_type'] == 'B':
                if order['status'] != 'rejected' and order['status'] != 'cancelled':
                    sorted_orders.append(order)
                    p_id = order['order_id']
                    for order in orders:
                        if order['parent_order_id'] == p_id and \
                           order['transaction_type'] == 'S':
                            sorted_orders.append(order)

        print_keys = [
        'symbol',
        'product',
        'order_type',
        'transaction_type',
        'status',
        'price',
        'trigger_price',
        'order_id',
        'parent_order_id',
        'exchange_time',
        ]
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


    def close_ops(self):
        print_s()
        print_l('Shutting Down')
        for sym, stock in self.stock_dict.items():
            self.client.unsubscribe(stock.instrument, LiveFeedType.Full)
        self.running = False
        print_l('Shut Down Complete.')
        print_s()

