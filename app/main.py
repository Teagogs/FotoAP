import sys
import os
from multiprocessing import freeze_support

# Adiciona o diretório pai ao path para permitir importações relativas
# Isso é útil ao executar o script diretamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ui.main_window import PhotoFinderApp

if __name__ == "__main__":
    # Necessário para o multiprocessing funcionar em executáveis (PyInstaller)
    freeze_support()
    
    app = PhotoFinderApp()
    app.mainloop()