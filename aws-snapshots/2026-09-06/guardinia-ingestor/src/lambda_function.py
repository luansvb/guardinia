import base64
import hashlib
import hmac
import json
import os
import time
import boto3
import logging
from typing import Any, Dict, Optional

# ======================================================================
# GuardinIA 2.0 - Ingestor
# API Gateway / Meta webhook -> SQS
# Ready to replace the current Guardinia-Ingestor
# ======================================================================

APP_NAME = "GuardinIA"
APP_VERSION = "2.0"
APP_ENV = os.environ.get("ENV", "production")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
SECRET_NAME = os.environ.get("SECRET_NAME", "guardinia/prod/credentials")
SECRET_CACHE_TTL_SECONDS = int(os.environ.get("SECRET_CACHE_TTL_SECONDS", "300"))

sqs = boto3.client("sqs", region_name=AWS_REGION)
secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)

_SECRET_CACHE: Dict[str, Any] = {"loaded_at": 0.0, "values": {}}


def response(status: int, body: Any) -> Dict[str, Any]:
    payload = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": payload,
    }


def get_secrets(force_refresh: bool = False) -> Dict[str, Any]:
    now_ts = time.time()
    if not force_refresh and _SECRET_CACHE["values"] and (now_ts - _SECRET_CACHE["loaded_at"] < SECRET_CACHE_TTL_SECONDS):
        return _SECRET_CACHE["values"]

    try:
        secret = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        values = json.loads(secret["SecretString"])
        _SECRET_CACHE["loaded_at"] = now_ts
        _SECRET_CACHE["values"] = values
        return values
    except Exception as exc:
        logger.error("secrets_load_failed | error=%s", exc)
        if _SECRET_CACHE["values"]:
            return _SECRET_CACHE["values"]
        return {}


def secret_or_env(key: str, default: Optional[str] = None) -> Optional[str]:
    secrets = get_secrets()
    value = secrets.get(key)
    if value not in (None, ""):
        return value
    env_value = os.environ.get(key)
    if env_value not in (None, ""):
        return env_value
    return default


def validate_signature(headers: Dict[str, str], body_bytes: bytes, app_secret: str) -> bool:
    signature = headers.get("x-hub-signature-256")
    if not signature or not app_secret:
        return False

    try:
        algo, provided_hash = signature.split("=", 1)
    except ValueError:
        return False

    if algo != "sha256":
        return False

    expected_hash = hmac.new(app_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash, provided_hash)


def parse_body(event: Dict[str, Any]) -> bytes:
    body_raw = event.get("body", "") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body_raw)
    return body_raw.encode("utf-8")


def lambda_handler(event, context):
    logger.info("%s %s initialized | env=%s", APP_NAME, APP_VERSION, APP_ENV)

    if not QUEUE_URL:
        logger.error("missing_queue_url")
        return response(500, {"erro": "SQS_QUEUE_URL não configurada"})

    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    secrets = get_secrets()
    verify_token = secrets.get("VERIFY_TOKEN") or os.environ.get("VERIFY_TOKEN")
    app_secret = secrets.get("APP_SECRET") or os.environ.get("APP_SECRET")

    if method == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
            return {"statusCode": 200, "body": params.get("hub.challenge", "")}
        return {"statusCode": 403, "body": "Forbidden"}

    if method != "POST":
        return {"statusCode": 405, "body": "Method Not Allowed"}

    body_bytes = parse_body(event)
    headers = {str(k).lower(): str(v) for k, v in (event.get("headers") or {}).items()}

    if not validate_signature(headers, body_bytes, app_secret or ""):
        logger.warning("invalid_meta_signature")
        return response(403, {"erro": "Assinatura inválida"})

    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=body_bytes.decode("utf-8"),
            MessageAttributes={
                "source": {"StringValue": "meta_whatsapp", "DataType": "String"},
                "version": {"StringValue": APP_VERSION, "DataType": "String"},
            },
        )
        logger.info("message_enqueued")
        return {"statusCode": 200, "body": "OK"}
    except Exception as exc:
        logger.error("sqs_send_failed | error=%s", exc)
        return response(500, {"erro": "Falha ao enfileirar mensagem"})
