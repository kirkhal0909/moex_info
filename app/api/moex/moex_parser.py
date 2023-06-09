from app.helpers.dates import minus_today
from app.helpers.dictionaries import first_key
from app.api.bcs.bcs import BCS
from app.api.smart_lab.smart_lab import SmartLab

class MOEXParser():
  def __init__(self, client):
    self.client = client
    self.bcs = BCS()
    self.smart_lab = SmartLab()

  def today_prices(self):
    response = self.client.stocks_prices_today()
    data_info = self.get_data(response, 0)
    data_trade = self.get_data(response, 1)
    stocks = {}
    pos = 1
    while pos < len(data_info):
      if data_trade[pos]['@OPEN']:
        stocks[data_info[pos]['@SECID']] = {
          'name': data_info[pos]['@SHORTNAME'],
          'open': data_trade[pos]['@OPEN'],
          'close': data_trade[pos]['@LAST'],
          'high': data_trade[pos]['@HIGH'],
          'low': data_trade[pos]['@LOW'],
          'change': data_trade[pos]['@CHANGE'],
          'capitalization': data_trade[pos]['@ISSUECAPITALIZATION'],
          'level': data_info[pos]['@LISTLEVEL']
        }
      pos += 1
    return stocks

  def stocks_prices(self, tickers=['all'], days_ranges = [7, 14, 30, 90]):
    tickers_data = {}
    today_prices = self.today_prices()
    if tickers == ['all']:
      tickers = list(today_prices.keys())[1:]
    for ticker in tickers:
      prices = self.get_data(self.client.stock_prices(ticker, { 'from': minus_today(max(days_ranges)) }), 1)
      tickers_data[ticker] = {
        'changes': {},
        **(today_prices.get(ticker) or {}),
        'dates': [row['@TRADEDATE'] for row in prices],
        'open': [row['@OPEN'] for row in prices],
        'close': [row['@CLOSE'] for row in prices],
        'high': [row['@HIGH'] for row in prices],
        'low': [row['@LOW'] for row in prices],
        'volume': [row['@VOLUME'] for row in prices],
        'false_breakout': self.__false_breakout__(prices)
      }
      external_functions = [self.bcs.parser.ticker_data, self.smart_lab.parser.reports]
      for external_fucntion in external_functions:
        try:
          tickers_data[ticker] = {
            **tickers_data[ticker],
            **external_fucntion(ticker)
          }
        except:
          None
      for days in days_ranges:
        tickers_data[ticker]['changes'][days] = self.__changes__(prices, days)
      days = first_key(tickers_data[ticker]['changes'])
      if tickers_data[ticker].get('percent'):
        dividend_value = round(tickers_data[ticker]['changes'][days][1] / 100 * tickers_data[ticker].get('percent'), 2)
        tickers_data[ticker]['dividend_value'] = dividend_value
        tickers_data[ticker]['mark_highlight'] = '✓' if dividend_value > 400_000_000 else ''
    return self.sort_tickers_data(tickers_data)

  def __false_breakout__(self, prices):
    breakouts = [False]
    candle = lambda pos:[
      float(prices[pos]['@LOW']),
      sorted(
        [float(prices[pos]['@OPEN']), float(prices[pos]['@CLOSE'])]
      ),
      float(prices[pos]['@HIGH'])
    ]
    indents = lambda candle:all([ candle[1][0] - candle[0] >= 0, candle[2] - candle[1][1] >= 0])
    for pos in range(1, len(prices)-1, 1):
      if prices[pos]['@LOW'] != '' and prices[pos+1]['@LOW'] != '':
        left_candle = candle(pos)
        right_candle = candle(pos+1)
        candle_in = right_candle[1][0] >= left_candle[1][0] and right_candle[1][1] <= left_candle[1][1]
        breakouts.append(candle_in)# and indents(left_candle) and indents(right_candle))
      else:
        breakouts.append(False)
    return breakouts

  def sort_tickers_data(self, tickers_data):
    sorted_data = sorted((tickers_data.items()), key=lambda ticker:ticker[1]['changes'][first_key(ticker[1]['changes'])][0] )
    return dict(sorted_data)

  def moex_indexes(self):
    start = 0
    get_indexes = lambda start: self.get_data(self.client.index_list({ 'start': start, 'date': minus_today(1) }))
    data = get_indexes(start)
    indexes = {}
    while data:
      for block in data:
        index = block['@SECID']
        capitalization = block['@CAPITALIZATION']
        if 'MOEX' in index and capitalization:
          indexes[index] = {
            'name': block['@SHORTNAME'],
            'capitalization': capitalization,
            'tickers': self.stocks_prices(self.securities_list(index))
          }
      start += 100
      data = get_indexes(start)

    return indexes

  def indexes_changes(self, indexes_dict, days_ranges = [7, 14, 30, 90]):
    for index in indexes_dict:
      get_prices = lambda days: self.get_data(self.client.index_prices(index, { 'from': minus_today(days) }))
      prices = get_prices(max(days_ranges))
      indexes_dict[index] = {
        **indexes_dict[index],
        'changes': { days:self.__changes__(prices, days) for days in days_ranges }
      }

    return self.sort_tickers_data(indexes_dict)

  def securities_list(self, index):
    return [row['@ticker'] for row in self.get_data(self.client.securities_list(index))]

  def __changes__(self, prices, days):
    prices = prices[-days:]
    for row in prices:
      if row['@HIGH'] == '':
        return 0
    value = sum([float(row['@VALUE']) for row in prices])
    low = min([float(row['@LOW']) for row in prices])
    high = max([float(row['@HIGH']) for row in prices])
    last_close = float(prices[-1]['@CLOSE'])
    changes = [round((1 - low/last_close) * 100, 2), round(-(1-last_close/high) * 100, 2)]
    percent_change = changes[0] if changes[0] > abs(changes[1]) else changes[1]
    return [percent_change, int(value)]

  def get_data(self, response, data_position = 0):
    try:
      return response['document']['data']['rows']['row']
    except:
      if response['document']['data'][data_position]['rows'] == None:
        return None
      return response['document']['data'][data_position]['rows']['row']
