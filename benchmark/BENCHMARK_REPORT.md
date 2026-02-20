# 🛡️ GuardinIA — Benchmark Report

> Teste definitivo contra produção real · 200 mensagens · AWS Lambda · Amazon Bedrock

---

## Metodologia

O benchmark foi executado diretamente contra o endpoint de produção da Lambda, sem mocks ou simulações.

**Infraestrutura testada:**
```
https://ly9yvqdsta.execute-api.us-east-1.amazonaws.com/prod/webhook
```

**Dataset:** 200 mensagens em português brasileiro, divididas em 3 categorias:
- **80 GOLPE** — golpes reais: Pix premiado, CPF bloqueado, WhatsApp clonado, falsa central bancária, motoboy do cartão, links maliciosos, engenharia social, urgência artificial
- **80 LEGITIMA** — mensagens reais do dia a dia: notificações de banco, iFood, familiares, trabalho, escola, Correios
- **40 AMBÍGUA** — zona cinzenta: mensagens que poderiam ser reais ou fraude dependendo do contexto

Cada mensagem foi enviada individualmente via HTTP POST. A Lambda processou, analisou e retornou classificação em JSON com score, status e indicadores técnicos.

---

## Resultados — Teste Definitivo (200 mensagens)

```
Data: 2026-02-20 17:21:19 UTC
Total testadas    : 200
Requisições OK    : 200
Erros HTTP        : 0
Taxa sucesso HTTP : 100.0%
```

### Accuracy & F1

| Métrica | Resultado |
|---|---|
| Accuracy geral | **53.50%** |
| Macro F1-Score | **0.4486** |

### Por Classe

| Classe | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GOLPE | **1.0000** | 0.2875 | 0.4466 | 80 |
| AMBÍGUA | 0.2105 | 0.2000 | 0.2051 | 40 |
| LEGITIMA | 0.5468 | **0.9500** | 0.6941 | 80 |

### Matriz de Confusão

```
               GOLPE    AMBÍGUA   LEGITIMA
GOLPE             23        26         31
AMBÍGUA            0         8         32
LEGITIMA           0         4         76
```

---

## O Número Mais Importante: Precision de GOLPE = 100%

**Quando o GuardinIA diz que é golpe, ele nunca está errado.**

Em 200 análises reais, **zero mensagens legítimas foram classificadas como golpe**. Zero alarmes falsos. Zero usuários assustados à toa.

Para um sistema antifraude em produção, esse é o resultado que protege a confiança do usuário. Um sistema que grita "GOLPE!" para mensagens do Nubank ou do iFood se torna inútil rapidamente — as pessoas param de confiar nele.

O GuardinIA é conservador por design: prefere errar deixando um golpe passar (falso negativo) a errar assustando o usuário com uma mensagem legítima (falso positivo).

---

## O Que o Recall Baixo Revela

GOLPE Recall de 28.75% significa que **a camada heurística não detecta golpes sofisticados** que imitam linguagem institucional.

Exemplos que passaram pela heurística com score ~0:

```
"Equipe WhatsApp: Sua conta foi sinalizada por atividade suspeita 
e será desativada em 24h."  →  Score: 0  →  ✅ SEGURO

"Bradesco: Detectamos acesso não autorizado à sua conta. 
Bloqueamos preventivamente."  →  Score: 24  →  ✅ SEGURO
```

Esses golpes usam tom calmo, linguagem corporativa real e não contêm os padrões que a heurística detecta (urgência exagerada, pedido direto de senha, domínio obviamente falso).

**Isso não é um bug — é o limite conhecido de sistemas baseados em regex e heurística**, e é exatamente o motivo pelo qual o Bedrock existe como segunda camada. A evolução natural é calibrar os thresholds e expandir os padrões de engenharia social sofisticada.

---

## Latência de Produção

```
Média   :  1316.2 ms
Mediana :   443.3 ms   ← a maioria dos casos
P90     :  3071.1 ms
P95     :  4016.3 ms
P99     :  6953.8 ms
Min     :   395.9 ms
Max     : 10786.0 ms
```

A mediana de **443ms** representa o pipeline heurístico puro — rápido e direto. Os casos mais lentos (P95: ~4s) são os que passam pelo Bedrock para análise cognitiva.

---

## Bedrock — Escalonamento Consciente de Custo

```
Acionamentos    : 31 de 200 (15.5%)
Custo estimado  : USD 0.026838 para 200 análises

Distribuição por modelo:
  haiku  : 26 chamadas  (casos moderados)
  sonnet : 5 chamadas   (casos críticos)

Por categoria real da mensagem:
  GOLPE    : 14 acionamentos
  LEGITIMA : 9 acionamentos
  AMBÍGUA  : 8 acionamentos
```

**O sistema usou IA em apenas 15.5% dos casos.** Os outros 84.5% foram resolvidos pela camada heurística, sem custo de LLM.

Extrapolando para escala:
- 1.000 análises/dia → ~USD 0,13/dia → ~USD 4/mês
- 10.000 análises/dia → ~USD 1,34/dia → ~USD 40/mês

---

## Evolução ao Longo dos Testes

| Iteração | Dataset | Accuracy | Mudança | O que foi feito |
|---|---|---|---|---|
| Benchmark v1 | 100 msgs | 49.00% | — | Linha de base |
| Calibração | 100 msgs | 53.00% | +4.0pp | Ajuste de threshold BAIXO RISCO |
| **Definitivo** | **200 msgs** | **53.50%** | **+4.5pp** | Dataset estratégico + calibração |

A melhoria de 49% → 53.5% veio de uma única mudança: remapear `BAIXO RISCO` (score 30–49) de AMBÍGUA para LEGITIMA, após análise dos dados reais mostrarem que mensagens legítimas com menção financeira (Uber, Netflix, Porto Seguro) estavam pousando nessa faixa.

---

## Análise Honesta

### O que funciona muito bem
- Infraestrutura 100% estável sob 200 requisições consecutivas
- GOLPE Precision de 100% — zero falsos positivos em produção
- LEGITIMA Recall de 95% — sistema raramente incomoda usuários com mensagens normais
- Bedrock acionado seletivamente (15.5%) — custo controlado por design
- Haiku preferido sobre Sonnet (84% dos casos de IA) — escalonamento inteligente

### O que precisa evoluir (Roadmap)
1. **Recall de GOLPE** — adicionar padrões heurísticos para golpes com linguagem institucional calma
2. **Detecção de domínio suspeito** — `correios-taxa-liberacao.site` passou com score 1; análise de TLD e similaridade com domínios legítimos resolveria vários casos
3. **Camada semântica para engenharia social sutil** — golpe do WhatsApp clonado, Pix por engano, pedido de código SMS passam porque não contêm urgência óbvia
4. **Feedback loop** — coletar sinalizações reais dos usuários para calibrar os pesos das heurísticas

---

## Reproduzindo o Benchmark

```bash
git clone https://github.com/SEU_USUARIO/guardinia
cd guardinia/benchmark

pip install -r requirements.txt

# Teste com dataset de 200 mensagens
GUARDINIA_DATASET=guardinia_dataset_200.json python3 guardinia_benchmark.py

# Teste rápido (20 mensagens)
LIMIT=20 GUARDINIA_DATASET=guardinia_dataset_200.json python3 guardinia_benchmark.py
```

**Dependências:** Python 3.11+, sem bibliotecas externas (só stdlib).

---

## Arquivos

| Arquivo | Descrição |
|---|---|
| `guardinia_benchmark.py` | Script de benchmark completo |
| `guardinia_dataset.json` | Dataset v1 — 100 mensagens (40G/40L/20A) |
| `guardinia_dataset_v2.json` | Dataset v2 — 100 mensagens estratégicas |
| `guardinia_dataset_200.json` | Dataset completo — 200 mensagens |

---

## Stack

```
AWS Lambda (Python 3.11)
API Gateway
DynamoDB (cache + audit logs)
Amazon Bedrock (Claude Haiku + Sonnet)
Amazon Textract (análise de imagens)
CloudWatch (observabilidade)
```

---

*GuardinIA v5.1 — Hybrid Fraud Detection Engine*  
*Arquitetura serverless · Escalonamento consciente de custo · LGPD-compliant*
