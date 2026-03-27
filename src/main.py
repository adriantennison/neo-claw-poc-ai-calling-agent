from fastapi import FastAPI
from dotenv import load_dotenv
from routes.calls import router as calls_router

load_dotenv()

app = FastAPI(title="AI Calling Agent")
app.include_router(calls_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
