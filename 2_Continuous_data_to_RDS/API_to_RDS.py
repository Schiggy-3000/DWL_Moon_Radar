from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from pytrends.request import TrendReq
from sqlalchemy import create_engine
from datetime import datetime
from airflow import DAG
import pandas as pd
import logging
import requests
import psycopg2
import praw
import json
import os


# DAG Functions
def fetch_coin_data_fct():

    # Pull data
    coins = ["convex-finance", "ribbon-finance", "rari-governance-token", "gmx", "nftx", "ftx-token", "audius", "ecomi",
             "spell-token", "dopex", "gro-dao-token", "raydium"]

    df_coin_data = pd.DataFrame()

    for coin in coins:
        url = 'https://api.coingecko.com/api/v3/coins/' + coin
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame.from_dict(data.get("market_data"))
        df = df.loc['usd', :]
        df["coin"] = coin
        df_coin_data = df_coin_data.append(df)

    # Connect to DB
    engine = create_engine(
        'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')

    # Upload to DB
    df_coin_data.to_sql('continuous_coin_data', engine, if_exists="append", index=False)


def fetch_reddit_data_fct():

    # Connect to API
    my_client_id = "qIZJdlnEWYTd4pUr6QtrhQ"
    my_client_secret = "foKDZFlOxPkoQDjzzpRU4myPPs-kVQ"
    my_user_agent = "Schiggy"

    reddit = praw.Reddit(client_id=my_client_id,
                         client_secret=my_client_secret,
                         user_agent=my_user_agent)

    # Pull data
    x_newest_posts = 10

    subr_1 = "audius"
    subr_2 = "ecomi"
    subr_3 = "FTXOfficial"
    subreddits = subr_1 + "+" + subr_2 + "+" + subr_3
    model = reddit.subreddit(subreddits)

    posts = []

    for post in model.new(limit=x_newest_posts):
        posts.append([post.num_comments,
                      'post.subreddit',
                      post.subreddit_subscribers,
                      post.created])

    df_reddit_data = pd.DataFrame(posts, columns=['num_comments',
                                                  'subreddit',
                                                  'subreddit_subscribers',
                                                  'date_unix'])

    # Connect to DB
    engine = create_engine(
        'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')

    # Upload to DB
    df_reddit_data.to_sql('continuous_reddit_data', engine, if_exists="append", index=False)


def fetch_google_data_fct():

    # Pull data
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

    for key in cat:
        cat_selected = key

        pytrend.build_payload(kw_list1, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df1 = pytrend.interest_over_time()

        pytrend.build_payload(kw_list2, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df2 = pytrend.interest_over_time()

        pytrend.build_payload(kw_list3, timeframe='now 1-H', geo='', gprop='', cat=cat_selected)
        interest_over_time_df3 = pytrend.interest_over_time()

        df_google_data = pd.concat([interest_over_time_df1, interest_over_time_df2, interest_over_time_df3], axis=1)
        df_google_data["category"] = cat[cat_selected]
        df_google_data.reset_index(inplace=True)

    # Connect to DB
    engine = create_engine(
        'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')

    # Upload to DB
    df_google_data.to_sql('continuous_google_data', engine, if_exists="append")


def fetch_twitter_data_fct():

    # Pull data
    moonlist = ['CVX', 'RBN', 'RGT', 'GMX', 'NFTX', 'FTX', 'DPX', 'OMI', 'RAY', 'STX', 'OCEAN ', 'AR', 'DYDX', 'REN','MOVR']

    appended_data = []
    for coin in moonlist:
        url = f"https://api.twitter.com/2/tweets/counts/recent?query=\"$\"{coin}"

        payload = {}
        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAAM4UwEAAAAAEE99W5gZMnu80PT0okAWYKO5H7w%3DoVBPqgoeaBWK6OO7eczlcVUCDcuecp40GwlGpIXrxOdg5gHMmR',
            'Cookie': 'guest_id=v1%3A163454991707626701; personalization_id="v1_IHRrtM7EN/nl33o110i1tg=="'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        your_json = response.text
        parsed = json.loads(your_json)
        df_twitter_data = pd.json_normalize(parsed, record_path=['data'])
        df_twitter_data.insert(0, "Name", coin)
        appended_data.append(df_twitter_data)

    df_twitter_data = pd.concat(appended_data)

    # Connect to DB
    engine = create_engine(
        'postgresql://bisasam:1234asdf@datalake.clnjs1yqzw0z.us-east-1.rds.amazonaws.com:5432/datalakebisasam')

    # Upload to DB
    df_twitter_data.to_sql('continuous_twitter_data', engine, if_exists="append")



# DAG
dag = DAG(
    'reddit_to_rds',
    schedule_interval='@daily',
    start_date=datetime.now()
)


# Nodes
fetch_coin = PythonOperator(
   task_id="fetch_coin_data",
   python_callable=fetch_coin_data_fct,
   dag=dag
)

fetch_reddit = PythonOperator(
   task_id="fetch_reddit_data",
   python_callable=fetch_reddit_data_fct,
   dag=dag
)

fetch_google = PythonOperator(
   task_id="fetch_google_data",
   python_callable=fetch_google_data_fct,
   dag=dag
)

fetch_twitter = PythonOperator(
   task_id="fetch_twitter_data",
   python_callable=fetch_twitter_data_fct,
   dag=dag
)


# Workflow
fetch_coin
fetch_reddit
fetch_google
fetch_twitter