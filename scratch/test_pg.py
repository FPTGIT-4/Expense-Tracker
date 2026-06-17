import psycopg

passwords = ["postgres", "admin", "root", "1234", "123456", "password", "Expense@123", "YourStrongPassword123", "micro", "VICTUSUSER", ""]

for pwd in passwords:
    try:
        conn = psycopg.connect(
            host="localhost",
            user="postgres",
            password=pwd,
            port=5432,
            autocommit=True
        )
        print(f"SUCCESS: Connected with password: {pwd}")
        
        # Create database and user if they don't exist
        with conn.cursor() as cur:
            # Check if role expense_user exists
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='expense_user';")
            if not cur.fetchone():
                print("Creating user expense_user...")
                cur.execute("CREATE USER expense_user WITH PASSWORD 'YourStrongPassword123';")
            else:
                print("User expense_user already exists. Updating password...")
                cur.execute("ALTER USER expense_user WITH PASSWORD 'YourStrongPassword123';")
                
            # Make expense_user superuser or give createrole/createdb just in case
            cur.execute("ALTER USER expense_user SUPERUSER;")
            
            # Check if database expense_tracker exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname='expense_tracker';")
            if not cur.fetchone():
                print("Creating database expense_tracker...")
                cur.execute("CREATE DATABASE expense_tracker OWNER expense_user;")
            else:
                print("Database expense_tracker already exists.")
                
        conn.close()
        break
    except Exception as e:
        print(f"Failed with password '{pwd}': {e}")
