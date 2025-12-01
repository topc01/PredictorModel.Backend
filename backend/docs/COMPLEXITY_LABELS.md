# Complexity Labels - Sistema de Complejidades

## Descripción General

El sistema maneja diferentes niveles de complejidad hospitalaria. Debido a que algunos nombres contienen tildes (acentos), se implementó un sistema de mapeo bidireccional entre:

- **Labels (API)**: Nombres sin tildes, usados en endpoints de la API
- **Real Names**: Nombres reales con tildes, usados en CSVs y almacenamiento

## Complejidades Disponibles

| API Label (sin tildes) | Nombre Real (con tildes) | Uso en API |
|------------------------|--------------------------|------------|
| `Baja` | Baja | `/predict/baja` |
| `Media` | Media | `/predict/media` |
| `Alta` | Alta | `/predict/alta` |
| `Neonatologia` | Neonatología | `/predict/neonatologia` |
| `Pediatria` | Pediatría | `/predict/pediatria` |
| `IntePediatrico` | Inte. Pediátrico | `/predict/intepediatrico` |
| `Maternidad` | Maternidad | `/predict/maternidad` |

## Uso en la API

### Endpoints de Predicción

```bash
# Usar labels en minúsculas (sin tildes)
GET /predict/baja
GET /predict/media
GET /predict/alta
GET /predict/neonatologia
GET /predict/pediatria
GET /predict/intepediatrico
GET /predict/maternidad
```

### Listar Complejidades Disponibles

```bash
GET /models/complexities
```

**Respuesta:**
```json
{
  "complexities": [
    {
      "label": "baja",
      "real_name": "Baja",
      "description": "Use 'baja' in API requests"
    },
    {
      "label": "neonatologia",
      "real_name": "Neonatología",
      "description": "Use 'neonatologia' in API requests"
    },
    ...
  ]
}
```

## Uso en el Código

### ComplexityMapper

La clase `ComplexityMapper` en `app/utils/complexities.py` centraliza todo el mapeo de complejidades.

#### Convertir Label → Nombre Real

```python
from app.utils.complexities import ComplexityMapper

# Convertir label de API a nombre real
real_name = ComplexityMapper.to_real_name("Neonatologia")
# Resultado: "Neonatología"
```

#### Convertir Nombre Real → Label

```python
from app.utils.complexities import ComplexityMapper

# Convertir nombre real a label de API
label = ComplexityMapper.to_label("Neonatología")
# Resultado: "Neonatologia"
```

#### Parsear Input de API (case-insensitive)

```python
from app.utils.complexities import ComplexityMapper

# Acepta input en minúsculas de la API
real_name = ComplexityMapper.parse_from_api("neonatologia")
# Resultado: "Neonatología"

real_name = ComplexityMapper.parse_from_api("alta")
# Resultado: "Alta"
```

#### Validación

```python
from app.utils.complexities import ComplexityMapper

# Validar si un label es válido
is_valid = ComplexityMapper.is_valid_label("Neonatologia")  # True
is_valid = ComplexityMapper.is_valid_label("InvalidLabel")  # False

# Validar si un nombre real es válido
is_valid = ComplexityMapper.is_valid_real_name("Neonatología")  # True
```

#### Obtener Todas las Complejidades

```python
from app.utils.complexities import ComplexityMapper

# Obtener todos los labels
labels = ComplexityMapper.get_all_labels()
# ['Baja', 'Media', 'Alta', 'Neonatologia', 'Pediatria', 'IntePediatrico', 'Maternidad']

# Obtener todos los nombres reales
real_names = ComplexityMapper.get_all_real_names()
# ['Baja', 'Media', 'Alta', 'Neonatología', 'Pediatría', 'Inte. Pediátrico', 'Maternidad']
```

## Estructura de Archivos

### CSVs (usan nombres reales con tildes)

```
data/
├── dataset.csv          # Columna "complejidad" usa nombres reales
├── predictions.csv      # Usa nombres reales
└── weekly.csv          # Usa nombres reales
```

**Ejemplo de dataset.csv:**
```csv
complejidad,demanda_pacientes,semana_año
Neonatología,45,2024-W01
Pediatría,60,2024-W01
Inte. Pediátrico,30,2024-W01
```

### Modelos (usan labels sin tildes en paths)

```
models/
├── Baja/
│   └── v_2024-11-28_17-18-28/
│       ├── model.pkl
│       └── metadata.json
├── Neonatologia/              # Label sin tilde
│   └── v_2024-11-28_17-18-28/
│       ├── model.pkl
│       └── metadata.json (complexity: "Neonatología")
└── IntePediatrico/            # Label sin tilde ni punto
    └── v_2024-11-28_17-18-28/
        ├── model.pkl
        └── metadata.json (complexity: "Inte. Pediátrico")
```

**Nota:** Los directorios usan labels (sin tildes) para evitar problemas de filesystem, pero el metadata.json dentro contiene el nombre real.

## Migración desde el Sistema Anterior

### Antes (código disperso)

```python
# En predict.py
def parse(complexity: str) -> str:
    match complexity:
        case 'neonatologia':
            return 'Neonatología'
        case 'pediatria':
            return 'Pediatría'
        ...

# En version.py
def label(complexity: str) -> str:
    if complexity == "Neonatología":
        return "Neonatologia"
    ...

# En retrain.py
complexity = complexity.replace("Neonatologia", "Neonatología")
```

### Ahora (centralizado)

```python
from app.utils.complexities import ComplexityMapper

# En predict.py
real_complexity = ComplexityMapper.parse_from_api(complexity)

# En version.py
label = ComplexityMapper.to_label(real_name)

# En retrain.py
if ComplexityMapper.is_valid_label(complexity):
    complexity = ComplexityMapper.to_real_name(complexity)
```

## Ejemplos de Uso Completo

### Endpoint de Predicción

```python
from fastapi import APIRouter, HTTPException
from app.utils.complexities import ComplexityMapper

@router.get("/predict/{complexity}")
async def predict_complexity(complexity: str):
    try:
        # Parsear input de API (case-insensitive)
        real_complexity = ComplexityMapper.parse_from_api(complexity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Usar el nombre real para cargar datos/modelo
    prediction = make_prediction(real_complexity)
    return prediction
```

### Reentrenamiento de Modelos

```python
from app.utils.complexities import ComplexityMapper

def retrain_all_models():
    # Iterar sobre todas las complejidades
    for real_name in ComplexityMapper.get_all_real_names():
        print(f"Retraining {real_name}...")
        retrain_model(real_name)
```

### Cargar Datos desde CSV

```python
from app.utils.complexities import ComplexityMapper

def load_data(complexity: str):
    # Convertir label a nombre real si es necesario
    if ComplexityMapper.is_valid_label(complexity):
        complexity = ComplexityMapper.to_real_name(complexity)
    
    # Filtrar CSV por nombre real
    df = pd.read_csv("dataset.csv")
    df = df[df["complejidad"] == complexity]
    return df
```

## Ventajas del Sistema Centralizado

1. **Single Source of Truth**: Todas las complejidades definidas en un solo lugar
2. **Validación Automática**: Errores claros si se usa una complejidad inválida
3. **Bidireccional**: Conversión fácil en ambas direcciones
4. **Case-Insensitive**: La API acepta input en minúsculas
5. **Documentación Clara**: Tabla visual de todas las complejidades disponibles
6. **Mantenibilidad**: Agregar nuevas complejidades es trivial
7. **Type Safety**: Métodos con tipos claros y documentación

## Agregar una Nueva Complejidad

Para agregar una nueva complejidad, solo necesitas actualizar `ComplexityMapper`:

```python
class ComplexityMapper:
    _COMPLEXITY_MAP = {
        "Baja": "Baja",
        "Media": "Media",
        "Alta": "Alta",
        "Neonatología": "Neonatologia",
        "Pediatría": "Pediatria",
        "Inte. Pediátrico": "IntePediatrico",
        "Maternidad": "Maternidad",
        "Nueva Complejidad": "NuevaComplejidad"  # ← Agregar aquí
    }
```

Automáticamente estará disponible en:
- Todos los endpoints de la API
- El endpoint `/models/complexities`
- Validaciones en toda la aplicación
- Reentrenamiento de modelos
