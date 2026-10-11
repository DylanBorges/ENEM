import os
import hashlib
import yaml
from urllib.request import Request, urlopen
from urllib.error import URLError
import shutil
import ssl
import subprocess
from typing import Any


def verify_sha256(file_path: str, expected_hash: str) -> bool:
    """Verifica hash criptográfico SHA-256 do arquivo baixado."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    calculated = sha256.hexdigest()
    return calculated.lower() == expected_hash.lower()


def download_microdados(manifest_path: str, target_dir: str = "./data/raw") -> dict[str, Any]:
    """Valida o manifesto oficial e dispara o download com checagem de integridade SHA-256."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    os.makedirs(target_dir, exist_ok=True)
    year = manifest["year"]
    dataset_name = manifest["dataset_name"]
    expected_sha256 = manifest.get("sha256")
    if not expected_sha256 or len(expected_sha256) != 64:
        raise ValueError("Manifesto sem SHA-256 verificado; registre o hash oficial ou auditado antes da ingestão")

    target_file = os.path.join(target_dir, f"{dataset_name}.zip")

    if not os.path.exists(target_file) or not verify_sha256(target_file, expected_sha256):
        partial = target_file + ".part"
        offset = os.path.getsize(partial) if os.path.exists(partial) else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        request = Request(manifest["source_url"], headers=headers)
        try:
            with urlopen(request, timeout=60) as response:
                # A server may ignore Range; restart rather than append duplicate bytes.
                append = offset > 0 and response.status == 206
                with open(partial, "ab" if append else "wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
        except URLError as exc:
            # Some Windows Python environments lack the system CA chain. curl with
            # Schannel still verifies TLS; never disable certificate validation.
            if not isinstance(exc.reason, ssl.SSLCertVerificationError) or not shutil.which("curl"):
                raise
            subprocess.run(
                ["curl", "--fail", "--location", "--retry", "3", "--continue-at", "-",
                 "--output", partial, manifest["source_url"]],
                check=True,
            )
        if not verify_sha256(partial, expected_sha256):
            raise ValueError("SHA-256 divergente; arquivo parcial preservado para auditoria")
        os.replace(partial, target_file)

    return {
        "year": year,
        "dataset_name": dataset_name,
        "target_file": target_file,
        "expected_sha256": expected_sha256,
        "status": "VERIFIED",
    }


if __name__ == "__main__":
    res = download_microdados("pipelines/inep/manifests/2025.yaml")
    print("Download pipeline:", res)
