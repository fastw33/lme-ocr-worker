# LME OCR Worker

Microservicio FastAPI para extraer datos estructurados desde capturas tipo tarjeta de mercado LME/SMM.

El worker no guarda en base de datos ni decide reglas de negocio. Solo recibe imagenes y devuelve JSON normalizado para que la API LME valide, revise y persista.

## Ejecutar

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8020
```

## Endpoints

- `GET /health`
- `POST /extract/lme-market-card`

El endpoint acepta uno o varios archivos en el campo `files`.

## Prueba local

```powershell
python scripts\extract_folder.py "C:\Users\tech\Downloads\tungten"
```
