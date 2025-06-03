#!/bin/bash

# Nombre del entorno virtual
VENV_DIR="venv"

# 1. Crear el entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv $VENV_DIR
fi

# 2. Activar el entorno virtual
source $VENV_DIR/bin/activate

# 3. Instalar dependencias
if [ -f requirements.txt ]; then
    echo "Instalando dependencias..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No se encontró requirements.txt, instalando dependencias principales..."
    pip install websockets
fi

# 4. Ejecutar la aplicación
echo "Iniciando la aplicación..."
python main.py
