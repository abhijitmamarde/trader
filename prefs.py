import calendar
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from trader import TradeCenter
from utils import load_config, round_off
from upstox_api.api import LiveFeedType


''' Components to make an options/future symbol.

    Example:NSE_FO NIFTY18JAN10900CE
'''
contracts = ('NIFTY_50', 'NIFTYINFRA', 'NIFTYIT',
             'NIFTYPSE', 'BANKNIFTY', 'NIFTYMID50')

options = ('CE', 'PE')

thursdays = ('18JAN', '18FEB', '18MAR', '18APR', '18MAY', '18JUN',
             '18JUL', '18AUG', '18SEP', '18OCT', '18NOV', '18DEC',)

sym_dict = {'NIFTY_50': 'NIFTY', 'BANK_NIFTY': 'BANKNIFTY'}


def get_all_thursdays(year=2018):
    'Used to generate the dates for all Thursdays in the year given'
    thursdays = []
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
              'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    cal = calendar.Calendar()
    for x in range(1, 13):
        month = cal.monthdayscalendar(year, x)
        for week in month:
            if week[5] > 0:
                th = '0' + str(week[3]) if week[3] < 10 else str(week[3])
                thursdays.append(th + months[x - 1])
    with open('thu.txt', 'w') as f:
        pass
    for th in thursdays:
        print(th + " 2018")
        with open('thu.txt', 'a') as f:
            f.write(th + "\n")


class Configurator(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.ts = TradeCenter(load_config())
        self.ts.run()
        self.master = master
        self.resultstock = ''
        self.strike_prices = []

        self.grid()
        self.master.title('Trader configurator')

        # ==================================================
        # Create all frames
        # ==================================================

        # Provides fields for making the option symbol
        selector_frame = Frame(self, borderwidth=1,
                               relief='solid')
        selector_frame.grid(row=0, column=0, columnspan=2, rowspan=7,
                            padx=5, pady=5, sticky='ewns')

        # Display ohlc for the stock Symbol selected
        info_frame = Frame(self, borderwidth=1, relief='solid')
        info_frame.grid(row=0, column=2, columnspan=2, rowspan=7,
                        sticky='ewns', padx=5, pady=5)

        # Frame for displaying currently loaded scripts
        self.scrips_frame = Frame(self, borderwidth=1,
                                  relief='solid')
        self.scrips_frame.grid(row=0, column=4, columnspan=5, rowspan=7,
                               padx=5, pady=5, sticky='ewns')

        # ==================================================
        # Stock selector Frame
        # ==================================================
        for i in range(7):
            selector_frame.rowconfigure(i, pad=5)

        for i in range(3):
            selector_frame.columnconfigure(i, pad=5)

        title_label = Label(selector_frame, text='Select a stock:')
        title_label.grid(row=0, columnspan=2, sticky='ewns')

        global contracts
        self.sym_label = Label(selector_frame, text='Symbol')
        self.sym_label.grid(row=1, column=0, sticky='w')
        self.symbol_combo = Combobox(selector_frame, values=contracts,
                                     state='readonly', text='')
        self.symbol_combo.bind('<<ComboboxSelected>>', lambda event, self=self:
                               self.select_symbol(event))
        self.symbol_combo.grid(row=1, column=1)

        global thursdays
        self.date_label = Label(selector_frame, text='Date')
        self.date_label.grid(row=2, column=0, sticky='w')
        self.dates_combo = Combobox(selector_frame, values=thursdays,
                                    state='readonly', text='')
        self.dates_combo.bind('<<ComboboxSelected>>', lambda event, self=self:
                              self.select_date(event))
        self.dates_combo.grid(row=2, column=1)

        self.price_label = Label(selector_frame, text='Strike Price')
        self.price_label.grid(row=3, column=0, sticky='w')
        self.price_combo = Combobox(selector_frame, text='No Symbol', values=[], state='readonly')
        self.price_combo.bind('<<ComboboxSelected>>', lambda event, self=self:
                              self.select_price(event))
        self.price_combo.grid(row=3, column=1)

        self.option_label = Label(selector_frame, text='Option')
        self.option_label.grid(row=4, column=0, sticky='w')
        self.option_combo = Combobox(selector_frame, values=('CE', 'PE'),
                                     state='readonly', text='')
        self.option_combo.bind('<<ComboboxSelected>>', lambda event, self=self:
                               self.select_option(event))
        self.option_combo.grid(row=4, column=1)

        self.label1 = Label(selector_frame, text='Current Selection:')
        self.label1.grid(row=5, column=0, sticky='w')
        self.result_label = Label(selector_frame, text='Nothing Selected')
        self.result_label.grid(padx=5, row=5, column=1)

        self.clear_button = Button(selector_frame, text='Clear all',
                                   command=self.clear_all)
        self.clear_button.grid(row=6, column=0, sticky='ewns', padx=5, pady=10)

        self.add_button = Button(selector_frame, text='Add scrip',
                                 command=self.add_stock)
        self.add_button.grid(row=6, column=1, sticky='ewns', padx=5, pady=10)

        # ==================================================
        # Current symbol info
        # ==================================================
        for i in range(8):
            selector_frame.rowconfigure(i, pad=5)

        for i in range(3):
            selector_frame.columnconfigure(i, pad=5)

        info_header_label = Label(info_frame, text='Stock info')
        info_header_label.grid(row=0, sticky='ewns')

        info_symbol_label = Label(info_frame, text='Symbol')
        info_symbol_label.grid(row=1, column=0, sticky='e')
        self.info_symbol = Label(info_frame, text='None selected')
        self.info_symbol.grid(row=1, column=1, sticky='', padx=10)

        info_ltp_label = Label(info_frame, text='LTP :')
        info_ltp_label.grid(row=2, column=0, sticky='e')
        self.info_ltp = Label(info_frame, text='')
        self.info_ltp.grid(row=2, column=1, sticky='w')

        info_open_label = Label(info_frame, text='Open :')
        info_open_label.grid(row=3, column=0, sticky='e')
        self.info_open = Label(info_frame, text='')
        self.info_open.grid(row=3, column=1, sticky='w')

        info_high_label = Label(info_frame, text='High :')
        info_high_label.grid(row=4, column=0, sticky='e')
        self.info_high = Label(info_frame, text='')
        self.info_high.grid(row=4, column=1, sticky='w')

        info_low_label = Label(info_frame, text='Low :')
        info_low_label.grid(row=5, column=0, sticky='e')
        self.info_low = Label(info_frame, text='')
        self.info_low.grid(row=5, column=1, sticky='w')

        info_close_label = Label(info_frame, text='Close :')
        info_close_label.grid(row=6, column=0, sticky='e')
        self.info_close = Label(info_frame, text='')
        self.info_close.grid(row=6, column=1, sticky='w')

        # ==================================================
        # Selected scrips Frame
        # ==================================================
        for i in range(7):
            self.scrips_frame.rowconfigure(i, pad=20)

        for i in range(3):
            self.scrips_frame.columnconfigure(i, pad=5)
        self.stock_label = Label(self.scrips_frame, text='Currently Selected:')
        self.stock_label.grid(columnspan=5)
        self.stock_list = Listbox(self.scrips_frame, height=8)
        self.stock_list.grid(row=1, columnspan=2, rowspan=3,
                             sticky='ewns', padx=5, pady=5)
        remove_scrip_button = Button(self.scrips_frame, text='Remove selected',
                                     command=lambda self=self:
                                     self.stock_list.delete(ANCHOR))
        remove_scrip_button.grid(row=4, columnspan=2, sticky='ewns', padx=5, pady=5)
        remove_all_button = Button(self.scrips_frame, text='Remove all',
                                   command=lambda self=self:
                                   self.stock_list.delete(0, END))
        remove_all_button.grid(row=5, columnspan=2, sticky='ewns', padx=5, pady=5)

        # ==================================================
        # App buttons
        # ==================================================
        self.start_button = Button(self, text='Start Upstox client',
                                   command=self.ts.start_listener)
        self.start_button.grid(padx=4, pady=4, row=10, column=0, sticky='ewns')

        self.quit_button = Button(self, text='quit', command=self.close_app)
        self.quit_button.grid(padx=4, pady=4, row=10, column=1, sticky='ewns')

        self.enable_trading = Checkbutton(self, text='Enable trading',
                                          variable=self.ts.trading)
        self.enable_trading.grid(padx=4, pady=4, row=10, column=2,
                                 columnspan=2, sticky='ewns')


    def center_window(self):
        w = 800
        h = 800
        sw = self.master.winfo_screenwidth()
        sh = self.master.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2

        self.master.geometry('{}x{}+{}+{}'.format(w, h, x, y))

    def select_symbol(self, event):
        'Get usable strike prices for the symbol provided'
        inst = None
        feed = None
        exch = 'NSE_INDEX'
        global sym_dict
        choice = self.symbol_combo.get()
        sym = sym_dict[choice]
        try:
            inst = self.ts.client.get_instrument_by_symbol(exch, choice)
        except Exception as e:
            print('Unable to load the instrument ' + choice)

        try:
            feed = self.ts.client.get_live_feed(inst, LiveFeedType.Full)
        except Exception as e:
            print('unable to get live feed for' + sym)


        bp = round_off(feed['ltp'], 100)
        strike_prices = []

        mult = 100
        for x in range(-5, 5):
            sp = int(bp + (x * mult))
            strike_prices.append(str(sp))

        self.price_combo['text'] = str(bp)
        self.price_combo['values'] = strike_prices

        self.result_label['text'] = sym.upper() \
            + self.dates_combo.get() \
            + self.price_combo.get()\
            + self.option_combo.get()
        self.set_info(feed)

    def select_date(self, event):
        'Sets the expiry date of the symbol'
        global sym_dict
        dt = self.dates_combo.get()
        r = sym_dict[self.symbol_combo.get().upper()] \
            + dt \
            + self.price_combo.get()\
            + self.option_combo.get()
        print(r)
        self.result_label['text'] = str(r)

    def select_price(self, event):
        '''Sets the strike price.
        
        Values calculated and set by select_symbol method.'''
        global sym_dict
        price = self.price_combo.get()
        self.result_label['text'] = sym_dict[self.symbol_combo.get().upper()]  \
            + self.dates_combo.get() \
            + str(price) \
            + self.option_combo.get()

    def select_option(self, event):
        global sym_dict
        opt = self.option_combo.get()
        self.result_label['text'] = sym_dict[self.symbol_combo.get().upper()] \
            + self.dates_combo.get() \
            + self.price_combo.get()\
            + opt

    def clear_all(self):
        self.symbol_combo.set('')
        self.dates_combo.set('')
        self.price_combo['values'] = []
        self.option_combo.set('')
        self.result_label['text'] = ''

    def add_stock(self):
        txt = self.result_label['text']
        cur_list = self.stock_list.get(0, END)
        if txt not in cur_list:
            self.stock_list.insert(END, str(txt))
            self.ts.register_stocks(txt)
        else:
            messagebox.showerror('Error',
                                 '{} is already in loading list'.
                                 format(txt))

    def remove_stock(self, stock_name):
        sym = self.stock_list.get(ANCHOR)
        self.stock_list.delete(ANCHOR)
        self.ts.remove_stocks(sym)
    
    def remove_all(self):
        syms = self.stock_list.get(0, END)
        self.stock_list.delete(0, END)
        for s in syms:
            self.ts.remove_stock(s)

    def set_info(self, feed=None):
        if feed is None:
            return
        print(feed)
        self.info_symbol['text'] = feed['symbol']
        self.info_ltp['text'] = feed['ltp']
        self.info_open['text'] = feed['open']
        self.info_high['text'] = feed['high']
        self.info_low['text'] = feed['low']
        self.info_close['text'] = feed['close']

    def close_app(self):
        self.ts.close_ops()
        exit()


def main():
    root = Tk()
    root.option_add('*Font', 'arial 12')
    app = Configurator(root)
    app.center_window()
    root.mainloop()


if __name__ == '__main__':
    main()
