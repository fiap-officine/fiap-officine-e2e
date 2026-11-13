# Roteiro do vídeo — Tech Challenge Fase 4 (até 15 min)

Para quem vai gravar. Cada bloco diz **o que mostrar**, **onde clicar/rodar** e
**o que falar**. Grave bloco a bloco e edite depois; os tempos são a meta.

---

## Véspera da gravação (checklist)

- [ ] Os 3 serviços no ar em homolog: `kubectl -n officine get pods` com
      `os-service`, `billing-service` e `execution-service` em `Running 1/1`.
- [ ] O namespace antigo da Fase 3 (`posfiap`) removido do cluster.
- [ ] `GET <API>/health`, `GET <API>/billing/health` e `GET <API>/execution/health`
      respondendo `healthy` (`<API>` = URL do API Gateway de homolog).
- [ ] Postman: importar `postman/fiap-officine-saga-e2e.postman_collection.json`
      e, nas variáveis da collection, colocar a URL do API Gateway em
      `os_url`, `billing_url` e `execution_url`.
- [ ] Rodar a pasta **0. Preparação** uma vez (cria operador, cliente, veículo,
      serviço, peça e **5 unidades** em estoque). Anotar o CPF do cliente.
- [ ] Mercado Pago sandbox: ter em mãos o **usuário comprador de teste** e um
      cartão de teste (ex.: Mastercard `5031 4332 1540 6351`, CVV `123`,
      validade `11/30`, titular **`APRO`** = aprovado).
- [ ] New Relic: abrir em abas o **Service Map**, o **Distributed Tracing**, o
      dashboard **"fiap-officine — Saga de OS"**, os **Logs** e a política de
      alertas **"fiap-officine — Saga de OS"**.
- [ ] GitHub: um PR pequeno já preparado em um dos serviços (ex.: texto do
      README) para o bloco de CI/CD.
- [ ] Terminal com `kubectl` apontando para o cluster de homolog.

> Dica: homolog usa `SAGA_PAYMENT_TIMEOUT_SECONDS=120` e
> `PAYMENT_EXPIRATION_MINUTES=5`, então dá para mostrar o timeout sem esperar muito.

---

## 0:00–1:00 — Abertura e arquitetura

**Mostrar:** o diagrama geral (README do os-service ou do PDF).

**Falar:**
- Três microsserviços, cada um com repositório, pipeline, infraestrutura e banco
  próprios: **OS Service** (orquestrador da saga, PostgreSQL `os_db`),
  **Billing** (orçamentos e Mercado Pago, PostgreSQL `billing_db`) e
  **Execution** (fila de execução e estoque, **DynamoDB**).
- Comunicação: REST para o cliente/operador e **SQS** entre os serviços;
  nenhum serviço acessa o banco do outro (inclusive a Lambda de autenticação).
- **Saga orquestrada**: o OS Service conduz os passos e dispara as compensações.

---

## 1:00–4:30 — Fluxo feliz (pasta **1. Caminho feliz**)

| Passo | Requisição no Postman | O que destacar |
|---|---|---|
| 1 | **1. Abrir OS (inicia a saga)** | resposta 201 com status `aguardando_orcamento` |
| 2 | **2. Consultar saga** | estado `BUDGET_PENDING` → `APPROVAL_PENDING` e o primeiro comando `GerarOrcamento` |
| 3 | **3. Orçamento gerado (Billing)** | orçamento criado pelo Billing a partir da mensagem |
| 4 | **4. Cliente aprova o orçamento** | aprovação com o **JWT do cliente** (login por CPF via Lambda) |
| 5 | **5. Cobrança Mercado Pago** | copiar o `checkout_url` |
| 6 | **Navegador:** abrir o `checkout_url` e pagar com o comprador e o cartão de teste | o Mercado Pago chama o webhook (assinatura `x-signature` validada) |
| 7 | **7. OS aguardando execução** | status `aguardando_execucao` |
| 8 | **8. Fila de execução** | OS na fila priorizada do Execution, peças reservadas |
| 9–11 | **9. iniciar-diagnostico**, **10. iniciar-reparo**, **11. finalizar** | o mecânico avança a OS; cada ação vira evento para o orquestrador |
| 12 | **12. OS finalizada + saga COMPLETED** | mostrar a **linha do tempo** em `steps` |
| 13 | **13. Entregar veículo** | status `entregue` |

> Pule a requisição **6. Simular pagamento** (ela só funciona com o gateway
> fake, usado no ambiente local).

**Falar:** cada passo é um comando numa fila e uma resposta na fila
`os-saga-replies`; tudo passa pelo **Transactional Outbox** e os consumers são
**idempotentes** (mensagem repetida não gera efeito duplicado).

---

## 4:30–8:00 — Falhas e compensação

### (a) Estoque insuficiente depois do pagamento (pasta **2. Falha: estoque insuficiente**)

1. **A. Abrir OS com 10 pastilhas** (o estoque tem 5).
2. **B. Orçamento** → **C. Aprovar** → **D. Cobrança** → pagar o `checkout_url`
   no sandbox (como no fluxo feliz).
3. **F. Saga compensada**: mostrar em `steps` a sequência
   `ReservaFalhou` → `EstornarPagamento` → `PagamentoEstornado` →
   `CancelarOrcamento` → saga `CANCELLED`, OS `cancelada`.
4. **G. Pagamento estornado**: status `estornado`. Opcional: mostrar o estorno no
   painel do Mercado Pago.

**Falar:** a compensação roda em **ordem inversa** e cada passo é confirmado
antes do próximo; se uma compensação falhar, ela é repetida e, ao esgotar as
tentativas, a saga vai para `FAILED` e dispara alerta.

### (b) Orçamento recusado (pasta **3. Falha: orçamento recusado**)

**R1** → **R2** → **R3. Cliente recusa** → **R4. OS cancelada**.

### (c) Resiliência da mensageria

```bash
kubectl -n officine scale deploy/billing-service --replicas=0
```

1. Abrir uma OS (**1. Abrir OS**). Em **2. Consultar saga**, ela fica parada em
   `BUDGET_PENDING`.
2. Mostrar a mensagem esperando na fila (console AWS → SQS →
   `fiap-officine-homolog-billing-commands` → *Mensagens disponíveis* = 1).
3. Voltar a réplica e consultar a saga de novo: ela continua sozinha.

```bash
kubectl -n officine scale deploy/billing-service --replicas=1
kubectl -n officine rollout status deploy/billing-service
```

### (d) Extras, se sobrar tempo

- **Timeout de pagamento:** aprovar um orçamento e não pagar; em ~2 min a saga
  compensa (`CancelarOrcamento`) e a OS é cancelada.
- **Ponto sem volta:** depois de **10. iniciar-reparo**,
  `POST /api/v1/ordens-servico/{id}/cancelar` responde **409**.

---

## 8:00–11:00 — CI/CD

1. No GitHub, abrir o PR preparado para `develop` e mostrar os checks
   **test** (lint + testes + cobertura ≥ 80%) e **quality** (SonarCloud
   Quality Gate).
2. Mostrar a regra de proteção da branch (*Settings → Rules*): PR obrigatório e
   checks exigidos.
3. Fazer o merge e abrir a aba **Actions**: `build-push` publica a imagem no ECR
   com a **tag = SHA do commit**; `deploy` roda o bootstrap do banco,
   `kustomize edit set image`, `rollout status` e o smoke test.
4. No terminal, mostrar a nova versão rodando:

```bash
kubectl -n officine get deploy os-service -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n officine rollout history deploy/os-service
```

5. SonarCloud: abrir o projeto e mostrar cobertura e Quality Gate.

**Falar:** cada serviço tem pipeline independente; nada vai para o cluster sem
passar nos testes, na cobertura mínima e no Quality Gate.

---

## 11:00–14:00 — Observabilidade (New Relic)

1. **Service Map**: os três serviços (`officine-os-service`,
   `officine-billing-service`, `officine-execution-service`) e as dependências.
2. **Distributed Tracing**: abrir o trace da abertura de uma OS e mostrar o
   mesmo trace atravessando OS → SQS → Billing → SQS → OS.
3. **Logs**: buscar `context.saga_id:"<saga_id do fluxo feliz>"` (o id está em
   **2. Consultar saga**) e mostrar os logs dos três serviços juntos.
4. **Dashboard "fiap-officine — Saga de OS"**: sagas iniciadas/concluídas/
   canceladas, funil, tempo médio por passo, compensações por motivo.
5. **Alertas**: mostrar a política (saga `FAILED`, mensagens na DLQ, latência
   p95, taxa de erro, webhook rejeitado) e, se houver, o incidente aberto
   durante os testes de falha.

---

## 14:00–15:00 — Encerramento

- Recapitular: 3 microsserviços, saga orquestrada com compensação, SQS +
  outbox + idempotência, SQL + NoSQL, Mercado Pago, testes ≥ 80% com BDD,
  SonarCloud, CI/CD independente com deploy no Kubernetes e observabilidade
  distribuída.
- Mostrar os links dos 7 repositórios (README do os-service ou do PDF).

---

## Se algo der errado na hora

| Sintoma | O que fazer |
|---|---|
| Saga parada em `PAYMENT_PENDING` depois de pagar | o webhook não chegou; o reconciliador consulta o Mercado Pago a cada minuto. Esperar ~1 min ou conferir o `MP_NOTIFICATION_URL` |
| Pod em `CrashLoopBackOff` | `kubectl -n officine logs deploy/<serviço> --previous` |
| `401` nas rotas do Billing/Execution | token expirado: refazer **Login operador** / **Login do cliente** |
| Saga não avança | `GET <API>/health` mostra `outbox.pending` e o status do SQS |
