from app.api.moex.moex_client import MOEXClient
from app.api.moex.moex_parser import MOEXParser
from app.api.moex.machine_learning.ml import ML

class MOEX():
  def __init__(self):
    self.client = MOEXClient()
    self.parser = MOEXParser(self.client)
    self.ml = ML(self.client, self.parser)
