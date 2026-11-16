# évolvé backend image (modular monolith, docs/08 §1 #2). SIMULATED, synthetic data only.
# Build context = repo root (see deploy/docker-compose.yml). Dependencies are exactly the runtime subset of
# scripts/allowed_deps.txt, pinned to the versions the test suites were run with (handoffs/DONE-*.md).
FROM python:3.13-slim

WORKDIR /repo
RUN pip install --no-cache-dir \
      fastapi==0.119.0 uvicorn==0.38.0 pydantic==2.12.3 cryptography==46.0.3 jsonschema==4.26.0 \
      fhir.resources==8.3.0 phenopackets==2.0.2.post5 httpx==0.28.1

# Only what the backend imports or reads: contracts, the service packages (bootstrap.py puts them on
# sys.path), and the synthetic V1-V5 fixtures that POST /api/demo/reset reseeds from.
COPY contracts/ contracts/
COPY services/ services/
COPY tests/golden/ tests/golden/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "evolve_api.main:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8000"]
