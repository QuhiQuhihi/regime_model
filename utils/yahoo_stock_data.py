import os
import sys

import numpy as np
import pandas as pd
import pandas_datareader.data as web


class yahoo_data:
    def __init__(self, **kwargs):
        # get required data from
        self.start_date = kwargs.get('start','1900-01-01')
        self.end_date = kwargs.get('end','2200-01-01')
        self.ticker_list = kwargs.get('ticker_list',[''])
        self.rebal_period = kwargs.get('rebal_period', '1D')

    def yahoo_stock_data_loading(self):
        return_df = pd.DataFrame()

        for ticker in self.ticker_list:
            adj_data = web.DataReader(ticker, 'yahoo', self.start_date, self.end_date)['Adj Close'].to_frame(ticker)
            return_df = pd.concat([return_df,adj_data], axis=1)

        result_df = return_df.resample(self.rebal_period).first().pct_change().dropna(axis=0)
        return result_df

