import os
import csv
from datetime import date


class OHLCLog():
    def __init__(self):
        tod = date.today()
        self.filename = "OHLC{}.csv".format(tod.strftime("%d%b%y"))
        if os.path.exists('./'+self.filename) == False:
            with open(self.filename, 'w') as f:
                fields = ['time', 'symbol', 'LTP', 'ATP', 'open', 'high', 'low', 'close']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

    def logOHLC(self, symbol, ohlc_data):
        with open(self.filename, 'a') as f:
            fields = ['time', 'symbol', 'LTP', 'ATP', 'open', 'high', 'low', 'close']
            ohlc_data['symbol'] = symbol
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writerow(ohlc_data)
