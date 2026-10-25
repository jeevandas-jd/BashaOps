"""Central configuration placeholder.

Keep secrets out of source control. Expand this module when the model and database
services are integrated.
"""
import os


APP_ENV = os.getenv("APP_ENV", "development")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bhashaops.db")
GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL", "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "replace-with-verified-model-tag")
