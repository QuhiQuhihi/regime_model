from re import I
import numpy as np
import pandas as pd

def monthly_rebalance_strategy(strategy, yld_df, bm_strategy, bm_yld_df,lookback_period = 12):
    """
    :param strategy: investment strategy, this function should return weight of portfolio in list form
    :param yld_df: yield data of asset classes, used as input of strategy generation
    :param bm_strategy: benchmark strategy, this fundction should return weight of portolio in list form
    :param bm_yld_df: benchmark yield data of strategy.
    :param lookback_period:
    :return: return of investment strategy and return of benchmark in dataframe
    """

    asset_list = yld_df.columns
    date_list = yld_df.index

    bm_asset_list = bm_yld_df.columns
    bm_date_list = bm_yld_df.index

    investment_weight = pd.DataFrame(columns=asset_list, index=date_list)
    benchmark_weight = pd.DataFrame(columns=bm_asset_list, index=bm_date_list)
    investment_return = pd.DataFrame(columns=['strategy_return','benchmark_return'], index=date_list)

    for i in range(len(investment_return)):
        if i < lookback_period-1:
            investment_weight.iloc[i,:]= 0
        else:
            investment_weight.iloc[i,:] = strategy(yld_df.iloc[i-lookback_period+1 : i+1])

    investment_weight['SUM']=investment_weight.sum(axis=1)

    for i in range(len(investment_return)):
        benchmark_weight.iloc[i,:] = bm_strategy(bm_yld_df).iloc[i]

    investment_weight['SUM']=investment_weight.sum(axis=1)

    for i in range(len(date_list)):
        ret = 0
        if i > 0:
            for asset in asset_list:
                asset_return = yld_df[asset].iloc[i]
                asset_weight = investment_weight[asset].iloc[i]
                ret += (1 + asset_return) * asset_weight
            investment_return['strategy_return'].iloc[i] = ret - 1
        else:
            pass

    for i in range(len(bm_date_list)):
        ret = 0
        for asset in bm_asset_list:
            bm_asset_return = bm_yld_df[asset].iloc[i]
            bm_asset_weight = benchmark_weight[asset].iloc[i]
            ret += (1 + bm_asset_return) * bm_asset_weight
        investment_return['benchmark_return'].iloc[i] = ret - 1

    # investment_return.loc[:, 'benchmark_return'] = bm_yld_df

    investment_return = pd.concat([investment_return,investment_weight], axis=1)
    investment_return = investment_return.iloc[lookback_period:]

    return investment_return

def momentum_rebalance_strategy(strategy, yld_df, bm_strategy, bm_yld_df,lookback_period = 0):
    """
    :param strategy: investment strategy, this function should return weight of portfolio in list form
    :param yld_df: yield data of asset classes, used as input of strategy generation
    :param bm_strategy: benchmark strategy, this fundction should return weight of portolio in list form
    :param bm_yld_df: benchmark yield data of strategy.
    :param lookback_period:
    :return: return of investment strategy and return of benchmark in dataframe
    """

    asset_list = yld_df.columns
    date_list = yld_df.index

    bm_asset_list = bm_yld_df.columns
    bm_date_list = bm_yld_df.index

    investment_return = pd.DataFrame(columns=['strategy_return','benchmark_return'], index=date_list)

    investment_weight = strategy(yld_df)
    investment_weight['SUM']=investment_weight.sum(axis=1)

    benchmark_weight = bm_strategy(bm_yld_df)


    for i in range(len(date_list)):
        if i == 0:
            investment_return['strategy_return'].iloc[i] = 0
        else:
            ret = 0
            for asset in asset_list:
                asset_return = yld_df[asset].iloc[i]
                asset_weight = investment_weight[asset].iloc[i-1]
                ret += (1 + asset_return) * asset_weight
            investment_return['strategy_return'].iloc[i] = ret - 1

    for i in range(len(date_list)):
        if i == 0:
            investment_return['benchmark_return'].iloc[i] = 0
        else:
            ret = 0
            for asset in bm_asset_list:
                bm_asset_return = bm_yld_df[asset].iloc[i]
                bm_asset_weight = benchmark_weight[asset].iloc[i-1]
                ret += (1 + bm_asset_return) * bm_asset_weight
            investment_return['benchmark_return'].iloc[i] = ret - 1

    investment_return = pd.concat([investment_return,investment_weight], axis=1)
    investment_return = investment_return.iloc[lookback_period:]

    return investment_return

def rp_rebalance_strategy(strategy, yld_df, bm_strategy, bm_yld_df,lookback_period = 12):
    """
    :param strategy: investment strategy, this function should return weight of portfolio in list form
    :param yld_df: yield data of asset classes, used as input of strategy generation
    :param bm_strategy: benchmark strategy, this fundction should return weight of portolio in list form
    :param bm_yld_df: benchmark yield data of strategy.
    :param lookback_period:
    :return: return of investment strategy and return of benchmark in dataframe
    """

    asset_list = yld_df.columns
    date_list = yld_df.index

    bm_asset_list = bm_yld_df.columns
    bm_date_list = bm_yld_df.index

    investment_weight = pd.DataFrame(columns=asset_list, index=date_list)
    benchmark_weight = pd.DataFrame(columns=bm_asset_list, index=bm_date_list)
    investment_return = pd.DataFrame(columns=['strategy_return','benchmark_return'], index=date_list)

    for i in range(len(investment_return)):
        if i < lookback_period:
            investment_weight.iloc[i,:]= 0
        else:
            investment_weight.iloc[i,:] = strategy(pd.DataFrame(yld_df.iloc[i-lookback_period+1 : i+1]).cov())

    for i in range(len(investment_return)):
        benchmark_weight.iloc[i,:] = bm_strategy(bm_yld_df).iloc[i]

    investment_weight['SUM']=investment_weight.sum(axis=1)

    for i in range(len(date_list)):
        ret = 0
        if i > 0:
            for asset in asset_list:
                asset_return = yld_df[asset].iloc[i]
                asset_weight = investment_weight[asset].iloc[i]
                ret += (1 + asset_return) * asset_weight
            investment_return['strategy_return'].iloc[i] = ret - 1
        else:
            pass

    for i in range(len(bm_date_list)):
        ret = 0
        if i > 0:
            for asset in bm_asset_list:
                bm_asset_return = bm_yld_df[asset].iloc[i]
                bm_asset_weight = benchmark_weight[asset].iloc[i]
                ret += (1 + bm_asset_return) * bm_asset_weight
            investment_return['benchmark_return'].iloc[i] = ret - 1
        else:
            pass

    # investment_return.loc[:, 'benchmark_return'] = bm_yld_df
    investment_return = pd.concat([investment_return,investment_weight], axis=1)
    investment_return = investment_return.iloc[lookback_period:]

    return investment_return

def mv_rebalance_strategy(strategy, yld_df, bm_strategy, bm_yld_df,lookback_period = 252):
    """
    :param strategy: investment strategy, this function should return weight of portfolio in list form
    :param yld_df: yield data of asset classes, used as input of strategy generation
    :param bm_strategy: benchmark strategy, this fundction should return weight of portolio in list form
    :param bm_yld_df: benchmark yield data of strategy.
    :param lookback_period:
    :return: return of investment strategy and return of benchmark in dataframe
    """

    asset_list = yld_df.columns
    date_list = yld_df.index

    bm_asset_list = bm_yld_df.columns
    bm_date_list = bm_yld_df.index

    investment_weight = pd.DataFrame(columns=asset_list, index=date_list)
    benchmark_weight = pd.DataFrame(columns=bm_asset_list, index=bm_date_list)
    investment_return = pd.DataFrame(columns=['strategy_return','benchmark_return'], index=date_list)

    for i in range(len(investment_return)):
        if i < lookback_period:
            investment_weight.iloc[i,:]= 0
        else:
            investment_weight.iloc[i,:] = strategy

    for i in range(len(investment_return)):
        benchmark_weight.iloc[i,:] = bm_strategy(bm_yld_df).iloc[i]

    investment_weight['SUM']=investment_weight.sum(axis=1)

    for i in range(len(date_list)):
        ret = 0
        if i > 0:
            for asset in asset_list:
                asset_return = yld_df[asset].iloc[i]
                asset_weight = investment_weight[asset].iloc[i]
                ret += (1 + asset_return) * asset_weight
            investment_return['strategy_return'].iloc[i] = ret - 1
        else:
            pass

    for i in range(len(bm_date_list)):
        ret = 0
        if i > 0:
            for asset in bm_asset_list:
                bm_asset_return = bm_yld_df[asset].iloc[i]
                bm_asset_weight = benchmark_weight[asset].iloc[i]
                ret += (1 + bm_asset_return) * bm_asset_weight
            investment_return['benchmark_return'].iloc[i] = ret - 1
        else:
            pass

    # investment_return.loc[:, 'benchmark_return'] = bm_yld_df
    investment_return = pd.concat([investment_return,investment_weight], axis=1)
    investment_return = investment_return.iloc[lookback_period:]

    return investment_return