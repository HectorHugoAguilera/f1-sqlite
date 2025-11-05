import sqlite3
import csv
import os

# --- Sistema de puntos ---
POINTS_BY_POSITION = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}


def get_points(position):
    return POINTS_BY_POSITION.get(position, 0)

# --- Conexión y tablas ---


def create_connection(db_name="f1.db"):
    return sqlite3.connect(db_name)


def initialize_db(conn, schema_path="schema.sql"):
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()

# --- Inserciones ---


def add_team(conn, name):
    conn.execute("INSERT OR IGNORE INTO teams (name) VALUES (?)", (name,))
    conn.commit()


def add_driver(conn, name, nationality):
    conn.execute("INSERT OR IGNORE INTO drivers (name, nationality) VALUES (?, ?)",
                 (name, nationality))
    conn.commit()


def add_race(conn, grand_prix, date, circuit):
    conn.execute("INSERT OR IGNORE INTO races (grand_prix, date, circuit) VALUES (?, ?, ?)",
                 (grand_prix, date, circuit))
    conn.commit()


def add_result(conn, race_name, driver_name, team_name, position):
    race_id = conn.execute(
        "SELECT id FROM races WHERE grand_prix=?", (race_name,)).fetchone()[0]
    driver_id = conn.execute(
        "SELECT id FROM drivers WHERE name=?", (driver_name,)).fetchone()[0]
    team_id = conn.execute(
        "SELECT id FROM teams WHERE name=?", (team_name,)).fetchone()[0]
    points = get_points(position)

    conn.execute("""
        INSERT OR REPLACE INTO results (race_id, driver_id, team_id, position, points)
        VALUES (?, ?, ?, ?, ?)
    """, (race_id, driver_id, team_id, position, points))
    conn.commit()

# --- Cargar resultados desde CSV ---


def load_results_from_csv(conn, csv_path):
    """
    Carga resultados desde un archivo CSV.
    Si la carrera, el piloto o el equipo no existen, los crea automáticamente.
    """
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            race = row["race"].strip()
            date = row.get("date", "Unknown")
            circuit = row.get("circuit", "Unknown")
            driver = row["driver"].strip()
            nationality = row.get("nationality", "Unknown")
            team = row.get("team", "Unknown")
            position = int(row["position"])

            # Crear equipo si no existe
            cur = conn.execute("SELECT id FROM teams WHERE name=?", (team,))
            if not cur.fetchone():
                add_team(conn, team)
                print(f"🆕 Equipo creado: {team}")

            # Crear piloto si no existe
            cur = conn.execute(
                "SELECT id FROM drivers WHERE name=?", (driver,))
            if not cur.fetchone():
                add_driver(conn, driver, nationality)
                print(f"🆕 Piloto creado: {driver} ({nationality}")

            # Crear carrera si no existe
            cur = conn.execute(
                "SELECT id FROM races WHERE grand_prix=?", (race,))
            if not cur.fetchone():
                add_race(conn, race, date, circuit)
                print(f"🆕 Carrera creada: {race} ({date}, {circuit})")

            # Agregar resultado
            add_result(conn, race, driver, team, position)

    print(f"✅ Resultados cargados desde {csv_path}\n")

# --- Cargar todos los CSV de una carpeta ---


def load_all_csv_from_folder(conn, folder_path="data"):
    files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]
    files.sort()  # orden alfabético (útil si los nombras por orden de carrera)

    if not files:
        print("⚠️ No se encontraron archivos CSV en la carpeta.")
        return

    for file in files:
        full_path = os.path.join(folder_path, file)
        print(f"📂 Procesando {file} ...")
        load_results_from_csv(conn, full_path)

# --- Consultas de clasificación ---


def get_driver_standings(conn):
    print("\n🏎️ Mundial de Pilotos:")
    cur = conn.execute("""
        SELECT d.name, SUM(r.points) AS total_points
        FROM results r
        JOIN drivers d ON d.id = r.driver_id
        GROUP BY d.id
        ORDER BY total_points DESC
    """)
    for i, (name, pts) in enumerate(cur.fetchall(), start=1):
        print(f"{i:2}. {name:20} {pts:>5} pts")


def get_constructor_standings(conn):
    print("\n🏆 Mundial de Constructores:")
    cur = conn.execute("""
        SELECT t.name, SUM(r.points) as total_points
        FROM results r
        JOIN teams t ON r.team_id = t.id
        GROUP BY t.id
        ORDER BY total_points DESC;
    """)
    for i, (team, pts) in enumerate(cur.fetchall(), start=1):
        print(f"{i:2}. {team:20} {pts:>5} pts")


# --- Main ---
if __name__ == "__main__":
    if os.path.exists("f1.db"):
        os.remove("f1.db")
    conn = create_connection()
    initialize_db(conn)

    # Cargar todos los archivos CSV de la carpeta data/
    load_all_csv_from_folder(conn, "data")

    # Mostrar clasificaciones
    get_driver_standings(conn)
    get_constructor_standings(conn)
