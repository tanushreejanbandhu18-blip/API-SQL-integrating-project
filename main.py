
import os
import requests
import pandas as pd

from pathlib import Path
from dotenv import load_dotenv
from mysql import connector


# --------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# --------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("API_KEY")
API_HOST = os.getenv("API_HOST")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")


# --------------------------------
# 2. FETCH PREMIER LEAGUE DATA
# --------------------------------

def fetch_standings():

    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-standing-all"

    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST
    }

    querystring = {"leagueid": "47"}

    response = requests.get(
        url,
        headers=headers,
        params=querystring,
        timeout=30
    )

    response.raise_for_status()

    standing_payload = response.json()

    standings_list = standing_payload["response"]["standing"]

    print("API data fetched successfully!")
    print("Total teams received:", len(standings_list))

    return standings_list


# --------------------------------
# 3. TRANSFORM DATA USING PANDAS
# --------------------------------

def transform_data(standings_list):

    standings_df = pd.DataFrame(standings_list)

    standings_df = standings_df[
        ['idx', 'name', 'played', 'wins', 'draws',
         'losses', 'scoresStr', 'goalConDiff', 'pts']
    ].copy()

    standings_df.columns = [
        'Position', 'Team', 'Played', 'Won', 'Drawn',
        'Lost', 'Goals', 'Goal_Difference', 'Points'
    ]

    print("Data transformation completed!")
    print("DataFrame shape:", standings_df.shape)

    return standings_df


# --------------------------------
# 4. LOAD DATA INTO MYSQL
# --------------------------------

def load_to_mysql(standings_df):

    records = list(
        standings_df.itertuples(index=False, name=None)
    )

    upsert_query = """
    INSERT INTO standings
    (Position, Team, Played, Won, Drawn, Lost,
     Goals, Goal_Difference, Points)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)

    ON DUPLICATE KEY UPDATE
        Team = VALUES(Team),
        Played = VALUES(Played),
        Won = VALUES(Won),
        Drawn = VALUES(Drawn),
        Lost = VALUES(Lost),
        Goals = VALUES(Goals),
        Goal_Difference = VALUES(Goal_Difference),
        Points = VALUES(Points)
    """

    server_conn = None
    cur = None

    try:

        server_conn = connector.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            database=MYSQL_DATABASE,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            connection_timeout=10
        )

        cur = server_conn.cursor(buffered=True)

        cur.executemany(upsert_query, records)

        server_conn.commit()

        print("MySQL loading completed!")
        print("Rows affected:", cur.rowcount)

    except Exception:
        if server_conn and server_conn.is_connected():
            server_conn.rollback()
        raise

    finally:
        if cur:
            cur.close()

        if server_conn and server_conn.is_connected():
            server_conn.close()


# --------------------------------
# 5. MAIN EXECUTION
# --------------------------------

def main():

    standings_list = fetch_standings()

    standings_df = transform_data(standings_list)

    load_to_mysql(standings_df)

    print("Premier League pipeline executed successfully!")


if __name__ == "__main__":
    main()
