"""Servidor descartável para demonstração visual; nunca usa o banco real."""

import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validar_cenarios import Demonstracao


def main():
    folder = ROOT / "tmp/aps4-swagger"
    folder.mkdir(parents=True, exist_ok=True)
    metadata = folder / "sessao.json"
    stop = folder / "parar"
    if stop.exists():
        stop.unlink()
    with tempfile.TemporaryDirectory(prefix="aps4-swagger-") as directory, patch.dict(os.environ, {"JWT_SECRET_KEY": secrets.token_urlsafe(48)}):
        demo = Demonstracao(directory)
        try:
            with demo.server():
                metadata.write_text(json.dumps({"url": demo.base + "/docs", "banco": str(demo.path),
                    "email_admin": "regressao@example.com", "senha_admin": demo.password,
                    "token_admin": demo.token, "email_usuario": "swagger@example.com",
                    "senha_usuario": secrets.token_urlsafe(24)}, indent=2), encoding="utf8")
                print(f"Swagger de teste: {demo.base}/docs", flush=True)
                print("Credenciais descartáveis em tmp/aps4-swagger/sessao.json (ignorado pelo Git).", flush=True)
                print("Para encerrar, crie tmp/aps4-swagger/parar. Dados temporários serão removidos.", flush=True)
                while not stop.exists():
                    time.sleep(0.5)
        finally:
            if metadata.exists():
                metadata.unlink()


if __name__ == "__main__":
    main()
