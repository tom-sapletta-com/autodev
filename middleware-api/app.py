from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "OK", "msg": "Middleware API działa"}
