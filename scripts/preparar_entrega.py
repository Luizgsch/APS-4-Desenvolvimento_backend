"""Empacota apenas código, testes e documentação, sem dados ou ambientes locais."""

import hashlib
import json
import os
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
NAME = "APS-4-Desenvolvimento-backend"


def main():
    paths = [ROOT / name for name in
             ("main.py", "database.py", "README.md", "requirements.txt", "requirements-dev.txt", ".gitignore", ".env.example")]
    for folder in ("controller", "model", "schema", "service", "security", "tests", "scripts"):
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and p.suffix == ".py"
                     and "__pycache__" not in p.parts)
    paths.extend((ROOT / "docs").glob("APS4-*.md"))
    for evidence in (ROOT / "docs/evidencias").glob("aps4-*"):
        if evidence.is_dir():
            paths.extend(p for p in evidence.rglob("*") if p.is_file() and p.suffix in {".json", ".txt", ".md"})
        elif evidence.suffix == ".json":
            paths.append(evidence)
    paths.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    contents = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in paths}
    values = {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}
    secret = values.get("JWT_SECRET_KEY") or ""
    for name, data in contents.items():
        path = Path(name)
        if ((path.name.startswith(".env") and name != ".env.example")
                or path.suffix in {".pem", ".key", ".db"} or path.name == "sessao.json"):
            raise ValueError(f"Arquivo sensível recusado: {name}")
        if len(secret.encode()) >= 32 and secret.encode() in data:
            raise ValueError(f"Chave local encontrada; pacote não gerado: {name}")
        if re.search(rb"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{20,}", data):
            raise ValueError(f"Possível token JWT encontrado; revise o arquivo: {name}")
    manifest = {"arquivos": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}}
    OUTPUT.mkdir(exist_ok=True)
    archive = OUTPUT / f"{NAME}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for name, data in contents.items():
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, data)
        info = ZipInfo("MANIFESTO.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        bundle.writestr(info, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (OUTPUT / f"{NAME}.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="ascii")
    (OUTPUT / "MANIFESTO.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Pacote: {archive}\nArquivos: {len(contents)}\nSHA-256: {checksum}")


if __name__ == "__main__":
    main()
