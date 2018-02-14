from bunch import Bunch
import csv
from datetime import timedelta, datetime
from ohlc import OHLC, OHLCLog
import pickle
import sqlite3
from sqlite3 import OperationalError
import time

OHLC_TABLE_FIELDS = ({'name':'ts', 'type':'DATETIME'},
                     {'name':'ltp', 'type':'REAL'},
                     {'name':'atp', 'type':'REAL'},
                     {'name':'open', 'type':'REAL'},
                     {'name':'high', 'type':'REAL'},
                     {'name':'low', 'type':'REAL'},
                     {'name':'close', 'type':'REAL'})

TABLE_TYPES = Bunch(ohlc=0, orders=1)

class StockDB:
    sqlite_file = "trade_db.sqlite"
    conn = None
    cursor = None
    tables = []
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
            self.tables.append(r[0])

        self.initialized = True


    def create_table(self, tablename, tabletype):
        '''Will only create a table if it doesn't exist'''
        global OHLC_TABLE_FIELDS

        if tabletype == TABLE_TYPES['ohlc']:
            fields = OHLC_TABLE_FIELDS
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
            self.tables.append(tablename)
            return True
        return False


    def add_data(self, tablename, tabletype, data):
        '''Accepts an OHLC class object and inserts it to the database.
        
        Fails if table does not exist
        Returns True on success, False on fail
        '''
        if tabletype == TABLE_TYPES.ohlc:
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
                        {'t':data.localtime,
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

    def run_query(self, query=None):
        if query == None:
            return None
        try:
            with self.conn:
                self.cursor.execute(query)
                return self.cursor.fetchall()
        except sqlite3.OperationalError as e:
            if 'no such table' in e.args[0]:
                 print("Table does not exist")
        return None

    def summary(self):
        'Prints all tables with first 5 entries'
        for t in self.tables:
            print('First 5 records in', t)
            try:
                with self.conn:
                    self.cursor.execute('''SELECT * FROM {}'''.format(t))
                    records = self.cursor.fetchmany(5)
                    print([d[0] for d in self.cursor.description])
                for r in records:
                    print(r)
            except Exception as e:
                print(e)
                return

    def close(self):
        self.conn.close()

    def load_ohlc_from_csv(self, ohlc_csv_file):
        data = OHLCLog.readohlc(ohlc_csv_file)
        sym = data[0].symbol
        self.create_table(sym, TABLE_TYPES.ohlc)
        for item in data:
            self.add_data(sym, TABLE_TYPES.ohlc, item)


def db_test():
    db = StockDB()
    db.initialize(':memory:')
    db.summary()
    db.close()

if __name__ == '__main__':
    db_test()
