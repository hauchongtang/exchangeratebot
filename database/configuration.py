import os


def config(filename='database.ini', section='postgresql'):

    # get section, default to postgresql
    db = {
        "host": os.environ.get("PGHOST", ""),
        "database": os.environ.get("PGDATABASE", ""),
        "user": os.environ.get("PGUSER", ""),
        "password": os.environ.get("PGPASSWORD", ""),
        "port": os.environ.get("PGPORT", "")
    }

    return db