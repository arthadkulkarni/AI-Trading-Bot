#import required libraries
import numpy as np
from AlgorithmImports import *

class TradingBot(QCAlgorithm):

    def initialize(self):
        #amount of money used to test
        self.SetCash(100000)

        #testing start and end dates
        self.SetStartDate(2020, 9, 1)
        self.SetEndDate(2024, 5, 28)

        #testing symbol
        self.symbol = self.AddEquity("SPY", Resolution.Daily).symbol

        self.lookback = 20

        self.ceiling = 30
        self.floor = 10

        #for stop loss
        self.initialStopRisk = 0.96
        self.trailingStopRisk = 0.9

        #schedules when to run
        self.schedule.on(self.DateRules.EveryDay(self.symbol), self.TimeRules.AfterMarketOpen(self.symbol, 30), Action(self.EveryMarketOpen))

    #decides what to do with new data
    def on_data(self, data: Slice):
        self.Plot("Data Chart", self.symbol, self.securities[self.symbol].close)
    

    def EveryMarketOpen(self):
        #looks at volatily in the past 30 days
        close = self.History(self.symbol, 31, Resolution.Daily)["close"]
        #takes standard deviations
        todayvolatility = np.std(close[1:31])
        yesterdayvolatilit = np.std(close[0:30])
        deltavol = (todayvolatility - yesterdayvolatility) / todayvolatility
        self.lookback = round(self.lookback * (1 + deltavol))

        #make sure lookback is within the set ceiling and floor
        if self.lookback > self.ceiling:
            self.lookback = self.ceiling
        elif self.lookback < self.floor:
            self.lookback = self.floor
        
        #check for breakout
        self.high = self.History(self.symbol, self.lookback, Resolution.DAILY)["high"]
        
        #make sure we are not already invested and if there is a breakout
        if not self.securities[self.symbol].Invested and self.securities[self.symbol].Close >= max(self.high[:-1]):
            self.SetHoldings(self.symbol, 1)
            self.breakoutlvl = max(self.high[:-1])
            self.highestPrice = self.breakoutlvl

        #if there is an open position
        if self.securities[self.symbol].invested:
            #set stop loss order
            if not self.transactions.GetOpenOrders(self.symbol):
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, -self.Portfolio[self.symbol].Quantity, self.initialStopRisk * self.breakoutlvl)
            
            #if its at a new high
            if self.securities[self.symbol].Close > self.highestPrice and self.initialStopRisk * self.breakoutlvl < self.securities[self.symbol].close * self.trailingStopRisk:
                #set new highest price
                self.highestPrice = self.securities[self.symbol].close
                updateFields = UpdateOrderFields()
                #set new stop price and the update
                updateFields.stopPrice = self.securities[self.symbol].close * self.trailingStopRisk
                self.stopMarketTicket.Update(updateFields)
                self.Debug(updateFields.stopPrice)

            self.Plot("Data Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))
