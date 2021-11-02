import datetime
import logging
import requests
import pandas as pd
from sqlalchemy import create_engine
from pytrends.request import TrendReq

from airflow import DAG

from airflow.operators.python_operator import PythonOperator


def start():
    logging.info('Starting the DAG')



def load_data_coin():
    logging.info('get data from API')
    coins = ["convex-finance", "ribbon-finance", "rari-governance-token", "gmx", "nftx", "ftx-token", "audius", "ecomi",
             "spell-token", "dopex", "gro-dao-token", "raydium"]

    df_coin_current_data = pd.DataFrame()

    for coin in coins:
        url = 'https://api.coingecko.com/api/v3/coins/' + coin
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame.from_dict(data.get("market_data"))
        df = df.loc['usd', :]
        df["coin"] = coin
        df_coin_current_data = df_coin_current_data.append(df)
        logging.info("The following data is written into the database:")
        logging.info(df_coin_current_data)

    ## connection to database
    engine = create_engine(
        'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')
    ## write dataframe to table
    df_coin_current_data.to_sql('coin_data', engine, if_exists="append")

def load_data_google_trend():
    # Only 5 keywords per request possible
    kw_list1 = ["convex finance", "ribbon finance", "rari governance token", "gmx", "nftx"]
    kw_list2 = ["ftx token", "audius", "ecomi", "spell token", "dopex"]
    kw_list3 = ["gro dao token", "raydium"]

    cat = {7: "Finance",
           814: "Currencies & Foreign Exchange",
           12: "Business & Industrial",
           784: "Business News",
           16: "News",
           1164: "Economy News",
           1163: "Financial Markets"}

    pytrend = TrendReq(hl='en-US', tz=360)

    logging.info('get data from API')
    for key in cat:
        cat_selected = key

        pytrend.build_payload(kw_list1, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df1 = pytrend.interest_over_time()
        logging.info(interest_over_time_df1.shape)

        pytrend.build_payload(kw_list2, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df2 = pytrend.interest_over_time()
        logging.info(interest_over_time_df2.shape)

        pytrend.build_payload(kw_list3, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df3 = pytrend.interest_over_time()
        logging.info(interest_over_time_df3.shape)

        df = pd.concat([interest_over_time_df1, interest_over_time_df2, interest_over_time_df3], axis=1)
        df["category"] = cat[cat_selected]
        df.reset_index(inplace=True)

        ## connection to database
        engine = create_engine(
            'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')
        ## write dataframe to table
        df.to_sql('google_trends_data', engine, if_exists="append")

dag = DAG(
    'Load_coin_gecko_data',
    schedule_interval='@hourly',
    start_date=datetime.datetime.now())


data_load_task_coin = PythonOperator(
    task_id="data_load_task_coin",
    python_callable=load_data_coin,
    dag=dag
)

data_load_google_trends = PythonOperator(
    task_id="data_load_google_trends",
    python_callable=load_data_google_trend,
    dag=dag
)


data_load_task_coin

data_load_google_trends
