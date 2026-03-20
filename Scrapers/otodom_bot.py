import os 
import psycopg2
from psycopg2 import OperationalError

def create_db_connection():
    """
    Creates a secure connection to the PostgreSQL database.
    Returns the connection object if successful, otherwise None.
    """
    try:
       
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            database="WarsawPropTech",
            user="postgres",
            password=os.getenv("DB_PASSWORD")  
        )

        print("🟢 SUCCESS: Connected to the WarsawPropTech database!")
        return connection

    except OperationalError as e:
        print(f"🔴 FATAL ERROR: Database connection failed.\nDetails: {e}")
        return None


def close_connection(connection):
    """
    Safely closes the database connection 
    """
    if connection:
        connection.close()
        print("⚪ INFO: Connection closed safely.")

# ----- TEST ------

if __name__ == "__main__":
    print("⏳ INFO: Initializing system...")
    db_cnn = create_db_connection()

    if db_cnn:
        close_connection(db_cnn)