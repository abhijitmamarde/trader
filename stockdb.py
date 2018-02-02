from bunch import Bunch
import csv
from datetime import timedelta, datetime
from ohlc import OHLC
import pickle
import sqlite3
from sqlite3 import OperationalError
import time

ohlc_table_fields = ({'name':'ts', 'type':'DATE'},
                     {'name':'ltp', 'type':'REAL'},
                     {'name':'atp', 'type':'REAL'},
                     {'name':'open', 'type':'REAL'},
                     {'name':'high', 'type':'REAL'},
                     {'name':'low', 'type':'REAL'},
                     {'name':'close', 'type':'REAL'})

table_types = Bunch(ohlc=0, open_orders=1)

class StockDB:
    sqlite_file = "trade_db.sqlite"
    conn = None
    cursor = None
    tables_made = []
    initialized = False


    def initialize(self, db_name=None):
        "Connects to or creates the sqlite DB"
        if db_name is not None:
            self.sqlite_file = db_name
        self.conn = sqlite3.connect(self.sqlite_file)
        self.cursor = self.conn.cursor()
        try:
            with self.conn:
                self.cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
        except Exception as e:
            print("Error in StockDB.initialize")
            print(e)

        result = self.cursor.fetchall()
        for r in result:
            self.tables_made.append(r[0])

        self.initialized = True


    def create_table(self, tablename, tabletype):
        global ohlc_table_fields

        if tabletype == table_types['ohlc']:
            fields = ohlc_table_fields
        else:
            return False

        if len(tablename) < 3:
            return False

        if self.table_exists(tablename):
            return True
        with self.conn:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS {tn}
                                    ('{nf}' {ft})'''.\
                                format(tn=tablename,
                                       nf=fields[0]['name'],
                                       ft=fields[0]['type']))

        for col in fields[1:]:
            with self.conn:
                self.cursor.execute('''ALTER TABLE {tn} ADD COLUMN
                                    '{cn}' {ct}'''.format(tn=tablename,
                                                          cn=col['name'],
                                                          ct=col['type']))

        if self.table_exists(tablename):
            self.tables_made.append({tablename:tabletype})
            return True
        return False


    def add_data(self, tablename, tabletype, data):
        '''Accepts an OHLC class object and inserts it to the database.
        
        Fails if table does not exist
        Returns True on success, False on fail
        '''
        if tabletype == table_types.ohlc:
            try:
                with self.conn:
                    self.cursor.execute(
                        '''INSERT INTO {tn} VALUES
                        (:t,
                        :l,
                        :a,
                        :op,
                        :hi,
                        :lo,
                        :cl)'''.format(tn=tablename), \
                        {'t':data.timestamp,
                         'l':data.ltp,
                         'a':data.atp,
                         'op':data.op,
                         'hi':data.hi,
                         'lo':data.lo,
                         'cl':data.cl})
            except sqlite3.OperationalError as e:
                print(e)
                return False
            return True
        return False


    def table_exists(self, table_name):
        '''Returns True if table_name exists in DB. will not check fields'''
        try:
            with self.conn:
                self.cursor.execute('SELECT * FROM {}'.format(table_name))
        except sqlite3.OperationalError as e:
            if 'no such table' in e.args[0]:
                return False

        return True


    def summary(self):
        'Prints list of all tables with basic info about them'
        print('summary')
        print(self.tables_made)
        for t in self.tables_made:
            try:
                with self.conn:
                    self.cursor.execute('''SELECT * FROM {}'''.format(t))
                    records = self.cursor.fetchmany(2)
                for r in records:
                    print(r)
            except Exception as e:
                print(e)
                return

    def close(self):
        self.conn.close()


def csv_to_db():
    db = StockDB()
    db.initialize()
    print("creating tables")
    dat = {}
    names = []
    ohlc_names = ['OHLC24JAN18.csv',
                  'OHLC25JAN18.csv']

    start_time = datetime.now()
    ctr = 0
    for fname in ohlc_names:
        with open(fname, 'r') as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            headers = next(readCSV)
            for row in readCSV:
                if len(row)<1:
                    continue
                if row[1] not in names:
                    names.append(row[1])
                    dat[row[1]] = []
                tmp = OHLC(*row)
                tmp.timestamp = fname[4:11]+'-'+tmp.timestamp
                dat[row[1]].append(tmp)
                ctr += 1
    print("Loaded {} records for {} stocks.".format(len(dat), len(names)))
    print("Adding to DB")

    for name in names:
        print("Creating table for {}".format(name))
        db.create_ohlc_table(name)
    for key in dat:
        print("Inserting records for {}".format(key))
        for obj in dat[key]:
            db.add_ohlc(obj)
            ctr +=1
        diff = int((datetime.now() - start_time).total_seconds())
        print("Added {} records to {} in {} seconds".format(ctr, key, diff))
        input("Press Enter to continue")
        ctr = 0
        start_time = datetime.now()

    db.close()


def db_test():
    db = StockDB()
    db.initialize(':memory:')
    with open('samples.pkl', 'rb') as f:
        quote = pickle.load(f)
    data = OHLC.fromquote(quote)
    db.summary()

if __name__ == '__main__':
    db_test()
