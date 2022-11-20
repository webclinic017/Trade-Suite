import asyncio
import json
import os
import sys
import dearpygui.dearpygui as dpg
import utils.DoStuff as do
import pandas as pd
import pandas_ta as ta
import Data as data
import Trade as trade
import Stats as stats
import Indicators as indicators

class Charts:

    def __init__(self, exchange, api, viewport_width, viewport_height, markets):
        # Name of exchange AND tag for dearpygui
        self.exchange = exchange

        # CCXT Instance for the exchange
        self.api = api

        # Products from the exchange: response of ccxt.exchange.load_markets()
        self.markets = markets

        self.symbols = list(self.markets.keys()) # List of symbols from the exchange
        self.timeframes = list(self.api.timeframes.keys()) # List of timeframes from the exchange

        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        self.last_chart = None # temp storage of last symbol so we can delete that chart when adding a new one
        self.OHLCV = None
        
        self.init_window() # Create a window for this exchange
        self.draw_charts_menu_nav_bar() # Draws the main navigation bar which waits for input to open a chart


    # TODO: Add the trade and market panels
    def trade_panel(self, sender, app_data, user_data):
        trade.push_trade_panel(sender, self.viewport_width)


    def market_stats_panel(self, sender, app_data, user_data):
        stats.push_stats_panel()

    def push_indicator_panel(self, sender, app_data, user_data):
        indicators.launch_indicator_panel(sender, app_data, user_data)
    

    def init_window(self):
        with dpg.window(label=f'Exchange: [{self.exchange}]',
            tag=self.exchange,
            on_close=dpg.delete_item(self.exchange),        # This is where you need to handle deletion of object?
            width=self.viewport_width - 25, 
            height=self.viewport_height - 75, 
            pos=[5, 30]):

            pass


    def save_candle_stick_data(self):
        data = json.dumps(self.OHLCV, indent=4)
        try:
            with open(f"exchanges/candles/{self.exchange}/{self.active_symbol.replace('/', '')}-{self.active_timeframe}.json", "w") as f:
                f.write(data)
        except FileNotFoundError as e:
            os.makedirs(f"exchanges/candles/{self.exchange}")
            with open(f"exchanges/candles/{self.exchange}/{self.active_symbol.replace('/', '')}-{self.active_timeframe}.json", "w") as f:
                f.write(data)

        with dpg.window(label="Data Saved", modal=True):
            dpg.add_text(f"{self.active_symbol}-{self.active_timeframe} successfully saved.")


    # TODO: Show you solving real world problems while creating this program with the cookbook and things you have learned


    def draw_charts_menu_nav_bar(self):
        with dpg.menu_bar(parent=self.exchange):

            with dpg.menu(label="BTC/USDT", tag=f"{self.exchange}-symbols-menu"):
                dpg.add_listbox(
                    sorted(self.symbols), 
                    tag=f"{self.exchange}-symbols", 
                    default_value="BTC/USDT",  
                    label=self.symbols[0], 
                    callback=lambda : dpg.configure_item(f"{self.exchange}-symbols-menu", 
                    label=dpg.get_value(f"{self.exchange}-symbols"))
                )
            
            with dpg.menu(label="1h", tag=f"{self.exchange}-timeframes-menu"):
                dpg.add_listbox(
                    self.timeframes, 
                    tag=f"{self.exchange}-timeframes", 
                    default_value="1h", 
                    callback=lambda : dpg.configure_item(f"{self.exchange}-timeframes-menu", 
                    label=dpg.get_value(f"{self.exchange}-timeframes"))
                )

            dpg.add_menu_item(label="+", callback=self.push_chart)

            dpg.add_menu_item(label="Trade", callback=self.trade_panel)
            dpg.add_menu_item(label="Stats", callback=self.market_stats_panel)
            dpg.add_menu_item(label="Indicators", callback=self.push_indicator_panel)
            dpg.add_menu_item(label="Save Data", callback=self.save_candle_stick_data)
            do.help("Click me to save this candlestick data locally for a faster loadup.")

    
    def push_chart(self, sender, app_data, user_data):
        """ Invoked every time the "+" is clicked from the "main_nav_bar"

        Args:
            sender (_type_): _description_
            app_data (_type_): _description_
            user_data (_type_): _description_
        """
        self.active_symbol = dpg.get_value(f"{self.exchange}-symbols")
        self.active_timeframe = dpg.get_value(f"{self.exchange}-timeframes")

        self.draw_chart(
            symbol=dpg.get_value(f"{self.exchange}-symbols"), 
            exchange=self.exchange,
            timeframe=dpg.get_value(f"{self.exchange}-timeframes"),
            parent=self.exchange
        )


    def draw_chart(self, symbol, exchange, timeframe, parent, since = "2019-01-01 00:00:00"):

        # TODO: Since should be optional, or set to a certain timeframe based on if its > a day or < than
        dpg.add_text("Fetching Data", tag=f"{self.exchange}-fetching-text", parent=parent)
        dpg.add_loading_indicator(circle_count=7, parent=parent, tag=f"{self.exchange}-loading", pos=[self.viewport_width/2, self.viewport_height/2 - 110], radius=10.0)

        dpg.delete_item(self.last_chart)

        #                          scrape_ohlcv(api="binance", max_retries=3, symbol="BTC/USDT", timeframe="1d", since="2015-09-01 00:00:00", limit=1000)
        # TODO: Check if there is saved data for this exchange, symbol, and timeframe: use that data if so
        candles = asyncio.run(data.scrape_ohlcv(api=self.exchange, max_retries=3, symbol=symbol, timeframe=timeframe, since=since, limit=1000))
        self.OHLCV = candles

        # Storage dictionary for fetched candles
        ohlcv = {"time":[], "open":[], "high":[], "low":[], "close":[], "volume":[]}
        for row in self.OHLCV:
            ohlcv['time'].append(row[0]/1000)
            ohlcv['open'].append(float(row[1]))
            ohlcv['high'].append(float(row[2]))
            ohlcv['low'].append(float(row[3]))
            ohlcv['close'].append(float(row[4]))
            ohlcv['volume'].append(float(row[5]))
        
        # Error handling for symbol not found.
        if candles is None:
            print("No symbol for this exchange.")
            dpg.delete_item(f"{self.exchange}-loading")
            return
    

        # Candlestick plot and volume plot
        with dpg.subplots(2, 1, label="", width=-1, height=-1, 
                            link_all_x=True, 
                            row_ratios=[1.0, 0.25], 
                            parent=parent,
                            tag=f"{self.exchange}-chart-{symbol}"):

            dpg.delete_item(f"{self.exchange}-loading")
            dpg.delete_item(f"{self.exchange}-fetching-text")

            self.last_chart = f"{self.exchange}-chart-{symbol}"

            # Candlestick plot
            with dpg.plot(tag=f"{self.exchange}-candle-{symbol}", label=f"Exchange: {exchange.upper()} | Symbol: {symbol} | Timeframe: {timeframe}"):

                dpg.add_plot_legend()

                xaxis_candles = dpg.add_plot_axis(dpg.mvXAxis, time=True)

                with dpg.plot_axis(dpg.mvYAxis, label="USD"):

                    dpg.add_candle_series(ohlcv['time'], ohlcv['open'], ohlcv['close'], ohlcv['low'], ohlcv['high'], tag=f"{self.exchange}-candle-{symbol}-series", time_unit=do.convert_timeframe(timeframe))
                    dpg.fit_axis_data(dpg.top_container_stack())
                    dpg.fit_axis_data(xaxis_candles)
                    
            # Volume plot
            with dpg.plot():

                dpg.add_plot_legend()
                xaxis_vol = dpg.add_plot_axis(dpg.mvXAxis, label="Time [UTC]")

                with dpg.plot_axis(dpg.mvYAxis, label="USD"):

                    dpg.add_bar_series(ohlcv['time'], ohlcv['volume'])
                    dpg.fit_axis_data(dpg.top_container_stack())
                    dpg.fit_axis_data(xaxis_vol)