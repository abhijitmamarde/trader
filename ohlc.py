from datetime import datetime

class OHLC:
    def __init__(self, timestamp=0 , sym='0', ltp=0.0, atp=0.0, op=0.0, hi=0.0, lo=0.0, cl=0.0):
        "timestamp: epochtime , sym:str, ltp:float, atp:float, op:float, hi:float, lo:float, cl:float"
        self.symbol = sym
        self.epoch = timestamp/1000
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

    def as_dict(self):
        return {'time':str(self.timestamp),
                'symbol':self.symbol,
                'ltp':self.ltp,
                'atp':self.atp,
                'open':self.op,
                'high':self.hi,
                'low':self.lo,
                'close':self.cl}

    @classmethod
    def fromquote(cls, quote):
        return cls( int(quote['timestamp']),
                   quote['symbol'],
                   float(quote['ltp']),
                   float(quote['atp']),
                   float(quote['open']),
                   float(quote['high']),
                   float(quote['low']),
                   float(quote['close']))

    @property
    def timestamp(self):
        'Get epoch as local date-time'
        fmt='%Y-%m-%d %H:%M:%S'
        return datetime.fromtimestamp(self.epoch).strftime(fmt)
