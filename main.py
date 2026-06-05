from fastapi import FastAPI

app = FastAPI(
    title="JB-Hackathon AI Service",
    description="AI 에이전트 서빙을 위한 FastAPI 서버",
    version="1.0.0"
)

# GET Ping (http://ai-app:8000/)
@app.get("/")
def ping_get():
    return {"status": "success", "message": "pong (GET)"}

# POST Ping (http://ai-app:8000/ping)
@app.post("/ping")
async def ping_post():
    return {"status": "success", "message": "pong (POST)"}