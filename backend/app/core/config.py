"""Application configuration — non-secrets hardcoded; JWT secret from environment only."""

from pathlib import Path
import os

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CIC_DDOS_CSV_PATH = PROJECT_ROOT / "CICDDoS.csv"
SIMULATOR_CSV_FALLBACK = PROJECT_ROOT / "artifacts" / "data" / "cicddos_sample.csv"


def resolve_simulator_csv_path() -> Path:
    """Full dataset locally, bundled sample in Docker/cloud."""
    override = os.getenv("CIC_DDOS_CSV_PATH", "").strip()
    if override:
        return Path(override)
    if CIC_DDOS_CSV_PATH.exists():
        return CIC_DDOS_CSV_PATH
    return SIMULATOR_CSV_FALLBACK


ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODELS_DIR = ARTIFACTS_DIR / "models"
GCN_MODEL_PATH = MODELS_DIR / "gcn_best.pt"
GAT_MODEL_PATH = MODELS_DIR / "gat_best.pt"
RF_BUNDLE_PATH = MODELS_DIR / "rf_bundle.joblib"
FEATURE_COLS_PATH = MODELS_DIR / "feature_cols.joblib"
DB_DIR = ARTIFACTS_DIR / "backend"
DB_PATH = DB_DIR / "ddos.db"

# API
APP_NAME = "Halal Graph DDoS Detection API"
APP_VERSION = "1.0.0"
API_V1_PREFIX = "/api/v1"
HOST = "0.0.0.0"
PORT = 8000
DEBUG = False

# Security (override JWT_SECRET in .env for production)

JWT_SECRET = os.getenv("JWT_SECRET", "halal-graph-ddos-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
BCRYPT_ROUNDS = 12

# Default bootstrap admin (change password after first login)
DEFAULT_ADMIN_EMAIL = "admin@gmail.com"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"

# CORS
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]

# Rate limiting
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60

# Redis (optional — set REDIS_URL to enable)
REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_PREDICTION_TTL_SECONDS = 30

# Inference
INFERENCE_DEVICE = "cpu"  # cuda if available at runtime
GNN_BATCH_SIZE = 64
GRAPH_MIN_FLOWS = 12
FLOW_BUFFER_MAX_PER_VICTIM = 48

PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

# Model loading (disable GAT/RF on low-RAM cloud — GCN is the primary detector)
_default_gat = "false" if os.getenv("PRODUCTION", "false").lower() == "true" else "true"
_default_rf = "false" if os.getenv("PRODUCTION", "false").lower() == "true" else "true"
LOAD_GCN = os.getenv("LOAD_GCN", "true").lower() == "true"
LOAD_GAT = os.getenv("LOAD_GAT", _default_gat).lower() == "true"
LOAD_RF = os.getenv("LOAD_RF", _default_rf).lower() == "true"

# Alerts
ALERT_PROB_THRESHOLD = 0.62  # matches tuned GCN threshold from training
SEVERITY_HIGH = 0.85
SEVERITY_MEDIUM = 0.65

# TLS-ready (terminate TLS at reverse proxy in production)
TLS_ENABLED = False

# Live demo stream (real CICDDoS samples through GNN pipeline)
LIVE_SIMULATOR_ENABLED = os.getenv("LIVE_SIMULATOR_ENABLED", "true").lower() == "true"
LIVE_SIMULATOR_INTERVAL_SECONDS = int(os.getenv("LIVE_SIMULATOR_INTERVAL_SECONDS", "3"))
LIVE_SIMULATOR_SAMPLE_ROWS = int(os.getenv("LIVE_SIMULATOR_SAMPLE_ROWS", "5000" if PRODUCTION else "4000"))
LIVE_SIMULATOR_TICKS_PER_INTERVAL = int(os.getenv("LIVE_SIMULATOR_TICKS_PER_INTERVAL", "2"))
LIVE_SIMULATOR_ATTACKS_PER_10 = int(os.getenv("LIVE_SIMULATOR_ATTACKS_PER_10", "4"))

# Prevention / mitigation
MITIGATION_AUTO_ENABLED = os.getenv("MITIGATION_AUTO_ENABLED", "true").lower() == "true"
MITIGATION_MODE = os.getenv("MITIGATION_MODE", "simulated")  # simulated | iptables | webhook
MITIGATION_WEBHOOK_URL = os.getenv("MITIGATION_WEBHOOK_URL", "")
MITIGATION_WEBHOOK_TIMEOUT = float(os.getenv("MITIGATION_WEBHOOK_TIMEOUT", "10"))
MITIGATION_BLOCK_TOP_K = int(os.getenv("MITIGATION_BLOCK_TOP_K", "5"))
MITIGATION_RATE_LIMIT_TOP_K = int(os.getenv("MITIGATION_RATE_LIMIT_TOP_K", "3"))
MITIGATION_QUARANTINE_TOP_K = int(os.getenv("MITIGATION_QUARANTINE_TOP_K", "2"))
MITIGATION_TTL_HOURS = int(os.getenv("MITIGATION_TTL_HOURS", "24"))
MITIGATION_FILTER_BLOCKED_FLOWS = os.getenv("MITIGATION_FILTER_BLOCKED_FLOWS", "true").lower() == "true"

UVICORN_WORKERS = int(os.getenv("UVICORN_WORKERS", "1"))

_extra_origins = os.getenv("CORS_ORIGINS", "")
if _extra_origins:
    merged = {o.strip() for o in CORS_ORIGINS}
    merged.update(o.strip() for o in _extra_origins.split(",") if o.strip())
    CORS_ORIGINS = sorted(merged)
