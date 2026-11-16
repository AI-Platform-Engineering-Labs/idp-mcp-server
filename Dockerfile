# One image for every local option: docker compose, Terraform (infra/local) and
# VS Code over stdio (`docker run -i`). Azure App Service runs the same code
# from source instead (see infra/azure), because the sandbox blocks ACR builds.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY server/requirements.txt .
RUN pip install -r requirements.txt

COPY server/idp_mcp ./idp_mcp
COPY server/catalog ./catalog

# Run as a non-root user (least privilege starts at the container).
RUN useradd --create-home --uid 10001 mcp
USER mcp

# Default is HTTP on 8000. VS Code overrides it with --transport stdio.
ENV MCP_TRANSPORT=http PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

ENTRYPOINT ["python", "-m", "idp_mcp"]
