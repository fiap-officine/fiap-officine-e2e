# fiap-officine-e2e

Ambiente e roteiro **ponta a ponta** da saga da Ordem de Serviço entre os três
microsserviços do Tech Challenge SOAT — Fase 4.

| Serviço | Porta local | Banco |
|---|---|---|
| [os-service](https://github.com/fiap-officine/fiap-officine-os-service) (orquestrador) | 8000 | PostgreSQL `os_db` |
| [billing-service](https://github.com/fiap-officine/fiap-officine-billing-service) | 8001 | PostgreSQL `billing_db` |
| [execution-service](https://github.com/fiap-officine/fiap-officine-execution-service) | 8002 | DynamoDB (LocalStack) |
| LocalStack (SQS + DynamoDB) | 4566 | — |

## Subindo

Clone os repositórios lado a lado e:

```bash
docker compose up -d --build
docker compose ps        # aguarde os 3 serviços "running"
```

As filas (`billing-commands`, `execution-commands`, `os-saga-replies` e suas
DLQs) são criadas por [scripts/localstack-init.sh](scripts/localstack-init.sh);
os dois bancos lógicos, com usuários próprios, por
[scripts/postgres-init.sql](scripts/postgres-init.sql).

Por padrão o Billing usa `PAYMENT_GATEWAY=fake`. Para o **sandbox real do
Mercado Pago**: `PAYMENT_GATEWAY=mercadopago MP_ACCESS_TOKEN=TEST-... MP_WEBHOOK_SECRET=... docker compose up -d`
(o webhook precisa de URL pública — use o ambiente de homolog ou um túnel).

## Roteiro automatizado

```bash
python scripts/e2e_saga.py
```

1. **Caminho feliz**: abre OS → orçamento gerado → cliente aprova → pagamento →
   reserva de estoque e fila → diagnóstico → reparo → finalização → entrega.
   Verifica saga `COMPLETED` e baixa de estoque.
2. **Compensação**: OS com mais peças que o estoque → após o pagamento o
   Execution responde `ReservaFalhou` → `EstornarPagamento` →
   `CancelarOrcamento` → OS `cancelada`, pagamento `estornado`.

Para rodar contra o cluster: `python scripts/e2e_saga.py --os https://<api> --billing https://<api> --execution https://<api>`.

## Postman

[postman/fiap-officine-saga-e2e.postman_collection.json](postman/fiap-officine-saga-e2e.postman_collection.json):
pastas *Preparação*, *Caminho feliz*, *Falha: estoque insuficiente → estorno* e
*Falha: orçamento recusado*. Rode no Runner com **delay de 2000 ms** (a saga é
assíncrona). Variáveis `os_url`, `billing_url`, `execution_url` apontam para
localhost; em AWS, use a URL do API Gateway nas três.

## Demonstrações para o vídeo

| Cena | Como provocar |
|---|---|
| Compensação por estoque | OS com quantidade maior que o saldo em `PUT /api/v1/estoque/{peca_id}` |
| Orçamento recusado | `POST /api/v1/orcamentos/{id}/recusar` |
| Timeout de pagamento | aprovar e não pagar; homolog usa `SAGA_PAYMENT_TIMEOUT_SECONDS=120` |
| Resiliência da mensageria | `kubectl -n officine scale deploy/billing-service --replicas=0`, abrir OS, mostrar a mensagem parada na fila, voltar a réplica e ver a saga continuar |
| Pivô | após `iniciar-reparo`, `POST /ordens-servico/{id}/cancelar` responde 409 |
| Linha do tempo | `GET /api/v1/ordens-servico/{id}/saga` |
