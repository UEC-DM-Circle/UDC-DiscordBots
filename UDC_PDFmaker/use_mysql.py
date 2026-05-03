from common import *


class UseMySQL:
    @staticmethod
    def get_connection():
        load_dotenv()
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )

    @classmethod
    def run_sql(cls, sql: str, params: tuple):
        conn = cls.get_connection()
        cursor = conn.cursor(buffered=True)
        if params != ():
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if sql.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return
