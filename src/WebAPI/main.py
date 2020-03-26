from typing import List

import uvicorn
from fastapi import FastAPI, Depends, Body

from proxy.storage import ProxyPoolStorage
from proxy.models import ProxyItem

app = FastAPI()

# Dependency
def get_storage():
    return ProxyPoolStorage()


@app.get("/", response_model=ProxyItem)
def get_default_random_proxy(storage: ProxyPoolStorage = Depends(get_storage)):
    return storage.get()

@app.get("/random", response_model=ProxyItem)
def get_random_proxy(random_range: int = 30, storage: ProxyPoolStorage = Depends(get_storage)):
    return storage.get_range_random(random_range)

@app.get("/all", response_model=List[ProxyItem])
def get_all(storage: ProxyPoolStorage = Depends(get_storage)):
    return storage.get_all()

@app.post("/activate")
def activate_proxy_item(item: ProxyItem = Body(...), storage: ProxyPoolStorage = Depends(get_storage)):
    suc = storage.activate(item)
    return {"state": suc}

@app.post("/deactivate")
def deactivate_proxy_item(item: ProxyItem = Body(...), storage: ProxyPoolStorage = Depends(get_storage)):
    suc = storage.deactivate(item)
    return {"state": suc}


if __name__ == "__main__":
    storage = ProxyPoolStorage()
    for index in range(100):
        storage.add(ProxyItem(
            ip="99.0.0.%s" % index,
            port=9999,
            https=False
        ))
    uvicorn.run(app, debug=True, use_colors=False)