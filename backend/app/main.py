from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.observability import setup_observability
from app.routers import (
    audit,
    auth,
    dashboard,
    leases,
    maintenance,
    payments,
    properties,
    statements,
)

app = FastAPI(title="Property Management API")
setup_observability(app)
app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(leases.router)
app.include_router(payments.router)
app.include_router(maintenance.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(statements.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
