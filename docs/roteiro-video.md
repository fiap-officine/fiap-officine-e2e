# Guia de gravação do vídeo — Tech Challenge Fase 4

Para quem vai gravar o vídeo. O ambiente já está no ar e foi testado de ponta a
ponta (inclusive com pagamento real no sandbox do Mercado Pago). Este guia diz
**o que você precisa**, **como preparar** e **o que mostrar em cada cena**.

---

## 1. O que o vídeo precisa mostrar (enunciado)

- Até **15 minutos**, no **YouTube ou Vimeo** (público ou não listado).
- **Fluxo completo de uma OS** passando pelos microsserviços.
- **Saga Pattern** em execução e **tratamento de falhas** (compensação).
- **Deploy automatizado** de pelo menos um microsserviço com validação de testes.
- **Monitoramento e rastreamento** dos fluxos distribuídos.

Dica: grave cada bloco separado e edite depois.

---

## 2. O projeto em dois minutos

O monólito da Fase 3 virou **três microsserviços**, cada um com repositório,
pipeline, Terraform e banco próprios:

| Serviço | Faz | Banco |
|---|---|---|
| **OS Service** (`fiap-officine-os-service`, era o `fiap-officine-api`) | clientes, veículos, catálogo, OS e **orquestração da saga** | PostgreSQL `os_db` |
| **Billing** (`fiap-officine-billing-service`) | orçamento, aprovação, **Mercado Pago** (Checkout Pro), estorno | PostgreSQL `billing_db` |
| **Execution** (`fiap-officine-execution-service`) | estoque, reserva de peças, fila de execução, ações do mecânico | **DynamoDB** |

- Entre os serviços só há **mensageria (Amazon SQS)**; REST só na borda (API
  Gateway → Traefik). A Lambda de login por CPF consulta o OS Service por REST.
- **Saga orquestrada** no OS Service: abre OS → gera orçamento → cliente aprova →
  pagamento → reserva de peças → execução → finaliza. Se algo falha antes do
  reparo começar, ele compensa em ordem inversa (libera reserva → estorna o
  pagamento → cancela o orçamento → cancela a OS).
- **Ambiente (homolog):** AWS **us-east-2 (Ohio)**, conta do Alex. Um nó K3s
  (EC2 `t3.small`, IP fixo), RDS PostgreSQL 16, DynamoDB, SQS, API Gateway +
  Lambda, ECR. New Relic na conta **8505579** (a mesma da Fase 3).
- O PDF da entrega (`docs/entrega/relatorio-fase4.pdf`) tem o diagrama geral,
  bom para a abertura.

| Endereço | Para quê |
|---|---|
| `https://xppl1n6lwl.execute-api.us-east-2.amazonaws.com` | entrada única (API Gateway) — chamada de `<API>` abaixo |
| `<API>/docs`, `<API>/billing/docs`, `<API>/execution/docs` | Swagger dos três serviços |
| https://sonarcloud.io/organizations/fiap-officine/projects | qualidade (público, sem login) |
| https://github.com/fiap-officine | repositórios e Actions |

---

## 3. Acessos que você precisa (peça ao Alex)

| Acesso | Para quê | Como |
|---|---|---|
| Organização `fiap-officine` no GitHub | cena de CI/CD (PR, checks, merge, Actions) | você já é membro; o merge exige 1 aprovação: peça para o Alex aprovar o seu PR (ou use o bypass de admin, se tiver) |
| **Usuário IAM na AWS** (`pedro-video`, só linha de comando) | ligar/parar a instância, pegar o kubeconfig, ver a fila do SQS (cena de resiliência) | o Alex passa a chave de acesso em particular. Permissões: `ReadOnlyAccess` + ligar/parar a instância do projeto. Configure com `aws configure` (região **us-east-2**, saída `json`) |
| **kubeconfig** do cluster | comandos `kubectl` (cena de resiliência e CI/CD) | `aws ssm get-parameter --name /fiap-officine/homolog/k3s/kubeconfig --with-decryption --query Parameter.Value --output text > kubeconfig.yaml`. É acesso de admin ao cluster: não comite nem compartilhe |
| **Conta Comprador de teste** do Mercado Pago | pagar no checkout (sandbox) | o login pede confirmação (MFA) na conta do Alex: **combine o horário com ele** antes de pagar (ensaio e gravação) para ele aprovar na hora |
| New Relic | cena de observabilidade | você já tem acesso à conta 8505579 |
| SonarCloud | mostrar cobertura e Quality Gate | projetos públicos, não precisa de login |

Instale também a **AWS CLI**, o **kubectl** e o **Postman**, e tenha **Python 3.12** para o ensaio automático.

---

## 4. Véspera da gravação (checklist)

1. **Ligar o ambiente** (fica parado para economizar). Se o banco também tiver
   sido parado, peça ao Alex para iniciar o RDS `fiap-officine-homolog-rds` antes.
   ```bash
   ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=fiap-officine-homolog-k3s-server"         --query 'Reservations[].Instances[].InstanceId' --output text)
   aws ec2 start-instances --instance-ids $ID
   aws ec2 wait instance-running --instance-ids $ID   # depois aguarde mais 3 min para o K3s subir
   ```
   O endereço do API Gateway não muda.
2. **Serviços no ar.** Abra no navegador: `<API>/health`,
   `<API>/billing/health` e `<API>/execution/health` → todos com `"status":"healthy"`.
3. **kubectl.**
   ```bash
   export KUBECONFIG=$PWD/kubeconfig.yaml      # PowerShell: $env:KUBECONFIG="$PWD\kubeconfig.yaml"
   kubectl -n officine get pods                # os-service, billing-service, execution-service em Running 1/1
   ```
4. **Ensaio automático** (clone o `fiap-officine-e2e`):
   ```bash
   python scripts/e2e_saga.py --os <API> --billing <API> --execution <API> --pagamento manual --cenario feliz
   ```
   O script mostra o link do checkout; pague (ver item 6) e ele conclui a saga até
   a entrega (`E2E OK ✅`). **Ensaie também a compensação** (`--cenario compensacao`):
   ela nunca rodou no cluster com Mercado Pago real, então é bom ver o estorno
   funcionando antes de gravar.
5. **Postman.** Importe `postman/fiap-officine-saga-e2e.postman_collection.json`.
   As variáveis já apontam para o API Gateway. Rode a pasta **0. Preparação** uma
   vez (cria operador, cliente, veículo, serviço, peça e **5 unidades** em
   estoque). Se rodar de novo, troque as variáveis `cpf` (ex.: `39053344705`) e
   `placa` (ex.: `DEM0002`) para não dar "já cadastrado". "Registrar operador"
   pode responder erro se o usuário já existir — tudo bem, o login funciona.
6. **Pagamento no sandbox:** abra o link do checkout numa **janela anônima**,
   entre com a conta Comprador de teste e pague com **saldo em conta** (foi o que
   funcionou no ensaio). Cartões salvos pedem o código de segurança `123`.
   **Pague em até 5 minutos** depois de aprovar o orçamento: depois disso a saga
   cancela a OS por timeout (e estorna se o pagamento chegar atrasado).
7. **Abas abertas:** Swagger, Postman, SonarCloud, GitHub (repositório +
   *Actions* + *Settings → Rules*), New Relic (*APM & Services*, *Distributed
   tracing*, *Logs*, *Dashboards* → "fiap-officine — Saga de OS", *Alerts*) e um
   terminal com `KUBECONFIG` e a AWS CLI configurados.
8. **PR pronto para a cena de CI/CD:** um branch com uma mudança pequena (por
   exemplo, uma linha no README do `fiap-officine-billing-service`) e o PR aberto
   para `develop`, ainda sem merge.

---

## 5. Roteiro cena a cena

| Tempo | Cena |
|---|---|
| 0:00–1:00 | Abertura e arquitetura |
| 1:00–4:30 | Fluxo feliz completo |
| 4:30–8:00 | Falhas e compensação |
| 8:00–11:00 | CI/CD com deploy automatizado |
| 11:00–14:00 | Observabilidade (New Relic) |
| 14:00–15:00 | Encerramento |

### 0:00–1:00 — Abertura e arquitetura

**Mostrar:** o diagrama da seção 2 do PDF.

**Falar:** três microsserviços com repositório, pipeline, infraestrutura e banco
próprios (PostgreSQL no OS e no Billing, DynamoDB no Execution); REST na borda e
SQS entre os serviços; nenhum serviço acessa o banco do outro; saga
**orquestrada** no OS Service, com compensação.

### 1:00–4:30 — Fluxo feliz (Postman, pasta **1. Caminho feliz**)

| Passo | Requisição | O que destacar |
|---|---|---|
| 1 | **1. Abrir OS (inicia a saga)** | 201, status `aguardando_orcamento` |
| 2 | **2. Consultar saga** | estado `APPROVAL_PENDING`, comando `GerarOrcamento` enviado e `OrcamentoGerado` recebido |
| 3 | **3. Orçamento gerado (Billing)** | o Billing criou o orçamento a partir da mensagem |
| 4 | **4. Cliente aprova o orçamento** | aprovação com o **token do cliente** (login por CPF) |
| 5 | **5. Cobrança Mercado Pago** | copie o `checkout_url` |
| 6 | **Navegador (janela anônima):** pagar com a conta Comprador de teste (saldo em conta) | o Mercado Pago confirma pelo **webhook** (assinatura `x-signature` validada e pagamento reconsultado na API) |
| 7 | **7. OS aguardando execução** | `aguardando_execucao` |
| 8 | **8. Fila de execução** | OS na fila do Execution, peças reservadas no DynamoDB |
| 9–11 | **9. Mecânico inicia diagnóstico**, **10. Mecânico inicia reparo (pivô)**, **11. Mecânico finaliza** | cada ação vira evento para o orquestrador |
| 12 | **12. OS finalizada + saga COMPLETED** | mostre a **linha do tempo** em `steps` |
| 13 | **13. Entregar veículo** | `entregue` |

> **Pule a requisição 6. Simular pagamento**: ela só funciona com o gateway fake
> do ambiente local.

Opcional (requisito da Fase 3): login do cliente pela **Lambda** —
`POST <API>/auth/login` com `{"cpf": "<cpf da Preparação>"}` devolve o JWT.

**Falar:** cada passo é um comando numa fila e uma resposta na fila
`os-saga-replies`; tudo passa pelo **Transactional Outbox** e os consumidores são
**idempotentes** (mensagem repetida não gera efeito duplicado).

### 4:30–8:00 — Falhas e compensação

**(a) Estoque insuficiente depois do pagamento** (pasta **2. Falha: estoque insuficiente**)

1. **A. Abrir OS com 10 pastilhas** (sobraram 3 em estoque após o fluxo feliz).
2. **B. Orçamento** → **C. Aprovar** → **D. Cobrança** → pague o `checkout_url`
   no sandbox. Pule **E. Pagar (fake)**.
3. **F. Saga compensada**: em `steps`, `ReservaFalhou` → `EstornarPagamento` →
   `PagamentoEstornado` → `CancelarOrcamento` → saga `CANCELLED`, OS `cancelada`.
4. **G. Pagamento estornado**: status `estornado`.

**Falar:** a compensação roda em **ordem inversa** e cada passo é confirmado antes
do próximo; se uma compensação falhar, ela é repetida e, ao esgotar as
tentativas, a saga vai para `FAILED` e dispara alerta.

**(b) Orçamento recusado** (pasta **3. Falha: orçamento recusado**):
**R1** → **R2** → **R3. Cliente recusa** → **R4. OS cancelada**.

**(c) Resiliência da mensageria**

```bash
kubectl -n officine scale deploy/billing-service --replicas=0
```

1. **1. Abrir OS** e **2. Consultar saga**: a saga fica parada em `BUDGET_PENDING`.
2. Mostre o comando esperando na fila (`ApproximateNumberOfMessages` = 1):
   ```bash
   aws sqs get-queue-attributes --attribute-names ApproximateNumberOfMessages      --queue-url $(aws sqs get-queue-url --queue-name fiap-officine-homolog-billing-commands --query QueueUrl --output text)
   ```
3. Volte a réplica e consulte a saga de novo: ela continua sozinha.

```bash
kubectl -n officine scale deploy/billing-service --replicas=1
kubectl -n officine rollout status deploy/billing-service
```

**(d) Extras, se sobrar tempo:** depois de **10. Mecânico inicia reparo (pivô)**,
`POST <API>/api/v1/ordens-servico/{id}/cancelar` responde **409** (ponto sem
volta). Timeout: aprovar e não pagar → em ~5 min a saga cancela (corte a espera).

### 8:00–11:00 — CI/CD

1. Abra o PR preparado: checks **test** (lint, testes, cobertura ≥ 80%) e
   **quality** (SonarCloud Quality Gate) — e o comentário do SonarCloud no PR.
2. *Settings → Rules*: ruleset `fase4-protecao-main-develop` (PR obrigatório,
   aprovação, checks exigidos, sem push direto).
3. Merge (com a aprovação do Alex) → aba **Actions** → workflow **CI/CD** em
   `develop`: `test` → `quality` → `build-push` (imagem no ECR com tag = SHA do
   commit) → `deploy` (bootstrap do banco, `kustomize`, `rollout status`, smoke test).
4. Terminal:
   ```bash
   kubectl -n officine get deploy billing-service -o jsonpath='{.spec.template.spec.containers[0].image}'
   kubectl -n officine rollout history deploy/billing-service
   ```
5. SonarCloud: projeto do serviço com cobertura (≈ 93–95%) e Quality Gate aprovado.

**Falar:** pipeline independente por serviço; nada vai para o cluster sem passar
nos testes, na cobertura mínima e no Quality Gate; credenciais vêm de GitHub
Secrets e do SSM, nunca do código.

### 11:00–14:00 — Observabilidade (New Relic)

1. **APM & Services**: `officine-os-service`, `officine-billing-service` e
   `officine-execution-service` (ignore `fiap-officine-api-homolog`, que é o
   monólito da Fase 3) e o **Service Map**.
2. **Distributed tracing**: o trace de uma OS atravessando OS → SQS → Billing →
   SQS → OS → Execution.
3. **Logs**: busque `context.saga_id:"<saga_id>"` (o id está em **2. Consultar
   saga**) e mostre os logs dos três serviços juntos.
4. **Dashboards → "fiap-officine — Saga de OS"**: sagas iniciadas/concluídas/
   canceladas, funil, tempo por passo, compensações por motivo.
5. **Alerts**: política "fiap-officine — Saga de OS" (saga `FAILED`, DLQ,
   falhas no consumer, latência p95, taxa de erro, webhook rejeitado).

### 14:00–15:00 — Encerramento

Recapitule (3 microsserviços, saga orquestrada com compensação, SQS + outbox +
idempotência, SQL + NoSQL, Mercado Pago, testes ≥ 80% com BDD, SonarCloud, CI/CD
independente com deploy no Kubernetes, observabilidade distribuída) e mostre os
links dos repositórios (seção 1 do PDF).

---

## 6. Depois de gravar

1. Publique no YouTube ou Vimeo (público ou **não listado**).
2. Mande o link para o Alex, ou coloque você mesmo no PDF: em
   `docs/entrega/relatorio-fase4.html`, troque `[LINK DO VÍDEO …]` pelo link e
   rode `powershell -ExecutionPolicy Bypass -File docs/entrega/gerar-pdf.ps1`
   (abra um PR com o PDF novo).
3. **Pare a instância** para economizar os créditos da conta: `aws ec2 stop-instances --instance-ids $ID`.

---

## 7. Se algo der errado

| Sintoma | O que fazer |
|---|---|
| Health retorna 503 ou não responde | instância parada ou ainda subindo: `aws ec2 describe-instances --instance-ids $ID --query 'Reservations[].Instances[].State.Name'` e aguarde 3–5 min após ligar |
| Botão **Pagar** desabilitado ou "A transação não aceita este meio de pagamento" | use **saldo em conta**, em janela anônima nova, logado na conta Comprador de teste |
| Saga cancelada sozinha depois de aprovar | passou de 5 min sem pagamento (timeout); abra outra OS |
| Saga parada em `PAYMENT_PENDING` depois de pagar | o reconciliador consulta o Mercado Pago a cada 1 min; espere um pouco |
| `401` nas chamadas | token expirado: refaça **Login operador** / **Login do cliente** |
| "Criar cliente" ou "Criar veículo" falha | já existe: troque as variáveis `cpf` e `placa` e rode a Preparação de novo |
| Pod com erro | `kubectl -n officine describe pod <pod>` e `kubectl -n officine logs deploy/<serviço>` |
| Saga não avança | `<API>/health` mostra o status do banco, do SQS e do outbox |
