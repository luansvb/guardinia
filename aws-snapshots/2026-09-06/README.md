# GuardinIA — snapshot sanitizado da AWS

Este diretório preserva o código-fonte completo das quatro funções Lambda observado no ambiente AWS em 6 de setembro de 2026.

## Escopo

| Diretório | Função AWS | Papel observado |
|---|---|---|
| `guardinia-ingestor` | `Guardinia-Ingestor` | Recebe o webhook canônico da Meta e publica a mensagem na fila SQS |
| `guardinia-processor` | `Guardinia-Processor` | Consome a fila SQS, analisa o conteúdo e envia a resposta pelo WhatsApp |
| `sentinela-web-analisador` | `sentinela_web_analisador` | Atende à análise de texto da aplicação web |
| `sentinela-whatsapp-webhook` | `sentinela_whatsapp_webhook` | Webhook direto secundário, sem evidência de participação no fluxo canônico |

## Regras de segurança

- Os arquivos Python foram extraídos dos pacotes de implantação e preservados sem alteração.
- Os `template.yaml` originais não fazem parte deste snapshot porque continham valores de configuração sensíveis e informações desatualizadas.
- Cada `snapshot.json` registra somente nomes de variáveis, configurações não secretas e dependências observadas.
- Este diretório é um inventário de recuperação e auditoria. Ele não deve ser usado diretamente como pacote de implantação.
- Credenciais, tokens, chaves, valores secretos, URLs privadas e conteúdo de mensagens foram deliberadamente excluídos.

## Integridade dos códigos preservados

| Função | Arquivo | SHA-256 |
|---|---|---|
| `Guardinia-Ingestor` | `guardinia-ingestor/src/lambda_function.py` | `d47302698d6b9dff1d92fca0b75cb56d88b386c50b38ba2c1ac5e8bff405d374` |
| `Guardinia-Processor` | `guardinia-processor/src/lambda_function.py` | `ad9e21c4c555c12c83d78a4b6430362c96ac2411b791c759692f49bb3eec6931` |
| `sentinela_web_analisador` | `sentinela-web-analisador/src/lambda_function.py` | `05602dce24b24bd50db7635677df83510b14af5c14329b409176da3ed02d59f8` |
| `sentinela_whatsapp_webhook` | `sentinela-whatsapp-webhook/src/webhook.py` | `fe5b59cc8a84e86f323c803855dd87bc39c3e40c101ba5161fd4c42e6121376e` |

## Limitações conhecidas

- O estado foi reconstruído a partir dos pacotes exportados e do inventário visual do console AWS.
- Os modelos SAM exportados não correspondiam integralmente às rotas e à concorrência observadas após os ajustes de 6 de setembro.
- O snapshot não substitui infraestrutura como código revisada.
- A tabela `guardinia_cache`, embora referenciada pelo código, não existia no inventário DynamoDB.
- O repositório público anterior continha somente um handler principal e não representava as quatro funções implantadas.

