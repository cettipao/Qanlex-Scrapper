# Importar librerías necesarias para el scraping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
from exportJson import json_to_excel, json_to_mysql
from dotenv import load_dotenv
from twocaptcha import TwoCaptcha
import os
import sys

# Cargar variables de entorno desde un archivo .env
load_dotenv()

# Determinar si estamos en un entorno de producción o no
PRODUCTION = os.getenv("PRODUCTION").lower() == "true"
api_key = os.getenv("APIKEY_2CAPTCHA")

# Configuración de la base de datos desde las variables de entorno
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

# Configuración de Selenium para el scraping
if PRODUCTION:
    # Opciones del navegador para producción (sin interfaz gráfica)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Modo sin interfaz gráfica
    chrome_options.add_argument("--no-sandbox")  # Necesario para entornos sin privilegios
    chrome_options.add_argument("--disable-dev-shm-usage")  # Soluciona problemas de memoria compartida en algunos sistemas
    chrome_options.add_argument("--disable-gpu")  # Opcional, puede mejorar la estabilidad
    chrome_options.add_argument("--window-size=1920,1080")  # Tamaño de la ventana virtual

    # Inicializar WebDriver con el ejecutable de ChromeDriver
    service = Service('/home/ubuntu/Qanlex-Scrapper/linux_driver/chromedriver')  # Ruta al ejecutable de ChromeDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

else:
    # Si no estamos en producción, usar el WebDriver estándar
    driver = webdriver.Chrome()


# Acceder a la página web para realizar el scraping
driver.get("http://scw.pjn.gov.ar/scw/home.seam")  # Sustituir con la URL de la página

# Esperar que el DOM de la página se cargue completamente
wait = WebDriverWait(driver, 10)

# Hacer clic en el botón "Por parte" para mostrar el formulario de búsqueda
por_parte_button = wait.until(EC.element_to_be_clickable((By.ID, "formPublica:porParte:header:inactive")))
por_parte_button.click()

# Esperar que el formulario se despliegue
wait.until(EC.visibility_of_element_located((By.ID, "formPublica:camaraPartes")))  # Esperar que el select de jurisdicción sea visible

# Interactuar con los campos dentro del formulario
# Seleccionar una jurisdicción, por ejemplo, "COM" que corresponde a la opción con value="10"
jurisdiccion_select = driver.find_element(By.ID, "formPublica:camaraPartes")
jurisdiccion_select.click()  # Hacer clic para mostrar las opciones
wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//select[@id='formPublica:camaraPartes']/option")))  # Esperar que las opciones estén visibles

# Seleccionar la jurisdicción "COM - Camara Nacional de Apelaciones en lo Comercial"
select = Select(jurisdiccion_select)
select.select_by_visible_text("COM - Camara Nacional de Apelaciones en lo Comercial")

# Ingresar "Residuos" en el campo "Parte
parte_input = driver.find_element(By.ID, "formPublica:nomIntervParte")
parte_input.send_keys("Residuos")  # Ingresar el valor "Residuos"

# Si api_key no esta vacio, resolver el CAPTCHA con el servicio de TwoCaptcha
if api_key:
    # Instanciar el servicio de resolución de CAPTCHA
    solver = TwoCaptcha(api_key)

    # Esperar que el CAPTCHA esté visible en la página
    captcha_iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")))

    # Cambiar al iframe donde se encuentra el CAPTCHA
    driver.switch_to.frame(captcha_iframe)

    try:
        captcha_token = solver.solve_captcha(
            site_key='6LcTJ1kUAAAAAJT1Xqu3gzANPfCbQG0nke9O5b6K', # Clave del sitio reCAPTCHA
            page_url=driver.current_url)
        
        driver.switch_to.default_content()

        # Ingresar el token del CAPTCHA en el campo correspondiente del formulario
        captcha_input = wait.until(EC.presence_of_element_located((By.ID, "g-recaptcha-response")))  # El campo donde se inserta el token
        driver.execute_script("arguments[0].style.display = 'block';", captcha_input)  # Hacer visible el campo si está oculto
        captcha_input.send_keys(captcha_token)

    except Exception as e:
        sys.exit(e)

# Si api_key esta vacio, resolver el CAPTCHA manualmente
else:
    input("Por favor, resuelve el CAPTCHA y presiona Enter para continuar...")


# Enviar el formulario para realizar la búsqueda
search_button = wait.until(EC.element_to_be_clickable((By.ID, "formPublica:buscarPorParteButton")))
search_button.click()

# Esperar el resultado (asumimos que el resultado se cargará en el DOM)
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "table-striped")))

# Extraer el contenido de la página usando BeautifulSoup
#soup = BeautifulSoup(driver.page_source, "html.parser")

rows = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]  # Saltar el encabezado

data = []  # Lista para almacenar los objetos con los datos

while True:
    # Obtengo el primer valor de rows para compararlo cuando cambie de página
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
            # Los datos solo aparecen al hacer clic en la pestaña
            intervinientes_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "expediente:j_idt261:header:inactive"))
            )
            intervinientes_tab.click()

            # Intentar recopilar datos de la tabla de participantes
            participants = []
            wait.until(EC.visibility_of_element_located((By.ID, "expediente:participantsTable")))
            participants_table = driver.find_element(By.ID, "expediente:participantsTable")
            tbodies = participants_table.find_elements(By.TAG_NAME, "tbody")

            """
            Aclaracion: 
            La tabla de intervinientes tiene como filas tbodys con distintos formatos
            """

            for tbody in tbodies:
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    # Filtrar filas visibles y con contenido útil
                    if row.is_displayed() and len(row.find_elements(By.TAG_NAME, "td")) > 1: # Verificar que la fila tenga al menos dos celdas
                        cols = row.find_elements(By.TAG_NAME, "td")
                        tipo = ""
                        nombre = ""
                        tomo_folio = ""
                        iej = ""

                        # A veces, el contenido a scrappear se encuentra dentro de un span con font-strong
                        # y hay que ignorar otros spans que solo tienen el nombre del atributo
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

            # Scrappeamos tambien los fiscales, si hay
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

            # Esperar que la tabla se recargue y esté lista para la siguiente iteración
            rows_changed = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:] 
            while rows_changed[0].text == primera_fila:
                time.sleep(0.5)
                rows_changed = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")[1:]

        else:
            break  # Si no hay botón "Siguiente", terminamos el loop
    except NoSuchElementException:
        break  # Si no encontramos el botón "Siguiente", terminamos el loop


driver.quit()
json_to_mysql(data, DB_HOST, DB_USER, DB_PASSWORD, DB_DATABASE)
json_to_excel(data, "data.xlsx")
