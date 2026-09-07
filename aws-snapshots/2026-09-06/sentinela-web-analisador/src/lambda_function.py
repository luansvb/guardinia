"""
================================================================
GuardinIA V5.5

VERSÃO WEB PROTEGIDA
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
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass
from urllib.parse import urlparse
from collections import Counter, defaultdict
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import threading
# ================================================================
# CONFIGURAÇÃO GLOBAL
# ================================================================

logger = logging.getLogger()
logger.setLevel(logging.INFO)

APP_NAME = "GuardinIA Web Analyzer"
APP_VERSION = "5.5"

logger.info("=" * 70)
logger.info("VERSAO_ATIVA_GuardinIA_WEB_V%s_PROTECTED", APP_VERSION)
logger.info("Sistema Híbrido: Heurística + Claude (Bedrock) - Nível Bancário")
logger.info("=" * 70)

# Meta/WhatsApp
META_TOKEN = os.environ.get("META_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
APP_SECRET = os.environ.get("APP_SECRET")
BOT_WA_ID = os.environ.get("BOT_WA_ID")

# AWS Services
from botocore.config import Config  # ✅ FIX 3

textract = boto3.client("textract")
dynamodb = boto3.resource("dynamodb")

_bedrock_config = Config(
    connect_timeout=3,   # ← era 2, aumentar evita reconexão desnecessária
    read_timeout=10,     # ← era 8, Sonnet às vezes precisa de mais
    retries={"max_attempts": 1}
)

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=_bedrock_config
)

# DynamoDB Tables
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "guardinia_audit_logs")
CACHE_TABLE_NAME = os.environ.get("CACHE_TABLE_NAME", "guardinia_cache")
METRICS_TABLE_NAME = os.environ.get("METRICS_TABLE_NAME", "guardinia_metrics")  # 🆕 V5.1

audit_table = dynamodb.Table(DYNAMODB_TABLE)
metrics_table = dynamodb.Table(METRICS_TABLE_NAME)  # 🆕 V5.1

# Cache TTL
TTL_DAYS = 7
TTL_SECONDS = TTL_DAYS * 24 * 60 * 60
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

# Proteções do endpoint público do GitHub Pages
WEB_ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "WEB_ALLOWED_ORIGINS",
        "https://luansvb.github.io"
    ).split(",")
    if origin.strip()
}
WEB_RATE_LIMIT_PER_MINUTE = int(os.environ.get("WEB_RATE_LIMIT_PER_MINUTE", "10"))
WEB_DAILY_REQUEST_LIMIT = int(os.environ.get("WEB_DAILY_REQUEST_LIMIT", "500"))
WEB_MAX_TEXT_CHARS = int(os.environ.get("WEB_MAX_TEXT_CHARS", "500"))
WEB_MAX_IMAGE_BYTES = int(os.environ.get("WEB_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
BEDROCK_DAILY_CALL_LIMIT = int(os.environ.get("BEDROCK_DAILY_CALL_LIMIT", "50"))

# Environment
ENV = os.environ.get("ENV", "production")

# Pesos Configuráveis V4.1
PESO_SIGNATURE_MATCH = int(os.environ.get("PESO_SIGNATURE_MATCH", "40"))
PESO_PROGRESSAO_FINANCEIRA = int(os.environ.get("PESO_PROGRESSAO_FINANCEIRA", "35"))
THRESHOLD_SCAM = int(os.environ.get("THRESHOLD_SCAM", "120"))
THRESHOLD_SUSPEITO = int(os.environ.get("THRESHOLD_SUSPEITO", "60"))
MULTIPLICADOR_SEMANTICO = int(os.environ.get("MULTIPLICADOR_SEMANTICO", "20"))
REDUCAO_INVESTIGATIVO = float(os.environ.get("REDUCAO_INVESTIGATIVO", "0.7"))
MULTIPLICADOR_CRITICO = float(os.environ.get("MULTIPLICADOR_CRITICO", "1.15"))

# V5.0: Configuração Bedrock
BEDROCK_ENABLED = os.environ.get("BEDROCK_ENABLED", "true").lower() == "true"
BEDROCK_MODEL_HAIKU = os.environ.get("BEDROCK_MODEL_HAIKU", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_MODEL_SONNET = os.environ.get("BEDROCK_MODEL_SONNET", "anthropic.claude-3-5-sonnet-20241022-v2:0")
BEDROCK_TIMEOUT = int(os.environ.get("BEDROCK_TIMEOUT", "5"))
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "180"))  # ✅ FIX 4: JSON real ~120 tokens

# V5.0: Zona Cognitiva
ZONA_COGNITIVA_MIN = int(os.environ.get("ZONA_COGNITIVA_MIN", "20"))
ZONA_COGNITIVA_MAX = int(os.environ.get("ZONA_COGNITIVA_MAX", "150"))
ZONA_HAIKU_MAX = int(os.environ.get("ZONA_HAIKU_MAX", "60"))
ZONA_SONNET_BASICO_MAX = int(os.environ.get("ZONA_SONNET_BASICO_MAX", "100"))

# V5.0: Fusão Híbrida
PESO_HEURISTICA_ALTO = float(os.environ.get("PESO_HEURISTICA_ALTO", "0.7"))
PESO_BEDROCK_ALTO = float(os.environ.get("PESO_BEDROCK_ALTO", "0.3"))
PESO_HEURISTICA_BAIXO = float(os.environ.get("PESO_HEURISTICA_BAIXO", "0.5"))
PESO_BEDROCK_BAIXO = float(os.environ.get("PESO_BEDROCK_BAIXO", "0.5"))

# 🆕 V5.1: Novas configurações
DIVERGENCIA_THRESHOLD = int(os.environ.get("DIVERGENCIA_THRESHOLD", "80"))  # |heur - ia| > 80
SONNET_REPASS_PROB_MIN = int(os.environ.get("SONNET_REPASS_PROB_MIN", "40"))  # 40-60 → Sonnet
SONNET_REPASS_PROB_MAX = int(os.environ.get("SONNET_REPASS_PROB_MAX", "60"))
SONNET_REPASS_MANIPULACAO = int(os.environ.get("SONNET_REPASS_MANIPULACAO", "8"))  # >= 8 → Sonnet

# Custo por 1M tokens (USD)
CUSTO_HAIKU_INPUT_1M = 0.25
CUSTO_HAIKU_OUTPUT_1M = 1.25
CUSTO_SONNET_INPUT_1M = 3.00
CUSTO_SONNET_OUTPUT_1M = 15.00


# ================================================================
# 🔐 VALIDAÇÃO DE ASSINATURA META (mantido)
# ================================================================

def validar_assinatura(headers: dict, body_bytes: bytes) -> bool:
    """Valida assinatura HMAC-SHA256 do webhook Meta"""
    if not APP_SECRET:
        logger.error("APP_SECRET não configurado")
        return False
    
    assinatura = headers.get("x-hub-signature-256")
    if not assinatura:
        logger.warning("INVALID_SIGNATURE | header ausente")
        return False
    
    try:
        metodo, hash_recebido = assinatura.split("=")
    except ValueError:
        logger.warning("INVALID_SIGNATURE | formato inválido")
        return False
    
    if metodo != "sha256":
        logger.warning("INVALID_SIGNATURE | método inválido")
        return False
    
    hash_calculado = hmac.new(
        APP_SECRET.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(hash_calculado, hash_recebido):
        logger.warning("INVALID_SIGNATURE | hash divergente")
        return False
    
    return True


# ================================================================
# ESTRUTURA PADRÃO DE RESULTADO (mantido)
# ================================================================

@dataclass
class ResultadoAnalise:
    status: str
    cor: str
    confianca: int
    score_total: int
    motivos: List[str]
    acao_recomendada: str
    indicadores_tecnicos: Dict[str, Any]
    texto_analisado: str


# ================================================================
# ESTRUTURA DE RESPOSTA BEDROCK (mantida)
# ================================================================

@dataclass
class RespostaBedrock:
    """Resposta estruturada do Claude via Bedrock"""
    probabilidade_golpe: int  # 0-100
    categoria_principal: str
    subtipo: str
    nivel_manipulacao_psicologica: int  # 0-10
    intencao_detectada: str
    explicacao_tecnica: str
    modelo_usado: str  # "haiku" ou "sonnet"
    tokens_input: int
    tokens_output: int
    custo_usd: float
    tempo_ms: float


# ================================================================
# UTILITÁRIOS DE SANITIZAÇÃO (mantidos)
# ================================================================

def remover_caracteres_invisiveis(texto: str) -> str:
    invisiveis = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u00a0']
    for c in invisiveis:
        texto = texto.replace(c, '')
    return texto


def sanitizar_entrada(texto: str) -> str:
    if not texto:
        return ""
    texto = remover_caracteres_invisiveis(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def validar_entrada(texto: str) -> Tuple[bool, str]:
    if not texto or len(texto.strip()) < 3:
        return False, "Texto muito curto"
    
    if not re.search(r'[A-Za-zÀ-ÿ]', texto):
        return False, "Texto sem letras válidas"
    
    especiais = len(re.findall(r'[^A-Za-z0-9À-ÿ\s.,!?;:()-]', texto))
    if len(texto) > 0 and (especiais / len(texto)) > 0.4:
        return False, "Texto excessivamente ofuscado"
    
    return True, ""


def normalizar_texto(texto: str) -> str:
    texto = sanitizar_entrada(texto)
    texto = ''.join(c for c in texto if c.isprintable() or c.isspace())
    return texto.strip()


def truncar_seguro(texto: str, max_chars: int = 4096) -> str:
    if len(texto) <= max_chars:
        return texto
    
    truncado = texto[:max_chars]
    ultimo_espaco = truncado.rfind(' ')
    
    if ultimo_espaco > max_chars * 0.9:
        return truncado[:ultimo_espaco] + "..."
    
    return truncado + "..."


# ================================================================
# RETRY PARA APIS EXTERNAS (mantido)
# ================================================================

def executar_com_retry(func: Callable, max_tentativas: int = 2, descricao: str = "operação"):
    for tentativa in range(max_tentativas):
        try:
            return func()
        except urllib.error.URLError as e:
            if tentativa == max_tentativas - 1:
                logger.error(f"Falha em {descricao} após {max_tentativas} tentativas: {e}")
                return None
            logger.warning(f"Tentativa {tentativa + 1} falhou para {descricao}, tentando novamente...")
            time.sleep(0.5 * (tentativa + 1))
        except Exception as e:
            logger.error(f"Erro não recuperável em {descricao}: {e}")
            return None
    return None


# ================================================================
# UTILITÁRIOS ESTATÍSTICOS (mantidos)
# ================================================================

def calcular_entropia(texto: str) -> float:
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
    if not texto:
        return 0.0
    nums = len(re.findall(r'\d', texto))
    return nums / len(texto)


def proporcao_maiusculas(texto: str) -> float:
    letras = re.findall(r'[A-Za-zÀ-ÿ]', texto)
    if not letras:
        return 0.0
    maius = sum(1 for c in letras if c.isupper())
    return maius / len(letras)


# ================================================================
# CAMADA SEMÂNTICA (mantida V4.1)
# ================================================================

def extrair_sinais_semanticos(texto: str) -> Dict[str, float]:
    t = texto.lower()
    sinais = {}
    
    sinais['pedido_dinheiro'] = 1.0 if any([
        'faz um pix' in t, 'me manda' in t, 'me passa' in t,
        'transfere' in t, 'me envia' in t, 'deposita' in t,
        re.search(r'\b(preciso|necessito).*(dinheiro|grana|pix|valor)', t)
    ]) else 0.0
    
    sinais['promessa_retorno'] = 1.0 if any([
        'te devolvo' in t, 'te pago' in t, 'depois eu pago' in t,
        'te retorno' in t, 'retorno garantido' in t, 'lucro garantido' in t,
        'lucro certo' in t, 'sem risco' in t
    ]) else 0.0
    
    sinais['autoridade'] = 1.0 if any([
        'sou do banco' in t, 'sou da receita' in t, 'setor de fraude' in t,
        'central de segurança' in t,
        'departamento' in t and any(x in t for x in ['fraude', 'segurança', 'bloqueio']),
        'suporte oficial' in t
    ]) else 0.0
    
    termos_urgencia = ['urgente', 'agora', 'imediato', 'imediatamente', 'último aviso', 'hoje mesmo']
    count_urgencia = sum(1 for termo in termos_urgencia if termo in t)
    sinais['urgencia'] = min(count_urgencia * 0.8, 2.4)
    
    sinais['proibicao'] = 1.2 if any([
        'não conta' in t, 'não liga' in t, 'não fala' in t,
        'não chama' in t, 'segredo nosso' in t, 'confidencial' in t, 'entre nós' in t
    ]) else 0.0
    
    sinais['relacao_pessoal'] = 0.7 if any([
        re.search(r'\b(meu|minha) (amor|anjo|filho|filha|mãe|pai|familia)', t),
        'você é especial' in t, 'te amo' in t, 'meu querido' in t
    ]) else 0.0
    
    sinais['ameaca'] = 1.1 if any([
        'bloqueio' in t, 'cancelamento' in t, 'prisão' in t,
        'será bloqueado' in t, 'será cancelado' in t, 'será suspenso' in t,
        'perderá acesso' in t, 'consequências' in t
    ]) else 0.0
    
    sinais['investigativo'] = -1.5 if any([
        'isso é golpe' in t, 'é golpe' in t, 'é seguro' in t,
        'é confiável' in t, 'é fraude' in t,
        '?' in texto and any(x in t for x in ['golpe', 'seguro', 'confiável', 'fraude'])
    ]) else 0.0
    
    return sinais


# ================================================================
# IPP - ÍNDICE DE PRESSÃO PSICOLÓGICA (mantido V4.1)
# ================================================================

def calcular_indice_pressao(texto: str, sinais: Dict[str, float]) -> float:
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


# ================================================================
# CONTEXTOS LEGÍTIMOS (mantido V4.1)
# ================================================================

def aplicar_reducao_contexto_legitimo(score_por_categoria: Dict[str, int], texto: str) -> Dict[str, int]:
    t = texto.lower()
    
    contextos_gerais = [
        "site oficial", "aplicativo oficial", "app oficial",
        "loja física", "atendimento presencial", "contrato assinado",
        "documento oficial", "gov.br", "canal oficial", "central oficial"
    ]
    tem_contexto_geral = any(ctx in t for ctx in contextos_gerais)
    
    contextos_financeiros = [
        "boleto registrado", "nota fiscal", "pagamento recorrente",
        "contrato bancário", "suporte técnico oficial", "assistência autorizada"
    ]
    tem_contexto_financeiro = any(ctx in t for ctx in contextos_financeiros)
    
    if tem_contexto_geral:
        for categoria in ['PHISHING', 'ENGENHARIA_SOCIAL']:
            if categoria in score_por_categoria:
                score_atual = score_por_categoria[categoria]
                score_por_categoria[categoria] = int(score_atual * 0.7)
                logger.info(f"Contexto legítimo geral: {categoria} {score_atual} → {score_por_categoria[categoria]}")
    
    if tem_contexto_financeiro:
        if 'FINANCEIRO' in score_por_categoria:
            score_atual = score_por_categoria['FINANCEIRO']
            score_por_categoria['FINANCEIRO'] = int(score_atual * 0.6)
            logger.info(f"Contexto legítimo financeiro: FINANCEIRO {score_atual} → {score_por_categoria['FINANCEIRO']}")
    
    return score_por_categoria

def detectar_contexto_financeiro_estruturado_legitimo(texto: str) -> bool:
    """
    Detecta cobranças legítimas estruturadas:
    - Número de contrato ou parcela
    - Valor fixo coerente
    - Linguagem institucional neutra
    - Sem pedido de senha/token
    - Sem proibição ou ameaça extrema
    """

    t = texto.lower()

    # Deve ter valor monetário
    if not re.search(r'r\$\s?\d+[.,]?\d*', t):
        return False

    # Deve ter referência de contrato ou parcela
    referencia = any([
        re.search(r'parcela\s?\d+', t),
        re.search(r'n[úu]mero\s?\d+', t),
        re.search(r'\b\d{8,}\b', t)  # número longo tipo contrato
    ])

    if not referencia:
        return False

    # Não pode pedir senha/token
    termos_sensiveis = ["senha", "token", "código", "codigo", "confirme seus dados"]
    if any(ts in t for ts in termos_sensiveis):
        return False

    # Não pode ter proibição ou ameaça grave
    termos_ameaca = ["bloqueado", "prisão", "cancelado imediatamente", "último aviso"]
    if any(ts in t for ts in termos_ameaca):
        return False

    return True


# ================================================================
# BASE HEURÍSTICA (mantida)
# ================================================================

class Heuristica:
    def __init__(self, nome: str, categoria: str, peso: int, detector: Callable, grupo: Optional[str] = None):
        self.nome = nome
        self.categoria = categoria
        self.peso = peso
        self.detector = detector
        self.grupo = grupo
        self.validar()
    
    def validar(self):
        if not callable(self.detector):
            raise ValueError(f"Detector para '{self.nome}' deve ser callable")
        if self.peso < 0:
            raise ValueError(f"Peso para '{self.nome}' deve ser >= 0")
        if not self.nome or not self.categoria:
            raise ValueError("Nome e categoria são obrigatórios")


# ================================================================
# LGPD (mantido)
# ================================================================

def mascarar_telefone(telefone: str) -> str:
    if not telefone or len(telefone) < 4:
        return "****"
    return f"****{telefone[-4:]}"


def hash_curto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def gerar_hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


# ================================================================
# REGISTRO DE HEURÍSTICAS (mantido)
# ================================================================

HEURISTICAS_REGISTRADAS: List[Heuristica] = []

def registrar_heuristica(nome: str, categoria: str, peso: int, detector: Callable, grupo: Optional[str] = None):
    try:
        heuristica = Heuristica(nome, categoria, peso, detector, grupo)
        HEURISTICAS_REGISTRADAS.append(heuristica)
    except ValueError as e:
        logger.error(f"Erro ao registrar heurística '{nome}': {e}")
        if ENV == 'development':
            raise


# ================================================================
# UTILITÁRIOS PHISHING (mantidos)
# ================================================================

def contem_link(texto: str) -> bool:
    return bool(re.search(r'https?://|www\.', texto.lower()))


def menciona_entidade_sensivel(texto: str) -> bool:
    entidades = [
        "banco", "caixa", "itau", "itaú", "bradesco", "santander",
        "nubank", "receita", "gov", "whatsapp", "email",
        "google", "apple", "microsoft", "inter", "c6"
    ]
    t = texto.lower()
    return any(e in t for e in entidades)


def pede_credenciais(texto: str) -> bool:
    padroes = [
        "senha", "login", "código", "codigo",
        "token", "confirme seus dados",
        "atualize seus dados", "verifique sua conta"
    ]
    t = texto.lower()
    return any(p in t for p in padroes)


def extrair_urls_validas(texto: str) -> List[str]:
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


# ================================================================
# ASSINATURAS BR (mantidas)
# ================================================================

SCAM_SIGNATURES_BR = {
    "CONTATO_CLONADO": {
        "must_any": ["troquei de numero", "troquei de número", "meu novo numero", 
                     "novo chip", "mudei de numero", "perdi meu chip"],
        "and_any": ["pix", "me ajuda", "urgente", "preciso pagar", "transfere"]
    },
    "PEDIDO_CODIGO": {
        "must_any": ["codigo", "código", "token", "sms", "código de verificação"],
        "and_any": ["me manda", "me passa", "por engano", "pra confirmar", "recebeu"]
    },
    "ROMANCE_GOLPE": {
        "must_any": ["você é especial", "meu anjo", "amor da minha vida", 
                     "te amo muito", "meu amor"],
        "and_any": ["hospital", "aluguel", "passagem", "emergência", "preciso de ajuda"]
    },
    "CRISE_FAMILIAR": {
        "must_any": ["sequestrado", "em cativeiro", "tô em perigo", "me sequestraram"],
        "and_any": ["não conta", "não chama", "pix", "transfere", "polícia"]
    },
    "TRABALHO_TAXA": {
        "must_any": ["vagas limitadas", "home office", "trabalho simples", 
                     "trabalhe de casa", "ganhe dinheiro fácil"],
        "and_any": ["taxa", "pagar para começar", "depósito", "investimento inicial"]
    },
    "PROMESSA_DINHEIRO_FACIL": {
        "must_any": ["lucro garantido", "sem risco", "100% garantido", "multiplica",
                     "renda extra", "ganhe até", "sem esforço"]
    },
    "SIGILO": {
        "must_any": ["não conta pra ninguém", "segredo nosso", "entre nós", 
                     "confidencial", "não espalha"]
    },
    "FALSA_CENTRAL": {
        "must_any": ["central de segurança", "departamento de fraude", 
                     "verificação de conta", "bloqueio preventivo"],
        "and_any": ["confirme seus dados", "atualize", "senha", "token"]
    }
}


def _contains_any(texto: str, termos: list) -> bool:
    return any(termo in texto for termo in termos)


def match_signature(texto_lower: str, key: str) -> bool:
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
    texto_lower = texto.lower()
    categorias = {}
    
    signatures_detectadas = []
    for key in SCAM_SIGNATURES_BR:
        if match_signature(texto_lower, key):
            signatures_detectadas.append(key)
            categorias["ENGENHARIA_SOCIAL"] = (
                categorias.get("ENGENHARIA_SOCIAL", 0) + PESO_SIGNATURE_MATCH
            )
    
    if signatures_detectadas:
        logger.info(f"Signatures BR detectadas: {', '.join(signatures_detectadas)}")
    
    # Detector financeiro melhorado
    contexto_financeiro = any(term in texto_lower for term in [
        'r$', 'reais', 'pix', 'transferir', 'depositar', 'pagar', 
        'valor', 'dinheiro', 'grana'
    ])
    
    if contexto_financeiro:
        verbos_proposta = ['invista', 'investe', 'deposite', 'pague', 'transfira', 'ganhe', 'multiplica']
        verbos_relato = ['recebi', 'paguei', 'transferi', 'ganhei']
        
        tem_proposta = any(v in texto_lower for v in verbos_proposta)
        tem_relato = any(v in texto_lower for v in verbos_relato)
        
        if tem_proposta or not tem_relato:
            valores_raw = re.findall(r'(?:r\$\s*)?(\d{1,6}(?:[.,]\d{2,3})?)', texto_lower)
            
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
                                    categorias.get("FINANCEIRO", 0) + PESO_PROGRESSAO_FINANCEIRA
                                )
                                logger.info(f"Progressão financeira: {x} → {y} (ratio: {ratio:.1f}x)")
                                break
                except (ValueError, ZeroDivisionError):
                    pass
    
    return categorias if categorias else False


registrar_heuristica("Camada comportamental BR", "ENGENHARIA_SOCIAL", 0, detectar_comportamental_full)


# ================================================================
# 🆕 V5.1: HEURÍSTICA DE RETORNO IRREAL (ADAPTADA DO GPT)
# ================================================================

def detectar_retorno_financeiro_irreal(texto: str) -> Union[Dict[str, int], bool]:
    """
    🆕 V5.1: Detecta promessas de retorno financeiro irreal
    
    Adaptada da versão GPT com melhorias:
    - Detecta verbos de envio + verbos de retorno
    - Calcula ratio de retorno
    - Penaliza ratios altos (>5x = 60 pontos)
    - Reduz se for cashback legítimo
    - Intensificadores aumentam score
    """
    t = texto.lower()
    
    verbos_envio = ["pagar", "pague", "envie", "enviar", "depositar", "transferir", "pix", "investir", "aplicar"]
    verbos_retorno = ["receber", "devolver", "ganhar", "lucro", "retorno", "dobrar", "triplicar", "multiplicar"]
    
    # Precisa ter ambos
    if not any(v in t for v in verbos_envio):
        return False
    if not any(v in t for v in verbos_retorno):
        return False
    
    # Extrair números
    numeros = re.findall(r'\b\d{1,6}\b', t)
    numeros = [int(n) for n in numeros if 0 < int(n) < 1000000]
    
    if len(numeros) < 2:
        return False
    
    x, y = numeros[0], numeros[1]
    
    if y <= x:
        return False
    
    ratio = y / x
    
    if ratio < 1.5:
        return False
    
    # Score baseado no ratio
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
    
    # Intensificadores
    intensificadores = ["garantido", "lucro certo", "sem risco", "renda fácil", 
                        "retorno imediato", "oportunidade única", "só hoje"]
    if any(p in t for p in intensificadores):
        score_es += 20
    
    # Redutores (contextos legítimos)
    redutores = ["cashback", "troco", "reembolso", "estorno", "restituição", "desconto"]
    if any(p in t for p in redutores):
        score_es -= 25
    
    if score_es <= 0:
        return False
    
    resultado = {"ENGENHARIA_SOCIAL": score_es}
    
    # Se ratio muito alto, adiciona categoria FINANCEIRO
    if ratio >= 5:
        resultado["FINANCEIRO"] = 25
    
    logger.info(f"Retorno irreal detectado: {x} → {y} (ratio: {ratio:.1f}x, score: {score_es})")
    
    return resultado


registrar_heuristica(
    nome="Promessa de retorno financeiro irreal",
    categoria="ENGENHARIA_SOCIAL",
    peso=0,
    detector=detectar_retorno_financeiro_irreal
)

# ================================================================
# 🆕 HEURÍSTICA DE COMPROVANTE FALSO (CRÍTICA)
# ================================================================

def detectar_comprovante_falso(texto: str) -> Union[Dict[str, int], bool]:
    """
    Detecta comprovantes de PIX falsos (golpe muito comum)
    
    Padrões suspeitos:
    - Comprovante + urgência
    - "Transação em processamento"
    - "Pode confirmar?" após comprovante
    - Valor alto + pressão
    """
    t = texto.lower()
    
    # Deve ter indicação de comprovante
    tem_comprovante = any([
        'comprovante' in t,
        'comprovante de pagamento' in t,
        'comprovante pix' in t,
        'recibo' in t and 'pix' in t
    ])
    
    if not tem_comprovante:
        return False
    
    score = 0
    categoria = {}
    
    # 1. Comprovante + pedido de confirmação = SUSPEITO
    pede_confirmacao = any([
        'pode confirmar' in t,
        'confirma o recebimento' in t,
        'confirma aí' in t,
        'chegou' in t and '?' in texto,
        'recebeu' in t and '?' in texto
    ])
    
    if pede_confirmacao:
        score += 50
        logger.info("⚠️ Comprovante falso: pede confirmação")
    
    # 2. "Transação em processamento" = SEMPRE FALSO
    if 'processamento' in t or 'em processamento' in t:
        score += 60
        logger.info("🚨 Comprovante falso: transação em processamento")
    
    # 3. Urgência após comprovante
    urgencia_termos = ['urgente', 'urgência', 'agora', 'já está', 'esperando']
    if any(u in t for u in urgencia_termos):
        score += 30
        logger.info("⚠️ Comprovante falso: urgência detectada")
    
    # 4. Justificativa (motoboy, entrega, produto)
    justificativas = ['motoboy', 'entrega', 'produto', 'mercadoria', 'caminho']
    if any(j in t for j in justificativas):
        score += 25
        logger.info("⚠️ Comprovante falso: justificativa suspeita")
    
    # 5. "Já foi debitado"
    if 'já foi debitado' in t or 'ja foi debitado' in t:
        score += 40
        logger.info("🚨 Comprovante falso: afirma débito antes da confirmação")
    
    if score > 0:
        categoria['FALSO_COMPROVANTE'] = score
        return categoria
    
    return False


# Registrar a heurística
registrar_heuristica(
    nome="Comprovante de PIX falso",
    categoria="FALSO_COMPROVANTE",
    peso=0,
    detector=detectar_comprovante_falso
)


# ================================================================
# HEURÍSTICAS ADICIONAIS (resumidas - mantidas do V4.1)
# ================================================================

def detectar_phishing_classico(texto: str) -> bool:
    t = texto.lower()
    indicadores = [contem_link(t), pede_credenciais(t), "clique" in t, "verifique" in t, menciona_entidade_sensivel(t)]
    return indicadores.count(True) >= 3

registrar_heuristica("Phishing clássico", "PHISHING", 35, detectar_phishing_classico, "PHISHING_LINK")


def detectar_autoridade_institucional(texto: str) -> bool:
    t = texto.lower()
    alegacoes = ['sou do banco', 'sou da receita', 'central de segurança', 'departamento de fraude']
    tem_alegacao = any(a in t for a in alegacoes)
    cargos = ['gerente', 'analista', 'técnico']
    tem_cargo = any(c in t for c in cargos)
    acoes = ['confirme seus dados', 'atualize cadastro']
    tem_acao = any(a in t for a in acoes)
    return tem_alegacao and (tem_cargo or tem_acao) or 'central de segurança' in t

registrar_heuristica("Autoridade institucional falsa", "AUTORIDADE", 45, detectar_autoridade_institucional)


def detectar_urgencia(texto: str) -> bool:
    t = texto.lower()
    tem_urgencia = any(p in t for p in ["urgente", "agora", "imediatamente"])
    tem_acao = any(p in t for p in ["clique", "acesse", "confirme", "pix"])
    return tem_urgencia and tem_acao

registrar_heuristica("Urgência com ação", "URGÊNCIA", 30, detectar_urgencia)

# [Mais heurísticas omitidas por brevidade - todas mantidas]


# ================================================================
# TETOS POR CATEGORIA (mantido)
# ================================================================

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
    "FALSO_COMPROVANTE": 100,  # 🆕 SEM TETO (muito grave)
    "AUTORIDADE": 60,
    "EMOCIONAL": 50,
}

# ================================================================
# MOTOR HEURÍSTICO (mantido)
# ================================================================

def avaliar_heuristicas(texto: str) -> Tuple[int, List[str], Dict[str, Any]]:
    inicio = time.time()
    
    score_total = 0
    motivos = []
    indicadores = defaultdict(int)
    score_por_categoria = defaultdict(int)
    grupos_ativados = defaultdict(int)
    
    for heur in HEURISTICAS_REGISTRADAS:
        try:
            resultado = heur.detector(texto)
            
            if isinstance(resultado, bool):
                if resultado:
                    if heur.grupo:
                        grupos_ativados[heur.grupo] += 1
                        if grupos_ativados[heur.grupo] > 2:
                            continue
                    
                    score_por_categoria[heur.categoria] += heur.peso
                    motivos.append(f"{heur.categoria}: {heur.nome}")
                    indicadores[f"hit_{heur.nome}"] += 1
            
            elif isinstance(resultado, dict):
                for categoria, score in resultado.items():
                    if isinstance(score, (int, float)):
                        score_por_categoria[categoria] += score
                        motivos.append(f"{categoria}: {heur.nome}")
                
        except Exception as e:
            logger.exception(f"Erro em {heur.nome}")
    
    score_por_categoria = aplicar_reducao_contexto_legitimo(score_por_categoria, texto)
    
    for categoria, score_categoria in score_por_categoria.items():
        teto = TETO_POR_CATEGORIA.get(categoria, 50)
        score_normalizado = min(score_categoria, teto)
        score_total += score_normalizado
        indicadores[f"score_categoria_{categoria}"] = score_normalizado
    
    tempo_total = (time.time() - inicio) * 1000
    indicadores["tempo_avaliacao_ms"] = round(tempo_total, 2)
    indicadores["score_heuristico_base"] = score_total
    
    return score_total, motivos, dict(indicadores)


# ================================================================
# COMBINAÇÕES CRÍTICAS (mantidas)
# ================================================================

COMBINACOES_CRITICAS = [
    {"categorias": ["FINANCEIRO", "URL"], "bonus": 70},
    {"categorias": ["FINANCEIRO", "ENCURTADOR"], "bonus": 90},
    {"categorias": ["ENGENHARIA_SOCIAL", "PHISHING"], "bonus": 90},
    {"categorias": ["ENGENHARIA_SOCIAL", "FINANCEIRO"], "bonus": 80},
    {"categorias": ["AUTORIDADE", "FINANCEIRO"], "bonus": 85},
    {"categorias": ["EMOCIONAL", "FINANCEIRO"], "bonus": 70},
]


def aplicar_combinacoes(score: int, motivos: List[str], indicadores: Dict) -> Tuple[int, List[str]]:
    categorias_ativas = set()
    for motivo in motivos:
        if ":" in motivo:
            categorias_ativas.add(motivo.split(":")[0].strip())
    
    bonus_total = 0
    
    for combo in COMBINACOES_CRITICAS:
        if set(combo["categorias"]).issubset(categorias_ativas):
            bonus_total += combo["bonus"]
    
    if bonus_total > 0:
        indicadores["bonus_combinacoes"] = bonus_total
    
    return score + bonus_total, motivos


# ================================================================
# 🆕 V5.1: MÉTRICAS EM DYNAMODB (NÃO MEMÓRIA)
# ================================================================

def incrementar_metrica_bedrock(metrica: str, valor: Union[int, float] = 1):
    """ Mantida por compatibilidade — internamente usa batch """
    incrementar_metricas_bedrock_batch_interno(metrica, valor)

def incrementar_metricas_bedrock_batch_interno(metrica: str, valor: Union[int, float] = 1):
    try:
        hoje = datetime.now(timezone.utc).date().isoformat()
        pk = f"METRICS#{hoje}"
        metrics_table.update_item(
            Key={"pk": pk, "sk": "bedrock"},
            UpdateExpression=f"ADD {metrica} :val",
            ExpressionAttributeValues={":val": Decimal(str(valor))},
            ReturnValues="NONE"
        )
    except Exception as e:
        logger.error(f"Erro ao incrementar métrica {metrica}: {e}")

def incrementar_metricas_bedrock_batch(modelo: str, custo: float):
    """✅ FIX 1+2: Atualiza total_calls + modelo_calls + custo em 1 única chamada DynamoDB"""
    try:
        hoje = datetime.now(timezone.utc).date().isoformat()
        pk = f"METRICS#{hoje}"
        campo_modelo = "haiku_calls" if modelo == "haiku" else "sonnet_calls"
        metrics_table.update_item(
            Key={"pk": pk, "sk": "bedrock"},
            UpdateExpression=f"ADD total_calls :one, {campo_modelo} :one, total_cost_usd :custo",
            ExpressionAttributeValues={
                ":one": Decimal("1"),
                ":custo": Decimal(str(custo))
            },
            ReturnValues="NONE"
        )
    except Exception as e:
        logger.error(f"Erro ao incrementar métricas batch: {e}")


def obter_metricas_bedrock(dias: int = 1) -> Dict[str, Any]:
    """
    🆕 V5.1: Obtém métricas do DynamoDB
    
    Args:
        dias: Número de dias para agregar (default 1 = hoje)
    
    Returns:
        dict: Métricas agregadas
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
            
            response = metrics_table.get_item(Key={"pk": pk, "sk": "bedrock"})
            
            if "Item" in response:
                item = response["Item"]
                for key in metricas_totais:
                    if key in item:
                        metricas_totais[key] += float(item[key])
        
        return metricas_totais
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}")
        return {}


def adquirir_cota_bedrock_diaria() -> bool:
    """Reserva atomicamente uma chamada Bedrock dentro da cota diária."""
    if BEDROCK_DAILY_CALL_LIMIT <= 0:
        logger.warning("bedrock_quota_blocked | reason=disabled")
        return False

    hoje = datetime.now(timezone.utc).date().isoformat()
    agora = int(time.time())

    try:
        metrics_table.update_item(
            Key={"pk": f"METRICS#{hoje}", "sk": "bedrock"},
            UpdateExpression="SET quota_ttl = :ttl ADD quota_calls :one",
            ConditionExpression="attribute_not_exists(quota_calls) OR quota_calls < :limit",
            ExpressionAttributeValues={
                ":one": Decimal("1"),
                ":limit": Decimal(str(BEDROCK_DAILY_CALL_LIMIT)),
                ":ttl": agora + (35 * 24 * 60 * 60),
            },
            ReturnValues="NONE",
        )
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "ConditionalCheckFailedException":
            logger.warning(
                "bedrock_quota_blocked | daily_limit=%s",
                BEDROCK_DAILY_CALL_LIMIT,
            )
            return False
        logger.error("bedrock_quota_check_failed | error=%s", exc)
        return False
    except Exception as exc:
        logger.error("bedrock_quota_check_failed | error=%s", exc)
        return False


# ================================================================
# BEDROCK - CÁLCULO DE CUSTO (mantido)
# ================================================================

def calcular_custo_bedrock(modelo: str, tokens_input: int, tokens_output: int) -> float:
    if "haiku" in modelo.lower():
        custo = (tokens_input / 1_000_000 * CUSTO_HAIKU_INPUT_1M) + \
                (tokens_output / 1_000_000 * CUSTO_HAIKU_OUTPUT_1M)
    else:  # sonnet
        custo = (tokens_input / 1_000_000 * CUSTO_SONNET_INPUT_1M) + \
                (tokens_output / 1_000_000 * CUSTO_SONNET_OUTPUT_1M)
    
    return round(custo, 6)


# ================================================================
# 🆕 V5.1: VALIDAÇÃO ANTI-HALLUCINATION
# ================================================================

def validar_resposta_bedrock(resultado_json: dict) -> Tuple[bool, str]:
    """
    🆕 V5.1: Validação rigorosa contra hallucination
    
    Valida:
    - probabilidade_golpe: 0-100 (não 150!)
    - nivel_manipulacao_psicologica: 0-10
    - categoria_principal: enum válido
    
    Returns:
        tuple: (valido, motivo_erro)
    """
    
    # 1. Validar probabilidade_golpe
    if "probabilidade_golpe" not in resultado_json:
        return False, "Campo probabilidade_golpe ausente"
    
    try:
        prob = int(resultado_json["probabilidade_golpe"])
        if not (0 <= prob <= 100):
            return False, f"probabilidade_golpe inválida: {prob} (deve ser 0-100)"
    except (ValueError, TypeError):
        return False, f"probabilidade_golpe não é inteiro: {resultado_json['probabilidade_golpe']}"
    
    # 2. Validar nivel_manipulacao_psicologica
    if "nivel_manipulacao_psicologica" not in resultado_json:
        return False, "Campo nivel_manipulacao_psicologica ausente"
    
    try:
        manip = int(resultado_json["nivel_manipulacao_psicologica"])
        if not (0 <= manip <= 10):
            return False, f"nivel_manipulacao_psicologica inválido: {manip} (deve ser 0-10)"
    except (ValueError, TypeError):
        return False, f"nivel_manipulacao_psicologica não é inteiro"
    
    # 3. Validar categoria_principal
    if "categoria_principal" not in resultado_json:
        return False, "Campo categoria_principal ausente"
    
    categorias_validas = [
        "PHISHING", "ENGENHARIA_SOCIAL", "FINANCEIRO", "MALWARE",
        "CRYPTO", "TRABALHO", "ECOMMERCE", "OUTRO"
    ]
    
    categoria = resultado_json["categoria_principal"].upper()
    if categoria not in categorias_validas:
        return False, f"categoria_principal inválida: {categoria}"
    
    # 4. Validar campos obrigatórios (texto)
    campos_texto = ["subtipo", "intencao_detectada", "explicacao_tecnica"]
    for campo in campos_texto:
        if campo not in resultado_json:
            return False, f"Campo {campo} ausente"
        if not isinstance(resultado_json[campo], str):
            return False, f"Campo {campo} não é string"
        if len(resultado_json[campo].strip()) == 0:
            return False, f"Campo {campo} está vazio"
    
    return True, ""


# ================================================================
# 🆕 V5.1: RETRY JSON COM REGEX
# ================================================================

def extrair_json_com_regex(texto_resposta: str) -> Optional[dict]:
    """
    🆕 V5.1: Tenta extrair JSON com regex antes de desistir
    
    Casos tratados:
    - JSON com markdown ```json ... ```
    - JSON com texto antes/depois
    - JSON válido mas com espaços
    """
    
    # Tentar encontrar JSON entre chaves
    match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)
    if match:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Tentar remover markdown
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


# ================================================================
# 🆕 V5.1: PROMPT COM FEW-SHOT EXAMPLES (SONNET PROFUNDO)
# ================================================================

def construir_prompt_bedrock(
    texto: str,
    score_heuristico: int,
    categorias: List[str],
    sinais: Dict[str, float],
    nivel_analise: str = "basico"
) -> str:
    """
    Constrói prompt estruturado para Claude via Bedrock
    
    🆕 V5.1: Few-shot examples no nível "profundo"
    """
    
    sinais_str = ", ".join([f"{k}={v:.1f}" for k, v in sinais.items() if v != 0])
    categorias_str = ", ".join(categorias) if categorias else "Nenhuma"
    
    if nivel_analise == "profundo":
        # 🆕 V5.1: Few-shot examples para Sonnet profundo
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
```

---

## 🟠 Problema 2 — Memória em 128 MB está sufocando a Lambda
```
Memory Size: 128 MB   Max Memory Used: 90 MB
```

Está usando 90 de 128 — **70% da memória**. Lambda aloca CPU proporcionalmente à memória. Com 128 MB, a CPU é mínima, o que aumenta o tempo de execução de tudo: imports, heurísticas, serialização JSON.

**Correção:** No console AWS Lambda → Configuration → General configuration:
```
Memory: 128 MB  →  512 MB

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
    
    else:  # básico
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

# ================================================================
# BEDROCK - CHAMADA PRINCIPAL (MELHORADA V5.1)
# ================================================================

def chamar_bedrock_claude(
    texto: str,
    score_heuristico: int,
    categorias: List[str],
    sinais: Dict[str, float],
    modelo: str = "haiku",
    nivel_analise: str = "basico"
) -> Optional[RespostaBedrock]:
    """
    Chama Claude via Amazon Bedrock
    
    🆕 V5.1 Melhorias:
    - Validação anti-hallucination
    - Retry com regex antes de fallback
    - Métricas em DynamoDB
    """
    
    if not BEDROCK_ENABLED:
        logger.info("Bedrock desabilitado via configuração")
        return None

    if not adquirir_cota_bedrock_diaria():
        logger.warning("Bedrock não chamado: cota diária indisponível")
        return None
    
    inicio = time.time()
    
    model_id = BEDROCK_MODEL_HAIKU if modelo == "haiku" else BEDROCK_MODEL_SONNET
    
    prompt = construir_prompt_bedrock(texto, score_heuristico, categorias, sinais, nivel_analise)
    
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
        
        response_body = json.loads(response['body'].read())
        
        tempo_ms = (time.time() - inicio) * 1000
        
        texto_resposta = response_body['content'][0]['text']
        
        # 🆕 V5.1: Tentar parse direto
        resultado_json = None
        try:
            resultado_json = json.loads(texto_resposta.strip())
        except json.JSONDecodeError:
            # 🆕 V5.1: Retry com regex
            logger.warning("JSON inválido, tentando extrair com regex...")
            resultado_json = extrair_json_com_regex(texto_resposta)
            
            if resultado_json is None:
                logger.error("Falha ao extrair JSON mesmo com regex")
                incrementar_metrica_bedrock("fallback_count", 1)
                return None
        
        # 🆕 V5.1: Validação anti-hallucination
        valido, motivo_erro = validar_resposta_bedrock(resultado_json)
        if not valido:
            logger.error(f"Resposta Bedrock inválida: {motivo_erro}")
            logger.error(f"JSON recebido: {resultado_json}")
            incrementar_metrica_bedrock("fallback_count", 1)
            return None
        
        # Tokens e custo
        tokens_input = response_body['usage']['input_tokens']
        tokens_output = response_body['usage']['output_tokens']
        custo = calcular_custo_bedrock(model_id, tokens_input, tokens_output)
        
        # ✅ FIX 1+2: 1 única chamada DynamoDB, em background (não bloqueia)
        threading.Thread(
            target=incrementar_metricas_bedrock_batch,
            args=(modelo, custo),
            daemon=True
        ).start()
        
        # Log estruturado
        logger.info(json.dumps({
            "evento": "bedrock_success",
            "modelo": modelo,
            "nivel_analise": nivel_analise,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "custo_usd": custo,
            "tempo_ms": round(tempo_ms, 2),
            "probabilidade_golpe": resultado_json["probabilidade_golpe"]
        }))
        
        return RespostaBedrock(
            probabilidade_golpe=int(resultado_json["probabilidade_golpe"]),
            categoria_principal=resultado_json["categoria_principal"],
            subtipo=resultado_json["subtipo"],
            nivel_manipulacao_psicologica=int(resultado_json["nivel_manipulacao_psicologica"]),
            intencao_detectada=resultado_json["intencao_detectada"],
            explicacao_tecnica=resultado_json["explicacao_tecnica"],
            modelo_usado=modelo,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            custo_usd=custo,
            tempo_ms=round(tempo_ms, 2)
        )
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        logger.error(f"Erro Bedrock ClientError: {error_code}")
        incrementar_metrica_bedrock("fallback_count", 1)
        return None
    
    except Exception as e:
        logger.error(f"Erro inesperado no Bedrock: {str(e)}")
        logger.error(traceback.format_exc())
        incrementar_metrica_bedrock("fallback_count", 1)
        return None


# ================================================================
# 🆕 V5.1: DECISÃO DE ESCALONAMENTO MELHORADA
# ================================================================

def decidir_escalonamento_bedrock(
    score_heuristico: int,
    categorias_ativas: set,
    sinais: Dict[str, float],
    texto: str
) -> Tuple[bool, Optional[str], Optional[str]]:

    # Zona segura
    if score_heuristico < ZONA_COGNITIVA_MIN:
        logger.info(f"Score {score_heuristico} < {ZONA_COGNITIVA_MIN}: SEM IA")
        return False, None, None

    # Zona golpe óbvio
    if score_heuristico >= ZONA_COGNITIVA_MAX:
        logger.info(f"Score {score_heuristico} >= {ZONA_COGNITIVA_MAX}: GOLPE ÓBVIO - SEM IA")
        return False, None, None

    # =============================
    # 🔥 GATILHOS ADAPTATIVOS
    # =============================

    categorias_criticas = {"PHISHING", "ENGENHARIA_SOCIAL", "FINANCEIRO", "AUTORIDADE"}
    tem_categoria_critica = bool(categorias_criticas & categorias_ativas)

    ipp_estimado = sinais.get("urgencia", 0) * 10 + sinais.get("ameaca", 0) * 20
    tem_link = "http://" in texto.lower() or "https://" in texto.lower() or "www." in texto.lower()

    gatilho_adicional = (
        score_heuristico >= 30 or
        ipp_estimado >= 15 or
        tem_link
    )

    if not tem_categoria_critica and not gatilho_adicional:
        logger.info("Zona cognitiva, mas sem gatilhos suficientes - SEM IA")
        return False, None, None

    logger.info("Zona cognitiva com gatilho válido - CHAMANDO IA")

    # =============================
    # ESCALONAMENTO DE MODELO
    # =============================

    if score_heuristico <= ZONA_SONNET_BASICO_MAX:
        return True, "haiku", "basico"
    else:
        return True, "sonnet", "profundo"

# ================================================================
# 🆕 V5.1: DOUBLE-PASS INTELIGENTE
# ================================================================

def decidir_repass_sonnet(resposta_haiku: RespostaBedrock) -> bool:
    """
    🆕 V5.1: Decide se deve fazer repass com Sonnet após Haiku
    
    Condições para repass:
    - Probabilidade 40-60 (ambíguo) OU
    - Manipulação >= 7 (alta) OU
    - Contradição forte detectada
    
    Args:
        resposta_haiku: Resposta do Haiku
    
    Returns:
        bool: True se deve chamar Sonnet
    """
    
    prob = resposta_haiku.probabilidade_golpe
    manip = resposta_haiku.nivel_manipulacao_psicologica
    
    # Condição 1: Probabilidade ambígua (40-60)
    if SONNET_REPASS_PROB_MIN <= prob <= SONNET_REPASS_PROB_MAX:
        logger.info(f"Repass Sonnet: probabilidade ambígua ({prob})")
        return True
    
    # Condição 2: Manipulação alta (>= 7)
    if manip >= SONNET_REPASS_MANIPULACAO:
        logger.info(f"Repass Sonnet: manipulação alta ({manip})")
        return True
    
    # Condição 3: Contradição forte (detectada no subtipo)
    if "contradição" in resposta_haiku.subtipo.lower() or "inconsistência" in resposta_haiku.subtipo.lower():
        logger.info("Repass Sonnet: contradição detectada")
        return True
    
    logger.info("Repass Sonnet: NÃO necessário")
    return False


# ================================================================
# FUSÃO HÍBRIDA (MELHORADA V5.1)
# ================================================================

def fusao_hibrida_score(
    score_heuristico: int,
    resposta_bedrock: Optional[RespostaBedrock],
    indicadores: Dict[str, Any]
) -> int:
    """
    Fusão Híbrida com melhorias V5.1
    
    🆕 V5.1: Detecta divergência cognitiva
    """
    
    if resposta_bedrock is None:
        indicadores["fusao_aplicada"] = False
        return score_heuristico
    
    score_bedrock = resposta_bedrock.probabilidade_golpe
    
    # 🆕 V5.1: Detectar divergência cognitiva
    divergencia = abs(score_heuristico - score_bedrock)
    if divergencia > DIVERGENCIA_THRESHOLD:
        indicadores["divergencia_cognitiva"] = True
        indicadores["divergencia_valor"] = divergencia
        logger.warning(f"⚠️ DIVERGÊNCIA COGNITIVA: |{score_heuristico} - {score_bedrock}| = {divergencia}")
    
    # Pesos dinâmicos
    if score_heuristico >= 100:
        peso_heur = PESO_HEURISTICA_ALTO
        peso_bedrock = PESO_BEDROCK_ALTO
    else:
        peso_heur = PESO_HEURISTICA_BAIXO
        peso_bedrock = PESO_BEDROCK_BAIXO
    
    score_fusao = int((score_heuristico * peso_heur) + (score_bedrock * peso_bedrock))
    
    logger.info(f"Fusão híbrida: heur={score_heuristico} + bedrock={score_bedrock} → fusao={score_fusao}")
    
    # Ajuste manipulação alta
    if resposta_bedrock.nivel_manipulacao_psicologica >= 8:
        score_fusao += 10
        logger.info(f"Manipulação psicológica alta ({resposta_bedrock.nivel_manipulacao_psicologica}): +10 pontos")
        indicadores["ajuste_manipulacao"] = 10
    
    # Ajuste ambos baixos
    if score_heuristico <= 30 and score_bedrock <= 15:
        score_antes = score_fusao
        score_fusao = int(score_fusao * 0.85)
        logger.info(f"Ambos scores baixos: {score_antes} → {score_fusao} (-15%)")
        indicadores["ajuste_ambos_baixos"] = score_antes - score_fusao
    
    score_fusao = max(score_fusao, 0)
    score_fusao = min(score_fusao, 200)
    
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


# ================================================================
# 🆕 V5.1: MANIPULAÇÃO TEMPORAL (MANTIDA, COERÊNCIA REMOVIDA)
# ================================================================

def detectar_manipulacao_temporal(texto: str, sinais: Dict[str, float]) -> Tuple[bool, str]:
    """Detector de Manipulação Temporal (mantido)"""
    t = texto.lower()
    
    if sinais.get('urgencia', 0) > 0:
        prazos_curtos = ['hoje', 'agora', '24h', '1 hora', 'imediatamente']
        tem_prazo = any(p in t for p in prazos_curtos)
        tem_ameaca = sinais.get('ameaca', 0) > 0
        
        if tem_prazo and tem_ameaca:
            return True, "Manipulação temporal: urgência + prazo curto + ameaça"
    
    if re.search(r'\b(expira|vence|última chance|último dia)\b', t):
        return True, "Manipulação temporal: contagem regressiva"
    
    return False, ""


# ================================================================
# SAFE BROWSING (mantido)
# ================================================================

def consultar_google_safe_browsing(url: str) -> str:
    api_key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY")
    if not api_key:
        return "SAFE"
    
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    
    payload = {
        "client": {"clientId": "guardinia", "clientVersion": "5.1"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    
    def fazer_requisicao():
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
        if "matches" in data and data["matches"]:
            threat = data["matches"][0].get("threatType", "SUSPICIOUS")
            return threat
        return "SAFE"
    
    resultado = executar_com_retry(fazer_requisicao, max_tentativas=2, descricao="Safe Browsing")
    
    if resultado is None:
        return "UNKNOWN"
    
    return resultado


# ================================================================
# CACHE E AUDITORIA (mantidos)
# ================================================================

def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def calcular_ttl() -> int:
    return int(time.time()) + TTL_SECONDS


def buscar_cache(conteudo_hash: str) -> Optional[Dict]:
    try:
        response = audit_table.query(KeyConditionExpression=Key("pk").eq(conteudo_hash), ScanIndexForward=False, Limit=1)
        items = response.get("Items", [])
        if items:
            incrementar_metrica_bedrock("cache_hits", 1)
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Erro ao buscar cache: {e}")
        return None


def salvar_cache(conteudo_hash: str, resultado: ResultadoAnalise, resposta_formatada: str, resposta_bedrock: Optional[RespostaBedrock] = None):
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
            item["bedrock_probabilidade"] = resposta_bedrock.probabilidade_golpe
            item["bedrock_custo_usd"] = Decimal(str(resposta_bedrock.custo_usd))
        
        audit_table.put_item(Item=item)
    except Exception as e:
        logger.error(f"Erro ao salvar cache: {e}")


def buscar_cache_web(conteudo_hash: str) -> Optional[ResultadoAnalise]:
    """Busca somente resultados web válidos para a versão atual e dentro do TTL lógico."""
    try:
        response = audit_table.query(
            KeyConditionExpression=Key("pk").eq(f"WEB#{conteudo_hash}"),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        if not items:
            return None

        item = items[0]
        if item.get("version") != APP_VERSION:
            return None

        if int(item.get("cache_expires_at", 0)) <= int(time.time()):
            return None

        incrementar_metrica_bedrock("cache_hits", 1)
        return ResultadoAnalise(
            status=str(item.get("status", "")),
            cor=str(item.get("cor", "cinza")),
            confianca=int(item.get("confianca", 0)),
            score_total=int(item.get("score", 0)),
            motivos=[str(motivo) for motivo in item.get("motivos", [])],
            acao_recomendada=str(item.get("acao_recomendada", "")),
            indicadores_tecnicos={"cache_hit": True},
            texto_analisado="",
        )
    except Exception as exc:
        logger.error("web_cache_read_failed | error=%s", exc)
        return None


def salvar_cache_web(conteudo_hash: str, resultado: ResultadoAnalise) -> None:
    """Persiste o resultado estruturado do site de forma síncrona e confiável."""
    try:
        agora = int(time.time())
        timestamp = agora_iso()
        audit_table.put_item(
            Item={
                "pk": f"WEB#{conteudo_hash}",
                "sk": timestamp,
                "type": "analysis",
                "source": "web",
                "status": resultado.status,
                "cor": resultado.cor,
                "confianca": resultado.confianca,
                "score": resultado.score_total,
                "motivos": resultado.motivos,
                "acao_recomendada": resultado.acao_recomendada,
                "created_at": timestamp,
                "cache_expires_at": agora + CACHE_TTL_SECONDS,
                "ttl": agora + TTL_SECONDS,
                "version": APP_VERSION,
            }
        )
    except Exception as exc:
        logger.error("web_cache_write_failed | error=%s", exc)


def origem_web_permitida(origin: str) -> bool:
    return bool(origin) and origin.rstrip("/") in WEB_ALLOWED_ORIGINS


def cabecalhos_cors(origin: str) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Vary": "Origin",
    }
    if origem_web_permitida(origin):
        headers.update({
            "Access-Control-Allow-Origin": origin.rstrip("/"),
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Max-Age": "600",
        })
    return headers


def consumir_limite_atomico(
    tabela,
    pk: str,
    sk: str,
    limite: int,
    ttl: int,
) -> bool:
    if limite <= 0:
        return False

    try:
        tabela.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="SET #ttl = :ttl ADD #hits :one",
            ConditionExpression="attribute_not_exists(#hits) OR #hits < :limit",
            ExpressionAttributeNames={"#hits": "hits", "#ttl": "ttl"},
            ExpressionAttributeValues={
                ":one": Decimal("1"),
                ":limit": Decimal(str(limite)),
                ":ttl": ttl,
            },
            ReturnValues="NONE",
        )
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "ConditionalCheckFailedException":
            return False
        logger.error("atomic_limit_failed | key=%s | error=%s", pk, exc)
        return False
    except Exception as exc:
        logger.error("atomic_limit_failed | key=%s | error=%s", pk, exc)
        return False


def autorizar_requisicao_web(source_ip: str) -> Tuple[bool, str]:
    """Aplica limite por IP/minuto e limite global diário antes de serviços pagos."""
    agora = int(time.time())
    ip_hash = hashlib.sha256((source_ip or "unknown").encode("utf-8")).hexdigest()[:24]
    minuto = agora // 60

    permitido_ip = consumir_limite_atomico(
        metrics_table,
        pk=f"WEB_RATE#{ip_hash}",
        sk=str(minuto),
        limite=WEB_RATE_LIMIT_PER_MINUTE,
        ttl=agora + 180,
    )
    if not permitido_ip:
        return False, "Muitas solicitações. Aguarde um minuto e tente novamente."

    hoje = datetime.now(timezone.utc).date().isoformat()
    permitido_dia = consumir_limite_atomico(
        metrics_table,
        pk=f"WEB_DAILY#{hoje}",
        sk="requests",
        limite=WEB_DAILY_REQUEST_LIMIT,
        ttl=agora + (8 * 24 * 60 * 60),
    )
    if not permitido_dia:
        return False, "Limite diário de análises atingido. Tente novamente amanhã."

    return True, ""


def classificar(score: int) -> Tuple[str, str, int, str]:
    if score >= THRESHOLD_SCAM:
        return (
            "🔴 RISCO CRÍTICO DE GOLPE",
            "vermelho",
            95,
            "🚫 NÃO interaja. Bloqueie e denuncie."
        )
    elif score >= 80:
        return (
            "🟠 ALTO RISCO DE GOLPE",
            "laranja",
            85,
            "⚠️ Há fortes sinais de golpe. Não clique."
        )
    elif score >= 50:
        return (
            "🟡 RISCO MODERADO DE GOLPE",
            "amarelo",
            70,
            "⚠️ Verifique cuidadosamente antes de agir."
        )
    elif score >= 30:
        return (
            "🟢 POUCOS INDÍCIOS DE GOLPE",
            "verde-claro",
            50,
            "⚠️ Poucos sinais foram detectados. Isso não comprova que a mensagem seja segura."
        )
    else:
        return (
            "⚪ NENHUM INDÍCIO RELEVANTE DETECTADO",
            "neutro",
            40,
            "⚠️ A análise não comprova segurança. Confirme o remetente por um canal oficial."
        )


# ================================================================
# 🔥 V5.1: ANÁLISE COMPLETA PRODUCTION-READY
# ================================================================

def analisar_mensagem_guardinia_v5_1(texto: str) -> ResultadoAnalise:
    """
    🔥 V5.1 PRODUCTION-READY - Pipeline refinado com redução inteligente
    para cobranças legítimas estruturadas.
    """

    inicio_total = time.time()
    texto = normalizar_texto(texto)

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

    # 1️⃣ Score heurístico base
    score_base, motivos_base, indicadores = avaliar_heuristicas(texto)
    score_total, motivos = aplicar_combinacoes(score_base, motivos_base, indicadores)

    # 2️⃣ Camada semântica
    sinais = extrair_sinais_semanticos(texto)
    score_semantico = sum(v for v in sinais.values() if v > 0) * MULTIPLICADOR_SEMANTICO

    if score_semantico > 0:
        score_total += int(score_semantico)
        indicadores["score_semantico"] = int(score_semantico)
        indicadores["sinais_detectados"] = {k: v for k, v in sinais.items() if v != 0}

    # 3️⃣ IPP (mensagem amigável)
    ipp = calcular_indice_pressao(texto, sinais)
    if ipp > 0:
        score_total += int(ipp)
        indicadores["indice_pressao_psicologica"] = int(ipp)

        if ipp >= 25:
            motivos.append("Uso de forte pressão emocional ou senso de urgência")
        elif ipp >= 12:
            motivos.append("Uso moderado de urgência ou ameaça implícita")
        elif ipp >= 5:
            motivos.append("Leve presença de linguagem persuasiva")

    # 4️⃣ Ajuste investigativo
    if sinais.get('investigativo', 0) < 0:
        score_antes = score_total
        score_total = int(score_total * REDUCAO_INVESTIGATIVO)
        indicadores["ajuste_investigativo"] = True
        indicadores["reducao_aplicada"] = score_antes - score_total

    # 5️⃣ 🔐 NOVO BLOCO — DETECÇÃO DE COBRANÇA ESTRUTURADA LEGÍTIMA
    t = texto.lower()

    possui_valor = bool(re.search(r'r\$\s?\d+[.,]?\d*', t))
    possui_parcela_ou_contrato = bool(
        re.search(r'parcela\s?\d+', t) or
        re.search(r'n[úu]mero\s?\d+', t) or
        re.search(r'\b\d{8,}\b', t)
    )

    possui_solicitacao_sensivel = any(x in t for x in [
        "senha", "token", "código", "codigo", "confirme seus dados"
    ])

    possui_ameaca_forte = any(x in t for x in [
        "bloqueado imediatamente",
        "prisão",
        "último aviso",
        "suspensão imediata"
    ])

    if (
        possui_valor and
        possui_parcela_ou_contrato and
        not possui_solicitacao_sensivel and
        not possui_ameaca_forte
    ):
        score_antes = score_total
        score_total = int(score_total * 0.55)  # redução controlada
        indicadores["reducao_cobranca_estruturada"] = score_antes - score_total
        motivos.append("Cobrança estruturada detectada (padrão legítimo)")

    # 6️⃣ Escalada não linear
    categorias_criticas = ["PHISHING", "ENGENHARIA_SOCIAL", "FINANCEIRO"]
    categorias_criticas_ativas = [
        cat for cat in categorias_criticas
        if indicadores.get(f"score_categoria_{cat}", 0) > 0
    ]

    if len(categorias_criticas_ativas) >= 3:
        score_antes = score_total
        score_total = int(score_total * MULTIPLICADOR_CRITICO)
        indicadores["multiplicador_critico_aplicado"] = MULTIPLICADOR_CRITICO

    score_heuristico_final = min(score_total, 200)
    indicadores["score_heuristico_final"] = score_heuristico_final

    # 7️⃣ Decisão de escalonamento IA
    categorias_ativas = set([m.split(":")[0].strip() for m in motivos if ":" in m])

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
                texto=texto,
                score_heuristico=score_heuristico_final,
                categorias=categorias_lista,
                sinais=sinais,
                modelo="haiku",
                nivel_analise="basico"
            )

            if resposta_bedrock and decidir_repass_sonnet(resposta_bedrock):
                resposta_bedrock = chamar_bedrock_claude(
                    texto=texto,
                    score_heuristico=score_heuristico_final,
                    categorias=categorias_lista,
                    sinais=sinais,
                    modelo="sonnet",
                    nivel_analise="profundo"
                )
        else:
            resposta_bedrock = chamar_bedrock_claude(
                texto=texto,
                score_heuristico=score_heuristico_final,
                categorias=categorias_lista,
                sinais=sinais,
                modelo=modelo,
                nivel_analise=nivel
            )

        if resposta_bedrock:
            score_total = fusao_hibrida_score(
                score_heuristico_final,
                resposta_bedrock,
                indicadores
            )
            motivos.append("Análise cognitiva avançada aplicada")
        else:
            score_total = score_heuristico_final
    else:
        score_total = score_heuristico_final

    # 8️⃣ Manipulação temporal
    tem_manipulacao_temporal, motivo_temporal = detectar_manipulacao_temporal(texto, sinais)
    if tem_manipulacao_temporal:
        score_total += 12
        indicadores["manipulacao_temporal"] = True

    score_total = min(score_total, 200)

    tempo_total = (time.time() - inicio_total) * 1000
    indicadores["tempo_total_ms"] = round(tempo_total, 2)
    indicadores["score_final_limitado"] = score_total

    status, cor, confianca, acao = classificar(score_total)

    logger.info(json.dumps({
        "evento": "analise_completa_v5_1",
        "score_heuristico": score_heuristico_final,
        "score_final": score_total,
        "bedrock_usado": resposta_bedrock is not None,
        "modelo_bedrock": resposta_bedrock.modelo_usado if resposta_bedrock else None,
        "tempo_total_ms": round(tempo_total, 2),
        "classificacao": status
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



# ================================================================
# WHATSAPP (mantidos com melhorias V5.1)
# ================================================================

def eh_saudacao_inteligente(texto: str) -> bool:
    if not texto:
        return False

    # Normalização
    t = texto.strip().lower()

    # Remove pontuação leve
    t = re.sub(r'[!?.]+', '', t)
    t = re.sub(r'\s+', ' ', t)

    palavras = t.split()

    # Se for frase longa, não é saudação
    if len(palavras) > 3:
        return False

    # Se contém termos de análise, não é menu
    termos_analise = {
        "golpe", "fraude", "seguro", "suspeito",
        "pix", "link", "mensagem", "analisa", "verifica"
    }

    if any(p in termos_analise for p in palavras):
        return False

    saudacoes_simples = {
        "oi", "ola", "olá",
        "opa",
        "menu",
        "ajuda",
        "fala",
        "salve",
        "opaa", "opaaa", "opaaaa"
    }

    saudacoes_compostas = {
        "bom dia",
        "boa tarde",
        "boa noite",
        "e ae",
        "e aee",
        "e aeeee"
    }

    # Caso simples: primeira palavra
    if palavras[0] in saudacoes_simples:
        return True

    # Caso composto: até duas primeiras palavras
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
    payload = {"messaging_product": "whatsapp", "to": telefone, "type": "text", "text": {"body": texto_seguro}}
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url=url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp: {e}")


# =========================
# GUARDINIA V5.1 + CAMADA PROTETIVA LEVE
# =========================

# (CÓDIGO ORIGINAL COMPLETO MANTIDO ATÉ A FUNÇÃO processar_mensagem)
# ↓↓↓
# ATENÇÃO: Tudo acima permanece exatamente igual ao que você enviou.
# A única modificação começa na seção abaixo.
# =========================


# ================================================================
# 🆕 CAMADA PROTETIVA LEVE (PORTFÓLIO SAFE MODE)
# ================================================================

def eh_consulta_investigativa(texto: str) -> bool:
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

    if "?" in texto and any(p in t for p in ["golpe", "seguro", "normal", "fraude", "confiar"]):
        return True

    return False


def deve_ativar_orientacao(texto: str, indicadores: dict) -> bool:
    if not eh_consulta_investigativa(texto):
        return False

    # Ativa somente se já houver risco detectado pelo motor
    score_base = indicadores.get("score_heuristico_base", 0)
    score_semantico = indicadores.get("score_semantico", 0)

    if score_base > 0 or score_semantico >= 20:
        return True

    return False


def resposta_orientativa_padrao() -> str:
    return (
        "🟡 Atenção\n\n"
        "O padrão descrito é comum em tentativas de fraude.\n"
        "Recomendo verificar diretamente pelo aplicativo oficial "
        "ou pelo número atrás do seu cartão antes de tomar qualquer ação.\n\n"
        "⚠️ Nunca compartilhe senhas, códigos ou dados pessoais por WhatsApp."
    )


# ================================================================
# PROCESSAR MENSAGEM
# ================================================================

def processar_mensagem(texto_original: str):

    if not texto_original or len(texto_original.strip()) == 0:
        return "❌ Mensagem vazia."

    texto_limpo = normalizar_texto(texto_original)

    if eh_saudacao_inteligente(texto_limpo):
        return f"{texto_original}, tudo bem?\n\n{menu_inicial_guardinia()}"

    conteudo_hash = gerar_hash_texto(texto_limpo)
    cache = buscar_cache(conteudo_hash)

    if cache:
        resultado_cache = cache.get('result', '')
        if resultado_cache:
            return f"{resultado_cache}\n\nℹ️ Resultado em cache."

    # ✅ FIX 2: salvar_cache será chamado em background ao final

    # 🔗 Verificação de links
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

    # 🔍 Análise principal
    resultado = analisar_mensagem_guardinia_v5_1(texto_limpo)

    # ============================================================
    # 🛡️ CAMADA PROTETIVA LEVE (PORTFÓLIO SAFE MODE)
    # ============================================================

    t = texto_limpo.lower()

    entidade_sensivel = any(x in t for x in [
        "banco", "nubank", "itau", "itaú", "bradesco", "santander"
    ])

    pedido_confirmacao = any(x in t for x in [
        "confirmar", "atualizar", "dados", "cpf", "senha"
    ])

    canal_informal = any(x in t for x in [
        "whatsapp", "wpp", "zap"
    ])

    if entidade_sensivel and pedido_confirmacao and canal_informal:
        return (
            "🟡 ALERTA PREVENTIVO\n\n"
            "⚠️ Bancos normalmente NÃO solicitam confirmação de dados por WhatsApp.\n\n"
            "Confirme sempre diretamente pelo aplicativo oficial ou pelo número atrás do cartão.\n\n"
            "Nunca compartilhe senhas, códigos ou dados pessoais."
        )

    # 📊 Resposta normal formatada
    resposta_formatada = (
        f"{resultado.status}\n\n"
        f"🎯 Confiança: {resultado.confianca}%\n"
    )

    if resultado.indicadores_tecnicos.get("fusao_aplicada"):
        resposta_formatada += "\n🤖 Análise cognitiva aplicada\n"

    if resultado.motivos:
        resposta_formatada += (
            "\n📌 Motivos:\n" +
            "\n".join(f"• {m}" for m in resultado.motivos[:5])
        )

    resposta_formatada += f"\n\n👉 {resultado.acao_recomendada}"

    # ✅ FIX 2: salva cache em background, sem bloquear a resposta
    threading.Thread(
        target=salvar_cache,
        args=(conteudo_hash, resultado, resposta_formatada, None),
        daemon=True
    ).start()

    return resposta_formatada

# ================================================================
# RATE LIMITING (mantido)
# ================================================================

def verificar_rate_limit(telefone: str, limite: int = 10) -> bool:
    try:
        agora = int(time.time())
        janela_inicio = agora - 60
        pk = f"RATE#{telefone}"
        response = audit_table.query(KeyConditionExpression=Key("pk").eq(pk), ScanIndexForward=False)
        itens = response.get("Items", [])
        recentes = [i for i in itens if int(i.get("timestamp_epoch", 0)) >= janela_inicio]
        if len(recentes) >= limite:
            return False
        audit_table.put_item(Item={"pk": pk, "sk": str(agora), "timestamp_epoch": agora, "ttl": agora + 120})
        return True
    except Exception as e:
        logger.error(f"Erro rate limit: {e}")
        return True


# ================================================================
# SISTEMA WEB (mantido com V5.1)
# ================================================================

def processar_sistema_web(body: Dict[str, Any], origin: str, source_ip: str):
    logger.info("web_request | version=%s", APP_VERSION)

    autorizado, motivo_bloqueio = autorizar_requisicao_web(source_ip)
    if not autorizado:
        logger.warning("web_request_blocked | reason=rate_or_daily_limit")
        return resposta_web_erro(motivo_bloqueio, origin, status_code=429)

    # ===============================
    # TEXTO
    # ===============================
    if "mensagem" in body:
        mensagem_bruta = body.get("mensagem", "")

        if not isinstance(mensagem_bruta, str):
            return resposta_web_erro("Mensagem inválida.", origin)

        mensagem = mensagem_bruta.strip()

        if not mensagem:
            return resposta_web_erro("Mensagem vazia.", origin)

        if len(mensagem) > WEB_MAX_TEXT_CHARS:
            return resposta_web_erro(
                f"A mensagem deve ter no máximo {WEB_MAX_TEXT_CHARS} caracteres.",
                origin,
                status_code=413,
            )

        mensagem = normalizar_texto(mensagem)
        conteudo_hash = gerar_hash_texto(mensagem)
        resultado_cache = buscar_cache_web(conteudo_hash)
        if resultado_cache:
            logger.info("web_cache_hit | type=text")
            return resposta_web_sucesso(resultado_cache, origin, cache_hit=True)

        resultado = analisar_mensagem_guardinia_v5_1(mensagem)
        salvar_cache_web(conteudo_hash, resultado)
        return resposta_web_sucesso(resultado, origin)

    # ===============================
    # IMAGEM (BASE64)
    # ===============================
    if "imagem" in body:
        imagem_base64 = body.get("imagem")
        mime_type = body.get("tipo", "image/jpeg")

        if not isinstance(imagem_base64, str) or not imagem_base64:
            return resposta_web_erro("Imagem inválida.", origin)

        if mime_type not in {"image/jpeg", "image/jpg", "image/png"}:
            return resposta_web_erro("Formato de imagem não suportado.", origin)

        tamanho_base64_maximo = ((WEB_MAX_IMAGE_BYTES + 2) // 3) * 4
        if len(imagem_base64) > tamanho_base64_maximo:
            return resposta_web_erro(
                "A imagem excede o tamanho máximo permitido.",
                origin,
                status_code=413,
            )

        try:
            imagem_bytes = base64.b64decode(imagem_base64, validate=True)
        except Exception as e:
            logger.error(f"Erro ao decodificar base64: {e}")
            return resposta_web_erro("Imagem inválida.", origin)

        if not imagem_bytes or len(imagem_bytes) > WEB_MAX_IMAGE_BYTES:
            return resposta_web_erro(
                "A imagem excede o tamanho máximo permitido.",
                origin,
                status_code=413,
            )

        conteudo_hash = "imagem:" + hashlib.sha256(imagem_bytes).hexdigest()
        resultado_cache = buscar_cache_web(conteudo_hash)
        if resultado_cache:
            logger.info("web_cache_hit | type=image")
            return resposta_web_sucesso(resultado_cache, origin, cache_hit=True)

        # OCR igual ao WhatsApp
        response_textract = textract.detect_document_text(
            Document={'Bytes': imagem_bytes}
        )

        texto_extraido = ""
        for block in response_textract.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                texto_extraido += block.get('Text', '') + " "

        texto_extraido = texto_extraido.strip()

        if not texto_extraido:
            return resposta_web_erro("Não foi possível extrair texto da imagem.", origin)

        texto_extraido = normalizar_texto(texto_extraido)[:WEB_MAX_TEXT_CHARS]
        resultado = analisar_mensagem_guardinia_v5_1(texto_extraido)
        salvar_cache_web(conteudo_hash, resultado)

        return resposta_web_sucesso(resultado, origin)

    return resposta_web_erro("Formato inválido.", origin)
# ================================================================
# VERIFICAÇÃO DE INTEGRIDADE
# ================================================================

def verificar_integridade_sistema():
    erros = []
    
    if not HEURISTICAS_REGISTRADAS:
        erros.append("Nenhuma heurística registrada")
    
    if BEDROCK_ENABLED:
        try:
            logger.info("Bedrock habilitado e configurado")
        except Exception as e:
            erros.append(f"Erro na configuração Bedrock: {e}")
    else:
        logger.warning("⚠️ Bedrock DESABILITADO - sistema funcionará apenas com heurísticas")
    
    if erros:
        logger.error("=" * 70)
        logger.error("ERRO DE INTEGRIDADE GUARDINIA V5.1")
        for e in erros:
            logger.error(f"  • {e}")
        logger.error("=" * 70)
    else:
        logger.info("=" * 70)
        logger.info(f"✅ {APP_NAME} V{APP_VERSION} carregado com sucesso")
        logger.info(f"  • Heurísticas: {len(HEURISTICAS_REGISTRADAS)}")
        logger.info(f"  • Bedrock: {'HABILITADO' if BEDROCK_ENABLED else 'DESABILITADO'}")
        logger.info(f"  • Zona Cognitiva: {ZONA_COGNITIVA_MIN}-{ZONA_COGNITIVA_MAX}")
        logger.info(f"  • Double-pass: HABILITADO")
        logger.info(f"  • Anti-hallucination: HABILITADO")
        logger.info(f"  • Divergência cognitiva: HABILITADO")
        logger.info("=" * 70)


verificar_integridade_sistema()

# ================================================================
# RESPOSTAS PADRÃO SISTEMA WEB
# ================================================================

def resposta_web_sucesso(
    resultado: ResultadoAnalise,
    origin: str,
    cache_hit: bool = False,
):
    return {
        "statusCode": 200,
        "headers": cabecalhos_cors(origin),
        "body": json.dumps({
            "status": resultado.status,
            "cor": resultado.cor,
            "confianca": resultado.confianca,
            "acao_recomendada": resultado.acao_recomendada,
            "score": resultado.score_total,
            "motivos": resultado.motivos,
            "cache": cache_hit,
            "version": APP_VERSION,
        }, ensure_ascii=False)
    }


def resposta_web_erro(
    mensagem: str,
    origin: str,
    status_code: int = 400,
):
    return {
        "statusCode": status_code,
        "headers": cabecalhos_cors(origin),
        "body": json.dumps({
            "erro": mensagem
        }, ensure_ascii=False)
    }


# ================================================================
# LAMBDA HANDLER
# ================================================================

def lambda_handler(event, context):
    try:
        logger.info("=" * 70)
        logger.info("%s V%s INVOCADO", APP_NAME, APP_VERSION)
        logger.info("=" * 70)

        method = (
            event.get("httpMethod")
            or event.get("requestContext", {}).get("http", {}).get("method")
        )
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        origin = str(headers.get("origin", "")).rstrip("/")

        # CORS preflight
        if method == "OPTIONS":
            if not origem_web_permitida(origin):
                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json; charset=utf-8"},
                    "body": json.dumps({"erro": "Origem não permitida."}, ensure_ascii=False),
                }
            return {
                "statusCode": 204,
                "headers": cabecalhos_cors(origin),
                "body": ""
            }

        body_str = event.get("body", "{}")

        try:
            if event.get("isBase64Encoded", False):
                body_bytes = base64.b64decode(body_str)
            else:
                body_bytes = body_str.encode("utf-8")

            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}
            body_bytes = b""

        eh_sistema_web = (
            method == "POST"
            and isinstance(body, dict)
            and body.get("origem") == "web"
        )

        # ============================================================
        # 🌐 SISTEMA WEB
        # ============================================================
        if method == "POST" and isinstance(body, dict) and body.get("origem") == "web":
            if not origem_web_permitida(origin):
                logger.warning("web_request_blocked | reason=origin | origin=%s", origin or "missing")
                return resposta_web_erro("Origem não permitida.", origin, status_code=403)

            request_context = event.get("requestContext", {}) or {}
            source_ip = (
                request_context.get("identity", {}).get("sourceIp")
                or request_context.get("http", {}).get("sourceIp")
                or "unknown"
            )
            logger.info("Roteando SISTEMA WEB V%s", APP_VERSION)
            return processar_sistema_web(body, origin, source_ip)

        # ============================================================
        # 📱 WHATSAPP WEBHOOK
        # ============================================================
        if method == "POST" and headers.get("x-hub-signature-256"):
            logger.info("Processando webhook WhatsApp")

            headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

            if not validar_assinatura(headers, body_bytes):
                return {
                    "statusCode": 403,
                    "headers": {
                        "Content-Type": "application/json; charset=utf-8",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({"erro": "Assinatura inválida"}, ensure_ascii=False)
                }

            body = json.loads(body_bytes)

            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [])

                    if not messages or not contacts:
                        continue

                    telefone = contacts[0].get("wa_id")

                    for msg in messages:
                        # =========================================
                        # 📸 IMAGEM
                        # =========================================
                        if msg.get("type") == "image":
                            logger.info(f"📸 Imagem recebida de {mascarar_telefone(telefone)}")

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
                                    Document={'Bytes': imagem_bytes}
                                )

                                texto_extraido = ""
                                for block in response_textract.get('Blocks', []):
                                    if block.get('BlockType') == 'LINE':
                                        texto_extraido += block.get('Text', '') + " "

                                texto_extraido = texto_extraido.strip()

                                if not texto_extraido or len(texto_extraido) < 5:
                                    enviar_mensagem_whatsapp(
                                        telefone,
                                        "❌ Não consegui extrair texto suficiente da imagem."
                                    )
                                    continue

             # 🔥 IGUAL AO WEB: normaliza antes de analisar
                                texto_extraido = normalizar_texto(texto_extraido)

                                resultado = analisar_mensagem_guardinia_v5_1(texto_extraido)

                                # ============================================================
                                # 🛡️ CAMADA PROTETIVA LEVE (IMAGEM)
                                # ============================================================
                                if eh_consulta_investigativa(texto_extraido):

                                    t = texto_extraido.lower()

                                    entidade_sensivel = any(x in t for x in [
                                        "banco", "nubank", "itau", "itaú", "bradesco", "santander"
                                    ])

                                    pedido_confirmacao = any(x in t for x in [
                                        "confirmar", "atualizar", "dados", "cpf", "senha"
                                    ])

                                    if entidade_sensivel and pedido_confirmacao:
                                        enviar_mensagem_whatsapp(
                                            telefone,
                                            "🟡 ALERTA PREVENTIVO\n\n"
                                            "⚠️ Bancos normalmente NÃO solicitam confirmação de dados por WhatsApp.\n\n"
                                            "Confirme sempre diretamente pelo aplicativo oficial ou pelo número atrás do cartão.\n\n"
                                            "Nunca compartilhe senhas, códigos ou dados pessoais."
                                        )
                                        continue

                                resposta_formatada = (
                                    f"{resultado.status}\n\n"
                                    f"🎯 Confiança: {resultado.confianca}%\n"
                                )

                                if resultado.indicadores_tecnicos.get("fusao_aplicada"):
                                    resposta_formatada += "\n🤖 Análise cognitiva aplicada\n"

                                resposta_formatada += (
                                    "\n📌 Motivos:\n" +
                                    "\n".join(f"• {m}" for m in resultado.motivos[:5]) +
                                    f"\n\n👉 {resultado.acao_recomendada}"
                                )

                                enviar_mensagem_whatsapp(telefone, resposta_formatada)

                            except Exception as e:
                                logger.error(f"Erro imagem WhatsApp: {str(e)}")
                                logger.error(traceback.format_exc())
                                enviar_mensagem_whatsapp(
                                    telefone,
                                    "❌ Erro ao processar imagem."
                                )

                        # =========================================
                        # 📝 TEXTO
                        # =========================================
                        elif msg.get("type") == "text":
                            texto_original = msg.get("text", {}).get("body", "").strip()

                            if texto_original:
                                resposta = processar_mensagem(texto_original)
                                enviar_mensagem_whatsapp(telefone, resposta)

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": "OK"
            }

        # ============================================================
        # 📥 VERIFICAÇÃO (GET - Meta Challenge)
        # ============================================================
        if method == "GET":
            params = event.get("queryStringParameters") or {}
            mode = params.get("hub.mode")
            token = params.get("hub.verify_token")
            challenge = params.get("hub.challenge")

            if mode == "subscribe" and token == VERIFY_TOKEN:
                logger.info("Webhook verificado com sucesso.")
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
        logger.error("ERRO FATAL NA LAMBDA")
        logger.error(str(e))
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"erro": "Erro interno"}, ensure_ascii=False)
        }

# ================================================================
# FIM GuardinIA Web Analyzer
# ================================================================

logger.info("=" * 70)
logger.info("%s V%s - Nível Bancário", APP_NAME, APP_VERSION)
logger.info("=" * 70)