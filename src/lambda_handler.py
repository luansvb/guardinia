"""
================================================================
GuardinIA 

Hybrid Fraud Detection Engine

AWS Serverless Architecture | Cost-aware AI Escalation | Production-ready

================================================================
"""

import random
import json
import os
import re
import math
import base64
import boto3
import logging
import traceback
import urllib.request
import hashlib
import time
import urllib.error
import urllib.parse
import hmac
import threading
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass
from urllib.parse import urlparse
from collections import Counter, defaultdict
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# ======================================================================
# GLOBAL CONFIGURATION
# ======================================================================

# ----------------------------------------------------------------------
# Application Metadata
# ----------------------------------------------------------------------

APP_NAME = "GuardinIA"
APP_VERSION = "v5.1"
APP_ENV = os.environ.get("ENV", "production")
ARCHITECTURE = "heuristic + bedrock (hybrid pipeline)"

# ----------------------------------------------------------------------
# Logger Configuration
# ----------------------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info(
    f"{APP_NAME} {APP_VERSION} initialized | "
    f"env={APP_ENV} | architecture={ARCHITECTURE}"
)

# ----------------------------------------------------------------------
# Meta / WhatsApp Configuration
# ----------------------------------------------------------------------

META_TOKEN = os.environ.get("META_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
APP_SECRET = os.environ.get("APP_SECRET")
BOT_WA_ID = os.environ.get("BOT_WA_ID")

# ----------------------------------------------------------------------
# AWS Services
# ----------------------------------------------------------------------

from botocore.config import Config

textract = boto3.client("textract")
dynamodb = boto3.resource("dynamodb")

_bedrock_config = Config(
    connect_timeout=3,   # Increased to reduce unnecessary reconnections
    read_timeout=10,     # Sonnet may require slightly longer processing time
    retries={"max_attempts": 1}
)

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=_bedrock_config
)

# ----------------------------------------------------------------------
# DynamoDB Tables
# ----------------------------------------------------------------------

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "guardinia_audit_logs")
CACHE_TABLE_NAME = os.environ.get("CACHE_TABLE_NAME", "guardinia_cache")
METRICS_TABLE_NAME = os.environ.get("METRICS_TABLE_NAME", "guardinia_metrics")

audit_table = dynamodb.Table(DYNAMODB_TABLE)
metrics_table = dynamodb.Table(METRICS_TABLE_NAME)

# ----------------------------------------------------------------------
# Cache Configuration
# ----------------------------------------------------------------------

TTL_DAYS = 7
TTL_SECONDS = TTL_DAYS * 24 * 60 * 60
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

# ----------------------------------------------------------------------
# Heuristic Weights (Configurable)
# ----------------------------------------------------------------------

PESO_SIGNATURE_MATCH = int(os.environ.get("PESO_SIGNATURE_MATCH", "40"))
PESO_PROGRESSAO_FINANCEIRA = int(os.environ.get("PESO_PROGRESSAO_FINANCEIRA", "35"))
THRESHOLD_SCAM = int(os.environ.get("THRESHOLD_SCAM", "120"))
THRESHOLD_SUSPEITO = int(os.environ.get("THRESHOLD_SUSPEITO", "60"))
MULTIPLICADOR_SEMANTICO = int(os.environ.get("MULTIPLICADOR_SEMANTICO", "20"))
REDUCAO_INVESTIGATIVO = float(os.environ.get("REDUCAO_INVESTIGATIVO", "0.7"))
MULTIPLICADOR_CRITICO = float(os.environ.get("MULTIPLICADOR_CRITICO", "1.15"))

# ----------------------------------------------------------------------
# Bedrock Configuration
# ----------------------------------------------------------------------

BEDROCK_ENABLED = os.environ.get("BEDROCK_ENABLED", "true").lower() == "true"
BEDROCK_MODEL_HAIKU = os.environ.get(
    "BEDROCK_MODEL_HAIKU",
    "anthropic.claude-3-haiku-20240307-v1:0"
)
BEDROCK_MODEL_SONNET = os.environ.get(
    "BEDROCK_MODEL_SONNET",
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)
BEDROCK_TIMEOUT = int(os.environ.get("BEDROCK_TIMEOUT", "5"))
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "180"))

# ----------------------------------------------------------------------
# Cognitive Zone Configuration
# ----------------------------------------------------------------------

ZONA_COGNITIVA_MIN = int(os.environ.get("ZONA_COGNITIVA_MIN", "20"))
ZONA_COGNITIVA_MAX = int(os.environ.get("ZONA_COGNITIVA_MAX", "150"))
ZONA_HAIKU_MAX = int(os.environ.get("ZONA_HAIKU_MAX", "60"))
ZONA_SONNET_BASICO_MAX = int(os.environ.get("ZONA_SONNET_BASICO_MAX", "100"))

# ----------------------------------------------------------------------
# Hybrid Fusion Weights
# ----------------------------------------------------------------------

PESO_HEURISTICA_ALTO = float(os.environ.get("PESO_HEURISTICA_ALTO", "0.7"))
PESO_BEDROCK_ALTO = float(os.environ.get("PESO_BEDROCK_ALTO", "0.3"))
PESO_HEURISTICA_BAIXO = float(os.environ.get("PESO_HEURISTICA_BAIXO", "0.5"))
PESO_BEDROCK_BAIXO = float(os.environ.get("PESO_BEDROCK_BAIXO", "0.5"))

# ----------------------------------------------------------------------
# Advanced Escalation Controls (v5.1)
# ----------------------------------------------------------------------

DIVERGENCIA_THRESHOLD = int(os.environ.get("DIVERGENCIA_THRESHOLD", "80"))
SONNET_REPASS_PROB_MIN = int(os.environ.get("SONNET_REPASS_PROB_MIN", "40"))
SONNET_REPASS_PROB_MAX = int(os.environ.get("SONNET_REPASS_PROB_MAX", "60"))
SONNET_REPASS_MANIPULACAO = int(os.environ.get("SONNET_REPASS_MANIPULACAO", "8"))

# ----------------------------------------------------------------------
# Cost Configuration (USD per 1M tokens)
# ----------------------------------------------------------------------

CUSTO_HAIKU_INPUT_1M = 0.25
CUSTO_HAIKU_OUTPUT_1M = 1.25
CUSTO_SONNET_INPUT_1M = 3.00
CUSTO_SONNET_OUTPUT_1M = 15.00

# ======================================================================
# Webhook Signature Validation (Meta / WhatsApp)
# ======================================================================

def validar_assinatura(headers: dict, body_bytes: bytes) -> bool:
    """
    Validate Meta webhook signature using HMAC-SHA256.

    Ensures the request originated from Meta by comparing the
    provided x-hub-signature-256 header with a locally calculated hash.
    """

    if not APP_SECRET:
        logger.error("signature_validation_failed | reason=missing_app_secret")
        return False

    signature_header = headers.get("x-hub-signature-256")
    if not signature_header:
        logger.warning("signature_validation_failed | reason=missing_header")
        return False

    try:
        method, received_hash = signature_header.split("=")
    except ValueError:
        logger.warning("signature_validation_failed | reason=invalid_format")
        return False

    if method != "sha256":
        logger.warning("signature_validation_failed | reason=invalid_method")
        return False

    calculated_hash = hmac.new(
        APP_SECRET.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.warning("signature_validation_failed | reason=hash_mismatch")
        return False

    return True

# ======================================================================
# Standard Analysis Result Model
# ======================================================================

@dataclass
class ResultadoAnalise:
    """
    Domain model representing the final outcome of a fraud analysis.

    This structure centralizes:
    - Classification result
    - Confidence level
    - Aggregated scoring
    - Technical indicators
    - Recommended action
    """

    status: str
    cor: str
    confianca: int
    score_total: int
    motivos: List[str]
    acao_recomendada: str
    indicadores_tecnicos: Dict[str, Any]
    texto_analisado: str

# ======================================================================
# Bedrock Cognitive Analysis Response Model
# ======================================================================

@dataclass
class RespostaBedrock:
    """
    Structured response returned by Claude (via Amazon Bedrock).

    Encapsulates:
    - Fraud probability estimation
    - Classification metadata
    - Psychological manipulation assessment
    - Model attribution
    - Token usage
    - Cost tracking
    - Execution latency
    """

    probabilidade_golpe: int  # Range: 0–100
    categoria_principal: str
    subtipo: str
    nivel_manipulacao_psicologica: int  # Range: 0–10
    intencao_detectada: str
    explicacao_tecnica: str

    modelo_usado: str  # "haiku" or "sonnet"

    tokens_input: int
    tokens_output: int
    custo_usd: float
    tempo_ms: float

# ======================================================================
# Input Sanitization & Normalization Utilities
# ======================================================================

def remover_caracteres_invisiveis(texto: str) -> str:
    """
    Remove common invisible or zero-width Unicode characters
    often used for obfuscation in scam messages.
    """
    invisiveis = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']
    for c in invisiveis:
        texto = texto.replace(c, '')
    return texto


def sanitizar_entrada(texto: str) -> str:
    """
    Basic input sanitization:
    - Removes invisible characters
    - Collapses excessive whitespace
    - Strips leading/trailing spaces
    """
    if not texto:
        return ""

    texto = remover_caracteres_invisiveis(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def validar_entrada(texto: str) -> Tuple[bool, str]:
    """
    Validates whether the input text is suitable for analysis.

    Checks:
    - Minimum length
    - Presence of valid alphabetic characters
    - Excessive obfuscation via special characters
    """
    if not texto or len(texto.strip()) < 3:
        return False, "Texto muito curto"

    if not re.search(r'[A-Za-zÀ-ÿ]', texto):
        return False, "Texto sem letras válidas"

    especiais = len(re.findall(r'[^A-Za-z0-9À-ÿ\s.,!?;:()-]', texto))
    if len(texto) > 0 and (especiais / len(texto)) > 0.4:
        return False, "Texto excessivamente ofuscado"

    return True, ""


def normalizar_texto(texto: str) -> str:
    """
    Full normalization pipeline:
    - Sanitization
    - Removal of non-printable characters
    - Final trimming
    """
    texto = sanitizar_entrada(texto)
    texto = ''.join(c for c in texto if c.isprintable() or c.isspace())
    return texto.strip()


def truncar_seguro(texto: str, max_chars: int = 4096) -> str:
    """
    Safely truncates text to a maximum character limit,
    attempting to preserve word boundaries when possible.
    """
    if len(texto) <= max_chars:
        return texto

    truncado = texto[:max_chars]
    ultimo_espaco = truncado.rfind(' ')

    if ultimo_espaco > max_chars * 0.9:
        return truncado[:ultimo_espaco] + "..."

    return truncado + "..."

# ======================================================================
# External API Retry Utility
# ======================================================================

def executar_com_retry(
    func: Callable,
    max_tentativas: int = 2,
    descricao: str = "external_operation"
):
    """
    Executes a callable with basic retry logic for transient network failures.

    - Retries on URLError
    - Applies incremental backoff
    - Fails fast on non-recoverable exceptions
    """

    for tentativa in range(max_tentativas):
        try:
            return func()

        except urllib.error.URLError as e:
            if tentativa == max_tentativas - 1:
                logger.error(
                    f"retry_failed | operation={descricao} "
                    f"| attempts={max_tentativas} | error={e}"
                )
                return None

            logger.warning(
                f"retry_attempt_failed | operation={descricao} "
                f"| attempt={tentativa + 1}"
            )

            time.sleep(0.5 * (tentativa + 1))

        except Exception as e:
            logger.error(
                f"non_recoverable_error | operation={descricao} | error={e}"
            )
            return None

    return None

# ======================================================================
# Statistical Signal Utilities
# ======================================================================

def calcular_entropia(texto: str) -> float:
    """
    Calculates Shannon entropy of the input text.

    Higher entropy may indicate:
    - Randomized content
    - Obfuscation attempts
    - Encoded payloads
    """
    if not texto or len(texto) < 20:
        return 0.0

    freq = Counter(texto.lower())
    total = len(texto)
    ent = 0.0

    for c in freq.values():
        p = c / total
        ent -= p * math.log2(p)

    return ent


def densidade_numerica(texto: str) -> float:
    """
    Computes the ratio of numeric characters in the text.

    Useful for detecting:
    - Suspicious financial emphasis
    - Account / ID heavy messages
    """
    if not texto:
        return 0.0

    nums = len(re.findall(r'\d', texto))
    return nums / len(texto)


def proporcao_maiusculas(texto: str) -> float:
    """
    Calculates uppercase letter proportion.

    High uppercase ratio may indicate:
    - Urgency tactics
    - Emotional manipulation
    - Aggressive formatting
    """
    letras = re.findall(r'[A-Za-zÀ-ÿ]', texto)
    if not letras:
        return 0.0

    maius = sum(1 for c in letras if c.isupper())
    return maius / len(letras)

# ======================================================================
# Semantic Signal Extraction Layer
# ======================================================================

def extrair_sinais_semanticos(texto: str) -> Dict[str, float]:
    """
    Extracts high-level semantic indicators commonly found in scam patterns.

    Each signal represents a behavioral or linguistic pattern such as:
    - Financial requests
    - Authority impersonation
    - Urgency pressure
    - Emotional manipulation
    - Threat escalation
    - Victim investigative awareness
    """

    t = texto.lower()
    sinais: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Direct Financial Request
    # ------------------------------------------------------------------
    sinais['pedido_dinheiro'] = 1.0 if any([
        'faz um pix' in t, 'me manda' in t, 'me passa' in t,
        'transfere' in t, 'me envia' in t, 'deposita' in t,
        re.search(r'\b(preciso|necessito).*(dinheiro|grana|pix|valor)', t)
    ]) else 0.0

    # ------------------------------------------------------------------
    # Promise of Financial Return
    # ------------------------------------------------------------------
    sinais['promessa_retorno'] = 1.0 if any([
        'te devolvo' in t, 'te pago' in t, 'depois eu pago' in t,
        'te retorno' in t, 'retorno garantido' in t, 'lucro garantido' in t,
        'lucro certo' in t, 'sem risco' in t
    ]) else 0.0

    # ------------------------------------------------------------------
    # Authority Impersonation
    # ------------------------------------------------------------------
    sinais['autoridade'] = 1.0 if any([
        'sou do banco' in t, 'sou da receita' in t, 'setor de fraude' in t,
        'central de segurança' in t,
        'departamento' in t and any(x in t for x in ['fraude', 'segurança', 'bloqueio']),
        'suporte oficial' in t
    ]) else 0.0

    # ------------------------------------------------------------------
    # Urgency Pressure
    # ------------------------------------------------------------------
    termos_urgencia = [
        'urgente', 'agora', 'imediato', 'imediatamente',
        'último aviso', 'hoje mesmo'
    ]
    count_urgencia = sum(1 for termo in termos_urgencia if termo in t)
    sinais['urgencia'] = min(count_urgencia * 0.8, 2.4)

    # ------------------------------------------------------------------
    # Isolation / Secrecy Attempt
    # ------------------------------------------------------------------
    sinais['proibicao'] = 1.2 if any([
        'não conta' in t, 'não liga' in t, 'não fala' in t,
        'não chama' in t, 'segredo nosso' in t,
        'confidencial' in t, 'entre nós' in t
    ]) else 0.0

    # ------------------------------------------------------------------
    # Emotional / Personal Bond Manipulation
    # ------------------------------------------------------------------
    sinais['relacao_pessoal'] = 0.7 if any([
        re.search(r'\b(meu|minha) (amor|anjo|filho|filha|mãe|pai|familia)', t),
        'você é especial' in t, 'te amo' in t, 'meu querido' in t
    ]) else 0.0

    # ------------------------------------------------------------------
    # Threat Escalation
    # ------------------------------------------------------------------
    sinais['ameaca'] = 1.1 if any([
        'bloqueio' in t, 'cancelamento' in t, 'prisão' in t,
        'será bloqueado' in t, 'será cancelado' in t,
        'será suspenso' in t, 'perderá acesso' in t,
        'consequências' in t
    ]) else 0.0

    # ------------------------------------------------------------------
    # Victim Investigative Awareness (negative signal)
    # ------------------------------------------------------------------
    sinais['investigativo'] = -1.5 if any([
        'isso é golpe' in t, 'é golpe' in t, 'é seguro' in t,
        'é confiável' in t, 'é fraude' in t,
        '?' in texto and any(
            x in t for x in ['golpe', 'seguro', 'confiável', 'fraude']
        )
    ]) else 0.0

    return sinais

# ======================================================================
# Psychological Pressure Index (IPP) 
# ======================================================================

def calcular_indice_pressao(texto: str, sinais: Dict[str, float]) -> float:
    """
    Calculates the Psychological Pressure Index (IPP).

    The IPP aggregates linguistic and behavioral indicators that
    reflect coercion tactics commonly used in scam attempts.

    Components:
    - Urgency escalation
    - Threat signals
    - Isolation / secrecy attempts
    - Uppercase intensity
    - Excessive exclamation usage
    """

    exclamacoes = texto.count('!')
    maiusculas_ratio = proporcao_maiusculas(texto)

    ipp = (
        sinais.get('urgencia', 0) * 10 +
        sinais.get('ameaca', 0) * 20 +
        sinais.get('proibicao', 0) * 25 +
        maiusculas_ratio * 15 +
        min(exclamacoes, 5) * 2
    )

    return ipp

# ======================================================================
# Legitimate Context Handling
# ======================================================================

def aplicar_reducao_contexto_legitimo(
    score_por_categoria: Dict[str, int],
    texto: str
) -> Dict[str, int]:
    """
    Applies score reduction when strong indicators of legitimate
    institutional context are detected.

    Objective:
    Reduce false positives in scenarios that resemble fraud patterns
    but contain structured and verifiable legitimacy signals.
    """

    t = texto.lower()

    # ------------------------------------------------------------------
    # General Institutional Context
    # ------------------------------------------------------------------
    contextos_gerais = [
        "site oficial", "aplicativo oficial", "app oficial",
        "loja física", "atendimento presencial", "contrato assinado",
        "documento oficial", "gov.br", "canal oficial", "central oficial"
    ]

    tem_contexto_geral = any(ctx in t for ctx in contextos_gerais)

    # ------------------------------------------------------------------
    # Structured Financial Context
    # ------------------------------------------------------------------
    contextos_financeiros = [
        "boleto registrado", "nota fiscal", "pagamento recorrente",
        "contrato bancário", "suporte técnico oficial",
        "assistência autorizada"
    ]

    tem_contexto_financeiro = any(ctx in t for ctx in contextos_financeiros)

    # ------------------------------------------------------------------
    # Apply Reductions
    # ------------------------------------------------------------------
    if tem_contexto_geral:
        for categoria in ['PHISHING', 'ENGENHARIA_SOCIAL']:
            if categoria in score_por_categoria:
                score_atual = score_por_categoria[categoria]
                score_por_categoria[categoria] = int(score_atual * 0.7)

                logger.info(
                    f"context_reduction_applied | type=general "
                    f"| category={categoria} "
                    f"| old_score={score_atual} "
                    f"| new_score={score_por_categoria[categoria]}"
                )

    if tem_contexto_financeiro:
        if 'FINANCEIRO' in score_por_categoria:
            score_atual = score_por_categoria['FINANCEIRO']
            score_por_categoria['FINANCEIRO'] = int(score_atual * 0.6)

            logger.info(
                f"context_reduction_applied | type=financial "
                f"| category=FINANCEIRO "
                f"| old_score={score_atual} "
                f"| new_score={score_por_categoria['FINANCEIRO']}"
            )

    return score_por_categoria


def detectar_contexto_financeiro_estruturado_legitimo(texto: str) -> bool:
    """
    Detects structured legitimate financial communication.

    Criteria:
    - Contains monetary value
    - Contains contract/installment reference
    - Does NOT request sensitive credentials
    - Does NOT include extreme threat or coercion language
    """

    t = texto.lower()

    # Must contain monetary value
    if not re.search(r'r\$\s?\d+[.,]?\d*', t):
        return False

    # Must reference contract or installment
    referencia = any([
        re.search(r'parcela\s?\d+', t),
        re.search(r'n[úu]mero\s?\d+', t),
        re.search(r'\b\d{8,}\b', t)  # long numeric identifier (e.g., contract)
    ])

    if not referencia:
        return False

    # Must NOT request sensitive credentials
    termos_sensiveis = [
        "senha", "token", "código", "codigo",
        "confirme seus dados"
    ]

    if any(ts in t for ts in termos_sensiveis):
        return False

    # Must NOT contain severe threat escalation
    termos_ameaca = [
        "bloqueado", "prisão",
        "cancelado imediatamente", "último aviso"
    ]

    if any(ts in t for ts in termos_ameaca):
        return False

    return True

# ======================================================================
# Heuristic Rule Definition (Core Engine)
# ======================================================================

class Heuristica:
    """
    Represents a single heuristic rule within the fraud detection engine.

    Attributes:
    - nome: Human-readable identifier
    - categoria: Fraud category associated with the rule
    - peso: Scoring weight applied when triggered
    - detector: Callable responsible for detection logic
    - grupo: Optional logical grouping identifier
    """

    def __init__(
        self,
        nome: str,
        categoria: str,
        peso: int,
        detector: Callable,
        grupo: Optional[str] = None
    ):
        self.nome = nome
        self.categoria = categoria
        self.peso = peso
        self.detector = detector
        self.grupo = grupo

        self.validar()

    def validar(self):
        """
        Ensures rule integrity before being registered in the engine.
        """

        if not callable(self.detector):
            raise ValueError(
                f"Invalid heuristic '{self.nome}': detector must be callable"
            )

        if self.peso < 0:
            raise ValueError(
                f"Invalid heuristic '{self.nome}': weight must be >= 0"
            )

        if not self.nome or not self.categoria:
            raise ValueError(
                "Heuristic must define both name and category"
            )

# ======================================================================
# Data Protection Utilities (LGPD Compliance)
# ======================================================================

def mascarar_telefone(telefone: str) -> str:
    """
    Masks phone numbers to preserve user privacy while
    retaining minimal traceability for logging purposes.
    """

    if not telefone or len(telefone) < 4:
        return "****"

    return f"****{telefone[-4:]}"


def hash_curto(texto: str) -> str:
    """
    Generates a short SHA-256 hash (first 12 characters).

    Used for lightweight identification in logs
    without exposing raw content.
    """

    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def gerar_hash_texto(texto: str) -> str:
    """
    Generates full SHA-256 hash of text.

    Intended for:
    - Deduplication
    - Cache keys
    - Audit references
    """

    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

# ======================================================================
# Heuristic Registration Registry
# ======================================================================

HEURISTICAS_REGISTRADAS: List[Heuristica] = []


def registrar_heuristica(
    nome: str,
    categoria: str,
    peso: int,
    detector: Callable,
    grupo: Optional[str] = None
):
    """
    Registers a heuristic rule in the global engine registry.

    - Validates rule integrity via Heuristica class
    - Appends to central registry
    - Fails fast in development environment
    """

    try:
        heuristica = Heuristica(
            nome=nome,
            categoria=categoria,
            peso=peso,
            detector=detector,
            grupo=grupo
        )

        HEURISTICAS_REGISTRADAS.append(heuristica)

    except ValueError as e:
        logger.error(
            f"heuristic_registration_failed "
            f"| name={nome} "
            f"| error={e}"
        )

        if ENV == "development":
            raise

# ======================================================================
# Phishing Detection Utilities
# ======================================================================

def contem_link(texto: str) -> bool:
    """
    Detects presence of URLs or web references.

    Used as a primary phishing signal trigger.
    """
    return bool(re.search(r'https?://|www\.', texto.lower()))


def menciona_entidade_sensivel(texto: str) -> bool:
    """
    Detects references to sensitive or high-value entities
    commonly impersonated in phishing attempts.
    """

    entidades = [
        "banco", "caixa", "itau", "itaú", "bradesco", "santander",
        "nubank", "receita", "gov", "whatsapp", "email",
        "google", "apple", "microsoft", "inter", "c6"
    ]

    t = texto.lower()
    return any(e in t for e in entidades)


def pede_credenciais(texto: str) -> bool:
    """
    Detects explicit credential harvesting attempts.
    """

    padroes = [
        "senha", "login", "código", "codigo",
        "token", "confirme seus dados",
        "atualize seus dados", "verifique sua conta"
    ]

    t = texto.lower()
    return any(p in t for p in padroes)


def extrair_urls_validas(texto: str) -> List[str]:
    """
    Extracts and minimally validates candidate URLs from text.

    Validation steps:
    - Ensures presence of domain
    - Ensures valid TLD length
    - Normalizes scheme if missing
    """

    if not texto:
        return []

    candidatos = re.findall(
        r"https?://[^\s<>'\"]+|www\.[^\s<>'\"]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
        texto.lower()
    )

    urls_validas = []

    for candidato in candidatos:
        url = candidato.strip()

        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        try:
            parsed = urlparse(url)

            if not parsed.netloc:
                continue

            if "." not in parsed.netloc:
                continue

            partes = parsed.netloc.split(".")
            if len(partes[-1]) < 2:
                continue

            urls_validas.append(url)

        except Exception:
            continue

    return list(set(urls_validas))

# ======================================================================
# Brazilian Scam Signatures (Behavioral Patterns)
# ======================================================================

SCAM_SIGNATURES_BR = {
    "CONTATO_CLONADO": {
        "must_any": [
            "troquei de numero", "troquei de número", "meu novo numero",
            "novo chip", "mudei de numero", "perdi meu chip"
        ],
        "and_any": [
            "pix", "me ajuda", "urgente",
            "preciso pagar", "transfere"
        ]
    },
    "PEDIDO_CODIGO": {
        "must_any": [
            "codigo", "código", "token",
            "sms", "código de verificação"
        ],
        "and_any": [
            "me manda", "me passa",
            "por engano", "pra confirmar", "recebeu"
        ]
    },
    "ROMANCE_GOLPE": {
        "must_any": [
            "você é especial", "meu anjo",
            "amor da minha vida", "te amo muito",
            "meu amor"
        ],
        "and_any": [
            "hospital", "aluguel",
            "passagem", "emergência",
            "preciso de ajuda"
        ]
    },
    "CRISE_FAMILIAR": {
        "must_any": [
            "sequestrado", "em cativeiro",
            "tô em perigo", "me sequestraram"
        ],
        "and_any": [
            "não conta", "não chama",
            "pix", "transfere", "polícia"
        ]
    },
    "TRABALHO_TAXA": {
        "must_any": [
            "vagas limitadas", "home office",
            "trabalho simples", "trabalhe de casa",
            "ganhe dinheiro fácil"
        ],
        "and_any": [
            "taxa", "pagar para começar",
            "depósito", "investimento inicial"
        ]
    },
    "PROMESSA_DINHEIRO_FACIL": {
        "must_any": [
            "lucro garantido", "sem risco",
            "100% garantido", "multiplica",
            "renda extra", "ganhe até",
            "sem esforço"
        ]
    },
    "SIGILO": {
        "must_any": [
            "não conta pra ninguém",
            "segredo nosso",
            "entre nós",
            "confidencial",
            "não espalha"
        ]
    },
    "FALSA_CENTRAL": {
        "must_any": [
            "central de segurança",
            "departamento de fraude",
            "verificação de conta",
            "bloqueio preventivo"
        ],
        "and_any": [
            "confirme seus dados",
            "atualize",
            "senha",
            "token"
        ]
    }
}


def _contains_any(texto: str, termos: list) -> bool:
    """
    Utility matcher for signature keyword groups.
    """
    return any(termo in texto for termo in termos)


def match_signature(texto_lower: str, key: str) -> bool:
    """
    Evaluates whether a given signature configuration
    matches the provided text.
    """

    cfg = SCAM_SIGNATURES_BR.get(key)
    if not cfg:
        return False

    if "must_any" in cfg:
        if not _contains_any(texto_lower, cfg["must_any"]):
            return False

    if "and_any" in cfg:
        if not _contains_any(texto_lower, cfg["and_any"]):
            return False

    return True


def detectar_comportamental_full(texto: str) -> Union[Dict[str, int], bool]:
    """
    Full behavioral detection layer for Brazilian scam patterns.

    Combines:
    - Signature matching
    - Financial escalation detection
    """

    texto_lower = texto.lower()
    categorias: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Signature Detection
    # ------------------------------------------------------------------
    signatures_detectadas = []

    for key in SCAM_SIGNATURES_BR:
        if match_signature(texto_lower, key):
            signatures_detectadas.append(key)
            categorias["ENGENHARIA_SOCIAL"] = (
                categorias.get("ENGENHARIA_SOCIAL", 0) + PESO_SIGNATURE_MATCH
            )

    if signatures_detectadas:
        logger.info(
            f"signature_match_detected "
            f"| signatures={','.join(signatures_detectadas)}"
        )

    # ------------------------------------------------------------------
    # Financial Escalation Pattern Detection
    # ------------------------------------------------------------------
    contexto_financeiro = any(term in texto_lower for term in [
        'r$', 'reais', 'pix', 'transferir', 'depositar',
        'pagar', 'valor', 'dinheiro', 'grana'
    ])

    if contexto_financeiro:

        verbos_proposta = [
            'invista', 'investe', 'deposite',
            'pague', 'transfira', 'ganhe', 'multiplica'
        ]

        verbos_relato = [
            'recebi', 'paguei', 'transferi', 'ganhei'
        ]

        tem_proposta = any(v in texto_lower for v in verbos_proposta)
        tem_relato = any(v in texto_lower for v in verbos_relato)

        if tem_proposta or not tem_relato:

            valores_raw = re.findall(
                r'(?:r\$\s*)?(\d{1,6}(?:[.,]\d{2,3})?)',
                texto_lower
            )

            if len(valores_raw) >= 2:
                try:
                    valores_float = []

                    for v in valores_raw:
                        v_clean = v.replace(',', '.')
                        if v_clean.count('.') > 1:
                            partes = v_clean.split('.')
                            v_clean = ''.join(partes[:-1]) + '.' + partes[-1]

                        valores_float.append(float(v_clean))

                    for i in range(len(valores_float) - 1):
                        x = valores_float[i]
                        y = valores_float[i + 1]

                        if y > x and x > 0:
                            ratio = y / x

                            if ratio >= 2:
                                categorias["FINANCEIRO"] = (
                                    categorias.get("FINANCEIRO", 0)
                                    + PESO_PROGRESSAO_FINANCEIRA
                                )

                                logger.info(
                                    f"financial_progression_detected "
                                    f"| from={x} | to={y} "
                                    f"| ratio={ratio:.1f}"
                                )

                                break

                except (ValueError, ZeroDivisionError):
                    pass

    return categorias if categorias else False


registrar_heuristica(
    "Camada comportamental BR",
    "ENGENHARIA_SOCIAL",
    0,
    detectar_comportamental_full
)

# ======================================================================
# Unrealistic Financial Return Heuristic (v5.1)
# ======================================================================

def detectar_retorno_financeiro_irreal(
    texto: str
) -> Union[Dict[str, int], bool]:
    """
    Detects unrealistic financial return promises.

    Logic:
    - Requires presence of payment + return verbs
    - Extracts numeric values
    - Computes return ratio
    - Applies score scaling based on ratio magnitude
    - Applies intensifiers
    - Applies legitimacy reducers
    """

    t = texto.lower()

    verbos_envio = [
        "pagar", "pague", "envie", "enviar",
        "depositar", "transferir", "pix",
        "investir", "aplicar"
    ]

    verbos_retorno = [
        "receber", "devolver", "ganhar",
        "lucro", "retorno", "dobrar",
        "triplicar", "multiplicar"
    ]

    # Must contain both send and return semantics
    if not any(v in t for v in verbos_envio):
        return False

    if not any(v in t for v in verbos_retorno):
        return False

    # Extract numeric values
    numeros = re.findall(r'\b\d{1,6}\b', t)
    numeros = [int(n) for n in numeros if 0 < int(n) < 1_000_000]

    if len(numeros) < 2:
        return False

    x, y = numeros[0], numeros[1]

    if y <= x:
        return False

    ratio = y / x

    if ratio < 1.5:
        return False

    # Ratio-based scoring
    if ratio < 2:
        score_es = 15
    elif ratio < 3:
        score_es = 25
    elif ratio < 5:
        score_es = 35
    elif ratio < 10:
        score_es = 45
    else:
        score_es = 60

    # Intensifiers
    intensificadores = [
        "garantido", "lucro certo", "sem risco",
        "renda fácil", "retorno imediato",
        "oportunidade única", "só hoje"
    ]

    if any(p in t for p in intensificadores):
        score_es += 20

    # Legitimate context reducers
    redutores = [
        "cashback", "troco", "reembolso",
        "estorno", "restituição", "desconto"
    ]

    if any(p in t for p in redutores):
        score_es -= 25

    if score_es <= 0:
        return False

    resultado = {"ENGENHARIA_SOCIAL": score_es}

    # Escalate to financial category if ratio is extreme
    if ratio >= 5:
        resultado["FINANCEIRO"] = 25

    logger.info(
        f"unrealistic_return_detected "
        f"| base={x} | target={y} "
        f"| ratio={ratio:.1f}x "
        f"| score={score_es}"
    )

    return resultado


registrar_heuristica(
    nome="Promessa de retorno financeiro irreal",
    categoria="ENGENHARIA_SOCIAL",
    peso=0,
    detector=detectar_retorno_financeiro_irreal
)

# ======================================================================
# Fake Payment Receipt Heuristic (Critical Pattern)
# ======================================================================

def detectar_comprovante_falso(
    texto: str
) -> Union[Dict[str, int], bool]:
    """
    Detects fake PIX payment receipt scams.

    Suspicious indicators:
    - Receipt mention + confirmation pressure
    - "Transaction processing" status
    - Urgency escalation after receipt
    - Delivery / courier justification
    - Claims of debit before confirmation
    """

    t = texto.lower()

    # ------------------------------------------------------------------
    # Must indicate receipt context
    # ------------------------------------------------------------------
    tem_comprovante = any([
        'comprovante' in t,
        'comprovante de pagamento' in t,
        'comprovante pix' in t,
        'recibo' in t and 'pix' in t
    ])

    if not tem_comprovante:
        return False

    score = 0
    categoria: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # 1. Confirmation pressure after receipt
    # ------------------------------------------------------------------
    pede_confirmacao = any([
        'pode confirmar' in t,
        'confirma o recebimento' in t,
        'confirma aí' in t,
        'chegou' in t and '?' in texto,
        'recebeu' in t and '?' in texto
    ])

    if pede_confirmacao:
        score += 50
        logger.info("fake_receipt_detected | reason=confirmation_pressure")

    # ------------------------------------------------------------------
    # 2. "Transaction processing" indicator (high severity)
    # ------------------------------------------------------------------
    if 'processamento' in t or 'em processamento' in t:
        score += 60
        logger.info("fake_receipt_detected | reason=processing_status")

    # ------------------------------------------------------------------
    # 3. Urgency escalation
    # ------------------------------------------------------------------
    urgencia_termos = [
        'urgente', 'urgência',
        'agora', 'já está', 'esperando'
    ]

    if any(u in t for u in urgencia_termos):
        score += 30
        logger.info("fake_receipt_detected | reason=urgency")

    # ------------------------------------------------------------------
    # 4. Delivery / product justification
    # ------------------------------------------------------------------
    justificativas = [
        'motoboy', 'entrega',
        'produto', 'mercadoria',
        'caminho'
    ]

    if any(j in t for j in justificativas):
        score += 25
        logger.info("fake_receipt_detected | reason=delivery_justification")

    # ------------------------------------------------------------------
    # 5. Premature debit claim
    # ------------------------------------------------------------------
    if 'já foi debitado' in t or 'ja foi debitado' in t:
        score += 40
        logger.info("fake_receipt_detected | reason=premature_debit_claim")

    if score > 0:
        categoria['FALSO_COMPROVANTE'] = score
        return categoria

    return False


# Register heuristic
registrar_heuristica(
    nome="Comprovante de PIX falso",
    categoria="FALSO_COMPROVANTE",
    peso=0,
    detector=detectar_comprovante_falso
)

# ======================================================================
# Additional Heuristics
# ======================================================================

def detectar_phishing_classico(texto: str) -> bool:
    """
    Detects classic phishing pattern based on signal combination.

    Requires at least 3 of:
    - Presence of link
    - Credential request
    - Call-to-action verbs
    - Sensitive entity mention
    """

    t = texto.lower()

    indicadores = [
        contem_link(t),
        pede_credenciais(t),
        "clique" in t,
        "verifique" in t,
        menciona_entidade_sensivel(t)
    ]

    return indicadores.count(True) >= 3


registrar_heuristica(
    "Phishing clássico",
    "PHISHING",
    35,
    detectar_phishing_classico,
    "PHISHING_LINK"
)


def detectar_autoridade_institucional(texto: str) -> bool:
    """
    Detects institutional impersonation attempts.
    """

    t = texto.lower()

    alegacoes = [
        'sou do banco',
        'sou da receita',
        'central de segurança',
        'departamento de fraude'
    ]

    tem_alegacao = any(a in t for a in alegacoes)

    cargos = ['gerente', 'analista', 'técnico']
    tem_cargo = any(c in t for c in cargos)

    acoes = ['confirme seus dados', 'atualize cadastro']
    tem_acao = any(a in t for a in acoes)

    return (
        tem_alegacao and (tem_cargo or tem_acao)
    ) or 'central de segurança' in t


registrar_heuristica(
    "Autoridade institucional falsa",
    "AUTORIDADE",
    45,
    detectar_autoridade_institucional
)


def detectar_urgencia(texto: str) -> bool:
    """
    Detects urgency combined with call-to-action.
    """

    t = texto.lower()

    tem_urgencia = any(p in t for p in [
        "urgente", "agora", "imediatamente"
    ])

    tem_acao = any(p in t for p in [
        "clique", "acesse", "confirme", "pix"
    ])

    return tem_urgencia and tem_acao


registrar_heuristica(
    "Urgência com ação",
    "URGÊNCIA",
    30,
    detectar_urgencia
)

# ======================================================================
# Category Score Caps (Risk Normalization Layer)
# ======================================================================

TETO_POR_CATEGORIA = {
    "PHISHING": 70,
    "ENGENHARIA_SOCIAL": 80,
    "FINANCEIRO": 70,
    "MALWARE": 70,
    "CRYPTO": 60,
    "INFRAESTRUTURA": 50,
    "TRABALHO": 50,
    "ECOMMERCE": 50,
    "URL": 40,
    "URGÊNCIA": 50,
    "ENCURTADOR": 50,
    "DOMINIO_SUSPEITO": 50,
    "FALSO_COMPROVANTE": 100, 
    "AUTORIDADE": 60,
    "EMOCIONAL": 50,
}

# ======================================================================
# Heuristic Evaluation Engine
# ======================================================================

def avaliar_heuristicas(texto: str) -> Tuple[int, List[str], Dict[str, Any]]:
    """
    Executes all registered heuristics and computes normalized risk score.

    Pipeline:
    - Executes each heuristic detector
    - Aggregates category scores
    - Applies contextual legitimacy reductions
    - Enforces category caps
    - Returns total score, triggered reasons, and technical indicators
    """

    inicio = time.time()

    score_total = 0
    motivos: List[str] = []
    indicadores = defaultdict(int)
    score_por_categoria = defaultdict(int)
    grupos_ativados = defaultdict(int)

    # ------------------------------------------------------------------
    # Execute Registered Heuristics
    # ------------------------------------------------------------------
    for heur in HEURISTICAS_REGISTRADAS:
        try:
            resultado = heur.detector(texto)

            # Boolean heuristic (fixed weight)
            if isinstance(resultado, bool):
                if resultado:

                    if heur.grupo:
                        grupos_ativados[heur.grupo] += 1
                        if grupos_ativados[heur.grupo] > 2:
                            continue

                    score_por_categoria[heur.categoria] += heur.peso
                    motivos.append(f"{heur.categoria}: {heur.nome}")
                    indicadores[f"hit_{heur.nome}"] += 1

            # Dynamic scoring heuristic (dict return)
            elif isinstance(resultado, dict):
                for categoria, score in resultado.items():
                    if isinstance(score, (int, float)):
                        score_por_categoria[categoria] += score
                        motivos.append(f"{categoria}: {heur.nome}")

        except Exception:
            logger.exception(
                f"heuristic_execution_error | name={heur.nome}"
            )

    # ------------------------------------------------------------------
    # Apply Legitimate Context Reductions
    # ------------------------------------------------------------------
    score_por_categoria = aplicar_reducao_contexto_legitimo(
        score_por_categoria,
        texto
    )

    # ------------------------------------------------------------------
    # Apply Category Caps and Aggregate Final Score
    # ------------------------------------------------------------------
    for categoria, score_categoria in score_por_categoria.items():
        teto = TETO_POR_CATEGORIA.get(categoria, 50)
        score_normalizado = min(score_categoria, teto)

        score_total += score_normalizado
        indicadores[f"score_categoria_{categoria}"] = score_normalizado

    # ------------------------------------------------------------------
    # Performance Metrics
    # ------------------------------------------------------------------
    tempo_total = (time.time() - inicio) * 1000
    indicadores["tempo_avaliacao_ms"] = round(tempo_total, 2)
    indicadores["score_heuristico_base"] = score_total

    return score_total, motivos, dict(indicadores)

# ======================================================================
# Critical Category Combinations (Risk Amplification Layer)
# ======================================================================

COMBINACOES_CRITICAS = [
    {"categorias": ["FINANCEIRO", "URL"], "bonus": 70},
    {"categorias": ["FINANCEIRO", "ENCURTADOR"], "bonus": 90},
    {"categorias": ["ENGENHARIA_SOCIAL", "PHISHING"], "bonus": 90},
    {"categorias": ["ENGENHARIA_SOCIAL", "FINANCEIRO"], "bonus": 80},
    {"categorias": ["AUTORIDADE", "FINANCEIRO"], "bonus": 85},
    {"categorias": ["EMOCIONAL", "FINANCEIRO"], "bonus": 70},
]


def aplicar_combinacoes(
    score: int,
    motivos: List[str],
    indicadores: Dict
) -> Tuple[int, List[str]]:
    """
    Applies additional risk bonus when critical category
    combinations are detected simultaneously.

    Rationale:
    Certain fraud vectors become significantly more dangerous
    when combined (e.g., financial + authority impersonation).
    """

    categorias_ativas = set()

    for motivo in motivos:
        if ":" in motivo:
            categorias_ativas.add(
                motivo.split(":")[0].strip()
            )

    bonus_total = 0

    for combo in COMBINACOES_CRITICAS:
        if set(combo["categorias"]).issubset(categorias_ativas):
            bonus_total += combo["bonus"]

    if bonus_total > 0:
        indicadores["bonus_combinacoes"] = bonus_total

    return score + bonus_total, motivos

# ======================================================================
# Bedrock Metrics Persistence (DynamoDB Aggregation)
# ======================================================================

def incrementar_metrica_bedrock(
    metrica: str,
    valor: Union[int, float] = 1
):
    """
    Backward-compatible wrapper.
    Internally delegates to batch update method.
    """
    incrementar_metricas_bedrock_batch_interno(metrica, valor)


def incrementar_metricas_bedrock_batch_interno(
    metrica: str,
    valor: Union[int, float] = 1
):
    """
    Increments a single metric field using DynamoDB atomic ADD.
    """

    try:
        hoje = datetime.now(timezone.utc).date().isoformat()
        pk = f"METRICS#{hoje}"

        metrics_table.update_item(
            Key={"pk": pk, "sk": "bedrock"},
            UpdateExpression=f"ADD {metrica} :val",
            ExpressionAttributeValues={
                ":val": Decimal(str(valor))
            },
            ReturnValues="NONE"
        )

    except Exception as e:
        logger.error(
            f"metrics_increment_failed "
            f"| metric={metrica} | error={e}"
        )


def incrementar_metricas_bedrock_batch(
    modelo: str,
    custo: float
):
    """
    Atomic batch update:
    - total_calls
    - model-specific calls
    - total_cost_usd

    All updated in a single DynamoDB request.
    """

    try:
        hoje = datetime.now(timezone.utc).date().isoformat()
        pk = f"METRICS#{hoje}"

        campo_modelo = (
            "haiku_calls" if modelo == "haiku"
            else "sonnet_calls"
        )

        metrics_table.update_item(
            Key={"pk": pk, "sk": "bedrock"},
            UpdateExpression=(
                f"ADD total_calls :one, "
                f"{campo_modelo} :one, "
                f"total_cost_usd :custo"
            ),
            ExpressionAttributeValues={
                ":one": Decimal("1"),
                ":custo": Decimal(str(custo))
            },
            ReturnValues="NONE"
        )

    except Exception as e:
        logger.error(
            f"metrics_batch_update_failed | error={e}"
        )


def obter_metricas_bedrock(dias: int = 1) -> Dict[str, Any]:
    """
    Retrieves aggregated Bedrock metrics from DynamoDB.

    Args:
        dias: Number of past days to aggregate (default=1).

    Returns:
        Aggregated metrics dictionary.
    """

    try:
        hoje = datetime.now(timezone.utc).date()

        metricas_totais = {
            "total_calls": 0,
            "haiku_calls": 0,
            "sonnet_calls": 0,
            "total_cost_usd": 0.0,
            "cache_hits": 0,
            "fallback_count": 0
        }

        for i in range(dias):
            data = (hoje - timedelta(days=i)).isoformat()
            pk = f"METRICS#{data}"

            response = metrics_table.get_item(
                Key={"pk": pk, "sk": "bedrock"}
            )

            if "Item" in response:
                item = response["Item"]

                for key in metricas_totais:
                    if key in item:
                        metricas_totais[key] += float(item[key])

        return metricas_totais

    except Exception as e:
        logger.error(
            f"metrics_fetch_failed | error={e}"
        )
        return {}

# ======================================================================
# Bedrock Cost Calculation Utility
# ======================================================================

def calcular_custo_bedrock(
    modelo: str,
    tokens_input: int,
    tokens_output: int
) -> float:
    """
    Calculates estimated Bedrock usage cost based on token consumption.

    Pricing model:
    - Cost per 1M input tokens
    - Cost per 1M output tokens
    - Differentiated by model (Haiku vs Sonnet)

    Returns:
        Estimated USD cost rounded to 6 decimal places.
    """

    if "haiku" in modelo.lower():
        custo = (
            (tokens_input / 1_000_000 * CUSTO_HAIKU_INPUT_1M) +
            (tokens_output / 1_000_000 * CUSTO_HAIKU_OUTPUT_1M)
        )
    else:  # Default to Sonnet pricing
        custo = (
            (tokens_input / 1_000_000 * CUSTO_SONNET_INPUT_1M) +
            (tokens_output / 1_000_000 * CUSTO_SONNET_OUTPUT_1M)
        )

    return round(custo, 6)

# ======================================================================
# Bedrock Response Validation (Anti-Hallucination Guard)
# ======================================================================

def validar_resposta_bedrock(
    resultado_json: dict
) -> Tuple[bool, str]:
    """
    Performs strict validation of Bedrock (LLM) JSON output.

    Validation rules:
    - probabilidade_golpe: integer between 0–100
    - nivel_manipulacao_psicologica: integer between 0–10
    - categoria_principal: allowed enum value
    - Required textual fields must exist and be non-empty strings

    Returns:
        (is_valid, error_message)
    """

    # ------------------------------------------------------------------
    # 1. Validate probabilidade_golpe
    # ------------------------------------------------------------------
    if "probabilidade_golpe" not in resultado_json:
        return False, "Campo probabilidade_golpe ausente"

    try:
        prob = int(resultado_json["probabilidade_golpe"])
        if not (0 <= prob <= 100):
            return False, (
                f"probabilidade_golpe inválida: {prob} "
                "(deve ser 0-100)"
            )
    except (ValueError, TypeError):
        return False, (
            f"probabilidade_golpe não é inteiro: "
            f"{resultado_json['probabilidade_golpe']}"
        )

    # ------------------------------------------------------------------
    # 2. Validate nivel_manipulacao_psicologica
    # ------------------------------------------------------------------
    if "nivel_manipulacao_psicologica" not in resultado_json:
        return False, "Campo nivel_manipulacao_psicologica ausente"

    try:
        manip = int(resultado_json["nivel_manipulacao_psicologica"])
        if not (0 <= manip <= 10):
            return False, (
                f"nivel_manipulacao_psicologica inválido: {manip} "
                "(deve ser 0-10)"
            )
    except (ValueError, TypeError):
        return False, "nivel_manipulacao_psicologica não é inteiro"

    # ------------------------------------------------------------------
    # 3. Validate categoria_principal
    # ------------------------------------------------------------------
    if "categoria_principal" not in resultado_json:
        return False, "Campo categoria_principal ausente"

    categorias_validas = [
        "PHISHING",
        "ENGENHARIA_SOCIAL",
        "FINANCEIRO",
        "MALWARE",
        "CRYPTO",
        "TRABALHO",
        "ECOMMERCE",
        "OUTRO"
    ]

    categoria = resultado_json["categoria_principal"].upper()

    if categoria not in categorias_validas:
        return False, (
            f"categoria_principal inválida: {categoria}"
        )

    # ------------------------------------------------------------------
    # 4. Validate required text fields
    # ------------------------------------------------------------------
    campos_texto = [
        "subtipo",
        "intencao_detectada",
        "explicacao_tecnica"
    ]

    for campo in campos_texto:
        if campo not in resultado_json:
            return False, f"Campo {campo} ausente"

        if not isinstance(resultado_json[campo], str):
            return False, f"Campo {campo} não é string"

        if len(resultado_json[campo].strip()) == 0:
            return False, f"Campo {campo} está vazio"

    return True, ""

# ======================================================================
# Resilient JSON Extraction (Regex Fallback Strategy)
# ======================================================================

def extrair_json_com_regex(
    texto_resposta: str
) -> Optional[dict]:
    """
    Attempts to extract valid JSON from LLM output using fallback strategies.

    Handles:
    - JSON wrapped in markdown blocks (```json ... ```)
    - JSON with leading/trailing explanatory text
    - Valid JSON with formatting noise
    """

    # ------------------------------------------------------------------
    # 1. Attempt to extract JSON block via regex
    # ------------------------------------------------------------------
    match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)

    if match:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # ------------------------------------------------------------------
    # 2. Attempt to remove markdown fences
    # ------------------------------------------------------------------
    texto_limpo = texto_resposta.strip()

    if texto_limpo.startswith("```json"):
        texto_limpo = texto_limpo[7:]

    if texto_limpo.startswith("```"):
        texto_limpo = texto_limpo[3:]

    if texto_limpo.endswith("```"):
        texto_limpo = texto_limpo[:-3]

    texto_limpo = texto_limpo.strip()

    try:
        return json.loads(texto_limpo)
    except json.JSONDecodeError:
        pass

    return None

# ======================================================================
# Bedrock Prompt Builder (Few-Shot Enhanced - v5.1)
# ======================================================================

def construir_prompt_bedrock(
    texto: str,
    score_heuristico: int,
    categorias: List[str],
    sinais: Dict[str, float],
    nivel_analise: str = "basico"
) -> str:
    """
    Builds structured prompt for Claude via Bedrock.

    - Supports basic mode (concise evaluation)
    - Supports deep mode with few-shot examples (Sonnet)
    """

    sinais_str = ", ".join(
        [f"{k}={v:.1f}" for k, v in sinais.items() if v != 0]
    )

    categorias_str = ", ".join(categorias) if categorias else "Nenhuma"

    # ------------------------------------------------------------------
    # Deep analysis mode (Few-Shot)
    # ------------------------------------------------------------------
    if nivel_analise == "profundo":

        prompt = f"""Você é um sistema técnico especializado em detecção de fraudes digitais, engenharia social e golpes financeiros.

Analise o texto abaixo com profundidade máxima, considerando:
- Intenção implícita e manipulação psicológica
- Coerência narrativa e contradições internas
- Pressão emocional e temporal
- Padrões de urgência artificial
- Perfil psicológico do emissor
- Probabilidade real de fraude

EXEMPLOS DE RESPOSTA CORRETA:

Entrada: "MÃE! ME SEQUESTRARAM! NÃO CHAMA POLÍCIA! TRANSFERE R$ 5000 AGORA!"
Saída: {{"probabilidade_golpe":98,"categoria_principal":"ENGENHARIA_SOCIAL","subtipo":"falso sequestro","nivel_manipulacao_psicologica":9,"intencao_detectada":"extorsão via pânico familiar","explicacao_tecnica":"proibição de contato com autoridades + urgência extrema + vínculo familiar"}}

Entrada: "Recebi mensagem pedindo PIX. Isso é golpe?"
Saída: {{"probabilidade_golpe":5,"categoria_principal":"OUTRO","subtipo":"consulta investigativa","nivel_manipulacao_psicologica":0,"intencao_detectada":"usuário verificando suspeita","explicacao_tecnica":"contexto de dúvida explícita, sem padrão de fraude"}}

Responda EXCLUSIVAMENTE em JSON válido (sem comentários, sem markdown):

{{
  "probabilidade_golpe": 0-100,
  "categoria_principal": "PHISHING|ENGENHARIA_SOCIAL|FINANCEIRO|MALWARE|CRYPTO|TRABALHO|ECOMMERCE|OUTRO",
  "subtipo": "descrição curta do subtipo",
  "nivel_manipulacao_psicologica": 0-10,
  "intencao_detectada": "descrição técnica da intenção",
  "explicacao_tecnica": "explicação técnica concisa"
}}

Texto a analisar:
\"\"\"
{texto[:800]}
\"\"\"

Score heurístico preliminar: {score_heuristico}
Categorias detectadas: {categorias_str}
Sinais semânticos: {sinais_str}

Responda apenas o JSON, sem texto adicional."""

    # ------------------------------------------------------------------
    # Basic analysis mode
    # ------------------------------------------------------------------
    else:

        prompt = f"""Você é um detector técnico de fraudes. Responda APENAS em JSON válido, sem texto adicional, sem markdown.

Formato obrigatório:
{{
  "probabilidade_golpe": <numero entre 0 e 100>,
  "categoria_principal": "<PHISHING|ENGENHARIA_SOCIAL|FINANCEIRO|MALWARE|OUTRO>",
  "subtipo": "<string curta>",
  "nivel_manipulacao_psicologica": <numero entre 0 e 10>,
  "intencao_detectada": "<string>",
  "explicacao_tecnica": "<string>"
}}

Texto a analisar:
\"\"\"{texto[:500]}\"\"\"

Score heurístico: {score_heuristico}
Categorias: {categorias_str}"""

    return prompt

# ======================================================================
# Bedrock Invocation Layer (Primary LLM Integration)
# ======================================================================

def chamar_bedrock_claude(
    texto: str,
    score_heuristico: int,
    categorias: List[str],
    sinais: Dict[str, float],
    modelo: str = "haiku",
    nivel_analise: str = "basico"
) -> Optional[RespostaBedrock]:
    """
    Invokes Claude via Amazon Bedrock.

    Enhancements (v5.1):
    - Anti-hallucination validation
    - Regex-based JSON recovery
    - DynamoDB-based metrics tracking
    - Cost calculation per request
    """

    if not BEDROCK_ENABLED:
        logger.info("bedrock_skipped | reason=disabled")
        return None

    inicio = time.time()

    model_id = (
        BEDROCK_MODEL_HAIKU
        if modelo == "haiku"
        else BEDROCK_MODEL_SONNET
    )

    prompt = construir_prompt_bedrock(
        texto,
        score_heuristico,
        categorias,
        sinais,
        nivel_analise
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": BEDROCK_MAX_TOKENS,
        "temperature": 0.0,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())
        tempo_ms = (time.time() - inicio) * 1000

        texto_resposta = response_body["content"][0]["text"]

        # --------------------------------------------------------------
        # JSON Parsing
        # --------------------------------------------------------------
        resultado_json = None

        try:
            resultado_json = json.loads(texto_resposta.strip())
        except json.JSONDecodeError:
            logger.warning("bedrock_invalid_json | attempting_regex_recovery")
            resultado_json = extrair_json_com_regex(texto_resposta)

            if resultado_json is None:
                logger.error("bedrock_json_recovery_failed")
                incrementar_metrica_bedrock("fallback_count", 1)
                return None

        # --------------------------------------------------------------
        # Anti-Hallucination Validation
        # --------------------------------------------------------------
        valido, motivo_erro = validar_resposta_bedrock(resultado_json)

        if not valido:
            logger.error(
                f"bedrock_validation_failed | reason={motivo_erro}"
            )
            logger.error(
                f"bedrock_invalid_payload | payload={resultado_json}"
            )
            incrementar_metrica_bedrock("fallback_count", 1)
            return None

        # --------------------------------------------------------------
        # Token Usage & Cost Calculation
        # --------------------------------------------------------------
        tokens_input = response_body["usage"]["input_tokens"]
        tokens_output = response_body["usage"]["output_tokens"]

        custo = calcular_custo_bedrock(
            model_id,
            tokens_input,
            tokens_output
        )

        # Non-blocking metrics update
        threading.Thread(
            target=incrementar_metricas_bedrock_batch,
            args=(modelo, custo),
            daemon=True
        ).start()

        # Structured success log
        logger.info(json.dumps({
            "event": "bedrock_success",
            "model": modelo,
            "analysis_level": nivel_analise,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": custo,
            "latency_ms": round(tempo_ms, 2),
            "fraud_probability": resultado_json["probabilidade_golpe"]
        }))

        return RespostaBedrock(
            probabilidade_golpe=int(resultado_json["probabilidade_golpe"]),
            categoria_principal=resultado_json["categoria_principal"],
            subtipo=resultado_json["subtipo"],
            nivel_manipulacao_psicologica=int(
                resultado_json["nivel_manipulacao_psicologica"]
            ),
            intencao_detectada=resultado_json["intencao_detectada"],
            explicacao_tecnica=resultado_json["explicacao_tecnica"],
            modelo_usado=modelo,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            custo_usd=custo,
            tempo_ms=round(tempo_ms, 2)
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        logger.error(
            f"bedrock_client_error | code={error_code}"
        )
        incrementar_metrica_bedrock("fallback_count", 1)
        return None

    except Exception as e:
        logger.error(
            f"bedrock_unexpected_error | error={str(e)}"
        )
        logger.error(traceback.format_exc())
        incrementar_metrica_bedrock("fallback_count", 1)
        return None

# ======================================================================
# Bedrock Escalation Decision Engine (Hybrid Orchestrator)
# ======================================================================

def decidir_escalonamento_bedrock(
    score_heuristico: int,
    categorias_ativas: set,
    sinais: Dict[str, float],
    texto: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Determines whether to escalate to Bedrock (LLM)
    and selects model + analysis depth.

    Decision layers:
    - Safe zone (no IA)
    - Obvious scam (no IA)
    - Cognitive zone with adaptive triggers
    - Model selection (Haiku vs Sonnet)
    """

    # ------------------------------------------------------------------
    # Safe Zone (Low Risk)
    # ------------------------------------------------------------------
    if score_heuristico < ZONA_COGNITIVA_MIN:
        logger.info(
            f"escalation_decision | action=skip | "
            f"reason=safe_zone | score={score_heuristico}"
        )
        return False, None, None

    # ------------------------------------------------------------------
    # Obvious Scam Zone (High Risk)
    # ------------------------------------------------------------------
    if score_heuristico >= ZONA_COGNITIVA_MAX:
        logger.info(
            f"escalation_decision | action=skip | "
            f"reason=obvious_scam | score={score_heuristico}"
        )
        return False, None, None

    # ------------------------------------------------------------------
    # Adaptive Trigger Layer
    # ------------------------------------------------------------------
    categorias_criticas = {
        "PHISHING",
        "ENGENHARIA_SOCIAL",
        "FINANCEIRO",
        "AUTORIDADE"
    }

    tem_categoria_critica = bool(
        categorias_criticas & categorias_ativas
    )

    ipp_estimado = (
        sinais.get("urgencia", 0) * 10 +
        sinais.get("ameaca", 0) * 20
    )

    tem_link = (
        "http://" in texto.lower() or
        "https://" in texto.lower() or
        "www." in texto.lower()
    )

    gatilho_adicional = (
        score_heuristico >= 30 or
        ipp_estimado >= 15 or
        tem_link
    )

    if not tem_categoria_critica and not gatilho_adicional:
        logger.info(
            "escalation_decision | action=skip | "
            "reason=no_valid_triggers"
        )
        return False, None, None

    logger.info(
        "escalation_decision | action=invoke_llm | "
        f"score={score_heuristico}"
    )

    # ------------------------------------------------------------------
    # Model Selection
    # ------------------------------------------------------------------
    if score_heuristico <= ZONA_SONNET_BASICO_MAX:
        return True, "haiku", "basico"
    else:
        return True, "sonnet", "profundo"

# ======================================================================
# Intelligent Double-Pass Escalation (Haiku → Sonnet)
# ======================================================================

def decidir_repass_sonnet(
    resposta_haiku: RespostaBedrock
) -> bool:
    """
    Determines whether a second-pass analysis with Sonnet is required
    after an initial Haiku evaluation.

    Escalation triggers:
    - Ambiguous probability range
    - High psychological manipulation score
    - Strong contradiction signals detected in subtype
    """

    prob = resposta_haiku.probabilidade_golpe
    manip = resposta_haiku.nivel_manipulacao_psicologica

    # ------------------------------------------------------------------
    # 1. Ambiguous probability range
    # ------------------------------------------------------------------
    if SONNET_REPASS_PROB_MIN <= prob <= SONNET_REPASS_PROB_MAX:
        logger.info(
            f"double_pass_trigger | reason=ambiguous_probability "
            f"| value={prob}"
        )
        return True

    # ------------------------------------------------------------------
    # 2. High manipulation score
    # ------------------------------------------------------------------
    if manip >= SONNET_REPASS_MANIPULACAO:
        logger.info(
            f"double_pass_trigger | reason=high_manipulation "
            f"| value={manip}"
        )
        return True

    # ------------------------------------------------------------------
    # 3. Strong contradiction indicator
    # ------------------------------------------------------------------
    subtipo_lower = resposta_haiku.subtipo.lower()

    if (
        "contradição" in subtipo_lower or
        "inconsistência" in subtipo_lower
    ):
        logger.info(
            "double_pass_trigger | reason=contradiction_detected"
        )
        return True

    logger.info("double_pass_trigger | action=skip")
    return False

# ======================================================================
# Hybrid Score Fusion Engine
# ======================================================================

def fusao_hibrida_score(
    score_heuristico: int,
    resposta_bedrock: Optional[RespostaBedrock],
    indicadores: Dict[str, Any]
) -> int:
    """
    Combines heuristic score with Bedrock probability output.

    Features:
    - Cognitive divergence detection
    - Dynamic weighting
    - Manipulation-based adjustment
    - Low-confidence dampening
    - Score normalization
    """

    if resposta_bedrock is None:
        indicadores["fusao_aplicada"] = False
        return score_heuristico

    score_bedrock = resposta_bedrock.probabilidade_golpe

    # ------------------------------------------------------------------
    # Cognitive Divergence Detection
    # ------------------------------------------------------------------
    divergencia = abs(score_heuristico - score_bedrock)

    if divergencia > DIVERGENCIA_THRESHOLD:
        indicadores["divergencia_cognitiva"] = True
        indicadores["divergencia_valor"] = divergencia

        logger.warning(
            f"cognitive_divergence_detected "
            f"| heur={score_heuristico} "
            f"| bedrock={score_bedrock} "
            f"| diff={divergencia}"
        )

    # ------------------------------------------------------------------
    # Dynamic Weight Selection
    # ------------------------------------------------------------------
    if score_heuristico >= 100:
        peso_heur = PESO_HEURISTICA_ALTO
        peso_bedrock = PESO_BEDROCK_ALTO
    else:
        peso_heur = PESO_HEURISTICA_BAIXO
        peso_bedrock = PESO_BEDROCK_BAIXO

    score_fusao = int(
        (score_heuristico * peso_heur) +
        (score_bedrock * peso_bedrock)
    )

    logger.info(
        f"hybrid_fusion "
        f"| heur={score_heuristico} "
        f"| bedrock={score_bedrock} "
        f"| fused={score_fusao}"
    )

    # ------------------------------------------------------------------
    # High Psychological Manipulation Boost
    # ------------------------------------------------------------------
    if resposta_bedrock.nivel_manipulacao_psicologica >= 8:
        score_fusao += 10
        indicadores["ajuste_manipulacao"] = 10

        logger.info(
            f"manipulation_boost_applied "
            f"| level={resposta_bedrock.nivel_manipulacao_psicologica}"
        )

    # ------------------------------------------------------------------
    # Low Confidence Dampening
    # ------------------------------------------------------------------
    if score_heuristico <= 30 and score_bedrock <= 15:
        score_antes = score_fusao
        score_fusao = int(score_fusao * 0.85)

        indicadores["ajuste_ambos_baixos"] = (
            score_antes - score_fusao
        )

        logger.info(
            f"low_confidence_dampening "
            f"| before={score_antes} "
            f"| after={score_fusao}"
        )

    # ------------------------------------------------------------------
    # Final Score Normalization
    # ------------------------------------------------------------------
    score_fusao = max(score_fusao, 0)
    score_fusao = min(score_fusao, 200)

    # ------------------------------------------------------------------
    # Observability Enrichment
    # ------------------------------------------------------------------
    indicadores["fusao_aplicada"] = True
    indicadores["score_heuristico_original"] = score_heuristico
    indicadores["score_bedrock"] = score_bedrock
    indicadores["score_fusao_final"] = score_fusao
    indicadores["peso_heuristico_usado"] = peso_heur
    indicadores["peso_bedrock_usado"] = peso_bedrock
    indicadores["bedrock_modelo"] = resposta_bedrock.modelo_usado
    indicadores["bedrock_custo_usd"] = resposta_bedrock.custo_usd
    indicadores["bedrock_tempo_ms"] = resposta_bedrock.tempo_ms

    return score_fusao

# ======================================================================
# Temporal Manipulation Detection
# ======================================================================

def detectar_manipulacao_temporal(
    texto: str,
    sinais: Dict[str, float]
) -> Tuple[bool, str]:
    """
    Detects artificial time pressure and deadline-based manipulation.

    Triggers:
    - Urgency + short deadline + threat
    - Countdown language (expiration / last chance)
    """

    t = texto.lower()

    # ------------------------------------------------------------------
    # Urgency + Short Deadline + Threat
    # ------------------------------------------------------------------
    if sinais.get("urgencia", 0) > 0:

        prazos_curtos = [
            "hoje",
            "agora",
            "24h",
            "1 hora",
            "imediatamente"
        ]

        tem_prazo = any(p in t for p in prazos_curtos)
        tem_ameaca = sinais.get("ameaca", 0) > 0

        if tem_prazo and tem_ameaca:
            return (
                True,
                "Manipulação temporal: urgência + prazo curto + ameaça"
            )

    # ------------------------------------------------------------------
    # Explicit Expiration / Countdown Language
    # ------------------------------------------------------------------
    if re.search(
        r"\b(expira|vence|última chance|último dia)\b",
        t
    ):
        return (
            True,
            "Manipulação temporal: contagem regressiva"
        )

    return False, ""

# ======================================================================
# Google Safe Browsing Integration
# ======================================================================

def consultar_google_safe_browsing(url: str) -> str:
    """
    Queries Google Safe Browsing API for URL threat intelligence.

    Returns:
        - "SAFE"       → No threat detected
        - Threat type  → e.g. MALWARE, SOCIAL_ENGINEERING
        - "UNKNOWN"    → Request failed after retries
    """

    api_key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY")

    if not api_key:
        return "SAFE"

    endpoint = (
        "https://safebrowsing.googleapis.com/v4/"
        f"threatMatches:find?key={api_key}"
    )

    payload = {
        "client": {
            "clientId": "guardinia",
            "clientVersion": "5.1"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    def fazer_requisicao():
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        if "matches" in data and data["matches"]:
            threat = data["matches"][0].get(
                "threatType",
                "SUSPICIOUS"
            )
            return threat

        return "SAFE"

    resultado = executar_com_retry(
        fazer_requisicao,
        max_tentativas=2,
        descricao="Safe Browsing"
    )

    if resultado is None:
        return "UNKNOWN"

    return resultado

# ======================================================================
# Cache, Audit & Final Classification Layer
# ======================================================================

def agora_iso() -> str:
    """
    Returns current UTC timestamp in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def calcular_ttl() -> int:
    """
    Calculates expiration timestamp for DynamoDB TTL.
    """
    return int(time.time()) + TTL_SECONDS


def buscar_cache(conteudo_hash: str) -> Optional[Dict]:
    """
    Retrieves latest cached analysis result for given content hash.
    """

    try:
        response = audit_table.query(
            KeyConditionExpression=Key("pk").eq(conteudo_hash),
            ScanIndexForward=False,
            Limit=1
        )

        items = response.get("Items", [])

        if items:
            incrementar_metrica_bedrock("cache_hits", 1)

        return items[0] if items else None

    except Exception as e:
        logger.error(
            f"cache_lookup_failed | error={e}"
        )
        return None


def salvar_cache(
    conteudo_hash: str,
    resultado: ResultadoAnalise,
    resposta_formatada: str,
    resposta_bedrock: Optional[RespostaBedrock] = None
):
    """
    Persists analysis result into DynamoDB audit table.
    """

    try:
        timestamp = agora_iso()

        item = {
            "pk": conteudo_hash,
            "sk": timestamp,
            "type": "text",
            "source": "whatsapp",
            "result": resposta_formatada,
            "score": resultado.score_total,
            "status": resultado.status,
            "created_at": timestamp,
            "ttl": calcular_ttl(),
            "version": "5.1"
        }

        if resposta_bedrock:
            item["bedrock_usado"] = True
            item["bedrock_modelo"] = resposta_bedrock.modelo_usado
            item["bedrock_probabilidade"] = (
                resposta_bedrock.probabilidade_golpe
            )
            item["bedrock_custo_usd"] = Decimal(
                str(resposta_bedrock.custo_usd)
            )

        audit_table.put_item(Item=item)

    except Exception as e:
        logger.error(
            f"cache_save_failed | error={e}"
        )


# ----------------------------------------------------------------------
# Final Risk Classification
# ----------------------------------------------------------------------

def classificar(score: int) -> Tuple[str, str, int, str]:
    """
    Converts numeric score into user-facing classification.

    Returns:
        (status_label, color, confidence, recommended_action)
    """

    if score >= 120:
        return (
            "🔴 GOLPE CONFIRMADO",
            "vermelho",
            95,
            "🚫 NÃO interaja. Bloqueie e denuncie."
        )

    elif score >= 80:
        return (
            "🟠 ALTAMENTE SUSPEITO",
            "laranja",
            85,
            "⚠️ Muito provavelmente golpe. Não clique."
        )

    elif score >= 50:
        return (
            "🟡 SUSPEITO",
            "amarelo",
            70,
            "⚠️ Verifique cuidadosamente antes de agir."
        )

    elif score >= 30:
        return (
            "🟢 BAIXO RISCO",
            "verde-claro",
            50,
            "✅ Aparenta ser legítimo, mas mantenha cautela."
        )

    else:
        return (
            "✅ SEGURO",
            "verde",
            95,
            "✅ Nenhum indicador de golpe detectado."
        )

# ======================================================================
# Full Analysis Pipeline (Production-Ready)
# ======================================================================

def analisar_mensagem_guardinia_v5_1(texto: str) -> ResultadoAnalise:
    """
    Complete GuardinIA hybrid analysis pipeline.

    Flow:
    - Input normalization & validation
    - Heuristic scoring
    - Semantic enrichment
    - Psychological pressure modeling
    - Legitimate billing reduction
    - Adaptive LLM escalation
    - Hybrid fusion
    - Final classification
    """

    inicio_total = time.time()
    texto = normalizar_texto(texto)

    # ------------------------------------------------------------------
    # Input Validation
    # ------------------------------------------------------------------
    valido, erro = validar_entrada(texto)

    if not valido:
        return ResultadoAnalise(
            status="❌ ERRO",
            cor="cinza",
            confianca=0,
            score_total=0,
            motivos=[f"Entrada inválida: {erro}"],
            acao_recomendada="Envie um texto válido para análise.",
            indicadores_tecnicos={},
            texto_analisado=texto[:200]
        )

    # ------------------------------------------------------------------
    # 1. Base Heuristic Score
    # ------------------------------------------------------------------
    score_base, motivos_base, indicadores = avaliar_heuristicas(texto)
    score_total, motivos = aplicar_combinacoes(
        score_base,
        motivos_base,
        indicadores
    )

    # ------------------------------------------------------------------
    # 2. Semantic Layer
    # ------------------------------------------------------------------
    sinais = extrair_sinais_semanticos(texto)

    score_semantico = sum(
        v for v in sinais.values() if v > 0
    ) * MULTIPLICADOR_SEMANTICO

    if score_semantico > 0:
        score_total += int(score_semantico)
        indicadores["score_semantico"] = int(score_semantico)
        indicadores["sinais_detectados"] = {
            k: v for k, v in sinais.items() if v != 0
        }

    # ------------------------------------------------------------------
    # 3. Psychological Pressure Index (IPP)
    # ------------------------------------------------------------------
    ipp = calcular_indice_pressao(texto, sinais)

    if ipp > 0:
        score_total += int(ipp)
        indicadores["indice_pressao_psicologica"] = int(ipp)

        if ipp >= 25:
            motivos.append(
                "Uso de forte pressão emocional ou senso de urgência"
            )
        elif ipp >= 12:
            motivos.append(
                "Uso moderado de urgência ou ameaça implícita"
            )
        elif ipp >= 5:
            motivos.append(
                "Leve presença de linguagem persuasiva"
            )

    # ------------------------------------------------------------------
    # 4. Investigative Reduction
    # ------------------------------------------------------------------
    if sinais.get("investigativo", 0) < 0:
        score_antes = score_total
        score_total = int(score_total * REDUCAO_INVESTIGATIVO)

        indicadores["ajuste_investigativo"] = True
        indicadores["reducao_aplicada"] = (
            score_antes - score_total
        )

    # ------------------------------------------------------------------
    # 5. Structured Legitimate Billing Reduction
    # ------------------------------------------------------------------
    t = texto.lower()

    possui_valor = bool(
        re.search(r'r\$\s?\d+[.,]?\d*', t)
    )

    possui_parcela_ou_contrato = bool(
        re.search(r'parcela\s?\d+', t) or
        re.search(r'n[úu]mero\s?\d+', t) or
        re.search(r'\b\d{8,}\b', t)
    )

    possui_solicitacao_sensivel = any(
        x in t for x in [
            "senha",
            "token",
            "código",
            "codigo",
            "confirme seus dados"
        ]
    )

    possui_ameaca_forte = any(
        x in t for x in [
            "bloqueado imediatamente",
            "prisão",
            "último aviso",
            "suspensão imediata"
        ]
    )

    if (
        possui_valor and
        possui_parcela_ou_contrato and
        not possui_solicitacao_sensivel and
        not possui_ameaca_forte
    ):
        score_antes = score_total
        score_total = int(score_total * 0.55)

        indicadores["reducao_cobranca_estruturada"] = (
            score_antes - score_total
        )

        motivos.append(
            "Cobrança estruturada detectada (padrão legítimo)"
        )

    # ------------------------------------------------------------------
    # 6. Non-Linear Escalation
    # ------------------------------------------------------------------
    categorias_criticas = [
        "PHISHING",
        "ENGENHARIA_SOCIAL",
        "FINANCEIRO"
    ]

    categorias_criticas_ativas = [
        cat for cat in categorias_criticas
        if indicadores.get(f"score_categoria_{cat}", 0) > 0
    ]

    if len(categorias_criticas_ativas) >= 3:
        score_total = int(score_total * MULTIPLICADOR_CRITICO)
        indicadores["multiplicador_critico_aplicado"] = (
            MULTIPLICADOR_CRITICO
        )

    score_heuristico_final = min(score_total, 200)
    indicadores["score_heuristico_final"] = (
        score_heuristico_final
    )

    # ------------------------------------------------------------------
    # 7. LLM Escalation Decision
    # ------------------------------------------------------------------
    categorias_ativas = set(
        m.split(":")[0].strip()
        for m in motivos
        if ":" in m
    )

    deve_chamar, modelo, nivel = decidir_escalonamento_bedrock(
        score_heuristico_final,
        categorias_ativas,
        sinais,
        texto
    )

    resposta_bedrock = None

    if deve_chamar:
        categorias_lista = list(categorias_ativas)

        if modelo == "haiku":
            resposta_bedrock = chamar_bedrock_claude(
                texto,
                score_heuristico_final,
                categorias_lista,
                sinais,
                modelo="haiku",
                nivel_analise="basico"
            )

            if (
                resposta_bedrock and
                decidir_repass_sonnet(resposta_bedrock)
            ):
                resposta_bedrock = chamar_bedrock_claude(
                    texto,
                    score_heuristico_final,
                    categorias_lista,
                    sinais,
                    modelo="sonnet",
                    nivel_analise="profundo"
                )
        else:
            resposta_bedrock = chamar_bedrock_claude(
                texto,
                score_heuristico_final,
                categorias_lista,
                sinais,
                modelo,
                nivel
            )

        if resposta_bedrock:
            score_total = fusao_hibrida_score(
                score_heuristico_final,
                resposta_bedrock,
                indicadores
            )
            motivos.append(
                "Análise cognitiva avançada aplicada"
            )
        else:
            score_total = score_heuristico_final
    else:
        score_total = score_heuristico_final

    # ------------------------------------------------------------------
    # 8. Temporal Manipulation Adjustment
    # ------------------------------------------------------------------
    tem_manipulacao_temporal, _ = (
        detectar_manipulacao_temporal(texto, sinais)
    )

    if tem_manipulacao_temporal:
        score_total += 12
        indicadores["manipulacao_temporal"] = True

    score_total = min(score_total, 200)

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------
    tempo_total = (time.time() - inicio_total) * 1000
    indicadores["tempo_total_ms"] = round(tempo_total, 2)
    indicadores["score_final_limitado"] = score_total

    status, cor, confianca, acao = classificar(score_total)

    logger.info(json.dumps({
        "event": "analysis_complete_v5_1",
        "heuristic_score": score_heuristico_final,
        "final_score": score_total,
        "bedrock_used": resposta_bedrock is not None,
        "bedrock_model": (
            resposta_bedrock.modelo_usado
            if resposta_bedrock else None
        ),
        "latency_ms": round(tempo_total, 2),
        "classification": status
    }))

    return ResultadoAnalise(
        status=status,
        cor=cor,
        confianca=confianca,
        score_total=score_total,
        motivos=motivos,
        acao_recomendada=acao,
        indicadores_tecnicos=indicadores,
        texto_analisado=texto[:500]
    )

# ======================================================================
# WhatsApp Utilities (Greeting Detection + Messaging)
# ======================================================================

def eh_saudacao_inteligente(texto: str) -> bool:
    if not texto:
        return False

    # Normalização
    t = texto.strip().lower()

    # Remove pontuação leve
    t = re.sub(r'[!?.]+', '', t)
    t = re.sub(r'\s+', ' ', t)

    palavras = t.split()

    # Se for frase longa, não é saudação simples
    if len(palavras) > 3:
        return False

    # Se contém termos de análise, não é menu
    termos_analise = {
        "golpe", "fraude", "seguro", "suspeito",
        "pix", "link", "mensagem", "analisa",
        "verifica", "avaliar", "checagem"
    }

    if any(p in termos_analise for p in palavras):
        return False

    # --------------------------------------------------------------
    # Saudações simples (1 palavra)
    # --------------------------------------------------------------
    saudacoes_simples = {
        # Clássicos
        "oi", "ola", "olá",
        "opa", "opa!",

        # Gírias comuns
        "fala", "salve", "eae", "eai", "eaii",
        "eaee", "eaei", "eaiii",

        # Informais
        "menu", "ajuda",
        "hey", "hello", "hi",

        # Variações com repetição
        "opaa", "opaaa", "opaaaa",
        "oii", "oiii", "oiiii",
        "olaaa", "olaaa",
        "falaaa", "falai",

        # Regionais
        "coe", "coé", "coee",
        "iae", "iae?",

        # Informal urbano
        "suave", "tranquilo",
        "tranquila", "tranqs"
    }

    # --------------------------------------------------------------
    # Saudações compostas (2 palavras)
    # --------------------------------------------------------------
    saudacoes_compostas = {
        # Tradicionais
        "bom dia",
        "boa tarde",
        "boa noite",

        # Informais
        "e ae",
        "e aee",
        "e aeeee",
        "e ai",
        "e aii",
        "e ai?",
        "e aí",
        "e aí?",
        "fala ai",
        "fala aí",
        "salve salve",

        # Compostos comuns
        "bom diaa",
        "boa tardee",
        "boa noitee",
        "opa tudo",
        "oi tudo",
        "olá tudo",

        # Cumprimento + pergunta curta
        "oi tudo",
        "oi td",
        "ola td",
        "olá td"
    }

    # Caso simples: primeira palavra
    if palavras[0] in saudacoes_simples:
        return True

    # Caso composto: duas primeiras palavras
    if len(palavras) >= 2:
        inicio = f"{palavras[0]} {palavras[1]}"
        if inicio in saudacoes_compostas:
            return True

    return False


def menu_inicial_guardinia() -> str:
    return (
        "Aqui é o GuardinIA 🤖🛡️\n"
        "Sistema híbrido com IA avançada para detecção de fraudes.\n\n"
        "📌 Como posso ajudar:\n"
        "• Analisar imagens\n"
        "• Avaliar mensagens\n"
        "• Identificar golpes sofisticados"
    )


def enviar_mensagem_whatsapp(telefone: str, texto: str):
    if not telefone or not texto:
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    texto_seguro = truncar_seguro(texto, 4096)

    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": texto_seguro}
    }

    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)

    except Exception as e:
        logger.error(f"whatsapp_send_failed | error={e}")

# ======================================================================
# Protective Advisory Layer (Portfolio Safe Mode)
# ======================================================================

def eh_consulta_investigativa(texto: str) -> bool:
    """
    Detects whether the user is asking a verification question
    (investigative intent rather than active scam execution).
    """

    if not texto:
        return False

    t = texto.lower()

    padroes = [
        "isso é normal",
        "isso e normal",
        "isso é golpe",
        "isso e golpe",
        "pode ser golpe",
        "é seguro",
        "e seguro",
        "posso confiar",
        "é fraude",
        "e fraude",
        "isso pode ser",
        "é confiável",
        "e confiavel",
        "isso é verdade"
    ]

    if any(p in t for p in padroes):
        return True

    if (
        "?" in texto and
        any(p in t for p in [
            "golpe",
            "seguro",
            "normal",
            "fraude",
            "confiar"
        ])
    ):
        return True

    return False


def deve_ativar_orientacao(
    texto: str,
    indicadores: dict
) -> bool:
    """
    Activates advisory guidance only if:
    - The user demonstrates investigative intent
    - The engine already detected risk signals
    """

    if not eh_consulta_investigativa(texto):
        return False

    score_base = indicadores.get("score_heuristico_base", 0)
    score_semantico = indicadores.get("score_semantico", 0)

    if score_base > 0 or score_semantico >= 20:
        return True

    return False


def resposta_orientativa_padrao() -> str:
    """
    Standard advisory message for investigative scenarios.
    """

    return (
        "🟡 Atenção\n\n"
        "O padrão descrito é comum em tentativas de fraude.\n"
        "Recomendo verificar diretamente pelo aplicativo oficial "
        "ou pelo número atrás do seu cartão antes de tomar qualquer ação.\n\n"
        "⚠️ Nunca compartilhe senhas, códigos ou dados pessoais por WhatsApp."
    )

# ======================================================================
# Message Processing Orchestrator
# ======================================================================

def processar_mensagem(texto_original: str) -> str:
    """
    Main orchestration layer for incoming WhatsApp messages.

    Flow:
    - Greeting detection
    - Cache lookup
    - Safe Browsing verification
    - Full hybrid analysis
    - Protective advisory layer
    - Response formatting
    - Async cache persistence
    """

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------
    if not texto_original or len(texto_original.strip()) == 0:
        return "❌ Mensagem vazia."

    texto_limpo = normalizar_texto(texto_original)

    # ------------------------------------------------------------------
    # Greeting shortcut
    # ------------------------------------------------------------------
    if eh_saudacao_inteligente(texto_limpo):
        return (
            f"{texto_original}, tudo bem?\n\n"
            f"{menu_inicial_guardinia()}"
        )

    # ------------------------------------------------------------------
    # Cache lookup
    # ------------------------------------------------------------------
    conteudo_hash = gerar_hash_texto(texto_limpo)
    cache = buscar_cache(conteudo_hash)

    if cache:
        resultado_cache = cache.get("result", "")
        if resultado_cache:
            return (
                f"{resultado_cache}\n\n"
                "ℹ️ Resultado em cache."
            )

    # ------------------------------------------------------------------
    # URL reputation check (Google Safe Browsing)
    # ------------------------------------------------------------------
    urls = extrair_urls_validas(texto_limpo)

    if urls:
        urls_maliciosas = []

        for url in urls:
            reputacao = consultar_google_safe_browsing(url)

            if reputacao in [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ]:
                urls_maliciosas.append((url, reputacao))

        if urls_maliciosas:
            return (
                f"🔴 {len(urls_maliciosas)} link(s) malicioso(s) detectado(s)\n\n"
                "🧠 Domínio listado como ameaça ativa.\n\n"
                "🚫 Não acesse esse(s) link(s)."
            )

    # ------------------------------------------------------------------
    # Core Hybrid Analysis
    # ------------------------------------------------------------------
    resultado = analisar_mensagem_guardinia_v5_1(texto_limpo)

    # ------------------------------------------------------------------
    # Protective Light Layer (Portfolio Safe Mode)
    # ------------------------------------------------------------------
    t = texto_limpo.lower()

    entidade_sensivel = any(x in t for x in [
        "banco", "nubank", "itau", "itaú",
        "bradesco", "santander"
    ])

    pedido_confirmacao = any(x in t for x in [
        "confirmar", "atualizar", "dados",
        "cpf", "senha"
    ])

    canal_informal = any(x in t for x in [
        "whatsapp", "wpp", "zap"
    ])

    if entidade_sensivel and pedido_confirmacao and canal_informal:
        return (
            "🟡 ALERTA PREVENTIVO\n\n"
            "⚠️ Bancos normalmente NÃO solicitam confirmação "
            "de dados por WhatsApp.\n\n"
            "Confirme sempre diretamente pelo aplicativo oficial "
            "ou pelo número atrás do cartão.\n\n"
            "Nunca compartilhe senhas, códigos ou dados pessoais."
        )

    # ------------------------------------------------------------------
    # Response Formatting
    # ------------------------------------------------------------------
    resposta_formatada = (
        f"{resultado.status}\n\n"
        f"🎯 Confiança: {resultado.confianca}%\n"
    )

    if resultado.indicadores_tecnicos.get("fusao_aplicada"):
        resposta_formatada += "\n🤖 Análise cognitiva aplicada\n"

    if resultado.motivos:
        resposta_formatada += (
            "\n📌 Motivos:\n" +
            "\n".join(
                f"• {m}"
                for m in resultado.motivos[:5]
            )
        )

    resposta_formatada += (
        f"\n\n👉 {resultado.acao_recomendada}"
    )

    # ------------------------------------------------------------------
    # Async cache persistence (non-blocking)
    # ------------------------------------------------------------------
    threading.Thread(
        target=salvar_cache,
        args=(
            conteudo_hash,
            resultado,
            resposta_formatada,
            None
        ),
        daemon=True
    ).start()

    return resposta_formatada

# ======================================================================
# Rate Limiting Layer
# ======================================================================

def verificar_rate_limit(
    telefone: str,
    limite: int = 10
) -> bool:
    """
    Sliding window rate limiting per phone number.

    Rules:
    - Window: 60 seconds
    - Default limit: 10 messages per minute
    - Uses DynamoDB with TTL auto-expiration
    - Fail-open strategy (does not block on internal errors)

    Returns:
        True  -> Allowed
        False -> Rate limit exceeded
    """

    try:
        agora = int(time.time())
        janela_inicio = agora - 60

        pk = f"RATE#{telefone}"

        response = audit_table.query(
            KeyConditionExpression=Key("pk").eq(pk),
            ScanIndexForward=False
        )

        itens = response.get("Items", [])

        recentes = [
            i for i in itens
            if int(i.get("timestamp_epoch", 0)) >= janela_inicio
        ]

        if len(recentes) >= limite:
            logger.warning(
                f"rate_limit_exceeded | telefone={telefone}"
            )
            return False

        audit_table.put_item(
            Item={
                "pk": pk,
                "sk": str(agora),
                "timestamp_epoch": agora,
                "ttl": agora + 120  # Auto-expire
            }
        )

        return True

    except Exception as e:
        logger.error(f"rate_limit_error | error={e}")
        return True  # Fail-open (availability > strict blocking)

# ======================================================================
# Web System Endpoint (GuardinIA v5.1)
# ======================================================================

def processar_sistema_web(body: dict) -> dict:
    """
    HTTP interface for the GuardinIA analysis engine.

    Expected input:
        {
            "mensagem": "<texto a ser analisado>"
        }

    Returns:
        JSON response with structured risk analysis.
    """

    logger.info("web_system_invocation | version=5.1")

    mensagem = body.get("mensagem", "")

    if not mensagem:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"erro": "Forneça 'mensagem'"},
                ensure_ascii=False
            )
        }

    try:
        # --------------------------------------------------------------
        # Input normalization and size protection
        # --------------------------------------------------------------
        texto_limpo = normalizar_texto(mensagem)

        if len(texto_limpo) > 5000:
            texto_limpo = texto_limpo[:5000]

        # --------------------------------------------------------------
        # Core analysis
        # --------------------------------------------------------------
        resultado = analisar_mensagem_guardinia_v5_1(
            texto_limpo
        )

        resposta = {
            "status": resultado.status,
            "cor": resultado.cor,
            "confianca": resultado.confianca,
            "motivos": resultado.motivos[:10],
            "acao_recomendada": resultado.acao_recomendada,
            "score": resultado.score_total,
            "indicadores": resultado.indicadores_tecnicos,
            "versao": "5.1_production_ready"
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(
                resposta,
                ensure_ascii=False
            )
        }

    except Exception as e:
        logger.error(
            f"web_system_error | error={str(e)}"
        )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {"erro": "Erro interno"},
                ensure_ascii=False
            )
        }

# ======================================================================
# System Integrity Verification
# ======================================================================

def verificar_integridade_sistema():
    """
    Performs startup integrity checks for GuardinIA.

    Validates:
    - Heuristic registration
    - Bedrock configuration state
    - Core cognitive parameters
    """

    erros = []

    # --------------------------------------------------------------
    # Heuristic validation
    # --------------------------------------------------------------
    if not HEURISTICAS_REGISTRADAS:
        erros.append("Nenhuma heurística registrada")

    # --------------------------------------------------------------
    # Bedrock status validation
    # --------------------------------------------------------------
    if BEDROCK_ENABLED:
        try:
            logger.info("bedrock_status | enabled=true")
        except Exception as e:
            erros.append(f"Erro na configuração Bedrock: {e}")
    else:
        logger.warning(
            "bedrock_status | enabled=false | running_in_heuristic_only_mode"
        )

    # --------------------------------------------------------------
    # Result reporting
    # --------------------------------------------------------------
    if erros:
        logger.error("=" * 70)
        logger.error("GUARDINIA_V5_1_INTEGRITY_ERROR")
        for e in erros:
            logger.error(f" - {e}")
        logger.error("=" * 70)
    else:
        logger.info("=" * 70)
        logger.info("GUARDINIA_V5_1_INITIALIZED_SUCCESSFULLY")
        logger.info(f"heuristics_count={len(HEURISTICAS_REGISTRADAS)}")
        logger.info(f"bedrock_enabled={BEDROCK_ENABLED}")
        logger.info(f"zona_cognitiva={ZONA_COGNITIVA_MIN}-{ZONA_COGNITIVA_MAX}")
        logger.info("double_pass_enabled=true")
        logger.info("anti_hallucination_enabled=true")
        logger.info("cognitive_divergence_detection_enabled=true")
        logger.info("=" * 70)


verificar_integridade_sistema()

# ======================================================================
# AWS Lambda Handler (GuardinIA v5.1)
# ======================================================================

def lambda_handler(event, context):
    """
    Entry point for GuardinIA serverless execution.

    Supports:
    - Web system (JSON API)
    - WhatsApp webhook (Meta)
    - Webhook verification (GET challenge)
    """

    try:
        logger.info("=" * 70)
        logger.info("GUARDINIA_V5_1_INVOCATION")
        logger.info("=" * 70)

        method = event.get("httpMethod")

        # --------------------------------------------------------------
        # CORS Preflight
        # --------------------------------------------------------------
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
                },
                "body": ""
            }

        body_str = event.get("body", "{}")

        try:
            if event.get("isBase64Encoded", False):
                body_bytes = base64.b64decode(body_str)
                body = json.loads(body_bytes)
            else:
                body_bytes = body_str.encode("utf-8")
                body = json.loads(body_str)
        except Exception:
            body = {}
            body_bytes = b""

        eh_sistema_web = "mensagem" in body

        # ==============================================================
        # Web System Route
        # ==============================================================
        if eh_sistema_web and method == "POST":
            logger.info("route=web_system")
            return processar_sistema_web(body)

        # ==============================================================
        # WhatsApp Webhook
        # ==============================================================
        if method == "POST" and not eh_sistema_web:
            logger.info("route=whatsapp_webhook")

            headers = {
                k.lower(): v
                for k, v in (event.get("headers") or {}).items()
            }

            # Signature validation
            if not validar_assinatura(headers, body_bytes):
                logger.warning("whatsapp_signature_invalid")
                return {
                    "statusCode": 403,
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps(
                        {"erro": "Assinatura inválida"},
                        ensure_ascii=False
                    )
                }

            body = json.loads(body_bytes)

            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    if "statuses" in value:
                        continue

                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [])

                    if not messages or not contacts:
                        continue

                    telefone = contacts[0].get("wa_id")
                    if not telefone:
                        continue

                    # Rate limiting
                    if not verificar_rate_limit(telefone):
                        enviar_mensagem_whatsapp(
                            telefone,
                            "⚠️ Muitas solicitações. Aguarde um momento."
                        )
                        continue

                    for msg in messages:

                        # --------------------------------------------------
                        # IMAGE MESSAGE
                        # --------------------------------------------------
                        if msg.get("type") == "image":
                            logger.info(
                                f"whatsapp_image_received | from={mascarar_telefone(telefone)}"
                            )

                            try:
                                image_id = msg.get("image", {}).get("id")
                                if not image_id:
                                    enviar_mensagem_whatsapp(
                                        telefone,
                                        "❌ Erro ao processar imagem."
                                    )
                                    continue

                                media_url = f"https://graph.facebook.com/v18.0/{image_id}"
                                headers_download = {
                                    "Authorization": f"Bearer {META_TOKEN}"
                                }

                                req = urllib.request.Request(
                                    media_url,
                                    headers=headers_download
                                )

                                with urllib.request.urlopen(req, timeout=10) as response:
                                    media_info = json.loads(
                                        response.read().decode("utf-8")
                                    )

                                image_url = media_info.get("url")
                                if not image_url:
                                    enviar_mensagem_whatsapp(
                                        telefone,
                                        "❌ Erro ao obter imagem."
                                    )
                                    continue

                                req_img = urllib.request.Request(
                                    image_url,
                                    headers=headers_download
                                )

                                with urllib.request.urlopen(req_img, timeout=10) as response_img:
                                    imagem_bytes = response_img.read()

                                enviar_mensagem_whatsapp(
                                    telefone,
                                    "🔍 Analisando imagem..."
                                )

                                response_textract = textract.detect_document_text(
                                    Document={"Bytes": imagem_bytes}
                                )

                                texto_extraido = ""
                                for block in response_textract.get("Blocks", []):
                                    if block["BlockType"] == "LINE":
                                        texto_extraido += block["Text"] + " "

                                texto_extraido = texto_extraido.strip()

                                if not texto_extraido or len(texto_extraido) < 5:
                                    enviar_mensagem_whatsapp(
                                        telefone,
                                        "❌ Não consegui extrair texto da imagem."
                                    )
                                    continue

                                resultado = analisar_mensagem_guardinia_v5_1(texto_extraido)

                                resposta_formatada = (
                                    f"{resultado.status}\n\n"
                                    f"🎯 Confiança: {resultado.confianca}%\n"
                                )

                                if resultado.indicadores_tecnicos.get("fusao_aplicada"):
                                    resposta_formatada += "\n🤖 Análise cognitiva aplicada\n"

                                resposta_formatada += (
                                    "\n📌 Motivos:\n" +
                                    "\n".join(
                                        f"• {m}"
                                        for m in resultado.motivos[:5]
                                    ) +
                                    f"\n\n👉 {resultado.acao_recomendada}"
                                )

                                enviar_mensagem_whatsapp(
                                    telefone,
                                    resposta_formatada
                                )

                            except Exception as e:
                                logger.error(
                                    f"whatsapp_image_error | error={str(e)}"
                                )
                                logger.error(traceback.format_exc())

                                enviar_mensagem_whatsapp(
                                    telefone,
                                    "❌ Erro ao processar imagem."
                                )

                        # --------------------------------------------------
                        # TEXT MESSAGE
                        # --------------------------------------------------
                        elif msg.get("type") == "text":
                            texto_original = (
                                msg.get("text", {})
                                .get("body", "")
                                .strip()
                            )

                            if texto_original:
                                resposta = processar_mensagem(texto_original)
                                enviar_mensagem_whatsapp(
                                    telefone,
                                    resposta
                                )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": "OK"
            }

        # ==============================================================
        # Webhook Verification (Meta Challenge)
        # ==============================================================
        if method == "GET":
            params = event.get("queryStringParameters") or {}

            mode = params.get("hub.mode")
            token = params.get("hub.verify_token")
            challenge = params.get("hub.challenge")

            if mode == "subscribe" and token == VERIFY_TOKEN:
                logger.info("webhook_verification_success")
                return {
                    "statusCode": 200,
                    "body": challenge
                }

            return {
                "statusCode": 403,
                "body": "Forbidden"
            }

        return {
            "statusCode": 405,
            "body": "Method Not Allowed"
        }

    except Exception as e:
        logger.error("lambda_fatal_error")
        logger.error(str(e))
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(
                {"erro": "Erro interno"},
                ensure_ascii=False
            )
        }

# ======================================================================
# GuardinIA – Production Ready
# ======================================================================

logger.info("=" * 70)
logger.info("GUARDINIA_PRODUCTION_READY_INITIALIZED")
logger.info("=" * 70)

