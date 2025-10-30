Para empezar a correr el backend, se debe tener instalado uv.

```bash
uv sync
```

Luego, se debe correr el backend con el siguiente comando:

```bash
uv run uvicorn app.main:app --host localhost --port 8000 --reload
```

El backend se correrá en <http://localhost:8000>
