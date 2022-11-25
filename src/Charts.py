import asyncio
import datetime
import json
import os
import sys
import threading
import time
import dearpygui.dearpygui as dpg
import utils.DoStuff as do
import pandas as pd
import pandas_ta as ta
import Data as data
import Trade as trade
import Indicators as indicators

class Charts:

    def __init__(self, exchange, symbol, timeframe, api, viewport_width, viewport_height, markets):
        """ Main Chart creation class.

        To create a chart on make an object with all the specified parameters and call draw_chart().

        Args:
            exchange (str): Actual name of the exchange.
            api (ccxt): CCXT exchange object
            viewport_width (int): Main viewport width
            viewport_height (int): Main viewport height
            markets (JSON): JSON of all the market data from the exchange: ccxt.load_markets()
        """

        self.MAIN_WINDOW = "main" # information on the main viewport tag


        # Name of exchange AND tag for dearpygui
        self.exchange = exchange

        # CCXT Instance for the exchange
        self.api = api

        # Products from the exchange: response of ccxt.exchange.load_markets()
        self.markets = markets

        self.symbols = list(self.markets.keys()) # List of symbols from the exchange
        self.timeframes = list(self.api.timeframes.keys()) # List of timeframes from the exchange

        # Viewport information
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        # Immediatel draw chart information
        self.symbol = symbol
        self.timeframe = timeframe

        self.last_chart = None # temp storage of last symbol so we can delete that chart when adding a new one
        self.OHLCV = None
        
        self.init_window() # Create a window for this exchange
        self.draw_charts_menu_nav_bar() # Draws the main navigation bar which waits for input to open a chart


    def trade_panel(self, sender, app_data, user_data):
        trade.push_trade_panel(sender, self.viewport_width)

    def push_indicator_panel(self, sender, app_data, user_data):
        indicators.push_indicator_panel(sender, app_data, user_data)
    

    def init_window(self):
        """ This is the parent of the charts. It is the exchange window, tagged with the exchange's name.
        """
        with dpg.window(label=f'Exchange: [{self.exchange}]',
            tag=self.exchange,
            on_close=dpg.delete_item(self.exchange),
            width=self.viewport_width - 25, 
            height=self.viewport_height - 75, 
            pos=[5, 30]):

            pass


    def save_candle_data(self):
        PATH = f"exchanges/candles/{self.exchange}"
        FILE = f"{PATH}/{self.symbol.replace('/', '_')}-{self.timeframe}.csv"

        if os.path.exists(FILE):
            pd.DataFrame(self.OHLCV).to_csv(FILE, mode="a", index=False, header=False)

        else:
            if not os.path.exists(PATH):
                os.makedirs(f"exchanges/candles/{self.exchange}")
            pd.DataFrame(self.OHLCV).to_csv(FILE, index=False, header=False)

        with dpg.window(label="Data Saved", modal=True, pos=(self.viewport_width/2, self.viewport_height/2)):
            dpg.add_text(f"{self.symbol}-{self.timeframe} successfully saved.")



    # TODO: Impliment this function
    # TODO: Fetch new data since save and update the file
    def pull_from_cache(self):
        files = os.listdir(f"exchanges/candles/{self.exchange}/")
        sym = dpg.get_value(f"{self.exchange}-symbols").replace('/', '')
        tf = dpg.get_value(f"{self.exchange}-timeframes")
        file = f"{sym}-{tf}.json"
        if file in files:
            print(file)
            try: 
                with open(f"exchanges/candles/{self.exchange}/{file}", "r") as f:
                    return (True, json.load(f))
            except Exception as e:
                print("Error")
        else:
            return (False, json.load(f))



    # TODO: Show you solving real world problems while creating this program with the cookbook and things you have learned


    def draw_charts_menu_nav_bar(self):
        with dpg.menu_bar(parent=self.exchange):

            with dpg.menu(label=self.symbol if self.symbol is not None else "BTC/USDT", tag=f"{self.exchange}-symbols-menu"):
                dpg.add_listbox(
                    sorted(self.symbols), 
                    default_value=self.symbol,
                    tag=f"{self.exchange}-symbols", 
                    callback=lambda : dpg.configure_item(f"{self.exchange}-symbols-menu", 
                    label=dpg.get_value(f"{self.exchange}-symbols")),
                    num_items=10
                )
            
            with dpg.menu(label=self.timeframe if self.timeframe is not None else "1h", tag=f"{self.exchange}-timeframes-menu"):
                dpg.add_listbox(
                    self.timeframes, 
                    default_value=self.timeframe,
                    tag=f"{self.exchange}-timeframes", 
                    callback=lambda : dpg.configure_item(f"{self.exchange}-timeframes-menu", 
                    label=dpg.get_value(f"{self.exchange}-timeframes")),
                    num_items=8
                )

            dpg.add_menu_item(label="+", callback=self.push_chart)

            dpg.add_menu_item(label="Trade", callback=self.trade_panel)
            dpg.add_menu_item(label="Indicators", callback=self.push_indicator_panel)

            with dpg.menu(label="Data"):
                dpg.add_menu_item(label="Save", callback=self.save_candle_data)
                dpg.add_menu_item(label="Load", callback=self.pull_from_cache)

    
    def push_chart(self):
        """ Invoked every time the "+" is clicked from the "main_nav_bar"
        """
        self.symbol = dpg.get_value(f"{self.exchange}-symbols")
        self.timeframe = dpg.get_value(f"{self.exchange}-timeframes")

        self.draw_chart(
            symbol=self.symbol, 
            timeframe=self.timeframe,
            parent=self.exchange
        )

    # def update_charts(self, **charts):
    #     active_charts = []
    #     active_charts.append(charts['id'])
    #     i = 0.0
    #     while True:
    #         for chart in active_charts:
    #             dpg.configure_item(chart, closes=i)
    #             i+=1
    #             time.sleep(.5)


    def draw_chart(self, symbol, timeframe, parent, since = "2022-01-01 00:00:00"):
        """ Function which is called to draw a chart to a window tagged as the exchange name. Only one chart / exchange right now, many 
        exchanges at once can be opened. It's used to immediately draw a chart upon application opening.

        Args:
            symbol (str): Name of the symbol
            timeframe (str): Name of the timeframe
            parent (str): Name of the parent the chart will be applied to
            since (str, optional): _description_. Defaults to "2022-10-01 00:00:00".
        """

        date_time_obj = datetime.datetime.strptime(since, '%Y-%m-%d %H:%M:%S')
        
        # Using this section to determine # of candles that will be returned for a progress bar during candle fetch
        print((datetime.datetime.now() - date_time_obj))

        # TODO: Since should be optional, or set to a certain timeframe based on if its > a day or < than
        dpg.add_text("Fetching Data", tag=f"{self.exchange}-fetching-text", parent=parent)
        dpg.add_loading_indicator(parent=parent, tag=f"{self.exchange}-loading", pos=[self.viewport_width/2, self.viewport_height/2 - 110], radius=10.0, style=1)

        dpg.delete_item(self.last_chart)

        # TODO: Check if there is saved data for this exchange, symbol, and timeframe: use that data if so


        self.OHLCV = asyncio.run(data.fetch_candles(exchange=self.exchange, max_retries=3, symbol=symbol, timeframe=timeframe, since=since, limit=1000, dataframe=False))
        chart_tag = f"{self.exchange}-candle-{symbol}-series"

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
        if self.OHLCV is None:
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
            with dpg.plot(tag=f"{self.exchange}-candle-{symbol}", label=f"Exchange: {self.exchange.upper()} | Symbol: {symbol} | Timeframe: {timeframe}"):

                dpg.add_plot_legend()

                xaxis_candles = dpg.add_plot_axis(dpg.mvXAxis, time=True)

                # In the works
                # values = (
                #     0.8, 2.4, 2.5, 3.9, 0.0, 4.0, 0.0,
                #     2.4, 0.0, 4.0, 1.0, 2.7, 0.0, 0.0,
                #     1.1, 2.4, 0.8, 4.3, 1.9, 4.4, 0.0,
                #     0.6, 0.0, 0.3, 0.0, 3.1, 0.0, 0.0,
                #     0.7, 1.7, 0.6, 2.6, 2.2, 6.2, 0.0,
                #     1.3, 1.2, 0.0, 0.0, 0.0, 3.2, 5.1,
                #     0.1, 2.0, 0.0, 1.4, 0.0, 1.9, 6.3
                # )
                # dpg.add_heat_series(values, 7, 7)

                with dpg.plot_axis(dpg.mvYAxis, label="USD"):

                    dpg.add_candle_series(
                        ohlcv['time'], 
                        ohlcv['open'], 
                        ohlcv['close'], 
                        ohlcv['low'], 
                        ohlcv['high'], 
                        tag=chart_tag,
                        time_unit=do.convert_timeframe(timeframe)
                    )
                    
                    dpg.fit_axis_data(dpg.top_container_stack())
                    dpg.fit_axis_data(xaxis_candles)
                    
            # Volume plot
            with dpg.plot():

                dpg.add_plot_legend()
                xaxis_vol = dpg.add_plot_axis(dpg.mvXAxis, label="Time [UTC]", time=True)

                with dpg.plot_axis(dpg.mvYAxis, label="USD"):

                    dpg.add_bar_series(ohlcv['time'], ohlcv['volume'])
                    
                    dpg.fit_axis_data(dpg.top_container_stack())
                    dpg.fit_axis_data(xaxis_vol)

        # x = threading.Thread(target=self.update_charts, kwargs={"id":chart_tag})
        # x.start()