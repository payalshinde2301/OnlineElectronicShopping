import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="electromart",
    user="postgres",
    password="Payal@123"
)

cursor = conn.cursor()