import os
import sys

import numpy as np
import pandas as pd


class index_data:
    def __init__(self, **kwargs):
        # get required data from
        self.start_date = kwargs.get('start','1900-01-01')
        self.end_date = kwargs.get('end','2200-01-01')
        self.rebal_period = kwargs.get('rebal_period','1D')
        self.rebal_date = kwargs.get('rebal_date', '01')

    def index_data_loading(self):
        base_dir = os.path.join('/mnt','c','workspace','project_quant')
        index_data_dir = os.path.join(base_dir,'data','index_data')

        result_df = pd.DataFrame()

        index_data_name_file = {
            'msci_acwi':'MSCI_All Country World.xlsx',
            'msci_world':'MSCI World.xlsx',
            'msci_emerging':'MSCI Emerging.xlsx',
            'msci_world_gross':'MSCI World Gross.xlsx',
            'msci_world_value':'MSCI World Value.xlsx',
            'msci_real_estate':'MSCI World Real Estate.xlsx',
            'bb_world_agg':'Bloomberg Barclays US AGG.xlsx',
            'bb_emerging_agg':'Bloomberg Barclays EM AGG.xlsx',
            'bb_corp_ig':'Bloomberg Barclays US Corp IG.xlsx',
            'bb_corp_hy':'Bloomberg Barclays US Corp HY.xlsx',
            'bb_infla_protect':'Bloomberg Barclays US Inflation Protected 7-10 year.xlsx',
            'snp_commodity':'SNP GSCI TR.xlsx',
            'us_short_treasury':'Bloomberg Barclays US 1-3 month treasury.xlsx',
        }
        for ind_name in index_data_name_file.keys():
            # load_index_data(self.start_date, self.end_date, index_data_dir,index_data_name_file[ind_name],ind_name)
            input = pd.read_excel(os.path.join(index_data_dir, index_data_name_file[ind_name]), index_col='Date')
            input = input.sort_index(ascending=False)
            index_df = input.iloc[:, 0].resample(self.rebal_period).first().pct_change().fillna(0)
            index_df.rename(ind_name, inplace=True)
            index_df = index_df.loc[self.start_date: self.end_date]


            result_df = pd.concat([
                result_df,
                index_df
            ], axis=1).fillna(0)

        result_df.index = pd.to_datetime(result_df.index)

        return result_df
    

    def index_cum_data_loading(self):
        base_dir = os.path.join('/mnt','c','workspace','project_quant')
        index_data_dir = os.path.join(base_dir,'data','index_data')

        result_df = pd.DataFrame()

        index_data_name_file = {
            'msci_acwi':'MSCI_All Country World.xlsx',
            'msci_world':'MSCI World.xlsx',
            'msci_emerging':'MSCI Emerging.xlsx',
            'msci_world_gross':'MSCI World Gross.xlsx',
            'msci_world_value':'MSCI World Value.xlsx',
            'msci_real_estate':'MSCI World Real Estate.xlsx',
            'bb_world_agg':'Bloomberg Barclays US AGG.xlsx',
            'bb_emerging_agg':'Bloomberg Barclays EM AGG.xlsx',
            'bb_corp_ig':'Bloomberg Barclays US Corp IG.xlsx',
            'bb_corp_hy':'Bloomberg Barclays US Corp HY.xlsx',
            'bb_infla_protect':'Bloomberg Barclays US Inflation Protected 7-10 year.xlsx',
            'snp_commodity':'SNP GSCI TR.xlsx',
            'us_short_treasury':'Bloomberg Barclays US 1-3 month treasury.xlsx',

        }
        for ind_name in index_data_name_file.keys():
            # load_index_data(self.start_date, self.end_date, index_data_dir,index_data_name_file[ind_name],ind_name)
            input = pd.read_excel(os.path.join(index_data_dir, index_data_name_file[ind_name]), index_col='Date')
            input = input.sort_index(ascending=False)
            reb_index = input.iloc[:, 0].resample(self.rebal_period).first()
            index_df = reb_index / reb_index.iloc[0]
            index_df = index_df.fillna(1)
            index_df.rename(ind_name, inplace=True)
            index_df = index_df.loc[self.start_date: self.end_date]


            result_df = pd.concat([
                result_df,
                index_df
            ], axis=1).fillna(0)

        result_df.index = pd.to_datetime(result_df.index)

        return result_df




