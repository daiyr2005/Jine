from fastapi import FastAPI
from mysite.api import todos, meetings
from  mysite.bot import telagram
import uvicorn

app = FastAPI()
app.include_router(todos.router)
app.include_router(meetings.router)
#app.include_router(telagram.router)


if __name__ == "__main__":
    uvicorn.run("mysite.main:app" if False else "main:app", host="127.0.0.1", port=8001, reload=True)