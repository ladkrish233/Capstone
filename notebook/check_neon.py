import os

import psycopg

conn=psycopg.connect(os.environ["DATABASE_URL"])
row=conn.execute(
    "select * from chunks"
).fetchall()

print(row)