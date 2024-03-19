import datetime

import psycopg2
from database.configuration import config


def update_exchange_rate(currency, rate):
    sql = f"""
    UPDATE ExchangeRate
    SET rate = {rate},
    updatedAt = NOW()
    WHERE currency = '{currency}'
  """
    conn: psycopg2.connection = None  # type: ignore

    updated_rows = 0
    try:
        # read database configuration
        params = config()
        # connect to PostgreSQL DB instance
        conn = psycopg2.connect(**params)
        # create new cursor
        cur = conn.cursor()

        # UPDATE
        cur.execute(sql)
        updated_rows = cur.rowcount
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        conn.close()

    return updated_rows


def get_last_saved_exchange_rate(currency, rate):
    sql = f"""
        SELECT * FROM ExchangeRate
        WHERE currency = '{currency}'
      """
    conn: psycopg2.connection = None  # type: ignore

    updated_rows = 0
    result = []
    try:
        # read database configuration
        params = config()
        # connect to PostgreSQL DB instance
        conn = psycopg2.connect(**params)
        # create new cursor
        cur = conn.cursor()

        # UPDATE
        cur.execute(sql)
        updated_rows = cur.rowcount

        res = cur.fetchone()
        if res is not None:
            result.append(res)

        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        conn.close()

    if len(result) > 0:
        datetime_object = result[0][2]

        # # Create a timedelta object for the timezone offset
        # timezone_offset = datetime.timedelta(hours=8, minutes=0)
        #
        # # Adjust the datetime object for the timezone offset
        # datetime_object += timezone_offset
        #
        # # Format the datetime object as per your requirement
        # formatted_datetime = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

        return result[0][1], datetime_object
    return rate, None
