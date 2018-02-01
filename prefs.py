import calendar
from tkinter import *

#NSE_FO NIFTY18JAN10900CE
contracts = ('NIFTY', 'NIFTYINFRA', 'NIFTYIT',
             'NIFTYPSE', 'BANKNIFTY', 'NIFTYMID50')
months = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
          'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')
options = ('CE', 'PE')

thursdays=(
'06JAN', '13JAN', '20JAN', '27JAN', '03FEB',
'10FEB', '17FEB', '24FEB', '03MAR', '10MAR',
'17MAR', '24MAR', '31MAR', '07APR', '14APR',
'21APR', '28APR', '05MAY', '12MAY', '19MAY',
'26MAY', '02JUN', '09JUN', '16JUN', '23JUN',
'30JUN', '07JUL', '14JUL', '21JUL', '28JUL',
'04AUG', '11AUG', '18AUG', '25AUG', '01SEP',
'08SEP', '15SEP', '22SEP', '29SEP', '06OCT',
'13OCT', '20OCT', '27OCT', '03NOV', '10NOV',
'17NOV', '24NOV', '01DEC', '08DEC', '15DEC',
'22DEC', '29DEC')


def get_all_thursdays(year=2018):
    global thursdays
    cal = calendar.Calendar()
    for x in range(1, 13):
        month = cal.monthdayscalendar(year, x)
        for week in month:
            if week[5] > 0:
                th = '0'+str(week[5]) if week[5] < 10 else str(week[5])
                thursdays.append(th+months[x-1])
    with open('thu.txt', 'w') as f:
        pass
    for th in thursdays:
        print(th+" 2018")
        with open('thu.txt', 'a') as f:
            f.write(th+"\n")

class GUI(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master)

        self.master = master
