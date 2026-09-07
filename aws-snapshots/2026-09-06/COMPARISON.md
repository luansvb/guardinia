# Comparação com o repositório público

## Base analisada

- Repositório: `luansvb/guardinia`
- Branch pública de referência: `main`
- Commit de referência: `e20ce18a4b637ffcb8d937891561e6ac1afae361`
- Branch reservada para a sincronização: `chore/sync-aws-snapshots`

## Código

O repositório público possuía somente `src/lambda_handler.py` como implementação principal. Esse arquivo é estruturalmente próximo ao código do `Guardinia-Processor`, mas não é idêntico à versão implantada.

| Comparação | Resultado |
|---|---:|
| Linhas no handler público | 4.136 |
| Linhas no Processor implantado | 4.159 |
| Regiões diferentes | 24 |
| Funções com diferenças | 6 |
| Funções equivalentes sem diferença | 65 |

As funções diferentes são:

- `buscar_cache`
- `salvar_cache`
- `classificar`
- `detectar_url_promessa`
- `processar_mensagem`
- `lambda_handler`

As mudanças observadas na versão implantada incluem validação da versão e expiração do cache, condição mais restritiva para promessas associadas a URLs, uso do limite configurável de classificação, persistência síncrona do cache e retorno de falhas parciais para novas tentativas do SQS.

Os outros três códigos implantados não possuíam representação completa no repositório:

- `Guardinia-Ingestor`
- `sentinela_web_analisador`
- `sentinela_whatsapp_webhook`

## Arquitetura e documentação

| Tema | Repositório público | Ambiente observado |
|---|---|---|
| Entrada canônica do WhatsApp | Uma Lambda síncrona | API legada → Ingestor → SQS → Processor |
| Cache | Tabela `guardinia_cache` documentada | Tabela ausente no inventário DynamoDB |
| Índices de auditoria | Dois GSIs documentados | Nenhum índice observado |
| Retenção do log de auditoria | 90 dias documentados | Código implantado configurado para 7 dias |
| Logs de acesso da API | Indicados como ativos | Não configurados nos estágios observados |
| Backup do DynamoDB | Não detalhado | Zero backups e PITR desativado |
| Proteção contra exclusão | Não detalhada | Desativada nas tabelas observadas |
| Infraestrutura como código | Terraform descrito como opcional | Nenhum estado completo da infraestrutura versionado |

## Decisão de preservação

Este snapshot é aditivo. Ele não substitui `src/lambda_handler.py`, não altera a arquitetura implantada e não oferece um modelo automático de deploy. A reconciliação do código canônico deverá ocorrer em uma etapa posterior, depois da preservação e da revisão dos quatro arquivos completos.

Os modelos SAM exportados foram excluídos porque continham configurações sensíveis e divergiam do estado final observado em rotas e concorrência. As informações não secretas necessárias para auditoria foram registradas nos arquivos `snapshot.json`.

