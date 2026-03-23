from fastapi import FastAPI

app = FastAPI(title="Sistema de Control de Cansancio en Choferes")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
