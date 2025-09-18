from fastapi import FastAPI
from starlette.requests import Request

from src.api import contacts, utils

app = FastAPI()

app.include_router(utils.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")


@app.get("/")
def read_root(request: Request):
    return {"message": "Contacts Application v1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
