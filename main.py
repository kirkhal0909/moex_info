from app.api.moex.moex import MOEX

moex = MOEX()
indexes = moex.parser.moex_indexes()

d = moex.parser.indexes_changes(indexes)
s = moex.parser.today_prices()