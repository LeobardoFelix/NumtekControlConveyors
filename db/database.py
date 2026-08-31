import sqlite3
from db.connection import db, DB_PATH

# Backwards-compatible alias kept for modules that still import db_path.
db_path = DB_PATH


def respaldar_base_datos():
    """Make a backup now (startup / shutdown / explicit)."""
    db.backup()

def ejecutar(query, params=None):
    db.execute(query, params)

def selectFromDB(query, params=None):
    return db.query(query, params)

def respaldar():
    db.backup()

def ejecutar_y_respaldar(query, params=None):
    """Run a statement.

    Historically this backed up the whole database file on every write,
    which made each INSERT/UPDATE/DELETE copy the file. Backups are now
    explicit (see :meth:`Database.backup`), so this just executes.
    """
    db.execute(query, params)

def inicializar_base_datos():
    #solo un respaldo al inicio  de la aplicacion
    respaldar_base_datos()
    # ejecutar("PRAGMA foreign_keys = ON;")
    # ejecutar("DROP TABLE currentParts")
    # ejecutar("DROP TABLE history")
    # ejecutar("DROP TABLE parts")
    # ejecutar("DROP TABLE conveyors")
    init_users_table()
    init_programs_table()
    init_sequences_table()
    init_conveyors_tables()
    init_parts_table()
    init_partNumbers_table()
    init_currentParts_table()
    init_history_table()
    init_workOrders_table()
    conveyors = {
        'A': 30,
        'B': 75,
        'C': 70,
        'D': 30
    }
    #ejecutar("DELETE FROM conveyors;")
    #ejecutar("DELETE FROM parts;")
    j = 1
    for nombre_tabla, cantidad_hangers in conveyors.items():
        #llena de hangers la tabla
        for i in range(1, cantidad_hangers + 1):
            ejecutar(f'''
                INSERT OR IGNORE INTO conveyors(hanger_id, hanger_num, conveyor, part_id)
                VALUES (?, ?, ?, ?)
            ''', (j, i,nombre_tabla,None))
            #ejecutar(f'''
            #    INSERT OR IGNORE INTO parts VALUES(?,?,?,?,?,?,?)
            #''', (j, j, 1, None, nombre_tabla, 0, 0)) 
            j = j + 1
    #print_sqlite_table('parts')
    #print_sqlite_table('conveyors')
def init_users_table():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT UNIQUE NOT NULL,
            password TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'user'
        );
    """)
def init_programs_table():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS programs (
            program_id TEXT PRIMARY KEY,
            path TEXT DEFAULT '',
            robot_num TEXT NOT NULL,
            conveyor_start TEXT DEFAULT NULL,
            conveyor_end TEXT DEFAULT NULL
        );
    """)

def init_sequences_table():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS sequences (
    sequence_id TEXT,
    program_id TEXT,
    step INT,
    min_drying_time TEXT NOT NULL,
    max_drying_time TEXT NOT NULL,
    FOREIGN KEY (program_id) REFERENCES programs(program_id)
        );
    """)
####
def init_conveyors_tables():
    ejecutar(f'''
            CREATE TABLE IF NOT EXISTS conveyors (
                hanger_id  INTEGER UNIQUE PRIMARY KEY,
                hanger_num INTEGER DEFAULT NULL, 
                conveyor TEXT NOT NULL,
                status TEXT DEFAULT 'EMPTY',
                enable INTEGER DEFAULT 1,
                part_id TEXT DEFAULT NULL,
                part_num TEXT DEFAULT NULL,
                order_id TEXT DEFAULT NULL,
                FOREIGN KEY (part_id) REFERENCES parts(part_id),
                FOREIGN KEY (part_num) REFERENCES partNumbers(part_num)
                DEFERRABLE INITIALLY DEFERRED
            )
        ''')

    #part_id TEXT DEFAULT ''
def init_partNumbers_table():
    #sequence_id = 0 Significa que no tiene una secuencia asignada
    ejecutar("""
        CREATE TABLE IF NOT EXISTS partNumbers (
            part_num TEXT PRIMARY KEY NOT NULL,
            sequence_id TEXT DEFAULT 0, 
            FOREIGN KEY (sequence_id) REFERENCES sequences(sequence_id)
            DEFERRABLE INITIALLY DEFERRED
        );
    """)
def init_parts_table():
    #Partes que existen en el sistema
    #start_time y start_date es el momento de 
    #inicialización de la parte distinto a la tabla history
    ejecutar("""
        CREATE TABLE IF NOT EXISTS parts (
            part_id TEXT PRIMARY KEY,
            part_num TEXT NOT NULL,
            status INTEGER DEFAULT 1,
            hanger_id INTEGER,
            hanger_num INTEGER,
            conveyor TEXT,
            sequence_index INTEGER NOT NULL DEFAULT 0,
            start_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_date TEXT DEAFULT NULL,
            end_time TEXT DEAFULT NULL,
            order_id TEXT DEFAULT NULL,
            FOREIGN KEY (part_num) REFERENCES partNumbers(part_num),
            FOREIGN KEY (hanger_id) REFERENCES conveyors(hanger_id),
            FOREIGN KEY (hanger_num) REFERENCES conveyors(hanger_num),
            FOREIGN KEY (conveyor) REFERENCES conveyors(conveyor)
            DEFERRABLE INITIALLY DEFERRED
        );
    """)
    ###

def init_currentParts_table():
    #Only the part and current program executing
    ejecutar("""
        CREATE TABLE IF NOT EXISTS currentParts (
            part_id TEXT PRIMARY KEY,
            part_num TEXT DEFAULT NULL,
            current_step INTEGER DEFAULT NULL,
            program_id TEXT DEFAULT NULL,
            robot_num INTEGER DEFAULT NULL,
            min_drying_time TEXT DEFAULT NULL,
            max_drying_time TEXT DEFAULT  NULL,
            state TEXT DEFAULT 'IDLE',
            start_date TEXT DEFAUL '00/00/00',
            start_time TEXT DEFAULT '00:00',
            end_date TEXT DEFAULT '00/00/00',
            end_time TEXT DEFAULT '00:00',
            run_time TEXT DEFAULT '00:00',
            station TEXT DEFAULT NULL,
            hanger_id TEXT DEFAULT NULL,
            hanger_num TEXT DEFAULT NULL,
            hanger_end TEXT DEFAULT NULL,
            conveyor_start TEXT DEFAULT NULL,
            conveyor_end TEXT DEFAULT NULL,
            time_deviation TEXT DEFAULT '00:00',
            current_hanger TEXT DEFAULT NULL,
            current_conveyor TEXT DEFAULT NULL,
            order_id TEXT DEFAULT NULL,
            FOREIGN KEY (part_id) REFERENCES parts(part_id),
            FOREIGN KEY (part_num) REFERENCES partNumbers(part_num),
            FOREIGN KEY (program_id) REFERENCES programs(program_id),
            FOREIGN KEY (robot_num) REFERENCES programs(robot_num),
            FOREIGN KEY (min_drying_time) REFERENCES sequences(min_drying_time),
            FOREIGN KEY (max_drying_time) REFERENCES sequences(max_drying_time),
            FOREIGN KEY (hanger_id) REFERENCES conveyors(hanger_id),
            FOREIGN KEY (hanger_num) REFERENCES conveyors(hanger_num)
            DEFERRABLE INITIALLY DEFERRED
        );
    """)
def init_history_table():
    ejecutar("""
        CREATE TABLE IF NOT EXISTS history (
            part_id TEXT DEFAULT NULL,
            part_num TEXT DEFAULT NULL,
            step INTEGER DEFAULT NULL,
            program_id TEXT DEFAULT NULL,
            robot_num INTEGER DEFAULT NULL,
            min_drying_time TEXT DEFAULT NULL,
            max_drying_time TEXT DEFAULT  NULL,
            state TEXT DEFAULT 'IDLE',
            start_date TEXT DEFAUL '00/00/00',
            start_time TEXT DEFAULT '00:00',
            end_date TEXT DEFAULT '00/00/00',
            end_time TEXT DEFAULT '00:00',
            run_time TEXT DEFAULT '00:00',
            station TEXT DEFAULT NULL,
            hanger_id TEXT DEFAULT NULL,
            hanger_num TEXT DEFAULT NULL,
            hanger_end TEXT DEFAULT NULL,
            conveyor_start TEXT DEFAULT NULL,
            conveyor_end TEXT DEFAULT NULL,
            time_deviation TEXT DEFAULT '00:00',
            order_id TEXT DEFAULT NULL,
            upload_date TEXT DEFAULT NULL,
            FOREIGN KEY (part_id) REFERENCES parts(part_id),
            FOREIGN KEY (part_num) REFERENCES partNumbers(part_num),
            FOREIGN KEY (step) REFERENCES sequences(step),
            FOREIGN KEY (program_id) REFERENCES programs(program_id),
            FOREIGN KEY (robot_num) REFERENCES programs(robot_num),
            FOREIGN KEY (min_drying_time) REFERENCES sequences(min_drying_time),
            FOREIGN KEY (max_drying_time) REFERENCES sequences(max_drying_time),
            FOREIGN KEY (hanger_id) REFERENCES conveyors(hanger_id),
            FOREIGN KEY (hanger_num) REFERENCES conveyors(hanger_num)
            DEFERRABLE INITIALLY DEFERRED
        );
    """)
    #print_sqlite_table("history")

def init_workOrders_table():
    ejecutar_y_respaldar("""
    CREATE TABLE IF NOT EXISTS workOrders (
        order_id TEXT DEFAULT NULL,
        part_num TEXT DEFAULT NULL,
        customer TEXT DEFAULT NULL,
        target_qty INTEGER DEFAULT NULL
    );
    """)
#Borrar despues
def print_sqlite_table(table_name):
    database_file = './db/db.db'
    connection = None
    try:
        # Connect to the database
        connection = sqlite3.connect(database_file)
        cursor = connection.cursor()

        # Execute a SELECT query to fetch all data
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)

        # Fetch all results
        rows = cursor.fetchall()

        # Print the column headers (optional, requires a bit more code)
        # You can get column names from cursor.description
        column_names = [description[0] for description in cursor.description]
        print(f"Columns in {table_name}: {column_names}")
        
        # Print the rows
        print(f"Data in {table_name}:")
        for row in rows:
            print(row)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        if connection:
            connection.close()

if __name__ == '__main__':
    inicializar_base_datos()
