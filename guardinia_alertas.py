#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════
GuardinIA — Configurar Alertas por Email (AWS SNS)

Executa UMA VEZ para configurar.
Depois disso, você recebe email quando alguém usar o GuardinIA.

Uso:
  python3 guardinia_alertas.py --configurar
  python3 guardinia_alertas.py --testar
  python3 guardinia_alertas.py --remover
════════════════════════════════════════════════════════════════════
"""

import boto3
import json
import argparse
import sys

# ── Configuração ────────────────────────────────────────────────────
LAMBDA_NAME   = "sentinela_whatsapp_webhook"
LOG_GROUP     = f"/aws/lambda/{LAMBDA_NAME}"
AWS_REGION    = "us-east-1"
EMAIL_ALERTA  = "luan.tardis@gmail.com"
TOPICO_NOME   = "guardinia-alertas"
FILTRO_NOME   = "guardinia-analise-completa"

# ── Clientes AWS ────────────────────────────────────────────────────
sns  = boto3.client("sns",  region_name=AWS_REGION)
logs = boto3.client("logs", region_name=AWS_REGION)


def criar_topico_sns() -> str:
    """Cria (ou recupera se já existe) o tópico SNS."""
    resp = sns.create_topic(Name=TOPICO_NOME)
    arn  = resp["TopicArn"]
    print(f"  ✅ Tópico SNS: {arn}")
    return arn


def inscrever_email(topico_arn: str):
    """Inscreve o email no tópico."""
    resp = sns.subscribe(
        TopicArn = topico_arn,
        Protocol = "email",
        Endpoint = EMAIL_ALERTA,
    )
    print(f"  ✅ Email inscrito: {EMAIL_ALERTA}")
    print(f"  📧 IMPORTANTE: Você receberá um email de confirmação da AWS.")
    print(f"     Clique em 'Confirm subscription' para ativar os alertas.")


def criar_filtro_log(topico_arn: str):
    """
    Cria filtro no CloudWatch Logs que dispara SNS
    toda vez que aparecer um log de análise completa.
    """
    try:
        logs.put_metric_filter(
            logGroupName  = LOG_GROUP,
            filterName    = FILTRO_NOME,
            filterPattern = '"analysis_complete_v5_1"',
            metricTransformations=[{
                "metricName"      : "GuardinIA_Analises",
                "metricNamespace" : "GuardinIA",
                "metricValue"     : "1",
                "unit"            : "Count",
            }]
        )
        print(f"  ✅ Filtro de métrica criado no CloudWatch")
    except Exception as e:
        print(f"  ⚠️  Filtro de métrica: {e}")

    # Cria alarme CloudWatch que dispara o SNS
    cw = boto3.client("cloudwatch", region_name=AWS_REGION)
    try:
        cw.put_metric_alarm(
            AlarmName          = "guardinia-uso-detectado",
            AlarmDescription   = "Alguém usou o GuardinIA",
            MetricName         = "GuardinIA_Analises",
            Namespace          = "GuardinIA",
            Statistic          = "Sum",
            Period             = 60,      # janela de 1 minuto
            EvaluationPeriods  = 1,
            Threshold          = 1,
            ComparisonOperator = "GreaterThanOrEqualToThreshold",
            AlarmActions       = [topico_arn],
            TreatMissingData   = "notBreaching",
        )
        print(f"  ✅ Alarme CloudWatch criado")
        print(f"     → Você receberá email quando alguém usar o sistema")
    except Exception as e:
        print(f"  ❌ Erro ao criar alarme: {e}")


def testar_alerta(topico_arn: str):
    """Envia mensagem de teste para o email."""
    sns.publish(
        TopicArn = topico_arn,
        Subject  = "🛡️ GuardinIA — Teste de alerta",
        Message  = (
            "Este é um teste do sistema de alertas do GuardinIA.\n\n"
            "Se você recebeu este email, os alertas estão configurados corretamente!\n\n"
            "Você será notificado automaticamente quando alguém usar o sistema.\n\n"
            "— GuardinIA v5.1"
        )
    )
    print(f"\n  📧 Email de teste enviado para {EMAIL_ALERTA}")
    print(f"  Verifique sua caixa de entrada (e spam).\n")


def buscar_topico_existente() -> str | None:
    """Verifica se o tópico já existe."""
    try:
        resp = sns.list_topics()
        for t in resp.get("Topics", []):
            if TOPICO_NOME in t["TopicArn"]:
                return t["TopicArn"]
    except Exception:
        pass
    return None


def remover_tudo():
    """Remove alarme, filtro e tópico."""
    cw = boto3.client("cloudwatch", region_name=AWS_REGION)

    try:
        cw.delete_alarms(AlarmNames=["guardinia-uso-detectado"])
        print("  ✅ Alarme removido")
    except Exception as e:
        print(f"  ⚠️  Alarme: {e}")

    try:
        logs.delete_metric_filter(
            logGroupName = LOG_GROUP,
            filterName   = FILTRO_NOME,
        )
        print("  ✅ Filtro de log removido")
    except Exception as e:
        print(f"  ⚠️  Filtro: {e}")

    topico_arn = buscar_topico_existente()
    if topico_arn:
        try:
            sns.delete_topic(TopicArn=topico_arn)
            print("  ✅ Tópico SNS removido")
        except Exception as e:
            print(f"  ⚠️  Tópico: {e}")


def main():
    parser = argparse.ArgumentParser(description="GuardinIA Alertas")
    parser.add_argument("--configurar", action="store_true",
                        help="Configura alertas por email (executa uma vez)")
    parser.add_argument("--testar",     action="store_true",
                        help="Envia email de teste")
    parser.add_argument("--remover",    action="store_true",
                        help="Remove toda a configuração de alertas")
    args = parser.parse_args()

    print("\n  🛡️  GuardinIA — Sistema de Alertas\n")

    if args.configurar:
        print("  Configurando alertas...\n")
        topico_arn = criar_topico_sns()
        inscrever_email(topico_arn)
        criar_filtro_log(topico_arn)
        print("\n  ════════════════════════════════════════")
        print("  ✅ Configuração concluída!")
        print(f"  📧 Confirme a inscrição no email: {EMAIL_ALERTA}")
        print("     (AWS envia email de confirmação agora)")
        print("  ════════════════════════════════════════\n")

    elif args.testar:
        topico_arn = buscar_topico_existente()
        if not topico_arn:
            print("  ❌ Tópico não encontrado. Rode --configurar primeiro.\n")
            sys.exit(1)
        testar_alerta(topico_arn)

    elif args.remover:
        print("  Removendo configuração...\n")
        remover_tudo()
        print("\n  ✅ Tudo removido.\n")

    else:
        parser.print_help()
        print("\n  Exemplo: python3 guardinia_alertas.py --configurar\n")


if __name__ == "__main__":
    main()
