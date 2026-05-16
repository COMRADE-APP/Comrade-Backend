import sqlite3

db_path = 'db.sqlite3'

def get_row_details():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    table = 'Payment_groupcertificate'
    column = 'id'
    val = '1'

    # Ensure table and column names are safe identifiers (basic check)
    if not table.isidentifier() or not column.isidentifier():
        print("Invalid table or column name. Must be valid identifiers.")
        return

    print(f"Fetching details for {table}.{column} = '{val}'")
    cursor.execute(f"SELECT * FROM {table} WHERE {column} = ?", (val,))
    row = cursor.fetchone()
    
    if row:
        # Get column names
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cursor.fetchall()]
        details = dict(zip(cols, row))
        print(details)
    else:
        print("Row not found.")
        
    conn.close()

if __name__ == "__main__":
    get_row_details()
