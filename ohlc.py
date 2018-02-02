import csv
from datetime import datetime, date
import os



class OHLC:
    fmt= '%Y-%m-%dT%H:%M:%S.%f%z'

    def __init__(self, epoch=0 , sym='0', ltp=0.0, atp=0.0, op=0.0, hi=0.0, lo=0.0, cl=0.0):
        "epoch: epoch in ms , sym:str, ltp:float, atp:float, op:float, hi:float, lo:float, cl:float"
        self.symbol = str(sym).upper()
        self.epoch = epoch
        self.ltp = ltp
        self.atp = atp
        self.op = op
        self.hi = hi
        self.lo = lo
        self.cl = cl


    def __str__(self):
        return "{t} | {s} | {l} | {a} | {o} | {c} | {h} | {w}".\
                format(t=self.timestamp,
                       s=self.symbol,
                       l=self.ltp,
                       a=self.atp,
                       o=self.op,
                       h=self.hi,
                       w=self.lo,
                       c=self.cl)

    @property
    def as_dict(self):
        return {'time':str(self.timestamp),
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

        (time_in_ISO, ltp, atp, high, low, open, close)
        Omits Symbol for ease of use with db storage methods'''
        return (str(self.timestamp), self.ltp,
                self.atp, self.op, self.hi, self.lo, self.cl)

    @classmethod
    def fromquote(cls, quote):
        return cls(int(quote['timestamp']),
                   str(quote['symbol']).upper(),
                   float(quote['ltp']),
                   float(quote['atp']),
                   float(quote['open']),
                   float(quote['high']),
                   float(quote['low']),
                   float(quote['close']))

    @property
    def timestamp(self):
        'Get epoch as local date-time in ISO'
        return datetime.fromtimestamp(self.epoch/1000.0).strftime(self.fmt)

    def fromISO(self, iso_time):
        'Set epoch from local date-time in ISO'
        fmt='%Y-%m-%dT%H:%M:%S.%f'
        self.epoch = datetime.strptime(iso_time, fmt).timestamp() * 1000.0

        
class OHLCLog:
    'Reads/Writes OHLC data in csv file. The symbol is used as the filename'
    def __init__(self, symbol=''):
        self.tod = date.today()
        self.csv_dict = {}
        
    def create_ohlc_file(self, symbol=None):
        if symbol == None:
            return
        filename = "OHLC-{}-{}.csv".format(symbol, tod.strftime("%d%b%y"))
        if os.path.exists('./'+self.filename) == False:
            with open(self.filename, 'w') as f:
                fields = ['time', 'symbol', 'ltp', 'atp',
                          'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
        self.csv_dict[symbol] = filename

    def logohlc(self, ohlc_dict):
        try:
            with open(self.csv_dict[ohlc.symbol], 'a') as f:
                fields = ['time', 'symbol', 'ltp', 'atp',
                          'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writerow(ohlc_data)
        except Exception as e:
            print("Error while adding OHLC record for", ohlc_data['symbol'])
            print(e)
            raise

    def readohlc(self, filename=None, numrows=0):
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

def test():
    log = OHLCLog()
    data = log.readohlc('NIFTY18FEB10800CEOHLC02Feb18.csv')
    print('Total records retrieved:', len(data))


if __name__ == '__main__':
    test()
