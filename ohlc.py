import csv
from datetime import datetime, date, timezone
import os



class OHLC:
    'For storing stock/derivative OHLC + ltp/atp'
    fmt= '%Y-%m-%d %H:%M:%S'
    def __init__(self, epoch=0 , sym='0', ltp=0.0, atp=0.0, op=0.0, hi=0.0, lo=0.0, cl=0.0):
        'Use fromquote() class method for easier creation.'
        self.symbol = str(sym).upper()
        if len(str(epoch)) > 12:
            self.epoch = epoch/1000
        else:
            self.epoch = epoch
        self.ltp = ltp
        self.atp = atp
        self.op = op
        self.hi = hi
        self.lo = lo
        self.cl = cl


    def __str__(self):
        return "{t} | {s} | {l} | {a} | {o} | {c} | {h} | {w}".\
                format(t=self.localtime,
                       s=self.symbol,
                       l=self.ltp,
                       a=self.atp,
                       o=self.op,
                       h=self.hi,
                       w=self.lo,
                       c=self.cl)

    @property
    def as_dict(self):
        return {'time':self.epoch,
                'symbol':self.symbol,
                'ltp':self.ltp,
                'atp':self.atp,
                'open':self.op,
                'high':self.hi,
                'low':self.lo,
                'close':self.cl}

    @property
    def as_tuple(self):
        '''Returns a tuple in

        (epoch, ltp, atp, high, low, open, close)
        Omits Symbol for ease of use with db storage methods'''
        return (self.epoch, self.ltp,
                self.atp, self.op, self.hi, self.lo, self.cl)

    @classmethod
    def fromquote(cls, quote):
        # Quote timestamps received in ms.
        return cls(int(quote['timestamp']/1000),
                   str(quote['symbol']).upper(),
                   float(quote['ltp']),
                   float(quote['atp']),
                   float(quote['open']),
                   float(quote['high']),
                   float(quote['low']),
                   float(quote['close']))

    @property
    def localtime(self):
        'Get epoch as local date-time in ISO'
        ts = datetime.fromtimestamp(self.epoch).strftime(self.fmt)
        return str(ts[:22])

    def fromISO(self, iso_time):
        '''Set epoch from time format =  %Y-%m-%dT%H:%M:%S'''
        fmt='%Y-%m-%dT%H:%M:%S'
        self.epoch = datetime.strptime(iso_time, fmt).timestamp()


class OHLCLog:
    ''' DEPRECATED in favor of python's logging.

    Use TradeCenter.init_logging() instead.
    Reads/Writes OHLC data in csv file.
    The symbol is used as the filename'''

    def __init__(self, symbol=''):
        self.tod = date.today()
        self.csv_dict = {}
        self.TS = 0
        self.ISO = 1


    def create_ohlc_file(self, symbol=None):
        if symbol == None:
            return
        filename = "OHLC-{}-{}.csv".format(symbol, self.tod.strftime("%d%b%y"))
        if os.path.exists('./'+filename) == False:
            with open(filename, 'w') as f:
                fields = ['time', 'symbol', 'ltp', 'atp',
                          'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
        self.csv_dict[symbol] = filename


    def logohlc(self, ohlc_dict):
        try:
            with open(self.csv_dict[ohlc_dict['symbol']], 'a') as f:
                fields = ['time', 'symbol', 'ltp', 'atp',
                          'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writerow(ohlc_dict)
        except Exception as e:
            print("Error while adding OHLC record for", ohlc_dict['symbol'])
            print(e)
            raise


    @classmethod
    def readohlc(self, filename=None, numrows=0, tf=0):
        'Returns specified number of rows from filename.csv as a list of OHLC objects'
        data = []
        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                ctr = 0
                for row in reader:
                    if len(row) < 1:
                        continue
                    if ctr >= numrows and numrows > 0:
                        return data
                    o = OHLC()
                    o.fromISO(row['time'])
                    o.symbol = row['symbol']
                    o.ltp = row['ltp']
                    o.atp = row['atp']
                    o.op = row['open']
                    o.hi = row['high']
                    o.lp = row['low']
                    o.cl = row['close']
                    data.append(o)
                    if numrows > 0:
                        ctr += 1
        except FileNotFoundError as e:
            print("ERROR - {} File not found! ".format(filename))
            print("\tPlease ensure filename is correct and")
            print("\tincludes the extension as well (*.csv)")
        finally:
            return data


def test_ohlc():
    test_quote = {'bids': [{'orders': 2, 'price': 97.5, 'quantity': 150},],
        'high': 111.85,
        'asks': [{'orders': 2, 'price': 97.75, 'quantity': 225}],
        'vtt': 3107850.0,
        'open': 100.0,
        'timestamp': '1517377333560',
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
        'instrument': None,
        'close': 115.75,
        'ltt': 1517377332000,
        'total_sell_qty': 221775,
        'atp': 103.58}
    data = OHLC.fromquote(test_quote)
    print("As dict\n", data.as_dict)
    print("As tuple\n", data.as_tuple)
    print("Time in ISO Format\n", data.localtime)
    print("Time in epoch\n", data.epoch)
    print(datetime.fromtimestamp(data.epoch, tz=timezone.utc))
    print("__str__ \n", data)


if __name__ == '__main__':
    test_ohlc()
