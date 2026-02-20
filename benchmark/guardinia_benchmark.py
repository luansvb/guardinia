#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════
GuardinIA v5.1 — Benchmark Definitivo
Hybrid Fraud Detection Engine | AWS Serverless

Métricas geradas:
  - Accuracy, Precision, Recall, F1-Score por classe
  - Matriz de confusão completa
  - Latência real (média, P50, P90, P95, P99, max)
  - Uso do Bedrock por categoria
  - Score distribution
  - Exemplos de acertos e erros reais
  - Relatório publicável em JSON + TXT

Estratégia técnica:
  Usa a rota Web System da Lambda (/webhook com {"mensagem": "..."})
  que retorna JSON estruturado com status, score, confiança e indicadores.
  Sem HMAC. Sem WhatsApp. Dados 100% reais de produção.
════════════════════════════════════════════════════════════════════════
"""

import json
import time
import urllib.request
import urllib.error
import statistics
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════

ENDPOINT = os.environ.get(
    "GUARDINIA_ENDPOINT",
    "https://ly9yvqdsta.execute-api.us-east-1.amazonaws.com/prod/webhook"
)

DATASET_PATH = os.environ.get(
    "GUARDINIA_DATASET",
    "guardinia_dataset.json"
)

# Delay entre requisições (segundos) — evita throttling
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "0.3"))

# Timeout por requisição
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))

# Quantas mensagens testar (None = todas)
LIMIT = os.environ.get("LIMIT")
LIMIT = int(LIMIT) if LIMIT else None


# ══════════════════════════════════════════════════════════════════════
# MAPEAMENTO DE CLASSIFICAÇÃO
# ══════════════════════════════════════════════════════════════════════
# score >= 120  → 🔴 GOLPE CONFIRMADO
# score >= 80   → 🟠 ALTAMENTE SUSPEITO
# score >= 50   → 🟡 SUSPEITO
# score >= 30   → 🟢 BAIXO RISCO
# score <  30   → ✅ SEGURO

def status_to_label(status: str, score: int) -> str:
    """
    Converte status da Lambda → GOLPE / AMBIGUA / LEGITIMA
    para comparação com o dataset.

    Thresholds reais da Lambda (whatsapp_lambda_V5_3):
      score >= 120 → 🔴 GOLPE CONFIRMADO
      score >= 80  → 🟠 ALTAMENTE SUSPEITO
      score >= 50  → 🟡 SUSPEITO
      score >= 30  → 🟢 BAIXO RISCO
      score <  30  → ✅ SEGURO
    """
    s = status.upper()
    if "GOLPE CONFIRMADO" in s:
        return "GOLPE"
    elif "ALTAMENTE SUSPEITO" in s:
        return "GOLPE"
    elif "SUSPEITO" in s:
        # 🟡 SUSPEITO = score 50-79 → zona cinzenta = AMBIGUA
        return "AMBIGUA"
    elif "BAIXO RISCO" in s:
        # score 30-49 → calibrado como LEGITIMA após análise do benchmark v1
        return "LEGITIMA"
    elif "SEGURO" in s:
        return "LEGITIMA"
    else:
        # Fallback por score (escala real da Lambda)
        if score >= 80:
            return "GOLPE"
        elif score >= 30:
            return "AMBIGUA"
        else:
            return "LEGITIMA"


# ══════════════════════════════════════════════════════════════════════
# CLIENTE HTTP
# ══════════════════════════════════════════════════════════════════════

def analyze(mensagem: str) -> Tuple[Optional[dict], float, Optional[str]]:
    """
    Envia mensagem para a rota Web System da Lambda.
    Retorna: (resultado_dict, latencia_ms, erro_str)
    """
    payload = json.dumps(
        {"mensagem": mensagem},
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST"
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            latencia_ms = (time.perf_counter() - start) * 1000
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return data, latencia_ms, None

    except urllib.error.HTTPError as e:
        latencia_ms = (time.perf_counter() - start) * 1000
        body = e.read().decode("utf-8") if e.fp else ""
        return None, latencia_ms, f"HTTP {e.code}: {body[:200]}"

    except Exception as e:
        latencia_ms = (time.perf_counter() - start) * 1000
        return None, latencia_ms, str(e)


# ══════════════════════════════════════════════════════════════════════
# MÉTRICAS
# ══════════════════════════════════════════════════════════════════════

def calcular_metricas(resultados: list) -> dict:
    """Calcula todas as métricas a partir dos resultados coletados."""

    classes = ["GOLPE", "AMBIGUA", "LEGITIMA"]
    cm = defaultdict(lambda: defaultdict(int))

    latencias = []
    bedrock_count = 0
    bedrock_by_category = defaultdict(int)
    bedrock_model_count = defaultdict(int)
    score_by_category = defaultdict(list)
    erros_http = 0
    total_custo_usd = 0.0

    acertos = []
    erros = []

    for r in resultados:
        if r["erro"]:
            erros_http += 1
            continue

        real = r["categoria_real"]
        pred = r["categoria_pred"]
        latencias.append(r["latencia_ms"])

        cm[real][pred] += 1

        if r.get("bedrock_usado"):
            bedrock_count += 1
            bedrock_by_category[real] += 1
            modelo = r.get("bedrock_modelo", "desconhecido")
            bedrock_model_count[modelo] += 1

        custo = r.get("bedrock_custo_usd") or 0
        total_custo_usd += float(custo) if custo else 0

        score_by_category[real].append(r["score"])

        if real == pred:
            acertos.append(r)
        else:
            erros.append(r)

    total_validos = len(resultados) - erros_http
    total_acertos = sum(cm[c][c] for c in classes)
    accuracy = total_acertos / total_validos if total_validos > 0 else 0

    # Precision, Recall, F1 por classe
    por_classe = {}
    for c in classes:
        tp = cm[c][c]
        fp = sum(cm[outro][c] for outro in classes if outro != c)
        fn = sum(cm[c][outro] for outro in classes if outro != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0)

        support = sum(cm[c].values())

        por_classe[c] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall":    round(recall, 4),
            "f1":        round(f1, 4),
            "support":   support
        }

    # Macro F1
    macro_f1 = statistics.mean(
        por_classe[c]["f1"] for c in classes
    )

    # Latência
    lat_sorted = sorted(latencias)
    n = len(lat_sorted)

    def percentil(lst, p):
        idx = max(0, int(len(lst) * p / 100) - 1)
        return lst[idx] if lst else 0

    metricas_lat = {
        "media_ms":  round(statistics.mean(latencias), 1) if latencias else 0,
        "mediana_ms": round(statistics.median(latencias), 1) if latencias else 0,
        "p90_ms":    round(percentil(lat_sorted, 90), 1),
        "p95_ms":    round(percentil(lat_sorted, 95), 1),
        "p99_ms":    round(percentil(lat_sorted, 99), 1),
        "min_ms":    round(min(latencias), 1) if latencias else 0,
        "max_ms":    round(max(latencias), 1) if latencias else 0,
        "stdev_ms":  round(statistics.stdev(latencias), 1) if len(latencias) > 1 else 0,
    }

    # Score médio por categoria
    score_stats = {
        cat: {
            "media": round(statistics.mean(scores), 1) if scores else 0,
            "mediana": round(statistics.median(scores), 1) if scores else 0,
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
        }
        for cat, scores in score_by_category.items()
    }

    return {
        "total_testadas":      len(resultados),
        "total_validas":       total_validos,
        "total_erros_http":    erros_http,
        "total_acertos":       total_acertos,
        "accuracy":            round(accuracy, 4),
        "accuracy_pct":        round(accuracy * 100, 2),
        "macro_f1":            round(macro_f1, 4),
        "por_classe":          por_classe,
        "confusion_matrix":    {k: dict(v) for k, v in cm.items()},
        "latencia":            metricas_lat,
        "bedrock": {
            "total_acionado":  bedrock_count,
            "taxa_acionamento": round(bedrock_count / total_validos * 100, 1) if total_validos > 0 else 0,
            "por_categoria":   dict(bedrock_by_category),
            "por_modelo":      dict(bedrock_model_count),
            "custo_total_usd": round(total_custo_usd, 6),
        },
        "score_stats":         score_stats,
        "exemplos_acerto":     acertos[:5],
        "exemplos_erro":       erros[:10],
    }


# ══════════════════════════════════════════════════════════════════════
# RELATÓRIO
# ══════════════════════════════════════════════════════════════════════

def gerar_relatorio(m: dict, meta: dict) -> str:
    """Gera relatório ASCII publicável."""

    divider = "═" * 70
    thin    = "─" * 70

    linhas = [
        "",
        divider,
        "  GuardinIA v5.1 — BENCHMARK REPORT",
        f"  Data: {meta['data']}",
        f"  Endpoint: {meta['endpoint']}",
        divider,
        "",
        "  SUMÁRIO EXECUTIVO",
        thin,
        f"  Total testadas    : {m['total_testadas']:>6}",
        f"  Requisições OK    : {m['total_validas']:>6}",
        f"  Erros HTTP        : {m['total_erros_http']:>6}",
        f"  Taxa sucesso HTTP : {(m['total_validas']/m['total_testadas']*100):.1f}%",
        "",
        f"  ✅ Accuracy geral : {m['accuracy_pct']:.2f}%",
        f"  📊 Macro F1-Score  : {m['macro_f1']:.4f}",
        "",
    ]

    # Métricas por classe
    linhas += [
        "  MÉTRICAS POR CLASSE",
        thin,
        f"  {'Classe':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}",
        f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}",
    ]
    for cls, v in m["por_classe"].items():
        linhas.append(
            f"  {cls:<12} {v['precision']:>10.4f} {v['recall']:>10.4f} {v['f1']:>10.4f} {v['support']:>10}"
        )
    linhas.append("")

    # Matriz de confusão
    classes = ["GOLPE", "AMBIGUA", "LEGITIMA"]
    cm = m["confusion_matrix"]
    linhas += [
        "  MATRIZ DE CONFUSÃO",
        "  (linhas = real, colunas = predito)",
        thin,
        f"  {'':15} {'GOLPE':>10} {'AMBIGUA':>10} {'LEGITIMA':>10}",
        f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10}",
    ]
    for real in classes:
        row = cm.get(real, {})
        linhas.append(
            f"  {real:<15} {row.get('GOLPE',0):>10} {row.get('AMBIGUA',0):>10} {row.get('LEGITIMA',0):>10}"
        )
    linhas.append("")

    # Latência
    lat = m["latencia"]
    linhas += [
        "  LATÊNCIA (produção real)",
        thin,
        f"  Média   : {lat['media_ms']:>7.1f} ms",
        f"  Mediana : {lat['mediana_ms']:>7.1f} ms",
        f"  P90     : {lat['p90_ms']:>7.1f} ms",
        f"  P95     : {lat['p95_ms']:>7.1f} ms",
        f"  P99     : {lat['p99_ms']:>7.1f} ms",
        f"  Min     : {lat['min_ms']:>7.1f} ms",
        f"  Max     : {lat['max_ms']:>7.1f} ms",
        f"  StdDev  : {lat['stdev_ms']:>7.1f} ms",
        "",
    ]

    # Bedrock
    bk = m["bedrock"]
    linhas += [
        "  BEDROCK (Escalonamento Cognitivo)",
        thin,
        f"  Acionamentos    : {bk['total_acionado']}",
        f"  Taxa            : {bk['taxa_acionamento']:.1f}%",
        f"  Custo estimado  : USD {bk['custo_total_usd']:.6f}",
    ]
    if bk["por_categoria"]:
        linhas.append("  Por categoria:")
        for cat, cnt in bk["por_categoria"].items():
            linhas.append(f"    • {cat}: {cnt}")
    if bk["por_modelo"]:
        linhas.append("  Por modelo:")
        for mdl, cnt in bk["por_modelo"].items():
            linhas.append(f"    • {mdl}: {cnt}")
    linhas.append("")

    # Score stats
    linhas += [
        "  SCORE MÉDIO POR CATEGORIA",
        thin,
    ]
    for cat, s in m["score_stats"].items():
        linhas.append(
            f"  {cat:<12}: média={s['media']:.1f}  mediana={s['mediana']:.1f}  [{s['min']}–{s['max']}]"
        )
    linhas.append("")

    # Exemplos de erros
    if m["exemplos_erro"]:
        linhas += [
            "  EXEMPLOS DE CLASSIFICAÇÃO INCORRETA",
            thin,
        ]
        for i, ex in enumerate(m["exemplos_erro"][:6], 1):
            msg_preview = ex["mensagem"][:80].replace("\n", " ")
            linhas += [
                f"  [{i}] Real: {ex['categoria_real']} → Predito: {ex['categoria_pred']}",
                f"      Score: {ex['score']} | Status: {ex['status']}",
                f"      \"{msg_preview}...\"",
                "",
            ]

    linhas += [
        divider,
        "  GuardinIA — Hybrid Fraud Detection Engine",
        "  AWS Lambda · API Gateway · DynamoDB · Bedrock · Serverless",
        divider,
        "",
    ]

    return "\n".join(linhas)


# ══════════════════════════════════════════════════════════════════════
# BARRA DE PROGRESSO
# ══════════════════════════════════════════════════════════════════════

def progress_bar(current: int, total: int, width: int = 40) -> str:
    pct  = current / total
    done = int(width * pct)
    bar  = "█" * done + "░" * (width - done)
    return f"[{bar}] {current:>4}/{total} ({pct*100:.1f}%)"


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "═" * 70)
    print("  GuardinIA v5.1 — Iniciando Benchmark")
    print("═" * 70)
    print(f"  Endpoint : {ENDPOINT}")
    print(f"  Dataset  : {DATASET_PATH}")
    print(f"  Delay    : {REQUEST_DELAY}s entre requisições")
    print("═" * 70 + "\n")

    # Carrega dataset
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Dataset não encontrado: {DATASET_PATH}")
        print("   Passe o caminho via variável: GUARDINIA_DATASET=caminho.json")
        sys.exit(1)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if LIMIT:
        dataset = dataset[:LIMIT]

    total = len(dataset)
    print(f"  📦 {total} mensagens carregadas\n")

    resultados = []
    inicio_total = time.time()

    for i, item in enumerate(dataset, 1):
        categoria_real = item["categoria"]
        mensagem = item["mensagem"]
        msg_preview = mensagem[:60].replace("\n", " ")

        # Progresso
        bar = progress_bar(i, total)
        print(f"\r  {bar}  {msg_preview[:30]:<30}", end="", flush=True)

        # Chamada real
        resultado, latencia_ms, erro = analyze(mensagem)

        if erro or not resultado:
            resultados.append({
                "id": item.get("id"),
                "categoria_real": categoria_real,
                "categoria_pred": "ERRO",
                "mensagem": mensagem,
                "status": None,
                "score": None,
                "latencia_ms": latencia_ms,
                "bedrock_usado": False,
                "bedrock_modelo": None,
                "bedrock_custo_usd": None,
                "erro": erro or "resposta_vazia",
            })
        else:
            status   = resultado.get("status", "")
            score    = resultado.get("score", 0) or 0
            indicadores = resultado.get("indicadores", {}) or {}

            categoria_pred = status_to_label(status, score)
            bedrock_usado  = indicadores.get("fusao_aplicada", False)
            bedrock_modelo = indicadores.get("bedrock_modelo")
            bedrock_custo  = indicadores.get("bedrock_custo_usd")

            resultados.append({
                "id": item.get("id"),
                "categoria_real": categoria_real,
                "categoria_pred": categoria_pred,
                "mensagem": mensagem,
                "status": status,
                "score": score,
                "confianca": resultado.get("confianca"),
                "motivos": resultado.get("motivos", [])[:3],
                "latencia_ms": round(latencia_ms, 2),
                "bedrock_usado": bedrock_usado,
                "bedrock_modelo": bedrock_modelo,
                "bedrock_custo_usd": bedrock_custo,
                "erro": None,
            })

        if i < total:
            time.sleep(REQUEST_DELAY)

    tempo_total_s = time.time() - inicio_total
    print(f"\n\n  ✅ Concluído em {tempo_total_s:.1f}s\n")

    # Calcula métricas
    metricas = calcular_metricas(resultados)

    # Metadados
    meta = {
        "data": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "endpoint": ENDPOINT,
        "total_mensagens": total,
        "tempo_total_segundos": round(tempo_total_s, 2),
        "versao_benchmark": "1.0.0",
    }

    # Relatório ASCII
    relatorio_txt = gerar_relatorio(metricas, meta)
    print(relatorio_txt)

    # Salva JSON completo
    output_json = {
        "meta": meta,
        "metricas": metricas,
        "resultados_individuais": resultados,
    }

    nome_base = f"guardinia_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with open(f"{nome_base}.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    with open(f"{nome_base}.txt", "w", encoding="utf-8") as f:
        f.write(relatorio_txt)

    print(f"  💾 JSON salvo : {nome_base}.json")
    print(f"  📄 TXT salvo  : {nome_base}.txt\n")


if __name__ == "__main__":
    main()
