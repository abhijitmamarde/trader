from datetime import datetime, date
from collections import namedtuple
import re

DATE = date.today().strftime("%d%b%y")
TIMEFMT = '%d%b%y-%H:%M:%S.%f'

CONFIG_FILE = 'config.txt'
CONFIG_TYPES = ('instruments',)
CONFIG_TEXT = '''!This file is auto generated. Do not edit.
!Lines beginning with exclamation mark(!) will be ignored by the program
!General Format:
!param='value with space'
!param=value
!Each category's expected data is mentioned in it's first line
'''

Acts = namedtuple('Actions', 'none buy mod_target mod_sl')
Actions = Acts(0, 1, 2, 3)

def print_l(line):
    global DATE
    with open('log{}.txt'.format(DATE), 'a') as f:
        formatted = '[{}] {}'.format(datetime.now(), line)
        print(formatted)
        formatted = formatted + '\n'
        f.write(formatted)

def print_s(spacer=''):
    if spacer == 'IN':
        print_l("<<<<<<<<<<<<<<")
    elif spacer == 'OUT':
        print_l(">>>>>>>>>>>>>>")
    else:
        print_l("=============================")



def is_trade_active():
    now = datetime.now()
    start_time = datetime(year=now.year,
                            month=now.month,
                            day=now.day,
                            hour=9,
                            minute=15)

    end_time = datetime(year=now.year,
                            month=now.month,
                            day=now.day,
                            hour=15,
                            minute=31)
    if now > start_time and now < end_time:
        return True
    else:
        return False


def load_config():
    config = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if not(line[0] == '!' or len(line) < 1):
                    terms = line.split('=')
                    config[terms[0]]=terms[1][:-1]
    except FileNotFoundError:
        print("Config not found, creating template")
        f = open(CONFIG_FILE, 'w')
        for line in CONFIG_TEXT:
            f.write(line)
        for header in CONFIG_TYPES:
            f.write('-'+header.upper())
            f.write('-END')
        f.close()

    return config


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


def round_off(num, div=0.1):
    x = div*round(num/div)
    return float(x)

def test_utils():
    load_config()

if __name__ == '__main__':
    test_utils()
