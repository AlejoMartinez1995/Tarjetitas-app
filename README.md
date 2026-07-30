# Tarjetitas App 💳📊

¡Bienvenido! **Tarjetitas App** es una solución integral y multiplataforma de gestión financiera personal orientada al control detallado de tarjetas de crédito. Desarrollada en **Python** utilizando **Flet**, la aplicación resuelve la descentralización de los resúmenes bancarios y la complejidad de proyectar cuotas futuras, compras en varios años y resúmenes compartidos.

La app se sincroniza automáticamente en la nube con un **Dashboard Ejecutivo en Google Sheets** personalizado para cada usuario, permitiendo registrar, visualizar y administrar consumos en tiempo real tanto desde la **APK móvil (Android)** como en escritorio.

---

## 🚀 Características Principales

* 📱 **Experiencia Móvil y Responsiva:** Interfaz en modo oscuro (*Midnight Dark + Electric Teal*) optimizada para dispositivos Android y escritorio con diseño reactivo.
* 📊 **Sincronización Cloud Automática:** Generación e inyección dinámica de datos directamente en tu propia planilla de Google Sheets sin depender de servidores externos.
* 🧮 **Parseador Inteligente de Montos:** Acepta formatos numéricos hispanos e internacionales (`1.500,50`, `1500.50`, etc.) de forma transparente.
* 📅 **Gestión Dinámica de Años y Cuotas:** Distribución automática de compras en cuotas a través de bucles dinámicos que se expanden a años futuros (`datetime.now().year`) sin límites fijos.
* 👥 **Soporte Multi-usuario y Responsables Libres:** Permite ingresar cualquier nombre de responsable e inserta automáticamente filas de totales consolidando gastos sin duplicaciones.
* 🗑️ **Gestión de Gastos y Borrado Atómico:** Lista interactiva con los últimos 5 gastos cargados en el mes. Al eliminar un gasto en cuotas, sus cuotas futuras en las pestañas de años siguientes se borran en cascada automáticamente.
* 🎨 **Dashboard Financiero Oscuro:** Diseño visual premium en Google Sheets con paletas desaturadas, celdas unificadas y fórmulas dinámicas `SUMIF` / `SUM` localizadas en español.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 🐍 (Lógica de negocio, cálculos de cuotas y estructuración de datos).
* **UI Framework:** Flet 💻📱 (Construcción de interfaz nativa cross-platform).
* **Integración Cloud:** `gspread` & `google-auth` ☁️ (Conexión segura y liviana con Google Sheets & Drive API).
* **Empaquetado Android:** `serious_python` / `flet build apk` 📦 (APK optimizada de ~210 MB libre de caché conflictivo).

---

## 📦 Estructura del Proyecto

```text
Tarjetita/
├── main.py              # Punto de entrada, UI de Flet y lógica de conexión a Google Sheets
├── requirements.txt     # Dependencias de producción (flet, gspread, google-auth, certifi)
├── creds.example.json   # Plantilla de estructura para la Service Account de Google
├── .gitignore           # Exclusión de entornos virtuales, APKs compiladas y creds.json
└── assets/              # Recursos estáticos y multimedia de la aplicación
```
---

## ⚙️ Instalación y Configuración Local
Si querés probar o desplegar la aplicación en tu entorno local, seguí estos pasos:

**1. Clonar el repositorio**

  Bash
  git clone [https://github.com/AlejoMartinez1995/Tarjetitas-app.git](https://github.com/AlejoMartinez1995/Tarjetitas-app.git)
  cd Tarjetitas-app

**2. Crear y activar un entorno virtual**

  Bash
  python -m venv venv

**En Windows:**

  venv\Scripts\activate

**En Linux/Mac:**

  source venv/bin/activate

**3. Instalar dependencias**

  Bash
  pip install -r requirements.txt

**4. Configurar las Credenciales de Google Cloud**

Para que la app pueda interactuar con Google Sheets:

  * Creá un proyecto en Google Cloud Console.
  * Habilitá la Google Sheets API y la Google Drive API.
  * Creá una Service Account y descargá el archivo de clave JSON.
  * Renombrá ese archivo a creds.json y colocalo en la raíz de este proyecto.
  * (Opcional) En tu Google Drive personal, creá una carpeta compartida y dale permisos de
    Editor al email de tu Service Account.

**5. Ejecutar la aplicación**

  Bash
  python main.py

## 📸 Vista previa de la aplicación
<table>
  <tr>
    <td align="center">
      <img width="300" alt="Vista Mobile 1" src="https://github.com/user-attachments/assets/26511167-e89d-46dd-8c76-af4c5b5fe1c8" />
    </td>
    <td align="center">
      <img width="300" alt="Vista Mobile 2" src="https://github.com/user-attachments/assets/40616e0f-44de-414e-84de-3a996481a5c7" />
    </td>
  </tr>
</table>

