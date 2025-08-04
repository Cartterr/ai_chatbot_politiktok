#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  TikTok Research Chatbot Launcher${NC}"
echo -e "${BLUE}=====================================${NC}"
echo

# Get Windows host IP (for WSL2)
WINDOWS_HOST=$(ip route show | grep -i default | awk '{print $3}')
if [ -z "$WINDOWS_HOST" ]; then
    WINDOWS_HOST="172.19.16.1"  # fallback
fi

echo -e "${YELLOW}Verificando Ollama en ${WINDOWS_HOST}:11434...${NC}"
echo

# Check if Ollama is running
if ! curl -s "http://${WINDOWS_HOST}:11434/" > /dev/null 2>&1; then
    echo -e "${RED}❌ Ollama no está ejecutándose en ${WINDOWS_HOST}:11434${NC}"
    echo -e "${YELLOW}Por favor inicia Ollama en Windows primero.${NC}"
    exit 1
fi

echo -e "${YELLOW}Verificando modelo qwen3:4b...${NC}"
echo

# Check if the required model is available
if ! curl -s "http://${WINDOWS_HOST}:11434/api/tags" | grep -q "qwen3:4b"; then
    echo -e "${RED}❌ Modelo qwen3:4b no encontrado${NC}"
    echo -e "${YELLOW}Descargando modelo qwen3:4b...${NC}"
    curl -X POST "http://${WINDOWS_HOST}:11434/api/pull" \
         -H "Content-Type: application/json" \
         -d '{"name": "qwen3:4b"}'
fi

echo -e "${YELLOW}Verificando directorio de datos...${NC}"
if [ ! -d "data" ]; then
    echo -e "${RED}❌ Directorio data/ no encontrado.${NC}"
    echo -e "${YELLOW}Creando directorio data/...${NC}"
    mkdir -p data
else
    echo -e "${GREEN}✅ Directorio data/ encontrado.${NC}"
    CSV_COUNT=$(find data -name "*.csv" | wc -l)
    PARQUET_COUNT=$(find data -name "*.parquet" | wc -l)
    echo -e "${BLUE}Se encontraron ${CSV_COUNT} archivos CSV y ${PARQUET_COUNT} archivos Parquet.${NC}"
fi
echo

echo -e "${YELLOW}Configurando entorno virtual para el backend...${NC}"
if [ ! -d "backend/venv" ]; then
    echo -e "${BLUE}Creando entorno virtual...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo -e "${GREEN}✅ Entorno virtual ya existe.${NC}"
fi
echo

echo -e "${YELLOW}Instalando dependencias del frontend...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}Instalando dependencias...${NC}"
    cd frontend
    npm install
    cd ..
else
    echo -e "${GREEN}✅ Dependencias ya instaladas.${NC}"
fi
echo

echo -e "${YELLOW}Iniciando backend y frontend...${NC}"
echo -e "${BLUE}Usando Ollama en: http://${WINDOWS_HOST}:11434${NC}"

# Set the Ollama base URL for the backend
export OLLAMA_BASE_URL="http://${WINDOWS_HOST}:11434"

echo "Usando Ollama en: $OLLAMA_BASE_URL"

# Check if concurrently is available
if command -v concurrently &> /dev/null; then
    echo "Iniciando backend y frontend con concurrently..."
    cd "$SCRIPT_DIR"
    concurrently \
        --names "BACKEND,FRONTEND" \
        --prefix-colors "blue,green" \
        "cd $SCRIPT_DIR/backend && source venv/bin/activate && python app.py" \
        "cd $SCRIPT_DIR/frontend && npm run dev"
else
    echo "concurrently no está instalado. Iniciando servicios en terminales separados..."

    # Try to open backend in a new terminal
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR/backend' && source venv/bin/activate && python app.py; exec bash"
        echo "✅ Backend iniciado en nueva terminal"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd '$SCRIPT_DIR/backend' && source venv/bin/activate && python app.py; exec bash" &
        echo "✅ Backend iniciado en nueva terminal"
    else
        echo "No se pudo abrir una nueva terminal para el backend."
        echo "Iniciando backend en segundo plano..."
        cd "$SCRIPT_DIR/backend"
        source venv/bin/activate
        nohup python app.py > ../backend.log 2>&1 &
        BACKEND_PID=$!
        echo "✅ Backend iniciado en segundo plano (PID: $BACKEND_PID)"
        echo "Los logs del backend se guardan en backend.log"
        echo ""
        echo "Para ver los logs del backend en tiempo real, ejecuta:"
        echo "  tail -f backend.log"
        echo ""
        echo "El backend estará disponible en: http://localhost:8001"
        echo ""
    fi

    # Start frontend
    echo "Iniciando frontend..."
    cd "$SCRIPT_DIR/frontend"
    npm run dev
fi