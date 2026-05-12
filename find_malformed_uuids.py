import sqlite3
import uuid

db_path = 'db.sqlite3' # Assuming it's in the root

def find_malformed_uuids():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = [
        ('Payment_paymentgroups', 'id'),
        ('Payment_groupcertificate', 'id'),
        ('Payment_groupcertificate', 'payment_group_id'),
    ]
    
    for table, column in tables:
        print(f"Checking table {table}, column {column}...")
        try:
            cursor.execute(f"SELECT {column} FROM {table}")
            rows = cursor.fetchall()
            for row in rows:
                val = row[0]
                if val is None:
                    continue
                try:
                    uuid.UUID(str(val))
                except ValueError:
                    print(f"MALFORMED UUID in {table}.{column}: '{val}'")
        except sqlite3.OperationalError as e:
            print(f"Error checking {table}: {e}")
            
    conn.close()

if __name__ == "__main__":
    find_malformed_uuids()
