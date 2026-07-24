import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from inicio.login import VentanaLogin
from inicio.splash import mostrar_splash
from db.database import inicializar_base_datos
from config import settings
from config.settings import DEV_MODE
from ventana_principal.principal import VentanaPrincipal

def manejar_excepcion(exctype, value, tb):
    print("❌ EXCEPCIÓN NO DETECTADA:")
    traceback.print_exception(exctype, value, tb)
sys.excepthook = manejar_excepcion

ruta_script = os.path.dirname(os.path.abspath(__file__))
ruta_recursos = os.path.join(ruta_script, "resources")
splash_path = os.path.join(ruta_recursos, "splash.png")
logo_path = os.path.join(ruta_recursos, "logo.png")

APP_UNICA = "MI_APLICACION_UNICA"
TIEMPO_SPLASH_MS = 3000
TEXT_INSTANCIA_EJECUCION = "LA APLICACION YA SE ESTÁ EJECUTANDO."
TEXT_INSTANCIA_EJECUCION_2 = "INSTANCIA EN EJECUCIÓN"
ventana_login = None
ventana_principal = None

def main():
    try:
        print("🟢 Iniciando aplicación...")
        inicializar_base_datos()
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(logo_path))
        #app.setWindowIcon(QIcon(logo_path))
        socket = QLocalSocket()
        socket.connectToServer(APP_UNICA)
        if socket.waitForConnected(100):
            QMessageBox.warning(None, TEXT_INSTANCIA_EJECUCION_2, TEXT_INSTANCIA_EJECUCION)
            sys.exit(0)
        else:
            server = QLocalServer()
            server.listen(APP_UNICA)
        def lanzar_login():
            global ventana_login, ventana_principal
            try:
                if DEV_MODE:
                    print("🟡 Dev mode — auto login as admin")
                    ventana_principal = VentanaPrincipal("admin")
                    ventana_principal.show()
                else:
                    print("📥 Mostrando ventana de login...")
                    ventana_login = VentanaLogin()
                    ventana_login.show()
                    print("✅ Login mostrado correctamente.")
            except Exception as e:
                print("❌ Error al lanzar login:")
                traceback.print_exc()
        mostrar_splash(splash_path, TIEMPO_SPLASH_MS, lanzar_login)
        def limpiar_y_salir():
            print("🔴 Cerrando aplicación...")
            server.close()
            server.removeServer(APP_UNICA)
            app.quit()
        app.aboutToQuit.connect(limpiar_y_salir)
        sys.exit(app.exec_())
    except Exception as e:
        print("❌ Error al iniciar la aplicación:")
        traceback.print_exc()

if __name__ == "__main__":
    main()