from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import json
import time
from exportJson import json_to_excel, json_to_mysql

chrome_options = Options()
chrome_options.add_argument("--headless")  # Modo sin interfaz gráfica
chrome_options.add_argument("--no-sandbox")  # Necesario para entornos sin privilegios
chrome_options.add_argument("--disable-dev-shm-usage")  # Soluciona problemas de memoria compartida en algunos sistemas
chrome_options.add_argument("--disable-gpu")  # Opcional, puede mejorar la estabilidad
chrome_options.add_argument("--window-size=1920,1080")  # Tamaño de la ventana virtual

# Inicializar el WebDriver
service = Service('chromedriver.exe')  # Ruta al ejecutable de ChromeDriver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Acceder a la página
driver.get("http://scw.pjn.gov.ar/scw/home.seam")  # Sustituir con la URL de la página

# Esperar que el DOM cargue completamente
wait = WebDriverWait(driver, 10)  # Espera explícita con un tiempo máximo de espera de 10 segundos

# Hacer clic en el elemento de "Por parte" para mostrar el formulario
por_parte_button = wait.until(EC.element_to_be_clickable((By.ID, "formPublica:porParte:header:inactive")))
por_parte_button.click()

# Esperar que se despliegue el formulario
wait.until(EC.visibility_of_element_located((By.ID, "formPublica:camaraPartes")))  # Esperar que el select de jurisdicción sea visible

# Interactuar con los campos dentro del formulario
# Seleccionar una jurisdicción, por ejemplo, "COM" que corresponde a la opción con value="10"
jurisdiccion_select = driver.find_element(By.ID, "formPublica:camaraPartes")
jurisdiccion_select.click()  # Hacer clic para mostrar las opciones
wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//select[@id='formPublica:camaraPartes']/option")))  # Esperar que las opciones estén visibles

# Seleccionar "COM" de las opciones del select
select = Select(jurisdiccion_select)
select.select_by_visible_text("COM - Camara Nacional de Apelaciones en lo Comercial")

# Ingresar un valor para el campo "Parte"
parte_input = driver.find_element(By.ID, "formPublica:nomIntervParte")
parte_input.send_keys("Residuos")  # Ingresar el valor "Residuos"

# Enviar el formulario para realizar la búsqueda
search_button = wait.until(EC.element_to_be_clickable((By.ID, "formPublica:buscarPorParteButton")))
input("Captcha Terminado:")  # Esta es una pausa manual para que se resuelva el CAPTCHA
# Hacer clic en el botón de búsqueda después de que el CAPTCHA ha sido resuelto
search_button.click()

# Esperar el resultado (asumimos que el resultado se cargará en el DOM)
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "table-striped")))

# Extraer el contenido de la página usando BeautifulSoup
soup = BeautifulSoup(driver.page_source, "html.parser")

rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]  # Saltar el encabezado

data = []  # Lista para almacenar los objetos con los datos


while True:
    # Imprimo el primer valor de rows
    rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]
    primera_fila = rows[0].text
    for i in range(len(rows)):
        # Extraer los datos de cada fila usando Selenium
        cols = rows[i].find_elements(By.TAG_NAME, 'td')  # Obtener celdas de la fila
        if len(cols) > 0:  # Verificar que la fila tiene datos

            # Buscar y hacer clic en el botón "Visualizar expediente"
            visualizar_button = rows[i].find_element(By.XPATH, ".//a[contains(@class, 'btn') and contains(@onclick, 'jsf.util.chain')]")
            visualizar_button.click()

            # Esperar que se cargue el contenido del modal (ajustar el ID según sea necesario)
            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "ui-fieldset-content")))

            # Extraer los datos del modal
            expediente = driver.find_element(By.XPATH, "//label[text()='Expediente:']/ancestor::div[@class='form-group']//span").text.strip()
            jurisdiccion = driver.find_element(By.XPATH, "//label[text()='Jurisdicción:']/ancestor::div[@class='form-group']//span").text.strip()
            dependencia = driver.find_element(By.XPATH, "//label[@for='detailDependencia']/ancestor::div[@class='form-group']//span").text.strip()
            situacion = driver.find_element(By.XPATH, "//label[@for='detailSituation']/ancestor::div[@class='form-group']//span").text.strip()
            caratula = driver.find_element(By.XPATH, "//label[@for='detailCover']/ancestor::div[@class='form-group']//span").text.strip()

            # Inicializar el array para almacenar las actuaciones
            actuaciones = []

            try:
                # Intentar localizar la tabla de actuaciones
                tabla_actuaciones = driver.find_element(By.ID, "expediente:action-table")

                # Encontrar las filas de la tabla
                filas = tabla_actuaciones.find_elements(By.TAG_NAME, "tr")[1:]  # Ignorar el encabezado

                # Iterar sobre las filas y extraer los datos
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    
                    if len(celdas) >= 5:
                        oficina = celdas[1].find_element(By.XPATH, ".//span[@class='font-color-black']").text.strip()  
                        fecha = celdas[2].find_element(By.XPATH, ".//span[@class='font-color-black']").text.strip()   
                        tipo = celdas[3].find_element(By.XPATH, ".//span[@class='font-color-black']").text.strip()    
                        descripcion = celdas[4].find_element(By.XPATH, ".//span[@class='font-color-black']").text.strip()  
                        a_fs = celdas[5].text.strip() if len(celdas) > 5 else ""  
                        
                        # Crear el objeto de actuación
                        actuacion = {
                            "OFICINA": oficina,
                            "FECHA": fecha,
                            "TIPO": tipo,
                            "DESCRIPCION_DETALLE": descripcion,
                            "A_FS": a_fs
                        }
                        
                        # Agregar la actuación al array
                        actuaciones.append(actuacion)

            except NoSuchElementException:
                # Si la tabla no existe, inicializar 'Actuaciones' como un array vacío
                actuaciones = []



            # Hacer clic en la pestaña "Intervinientes"
            intervinientes_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "expediente:j_idt261:header:inactive"))
            )
            intervinientes_tab.click()

            # Intentar recopilar datos de la tabla de participantes
            participants = []
            wait.until(EC.visibility_of_element_located((By.ID, "expediente:participantsTable")))
            participants_table = driver.find_element(By.ID, "expediente:participantsTable")
            tbodies = participants_table.find_elements(By.TAG_NAME, "tbody")

            for tbody in tbodies:
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    # Filtrar filas visibles y con contenido útil
                    if row.is_displayed() and len(row.find_elements(By.TAG_NAME, "td")) > 1:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        tipo = ""
                        nombre = ""
                        tomo_folio = ""
                        iej = ""

                        try:
                            tipo = cols[0].find_element(By.XPATH, ".//span[@class='font-strong']").text.strip()
                        except:
                            tipo = cols[0].text.strip()

                        try:
                            nombre = cols[1].find_element(By.XPATH, ".//span[@class='font-strong']").text.strip()
                        except:
                            nombre = cols[1].text.strip()

                        if len(cols) > 2:
                            tomo_folio = cols[2].text.strip()

                        if len(cols) > 3:
                            iej = cols[3].text.strip()

                        # Añadir solo si hay contenido relevante
                        if tipo or nombre or tomo_folio or iej:
                            participants.append({
                                "TIPO": tipo,
                                "NOMBRE": nombre,
                                "TOMO/FOLIO": tomo_folio,
                                "I.E.J.": iej
                            })

            fiscales = []
            try:
                fiscales_table = driver.find_element(By.ID, "expediente:fiscalesTable")
                rows = fiscales_table.find_elements(By.TAG_NAME, "tbody")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) == 3:
                        fiscales.append({
                            "FISCALIA": cols[0].text.strip(),
                            "FISCAL": cols[1].text.strip(),
                            "I.E.J.": cols[2].text.strip()
                        })

            except NoSuchElementException:
                pass


            # Hacer clic en la pestaña "Vinculados"
            vinculados_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "expediente:j_idt339:header:inactive"))
            )
            vinculados_tab.click()

            # Intentar recopilar datos de la tabla de vinculados
            vinculados = []
            wait.until(EC.visibility_of_element_located((By.ID, "expediente:vinculadosTab")))

            try:
                connected_table = driver.find_element(By.ID, "expediente:connectedTable")
                tbody = connected_table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    vinculados.append({
                        "Expediente": cols[0].text.strip(),
                        "Dependencia": cols[1].text.strip(),
                        "Situacion": cols[2].text.strip(),
                        "Caratula": cols[3].text.strip(),
                        "Ult. Actividad": cols[4].text.strip(),
                    })

            except NoSuchElementException:
                pass


            # Hacer clic en la pestaña "Recursos"
            recursos_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "expediente:j_idt371:header:inactive"))
            )
            recursos_tab.click()

            # Intentar recopilar datos de la tabla de recursos
            recursos = []
            wait.until(EC.visibility_of_element_located((By.ID, "expediente:j_idt371:content")))

            try:
                recursos_table = driver.find_element(By.ID, "expediente:recursosTable")
                tbody = recursos_table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    vinculados.append({
                        "Recurso": cols[0].text.strip(),
                        "Oficina de Elevacion": cols[1].text.strip(),
                        "Fecha de Presentacion": cols[2].text.strip(),
                        "Tipo de Recurso": cols[3].text.strip(),
                        "Estado Actual": cols[4].text.strip(),
                    })

            except NoSuchElementException:
                pass


            # Agregar los datos a la lista
            data.append({
                'Expediente': expediente,
                'Jurisdicción': jurisdiccion,
                'Dependencia': dependencia,
                'Situación': situacion,
                'Carátula': caratula,
                'Actuaciones': actuaciones,
                'Participantes': participants,
                'Fiscales': fiscales
            })


            # Volver a la página anterior (usando 'back' del navegador)
            driver.back()

            # Esperar que la tabla se recargue y esté lista para la siguiente iteración
            wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "table-striped")))
            rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]
    # Verificar si hay un botón "Siguiente" en la página
    try:
        siguiente_button = driver.find_element(By.ID, "j_idt118:j_idt208:j_idt215")
        if siguiente_button.is_displayed():  # Si el botón está visible
            siguiente_button.click()  # Hacer clic en "Siguiente"
            rows_changed = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:] 
            while rows_changed[0].text == primera_fila:
                time.sleep(0.5)
                rows_changed = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]
        else:
            break  # Si no hay botón "Siguiente", terminamos el loop
    except NoSuchElementException:
        break  # Si no encontramos el botón "Siguiente", terminamos el loop



# Imprimir los datos extraídos
# with open("data.json", "w", encoding="utf-8") as json_file:
#     json.dump(data, json_file, ensure_ascii=False, indent=4)

# Cerrar el navegador cuando termine
driver.quit()

file_path = "data.json"
# with open(file_path, "r", encoding="utf-8") as file:
#     data = json.load(file)
json_to_excel(data, "data.xlsx")  
#json_to_mysql(data, "localhost", "user", "password", "expedientes") 