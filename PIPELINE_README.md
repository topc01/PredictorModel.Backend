# Pipeline de Limpieza de Datos

Este documento describe el pipeline de limpieza de datos implementado basado en el notebook `Limpieza.ipynb`.

## 📋 Descripción General

El pipeline procesa archivos Excel con datos hospitalarios crudos y genera datasets limpios por complejidad, listos para entrenamiento de modelos de predicción.

## 🏗️ Arquitectura

```
backend/src/
├── pipeline/
│   ├── __init__.py
│   ├── data_cleaner.py           # Limpieza inicial del Excel
│   └── prediction_preparer.py    # Preparación de datos para predicción
├── routes/
│   ├── data.py                   # Endpoints para datos semanales (EXISTENTES)
│   └── pipeline.py               # Endpoints para procesamiento de Excel (NUEVOS)
└── utils/
    └── storage.py                # Gestión de almacenamiento (local/S3)
```

## 🔌 Nuevos Endpoints

### 1. `POST /pipeline/process-excel`

Procesa un archivo Excel crudo y genera CSVs por complejidad.

**Entrada:**

- Archivo Excel (.xlsx o .xls) con formato específico

**Requisitos del Excel:**

- **Mínimo 3 hojas**
- **Hoja 0**: Datos de pacientes
  - `Servicio Ingreso (Código)`
  - `Fecha Ingreso Completa`
  - `Estancia (Días)`
  - `Tipo de Paciente`
  - `Tipo de Ingreso`
- **Hoja 2**: Datos de servicios
  - `UO trat.`
  - `Complejidad`

**Proceso:**

1. Limpieza y normalización
2. Merge de hojas
3. Features temporales (semana, mes, estación)
4. One-hot encoding
5. Agrupación semanal
6. Creación de lags (1, 2, 3, 4, 10, 52 semanas)
7. Generación de CSVs

**Salida:**

```json
{
  "message": "Archivo procesado exitosamente",
  "complejidades_procesadas": {
    "Alta": "Procesada exitosamente",
    "Baja": "Procesada exitosamente",
    "Media": "Procesada exitosamente",
    "Neonatología": "Datos insuficientes",
    "Pediatría": "Procesada exitosamente"
  },
  "archivos_generados": {
    "Alta": "./data/Alta.csv",
    "Baja": "./data/Baja.csv",
    "Media": "./data/Media.csv",
    "Pediatría": "./data/Pediatría.csv"
  },
  "estadisticas": {
    "Alta": {"filas": 120, "columnas": 18},
    "Baja": {"filas": 98, "columnas": 18}
  },
  "timestamp": "2025-10-26T12:30:45"
}
```

### 2. `GET /pipeline/download/{complejidad}`

Descarga el CSV procesado de una complejidad específica.

**Parámetros:**

- `complejidad`: Alta | Media | Baja | Neonatología | Pediatría

**Salida:**

- Archivo CSV descargable

### 3. `GET /pipeline/download-all`

Descarga un ZIP con todos los CSVs procesados.

**Salida:**

- Archivo ZIP con CSVs de todas las complejidades procesadas

### 4. `GET /pipeline/status`

Obtiene el estado del pipeline y archivos disponibles.

**Salida:**

```json
{
  "message": "Estado del pipeline",
  "total_complejidades": 5,
  "archivos_procesados": 4,
  "storage_type": "local",
  "complejidades": {
    "Alta": {
      "procesado": true,
      "filas": 120,
      "columnas": 18,
      "ultima_semana": "2024-52"
    },
    "Media": {
      "procesado": true,
      "filas": 98,
      "columnas": 18,
      "ultima_semana": "2024-51"
    }
  }
}
```

## 📊 Formato de Datos de Salida

Cada CSV generado contiene las siguientes columnas:

```
semana_año                          # Identificador YYYY-WW
demanda_pacientes                   # Variable objetivo (a predecir)
demanda_lag1                        # Demanda de hace 1 semana
demanda_lag2                        # Demanda de hace 2 semanas
demanda_lag3                        # Demanda de hace 3 semanas
demanda_lag4                        # Demanda de hace 4 semanas
demanda_lag10                       # Demanda de hace 10 semanas
demanda_lag52                       # Demanda de hace 52 semanas (1 año)
estancia (días)_lag1               # Estancia promedio (semana anterior)
tipo de paciente_No Qx_lag1        # Proporción no quirúrgicos
tipo de paciente_Qx_lag1           # Proporción quirúrgicos
tipo de ingreso_No Urgente_lag1    # Proporción no urgentes
tipo de ingreso_Urgente_lag1       # Proporción urgentes
estacion_invierno_lag1             # One-hot: invierno
estacion_otoño_lag1                # One-hot: otoño
estacion_primavera_lag1            # One-hot: primavera
estacion_verano_lag1               # One-hot: verano
numero_semana                       # Número de semana (1-52)
```

## 💾 Almacenamiento

El sistema soporta dos modos de almacenamiento:

### Modo Local (Desarrollo)

```bash
# Variables de entorno
STORAGE_TYPE=local
STORAGE_BASE_PATH=./data
```

Los archivos se guardan en el directorio `./data/`

### Modo S3 (Producción/Lambda)

```bash
# Variables de entorno
STORAGE_TYPE=s3
STORAGE_BASE_PATH=hospital-data
S3_BUCKET=mi-bucket-nombre
```

Los archivos se guardan en S3: `s3://mi-bucket-nombre/hospital-data/`

## 🚀 Uso

### 1. Instalar dependencias

```bash
cd backend
uv sync

# Para soporte S3 (opcional)
uv sync --extra aws
```

### 2. Iniciar servidor

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Procesar Excel

```bash
curl -X POST http://localhost:8000/pipeline/process-excel \
  -F "file=@Datos_UC.xlsx"
```

O usar la interfaz Swagger: <http://localhost:8000/docs>

### 4. Verificar estado

```bash
curl http://localhost:8000/pipeline/status
```

### 5. Descargar CSVs

```bash
# Un archivo específico
curl -O http://localhost:8000/pipeline/download/Alta

# Todos los archivos
curl -O http://localhost:8000/pipeline/download-all
```

## 🔄 Endpoints Existentes vs Nuevos

### Endpoints EXISTENTES (`/data/*`)

- `POST /data/send` - Recibir datos semanales (JSON)
- `POST /data/upload` - Subir Excel con datos semanales
- `GET /data/template` - Descargar plantilla

**Propósito:** Recibir datos semanales NUEVOS para hacer predicciones

### Endpoints NUEVOS (`/pipeline/*`)

- `POST /pipeline/process-excel` - Procesar Excel crudo inicial
- `GET /pipeline/download/{complejidad}` - Descargar CSV procesado
- `GET /pipeline/download-all` - Descargar todos los CSVs
- `GET /pipeline/status` - Ver estado del pipeline

**Propósito:** Limpieza inicial de datos históricos para entrenar modelos

## 🧪 Testing

### Test con curl

```bash
# 1. Subir y procesar Excel
curl -X POST http://localhost:8000/pipeline/process-excel \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Datos_UC.xlsx"

# 2. Ver estado
curl http://localhost:8000/pipeline/status

# 3. Descargar CSV específico
curl -O http://localhost:8000/pipeline/download/Alta

# 4. Descargar todo
curl -O http://localhost:8000/pipeline/download-all
```

### Test con Python

```python
import requests

# Procesar Excel
with open('Datos_UC.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/pipeline/process-excel',
        files={'file': f}
    )
    print(response.json())

# Ver estado
status = requests.get('http://localhost:8000/pipeline/status')
print(status.json())

# Descargar CSV
csv = requests.get('http://localhost:8000/pipeline/download/Alta')
with open('Alta.csv', 'wb') as f:
    f.write(csv.content)
```

## 📦 Deployment en Lambda

### Configuración

1. **Variables de entorno:**

```
STORAGE_TYPE=s3
STORAGE_BASE_PATH=hospital-data
S3_BUCKET=mi-bucket-nombre
```

2. **Permisos IAM:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::mi-bucket-nombre/hospital-data/*"
    }
  ]
}
```

3. **Lambda Layer:**

- pandas
- numpy
- openpyxl
- boto3

### Consideraciones

- **Timeout:** Configurar al menos 5 minutos
- **Memoria:** Mínimo 512MB, recomendado 1GB
- **Tamaño del Excel:** Máximo 50MB para Lambda
- **Procesamiento:** ~1-3 minutos por archivo típico

## 🐛 Troubleshooting

### Error: "El archivo debe tener al menos 3 hojas"

**Solución:** Verificar que el Excel tenga el formato correcto con 3+ hojas

### Error: "Datos insuficientes (< 55 semanas)"

**Solución:** La complejidad no tiene suficientes datos históricos, es normal

### Error: "File not found"

**Solución:** Primero procesar el Excel con `/pipeline/process-excel`

### Error de importación de pandas/numpy

**Solución:** Ejecutar `uv sync` para instalar dependencias

## 📝 Notas

- Las complejidades con menos de 55 semanas NO serán procesadas
- Neonatología no tiene filtro mínimo de demanda (vs. otras que requieren ≥10 pacientes/semana)
- Los lags se crean automáticamente: 1, 2, 3, 4, 10, 52 semanas
- Las columnas de servicios poco frecuentes se eliminan automáticamente

## 🔗 Referencias

- Notebook original: `Limpieza.ipynb`
- FastAPI docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
