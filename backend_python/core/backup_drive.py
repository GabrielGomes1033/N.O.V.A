from __future__ import annotations

import base64
from datetime import datetime
import json
import os
from pathlib import Path

from core.memoria import carregar_memoria_usuario, salvar_memoria_usuario
from core.seguranca import obter_cifra

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
    import io
except Exception:
    service_account = None
    build = None
    MediaIoBaseDownload = None
    MediaIoBaseUpload = None
    io = None


SCOPE_DRIVE = ["https://www.googleapis.com/auth/drive.file"]


def _credenciais_disponiveis():
    return bool(
        os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE")
    )


def _carregar_credenciais():
    if service_account is None:
        return None

    raw_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    file_path = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "").strip()
    try:
        if raw_json:
            info = json.loads(raw_json)
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPE_DRIVE)
        if file_path and Path(file_path).is_file():
            return service_account.Credentials.from_service_account_file(file_path, scopes=SCOPE_DRIVE)
    except Exception:
        return None
    return None


def _drive_service():
    if build is None:
        return None
    creds = _carregar_credenciais()
    if creds is None:
        return None
    try:
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception:
        return None


def _backup_file_name():
    return os.getenv("NOVA_DRIVE_FILE_NAME", "nova_backup_memoria.json")


def _backup_folder_id():
    return os.getenv("NOVA_DRIVE_FOLDER_ID", "").strip()


def _query_nome_arquivo(nome):
    query = f"name = '{nome}' and trashed = false"
    pasta = _backup_folder_id()
    if pasta:
        query += f" and '{pasta}' in parents"
    return query


def _procurar_arquivo(service, nome):
    res = service.files().list(
        q=_query_nome_arquivo(nome),
        fields="files(id,name,modifiedTime)",
        pageSize=1,
    ).execute()
    arquivos = res.get("files", [])
    return arquivos[0] if arquivos else None


def _serializar_backup():
    memoria = carregar_memoria_usuario()
    payload = {
        "version": 1,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "memory": memoria,
    }
    bruto = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    cifra = obter_cifra()
    if cifra is None:
        return {
            "encrypted": False,
            "payload_b64": base64.b64encode(bruto).decode("ascii"),
        }
    token = cifra.encrypt(bruto)
    return {
        "encrypted": True,
        "payload_b64": base64.b64encode(token).decode("ascii"),
    }


def _desserializar_backup(raw):
    envelope = json.loads(raw.decode("utf-8"))
    payload_b64 = envelope.get("payload_b64", "")
    encrypted = bool(envelope.get("encrypted"))
    if not payload_b64:
        return None
    blob = base64.b64decode(payload_b64.encode("ascii"))

    if encrypted:
        cifra = obter_cifra()
        if cifra is None:
            return None
        blob = cifra.decrypt(blob)

    payload = json.loads(blob.decode("utf-8"))
    if not isinstance(payload, dict):
        return None
    memoria = payload.get("memory", {})
    if not isinstance(memoria, dict):
        return None
    return memoria


def status_backup_drive():
    if not _credenciais_disponiveis():
        return (
            "Backup Drive: não configurado. "
            "Defina GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON ou GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE."
        )
    service = _drive_service()
    if service is None:
        return "Backup Drive: credenciais inválidas ou biblioteca não instalada."
    arquivo = _procurar_arquivo(service, _backup_file_name())
    if not arquivo:
        return "Backup Drive: configurado, mas sem arquivo remoto ainda."
    return f"Backup Drive: ativo. Arquivo remoto: {arquivo.get('name')} (id={arquivo.get('id')})."


def sincronizar_backup_drive():
    service = _drive_service()
    if service is None:
        return False, "Drive não configurado ou indisponível."

    conteudo = _serializar_backup()
    payload = json.dumps(conteudo, ensure_ascii=False).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json", resumable=False)

    nome = _backup_file_name()
    arquivo = _procurar_arquivo(service, nome)
    try:
        if arquivo:
            service.files().update(fileId=arquivo["id"], media_body=media).execute()
            return True, "Backup secundário sincronizado no Google Drive."

        metadata = {"name": nome, "mimeType": "application/json"}
        pasta = _backup_folder_id()
        if pasta:
            metadata["parents"] = [pasta]
        service.files().create(body=metadata, media_body=media, fields="id").execute()
        return True, "Backup secundário criado no Google Drive."
    except Exception as exc:
        return False, f"Falha ao sincronizar backup no Drive: {exc}"


def restaurar_backup_drive():
    service = _drive_service()
    if service is None:
        return False, "Drive não configurado ou indisponível."

    arquivo = _procurar_arquivo(service, _backup_file_name())
    if not arquivo:
        return False, "Nenhum arquivo de backup remoto encontrado no Drive."

    request = service.files().get_media(fileId=arquivo["id"])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    try:
        while not done:
            _, done = downloader.next_chunk()
        memoria = _desserializar_backup(fh.getvalue())
        if memoria is None:
            return False, "Backup remoto inválido ou não compatível."
        salvar_memoria_usuario(memoria)
        return True, "Backup remoto restaurado para a memória da NOVA."
    except Exception as exc:
        return False, f"Falha ao restaurar backup do Drive: {exc}"
