import mysql.connector


def query(mysql_client: mysql.connector.MySQLConnection, query):
    """
    Query a mysql database using SQL syntax
    """

    cursor = mysql_client.cursor(dictionary=True)

    cursor.execute(query)

    results = list(cursor)
    cursor.close()
    mysql_client.commit()

    return results
