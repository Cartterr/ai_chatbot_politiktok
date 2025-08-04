# TikTok Research Chatbot

Este proyecto es un chatbot de investigación que analiza datos de TikTok sobre jóvenes chilenos discutiendo política. El sistema permite explorar espacios de educación política y alfabetizaciones políticas digitales en TikTok.

## Características

- 🤖 Chatbot alimentado por Ollama (Mistral)
- 📊 Visualización de datos interactiva
- 🔍 Búsqueda semántica en el corpus de datos
- 📈 Análisis de sentimientos en videos de TikTok
- 🔗 Análisis de redes de usuarios y temas

## Estructura del Proyecto

```
tiktok-research-chatbot/
├── backend/            # API FastAPI
├── frontend/           # Aplicación React
└── data/               # Archivos de datos CSV/Parquet
```

## Requisitos

- Python 3.8+ para el backend
- Node.js 14+ para el frontend
- Ollama instalado localmente con el modelo `bsahane/Mistral-Small-3.1:24b`

## Configuración

### 1. Preparar los datos

Coloque los archivos CSV o Parquet en el directorio `data/`:

- `cuentas_info.csv` o `cuentas_info.parquet`
- `combined_tiktok_data_cleaned_with_date.csv` o `combined_tiktok_data_cleaned_with_date.parquet`
- `data.csv` o `data.parquet`
- `subtitulos_videos_v3.csv` o `subtitulos_videos_v3.parquet`

### 2. Instalar el backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Instalar el frontend

```bash
cd frontend
npm install
```

## Ejecución del Sistema

### Iniciar Ollama (asegúrate de tener el modelo cargado)

```bash
# Verifica que el modelo esté disponible
ollama list

# Si necesitas descargar el modelo
ollama pull bsahane/Mistral-Small-3.1:24b
```

### Iniciar el Backend

```bash
cd backend
source venv/bin/activate  # En Windows: venv\Scripts\activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Iniciar el Frontend

```bash
cd frontend
npm run dev
```

El frontend estará disponible en: http://localhost:3000

## Exponer con Ngrok

Para hacer accesible el sistema a través de Internet:

```bash
# Exponer el backend (puerto 8000)
ngrok http 8000

# Exponer el frontend (puerto 3000)
ngrok http 3000
```

## Uso del Sistema

1. **Chatbot**: Realiza preguntas sobre los jóvenes chilenos en TikTok, sus discusiones políticas, temas de interés, etc.
2. **Visualizaciones**: Solicita gráficos específicos como "Muestra la distribución de perspectivas políticas" o "Analiza la evolución temporal de los videos"
3. **Resumen de datos**: Accede a una vista general de los datos disponibles

## Comandos Útiles

Para iniciar todo el sistema con un solo comando:

```bash
# Instala concurrently si no lo tienes
npm install -g concurrently

# Inicia backend y frontend simultáneamente
concurrently "cd backend && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000" "cd frontend && npm run dev"
```