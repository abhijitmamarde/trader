import time
import tkinter
import threading
from datetime import datetime
from trader import *
from gann import GannAngles
from utils import load_config, is_trade_active, round_off

RUNNING = False

def offline():
    config = load_config()
    center = TradeCenter()
    center.sign_in()
    masters = []
    ohlc_data = []
    for scrip in config['instruments']:
        if scrip[0] in masters:
            pass
        else:
            masters.append(scrip[0])
    center.load_masters(masters)

    orders = center._client.get_order_history()
    sorted_orders = []
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
            f.write("\n---------------------------------------------------------\n")

    trades = center._client.get_trade_book()
    with open('trades{}.txt'.format(dmy), 'w') as f:
        f.write('Trades Completed ----\n')
        for trade in trades:
            for key, val in trade.items():
                f.write("{} :: {}\n".format(key, val))
            f.write("\n-----------------\n")


def close_all(ts):
    c = threading.Condition()
    with c:
        c.wait()
    input('Press enter to close program at anytime.\n')
    global RUNNING
    RUNNING = False
    ts.close_ops()

def online():
    center = TradeCenter()
    if 1 > center.sign_in():
        print("Unable to sign in")
        return
    masters = []
    config = load_config()
    for scrip in config['instruments']:
        if scrip[0] in masters:
            pass
        else:
            masters.append(scrip[0])

    center.load_masters(masters)
    '''
    nifty_inst  = center._client.get_instrument_by_symbol('NSE_EQ', 'NIFTY')
    nifty       = center._client.get_live_feed(nifty_inst, LiveFeedType.Full)
    stocks      = []
    base = 0
    if is_trade_active():
        base = int(100 * (nifty['open'] // 100))
    else:
        base = int(100 * (nifty['close'] // 100))
    for x in range(-100, 100, 200):
        stocks.append(('NSE_FO', "NIFTY" + my + 11200 + 'CE'))
        stocks.append(('NSE_FO', "NIFTY" + my + 11000 + 'PE'))
    '''
    ym = '18FEB'
    stocks = []
    stocks.append(('NSE_FO', "NIFTY" + ym + str(11200) + 'CE'))
    stocks.append(('NSE_FO', "NIFTY" + ym + str(11000) + 'PE'))
    for stock in stocks:
        inst = center._client.get_instrument_by_symbol(stock[0], stock[1])
        stk = GannAngles(inst)
        if center.add_stock(stk, inst.symbol):
            print_l("Added {}".format(inst.symbol))
        else:
            print_l("Unable to add {}".format(inst.symbol))

    print_s()
    print("close thread starting")
    close_thread = threading.Thread(target=close_all, args=(center, ))
    close_thread.daemon = True
    close_thread.start()

    print("center listener starting")
    center.init_listener()
    center.start_listener()





def main():
    now = datetime.now()
    trade_end = datetime(year=now.year,
                           month=now.month,
                           day=now.day,
                           hour=15,
                           minute=30)

    if trade_end > now:
        online()
    else:
        offline()



if __name__=='__main__':
    main()
