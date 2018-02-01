import os
import csv
from datetime import date


class OHLCLog():
    def __init__(self, symbol=''):
        tod = date.today()
        self.filename = "{}OHLC{}.csv".format(symbol, tod.strftime("%d%b%y"))
        if os.path.exists('./'+self.filename) == False:
            with open(self.filename, 'w') as f:
                fields = ['time', 'symbol', 'ltp', 'atp', 'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

    def logOHLC(self, ohlc_data):
        with open(self.filename, 'a') as f:
            fields = ['time', 'symbol', 'ltp', 'atp', 'open', 'high', 'low', 'close']
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(ohlc_data)
