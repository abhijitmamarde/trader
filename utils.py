from datetime import datetime, date
from collections import namedtuple

DATE = date.today().strftime("%d%b%y")
TIMEFMT = '%d%b%y-%H:%M:%S.%f'

CONFIG_FILE = 'config.txt'
CONFIG_TYPES = ('instruments',)
CONFIG_TEXT = '''!Lines beginning with exclamation mark(!) will be ignored by the program
!General Format:
!-CATEGORY-
!-DATA-
!-DATA-
!-END-
!-NEXTCATEGORY-
!...
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
        print_l("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    elif spacer == 'OUT':
        print_l(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    else:
        print_l("=================================================================")



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
    setting = ''
    data = []
    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                if line[0] == '!':
                    pass
                else:
                    line.rstrip()
                    words = line.split()
                    if len(words) < 1:
                        print(words)
                    elif words[0][0] == '-':
                        if words[0][1:] == 'END':
                            config[setting.lower()] = data
                            setting = ''
                            data = []
                        else:
                            setting = words[0][1:]
                    else:
                        l = [i for i in words]
                        if len(l) > 1:
                            data.append(tuple(l))
                        elif len(l) == 1:
                            data = l.pop()
                        else:
                            pass
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


def round_off(num, div=0.1):
    x = div*round(num/div)
    return float(x)
