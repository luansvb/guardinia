#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
GuardinIA — Monitor de Uso
Busca logs reais do CloudWatch e exibe resumo limpo no terminal.

Uso:
  python3 guardinia_monitor.py           # últimas 24 horas
  python3 guardinia_monitor.py --horas 48
  python3 guardinia_monitor.py --horas 168   # última semana
════════════════════════════════════════════════════════════════════
"""

import boto3
import json
import argparse
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── Configuração ────────────────────────────────────────────────────
LAMBDA_NAME  = "sentinela_whatsapp_webhook"
LOG_GROUP    = f"/aws/lambda/{LAMBDA_NAME}"
AWS_REGION   = "us-east-1"

# ── Cliente ─────────────────────────────────────────────────────────
logs = boto3.client("logs", region_name=AWS_REGION)


def buscar_eventos(horas: int) -> list:
    """Busca todos os eventos de log das últimas N horas."""
    agora    = datetime.now(timezone.utc)
    inicio   = agora - timedelta(hours=horas)
    inicio_ms = int(inicio.timestamp() * 1000)
    fim_ms    = int(agora.timestamp() * 1000)

    eventos = []
    next_token = None

    while True:
        kwargs = dict(
            logGroupName  = LOG_GROUP,
            startTime     = inicio_ms,
            endTime       = fim_ms,
            limit         = 10000,
        )
        if next_token:
            kwargs["nextToken"] = next_token

        try:
            resp = logs.filter_log_events(**kwargs)
        except Exception as e:
            print(f"\n❌ Erro ao acessar CloudWatch: {e}")
            print("   Verifique se suas credenciais AWS estão configuradas.")
            sys.exit(1)

        eventos.extend(resp.get("events", []))
        next_token = resp.get("nextToken")
        if not next_token:
            break

    return eventos


def parsear_mensagens(eventos: list) -> list:
    """Extrai análises completas dos eventos de log."""
    analises = []

    for ev in eventos:
        msg = ev.get("message", "")

        # Log principal de análise completa
        if '"event": "analysis_complete_v5_1"' in msg or "analysis_complete" in msg:
            try:
                # Extrai o JSON do log
                inicio = msg.index("{")
                dados  = json.loads(msg[inicio:])
                dados["_timestamp_ms"] = ev["timestamp"]
                analises.append(dados)
            except Exception:
                pass

    return analises


def formatar_hora(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    # Converte para horário de Brasília (UTC-3)
    dt_br = dt - timedelta(hours=3)
    return dt_br.strftime("%d/%m %H:%M")


def classificar_status(classification: str) -> str:
    s = classification.upper() if classification else ""
    if "GOLPE CONFIRMADO"   in s: return "🔴 GOLPE"
    if "ALTAMENTE SUSPEITO" in s: return "🟠 SUSPEITO+"
    if "SUSPEITO"           in s: return "🟡 SUSPEITO"
    if "BAIXO RISCO"        in s: return "🟢 BAIXO RISCO"
    if "SEGURO"             in s: return "✅ SEGURO"
    return "⚪ DESCONHECIDO"


def exibir_resumo(analises: list, horas: int):
    divider = "═" * 62
    thin    = "─" * 62

    print(f"\n{divider}")
    print(f"  🛡️  GuardinIA — Monitor de Uso")
    print(f"  Período: últimas {horas}h  |  Log group: {LOG_GROUP}")
    print(divider)

    if not analises:
        print(f"\n  📭 Nenhuma análise encontrada nas últimas {horas} horas.\n")
        print(f"  Isso pode significar:")
        print(f"   • Ninguém usou o sistema nesse período")
        print(f"   • Os logs ainda não chegaram (pode demorar ~1 min)")
        print(f"   • O nome da função está diferente do esperado")
        print(f"\n  Função configurada: {LAMBDA_NAME}")
        print(f"{divider}\n")
        return

    # ── Estatísticas gerais ─────────────────────────────────────────
    total        = len(analises)
    bedrock_used = sum(1 for a in analises if a.get("bedrock_used"))
    custo_total  = sum(float(a.get("bedrock_custo_usd") or 0) for a in analises)

    contagem_status = defaultdict(int)
    for a in analises:
        label = classificar_status(a.get("classification", ""))
        contagem_status[label] += 1

    lat_list = [float(a["latency_ms"]) for a in analises if a.get("latency_ms")]
    lat_media = sum(lat_list) / len(lat_list) if lat_list else 0

    print(f"\n  RESUMO")
    print(thin)
    print(f"  Total de análises     : {total}")
    print(f"  Bedrock acionado      : {bedrock_used} ({bedrock_used/total*100:.1f}%)")
    print(f"  Custo estimado        : USD {custo_total:.6f}")
    print(f"  Latência média        : {lat_media:.0f} ms")

    print(f"\n  CLASSIFICAÇÕES")
    print(thin)
    ordem = ["🔴 GOLPE", "🟠 SUSPEITO+", "🟡 SUSPEITO",
             "🟢 BAIXO RISCO", "✅ SEGURO", "⚪ DESCONHECIDO"]
    for label in ordem:
        cnt = contagem_status.get(label, 0)
        if cnt > 0:
            barra = "█" * cnt + "░" * max(0, 20 - cnt)
            pct   = cnt / total * 100
            print(f"  {label:<18} {barra}  {cnt:>3} ({pct:.0f}%)")

    # ── Últimas análises ────────────────────────────────────────────
    print(f"\n  ÚLTIMAS ANÁLISES (mais recentes primeiro)")
    print(thin)
    print(f"  {'Hora':<8} {'Score':>6}  {'Bedrock':<10} {'Resultado'}")
    print(f"  {'----':<8} {'-----':>6}  {'-------':<10} {'---------'}")

    for a in sorted(analises, key=lambda x: x["_timestamp_ms"], reverse=True)[:20]:
        hora    = formatar_hora(a["_timestamp_ms"])
        score   = a.get("final_score", a.get("heuristic_score", "?"))
        modelo  = a.get("bedrock_model") or "—"
        status  = classificar_status(a.get("classification", ""))
        bk_icon = f"🤖 {modelo}" if a.get("bedrock_used") else "  —"
        print(f"  {hora:<8} {str(score):>6}  {bk_icon:<10} {status}")

    print(f"\n{divider}\n")


def main():
    parser = argparse.ArgumentParser(description="GuardinIA Monitor")
    parser.add_argument("--horas", type=int, default=24,
                        help="Quantas horas para trás buscar (padrão: 24)")
    args = parser.parse_args()

    print(f"\n  🔍 Buscando logs das últimas {args.horas}h...", end="", flush=True)
    eventos  = buscar_eventos(args.horas)
    analises = parsear_mensagens(eventos)
    print(f" {len(eventos)} eventos encontrados.")

    exibir_resumo(analises, args.horas)


if __name__ == "__main__":
    main()
