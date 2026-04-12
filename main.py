from fastapi import FastAPI, Depends

from urls.auth_router import auth_router
from urls.tracking_router import tracking_router
from auth.dependencies import get_current_user

app = FastAPI()
app.include_router(auth_router)
app.include_router(tracking_router)

@app.get("/", dependencies=[Depends(get_current_user)])
async def root():
    return {"message": "Hello World"}
