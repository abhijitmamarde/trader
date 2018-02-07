from datetime import datetime
from trader import *
from utils import load_config

config = None


class login_codes:
    success = 1
    fail = 0
    token_invalid = 2
    other = 3


def offline():
    ts = TradeCenter(config)
    ts.run(True)


def online():

    ym = '18FEB'
    stocks = []
    stocks.append(('NSE_FO', "NIFTY" + ym + str(11200) + 'CE'))
    stocks.append(('NSE_FO', "NIFTY" + ym + str(11000) + 'PE'))

    ts = TradeCenter(config)
    ts.run()


def main():
    global config
    config = load_config()
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



if __name__ == '__main__':
    main()
