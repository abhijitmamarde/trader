from datetime import datetime
import gspread
from ohlc import OHLC, OHLCLog
from oauth2client.service_account \
     import ServiceAccountCredentials as SAC
import pprint

scope = ['https://spreadsheets.google.com/feeds']
creds = SAC.from_json_keyfile_name('key.json', scope)
client = gspread.authorize(creds)
wb = client.open('upstox_data')
sheet = wb.sheet1

log = OHLCLog()
data = log.readohlc('NIFTY18FEB10800CEOHLC02Feb18.csv')

for item in data:
    print('adding', item)
    sheet.append_row(list(item.as_tuple))

print(sheet.row_count, "Rows in sheet")
