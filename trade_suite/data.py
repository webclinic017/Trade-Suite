from pathlib import Path
import threading
import time
import ccxt.async_support as ccas
import ccxt
import pandas as pd
import ccxt.pro as ccxtpro
from asyncio import run
import asyncio
import dearpygui.dearpygui as dpg


msec = 1000
minute = 60 * msec
hold = 30


async def retry_fetch_candles(api, max_retries:int, symbol: str, timeframe: str, since: str, limit: int):
    num_retries = 0
    try:
        num_retries += 1
        try: 
            ohlcv = await api.fetch_ohlcv(symbol, timeframe, since, limit)
        except ccxt.ExchangeError as e:
            print(e)
        return ohlcv
    except Exception as e:
        if num_retries > max_retries:
            return None



async def fetch_candles(exchange: str, max_retries:int, symbol: str, timeframe: str, since: str, limit: int, dataframe: bool):
    """ This function is called to fetch candlestick data from storage and the newest since the last saved date. It will return a list or dataframe
    of the candles.
    Args:
        exchange (str): Exchange name
        max_retries (int): Number of times to try fetching candles if failure occured
        symbol (str): Symbol name
        timeframe (str): Timeframe
        since (str): UTC timestamp
        limit (int): Number of candles to fetch per batch (max: 1000)
        dataframe (bool): True to return data as dataframe, false for list
    Returns:
        _type_: _description_
    """

    # TODO: Add to this function a way check if there exists a file for this exchange, symbol, timeframe and if so,
    # update the fetch since to the last timeframe in the file, update the file, and then return all_ohlcv
    # PATH = Path(f"exchanges/candles/{exchange}/{symbol}-{timeframe}.csv")
    # old_ohlcv = None
    # if PATH.exists():
    #     files = [x for x in PATH.iterdir()]
    #     for f in files:
    #         old_ohlcv = pd.read_csv(f)

    # CCXT exchange object
    # TODO: Instead of getattr() use ccxt.<exchange> name
    api = getattr(ccas, exchange)()

    timeframe_duration_in_seconds = api.parse_timeframe(timeframe)
    timeframe_duration_in_ms = timeframe_duration_in_seconds * 1000
    timedelta = limit * timeframe_duration_in_ms

    all_ohlcv = []

    now = api.milliseconds()
    fetch_since = api.parse8601(since)
    
    while fetch_since < now:
        
        ohlcv = await retry_fetch_candles(api, max_retries, symbol, timeframe, fetch_since, limit)
        if ohlcv is None:
            await api.close()
            return None
        fetch_since = (ohlcv[-1][0] + 1) if len(ohlcv) else (fetch_since + timedelta)
        all_ohlcv = all_ohlcv + ohlcv
        
        if len(all_ohlcv):
            print(len(all_ohlcv), 'candles in total from', api.iso8601(all_ohlcv[0][0]), 'to', api.iso8601(all_ohlcv[-1][0]))
        
        else:
            print(len(all_ohlcv), 'candles in total from', api.iso8601(fetch_since))

    # if old_ohlcv is not None concat the new candles and old, append the new candles to the file, and return the new concatinated results

    # start_thread(exchange, symbol, timeframe, candles, chart_tag)
    await api.close()
    return all_ohlcv if not dataframe else pd.DataFrame(all_ohlcv)


async def fetch_latest_candles(candles, exchange, symbol, timeframe):
    """ TODO: This function will fetch the latest candles since the last time saved in the local storage for an exchange, symbol, and timeframe.

    Args:
        candles (dict): Candlestick data that was saved and loaded.
        exchange (str): Name of the exchange.
        symbol (str): Symbol.
        timeframe (str): Timeframe.
    """

    # TODO: Add this to the params, which is passed from the Chart's draw_chart() function
    api = getattr(ccas, exchange)()

    columns = ['date', 'open', 'high', 'low', 'close', 'volume']

    # If the file exists load it
    old_candles = pd.DataFrame(candles)
    last_pull_time = old_candles.iat[-1, 0] # last stored time

    # This part grabs new candles since last_pull_time and drops the first row because its a duplicate.
    new_candles = pd.DataFrame(fetch_candles(3, symbol, timeframe, last_pull_time, 500), columns=columns)
    new_candles.drop(new_candles.head(1).index, inplace=True)
    
    # We will concat the new candles with the old candles
    new_ohlcv = pd.concat([old_candles, new_candles], ignore_index=True)

    # TODO: Write a method to save the new_ohlcv to its respective fille

    # Return all the candles
    return new_ohlcv


# TODO: Things to fix
"""
trade_suite/data.py line 59:

Also recommendation to use from pathlib import Path for path resolving everywhere
https://docs.python.org/3/library/pathlib.html
makes them cross platform and more feature rich


trade_suite/data.py line 178:
Nesting hell!
you should decrease nesting hell xD
Try to fight with guard clauses https://betterprogramming.pub/refactoring-guard-clauses-2ceeaa1a9da


avoid getaattr of loading stuff from libraries.
I will prefer seeing some way that will allow my IDE scanning inside of library automatically 
(for help information of a used class/function through right mouse click See Definition)


Stats.py line 120
install black library and launch on all your code
black src
to fix formatting 
with dpg.window(label="Crypto Stats", tag="stats-window", width=800, height=1000, pos=[15, 60], on_close = lambda sender: dpg.delete_item(sender)):


(incomplete README)


https://github.com/pattty847/Trade-Suite folder src can be renamed to trade_suite
and file main.py to __main__.py
import from from charts import Charts to from trade_suite import charts or to from .charts import charts
and import from utils.DoSttuff as do renamed to import trade_suite.utils.do_stuff as do
and adding __init__.py empty file to formersrc folder, and to src/utils folder
then you application could be started as python3 -m trade_suite as one package, and will be having less tangled importing... situation 
it will be kind of.. almost to... rules of python to prepare package for.... publishing... 
or to build into binary file. Or to reuse it as a package in another code xD 


it looks like good candidate for Enum
from enum import Enum

class CoinCategories(Enum):
  cryptocurrencies = "/cryptocurrency/"
  exchange = "/exchange/"

class CoinEndpoints(Enum):
  latest = "/latest"
  historical = "/historical"

they will be accessable as
CoinCategories.exchange

or as
CoinCategories["exchange"]

u can get their value by .value
or perhaps just using as class, without Enum :pithink: 
then it will be accessable without .value
class CoinCategories:
  cryptocurrencies = "/cryptocurrency/"
  exchange = "/exchange/"

class CoinEndpoints:
  latest = "/latest"
  historical = "/historical"

CoinEndpoints.latest


Fixed structures over dynamic dictionary structures when possible


"""