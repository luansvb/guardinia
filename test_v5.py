import boto3
import json
import time

lambda_client = boto3.client('lambda')

test_cases = [
    {
        "name": "Zona 1: Sem IA (<20)",
        "input": "Oi, tudo bem?",
        "expected_score_max": 20,
        "expected_bedrock": False
    },
    {
        "name": "Zona 2: Haiku (20-60)",
        "input": "Me passa PIX de R$ 50",
        "expected_score_min": 20,
        "expected_score_max": 60,
        "expected_bedrock": True
    },
    {
        "name": "Zona 3: Sonnet (60-100)",
        "input": "Sou do banco. Confirme dados urgente: bit.ly/confirm",
        "expected_score_min": 60,
        "expected_score_max": 100,
        "expected_bedrock": True
    }
]

def invoke_lambda(mensagem):
    payload = {
        "httpMethod": "POST",
        "body": json.dumps({"mensagem": mensagem})
    }

    response = lambda_client.invoke(
        FunctionName="sentinela_whatsapp_webhook",
        Payload=json.dumps(payload)
    )

    outer = json.loads(response["Payload"].read())

    if "body" not in outer:
        raise Exception("Resposta inesperada da Lambda")

    inner = json.loads(outer["body"])

    return inner

def run_tests():
    stats = {"total": 0, "passed": 0, "failed": 0}

    for test in test_cases:
        print(f"\n🧪 Executando: {test['name']}")

        inicio = time.time()

        try:
            result = invoke_lambda(test["input"])
            latency = (time.time() - inicio) * 1000

            score = result.get("score")
            indicadores = result.get("indicadores", {})

            passed = True
            errors = []

            if "expected_score_min" in test:
                if score < test["expected_score_min"]:
                    passed = False
                    errors.append("Score abaixo do mínimo")

            if "expected_score_max" in test:
                if score > test["expected_score_max"]:
                    passed = False
                    errors.append("Score acima do máximo")

            if "expected_bedrock" in test:
                fusao = indicadores.get("fusao_aplicada", False)
                if fusao != test["expected_bedrock"]:
                    passed = False
                    errors.append("Uso de IA inesperado")

            stats["total"] += 1

            if passed:
                stats["passed"] += 1
                print(f"  ✅ PASSOU | Score: {score} | {latency:.0f}ms")
            else:
                stats["failed"] += 1
                print(f"  ❌ FALHOU | Score: {score} | Erros: {errors}")

        except Exception as e:
            stats["total"] += 1
            stats["failed"] += 1
            print(f"  ❌ ERRO: {str(e)}")

    print("\n==============================")
    print("RESUMO")
    print("==============================")
    print(f"Total: {stats['total']}")
    print(f"Passou: {stats['passed']}")
    print(f"Falhou: {stats['failed']}")
    print("==============================")

if __name__ == "__main__":
    run_tests()
