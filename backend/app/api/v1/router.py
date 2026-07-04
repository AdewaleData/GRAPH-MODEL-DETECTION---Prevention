from fastapi import APIRouter

from . import alerts, auth, demo, graph, metrics, mitigation, predict

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(predict.router)
api_router.include_router(metrics.router)
api_router.include_router(alerts.router)
api_router.include_router(graph.router)
api_router.include_router(mitigation.router)
api_router.include_router(demo.router)
