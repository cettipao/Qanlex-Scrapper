import pandas as pd
import mysql.connector
from mysql.connector import Error
import json
from dotenv import load_dotenv
import os

# Obtener valores de database desde .env
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")


def json_to_excel(json_data, excel_file_path):
    """
    Convierte una lista de objetos JSON en un archivo Excel.

    :param json_data: Lista de objetos JSON
    :param excel_file_path: Ruta del archivo Excel de salida
    """
    # Preparar los DataFrames
    expedientes_df = pd.DataFrame(json_data)

    # Expandir columnas anidadas en dataframes separados
    actuaciones_df = []
    participantes_df = []
    fiscales_df = []

    for expediente in json_data:
        expediente_link = f"=HYPERLINK(\"#'Expedientes'!A{expedientes_df[expedientes_df['Expediente'] == expediente['Expediente']].index[0] + 2}\", \"{expediente['Expediente']}\")"
        if "Actuaciones" in expediente:
            for actuacion in expediente["Actuaciones"]:
                actuacion["Expediente"] = expediente_link
                actuaciones_df.append({"Expediente": expediente["Expediente"], **actuacion})
        if "Participantes" in expediente:
            for participante in expediente["Participantes"]:
                participante["Expediente"] = expediente_link
                participantes_df.append({"Expediente": expediente["Expediente"], **participante})
        if "Fiscales" in expediente:
            for fiscal in expediente["Fiscales"]:
                fiscal["Expediente"] = expediente_link
                fiscales_df.append({"Expediente": expediente["Expediente"], **fiscal})

    # Crear DataFrames
    actuaciones_df = pd.DataFrame(actuaciones_df)
    participantes_df = pd.DataFrame(participantes_df)
    fiscales_df = pd.DataFrame(fiscales_df)

    expedientes_df = expedientes_df.drop(columns=["Actuaciones", "Participantes", "Fiscales"], errors="ignore")

    # Guardar en Excel con múltiples hojas
    with pd.ExcelWriter(excel_file_path) as writer:
        expedientes_df.to_excel(writer, sheet_name='Expedientes', index=False)
        actuaciones_df.to_excel(writer, sheet_name='Actuaciones', index=False)
        participantes_df.to_excel(writer, sheet_name='Participantes', index=False)
        fiscales_df.to_excel(writer, sheet_name='Fiscales', index=False)

import mysql.connector
from mysql.connector import Error
from datetime import datetime

def json_to_mysql(json_data, host, user, password, database):
    """
    Inserta una lista de objetos JSON en una base de datos MySQL.

    :param json_data: Lista de objetos JSON
    :param host: Host de la base de datos
    :param user: Usuario de la base de datos
    :param password: Contraseña de la base de datos
    :param database: Nombre de la base de datos
    """
    try:
        connection = mysql.connector.connect(host=host, user=user, password=password, database=database)

        if connection.is_connected():
            cursor = connection.cursor()

            # Crear tablas si no existen
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Expedientes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    Expediente VARCHAR(255) UNIQUE,
                    Jurisdiccion VARCHAR(500),
                    Dependencia VARCHAR(500),
                    Situacion VARCHAR(255),
                    Caratula VARCHAR(1000)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Actuaciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    Expediente VARCHAR(255),
                    Oficina VARCHAR(50),
                    Fecha DATE,
                    Tipo VARCHAR(255),
                    DescripcionDetalle VARCHAR(1000),
                    A_FS VARCHAR(100),
                    FOREIGN KEY (Expediente) REFERENCES Expedientes(Expediente)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Participantes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    Expediente VARCHAR(255),
                    Tipo VARCHAR(255),
                    Nombre VARCHAR(1000),
                    TomoFolio VARCHAR(255),
                    IEJ VARCHAR(255),
                    FOREIGN KEY (Expediente) REFERENCES Expedientes(Expediente)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Fiscales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    Expediente VARCHAR(255),
                    Fiscalia VARCHAR(500),
                    Fiscal VARCHAR(255),
                    IEJ VARCHAR(255),
                    FOREIGN KEY (Expediente) REFERENCES Expedientes(Expediente)
                )
            """)

            # Eliminar datos existentes
            cursor.execute("DELETE FROM Actuaciones")
            cursor.execute("DELETE FROM Participantes")
            cursor.execute("DELETE FROM Fiscales")
            cursor.execute("DELETE FROM Expedientes")

            # Insertar datos en las tablas
            for expediente in json_data:
                cursor.execute("""
                    INSERT IGNORE INTO Expedientes (Expediente, Jurisdiccion, Dependencia, Situacion, Caratula)
                    VALUES (%s, %s, %s, %s, %s)
                """, (expediente["Expediente"], expediente["Jurisdicción"], expediente["Dependencia"],
                      expediente["Situación"], expediente["Carátula"]))

                if "Actuaciones" in expediente:
                    for actuacion in expediente["Actuaciones"]:
                        fecha = datetime.strptime(actuacion["FECHA"], "%d/%m/%Y") if actuacion["FECHA"] else None
                        cursor.execute("""
                            INSERT INTO Actuaciones (Expediente, Oficina, Fecha, Tipo, DescripcionDetalle, A_FS)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (expediente["Expediente"], actuacion["OFICINA"], fecha,
                              actuacion["TIPO"], actuacion["DESCRIPCION_DETALLE"], actuacion["A_FS"]))

                if "Participantes" in expediente:
                    for participante in expediente["Participantes"]:
                        cursor.execute("""
                            INSERT INTO Participantes (Expediente, Tipo, Nombre, TomoFolio, IEJ)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (expediente["Expediente"], participante["TIPO"], participante["NOMBRE"],
                              participante["TOMO/FOLIO"], participante["I.E.J."]))

                if "Fiscales" in expediente:
                    for fiscal in expediente["Fiscales"]:
                        cursor.execute("""
                            INSERT INTO Fiscales (Expediente, Fiscalia, Fiscal, IEJ)
                            VALUES (%s, %s, %s, %s)
                        """, (expediente["Expediente"], fiscal["FISCALIA"], fiscal["FISCAL"], fiscal["I.E.J."]))

            connection.commit()

    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()



if __name__ == "__main__":
    file_path = "data.json"
    #Pasar data.json a JSON
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    #json_to_excel(data, "data.xlsx")  # Convertir JSON a Excel
    json_to_mysql(data, DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE)  # Convertir JSON a MySQL