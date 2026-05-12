import sqlite3

db_path = 'db.sqlite3'

def delete_malformed_row():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    table = 'Payment_groupcertificate'
    column = 'id'
    val = '1'
    
    print(f"Deleting record where {table}.{column} = '{val}'")
    cursor.execute(f"DELETE FROM {table} WHERE {column} = ?", (val,))
    conn.commit()
    print(f"Rows affected: {cursor.rowcount}")
    
    conn.close()

if __name__ == "__main__":
    delete_malformed_row()
