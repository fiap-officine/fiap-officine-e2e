"""Roteiro E2E da saga contra os 3 serviços rodando (docker compose ou cluster).

Cenário 1 — caminho feliz: OS -> orçamento -> aprovação -> pagamento ->
reserva -> diagnóstico -> reparo -> finalização -> entrega.
Cenário 2 — compensação: estoque insuficiente após o pagamento -> estorno ->
cancelamento do orçamento -> OS cancelada.

Uso: python scripts/e2e_saga.py [--os http://localhost:8000]
     [--billing http://localhost:8001] [--execution http://localhost:8002]
Requer apenas a biblioteca padrão do Python.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class Api:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/")
        self.token = token

    def call(self, method: str, path: str, body=None, form=None, expected=(200, 201)):
        headers = {"Accept": "application/json"}
        data = None
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                status, payload = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, payload = exc.code, exc.read()
        parsed = json.loads(payload) if payload else None
        if status not in expected:
            raise AssertionError(f"{method} {path} -> {status}: {parsed}")
        return parsed


def esperar(descricao: str, func, timeout: float = 60.0):
    inicio = time.time()
    ultimo = None
    while time.time() - inicio < timeout:
        ultimo = func()
        if ultimo:
            print(f"  ✔ {descricao} ({time.time() - inicio:.1f}s)")
            return ultimo
        time.sleep(1)
    raise AssertionError(f"Timeout aguardando: {descricao} (último: {ultimo})")


def status_os(os_api: Api, os_id: int) -> str:
    return os_api.call("GET", f"/api/v1/ordens-servico/{os_id}")["status"]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows
    parser = argparse.ArgumentParser()
    parser.add_argument("--os", default="http://localhost:8000")
    parser.add_argument("--billing", default="http://localhost:8001")
    parser.add_argument("--execution", default="http://localhost:8002")
    args = parser.parse_args()

    sufixo = uuid.uuid4().hex[:6]
    publico = Api(args.os)
    usuario = f"operador_{sufixo}"
    publico.call("POST", "/api/v1/auth/register", {
        "username": usuario, "email": f"{usuario}@oficina.com",
        "nome_completo": "Operador E2E", "password": "senha12345",
    })
    token = publico.call("POST", "/api/v1/auth/login",
                         form={"username": usuario, "password": "senha12345"})["access_token"]
    os_api, billing, execution = Api(args.os, token), Api(args.billing, token), Api(args.execution, token)

    print("== Cadastros")
    cpf = "52998224725"
    clientes = os_api.call("GET", "/api/v1/clientes/?limit=200")
    cliente = next((c for c in clientes if c["cpf_cnpj"] == cpf), None) or os_api.call(
        "POST", "/api/v1/clientes/",
        {"nome": "Maria E2E", "cpf_cnpj": cpf, "email": "maria@e2e.com"})
    veiculo = os_api.call("POST", "/api/v1/veiculos/", {
        "cliente_id": cliente["id"], "placa": f"TST{int(sufixo, 16) % 10000:04d}",
        "marca": "VW", "modelo": "Gol", "ano": 2019})
    servico = os_api.call("POST", "/api/v1/servicos/", {
        "nome": f"Troca de pastilhas {sufixo}", "preco": 120.0, "tempo_estimado_minutos": 60})
    peca = os_api.call("POST", "/api/v1/pecas/", {"nome": f"Pastilha {sufixo}", "preco": 80.0})
    execution.call("PUT", f"/api/v1/estoque/{peca['id']}",
                   {"quantidade_entrada": 5, "estoque_minimo": 1, "nome": peca["nome"]})
    token_cliente = publico.call("POST", "/api/v1/auth/cliente", {"cpf": cpf})["access_token"]
    billing_cliente = Api(args.billing, token_cliente)

    def abrir_os(qtd: int) -> int:
        return os_api.call("POST", "/api/v1/ordens-servico/", {
            "cliente_id": cliente["id"], "veiculo_id": veiculo["id"],
            "itens_servico": [{"servico_id": servico["id"], "quantidade": 1}],
            "itens_peca": [{"peca_id": peca["id"], "quantidade": qtd}],
        })["id"]

    def aprovar_e_pagar(os_id: int) -> None:
        orcamento = esperar("orçamento gerado pelo Billing", lambda: next(
            iter(billing.call("GET", f"/api/v1/orcamentos/?os_id={os_id}")), None))
        esperar("OS aguardando aprovação", lambda: status_os(os_api, os_id) == "aguardando_aprovacao")
        billing_cliente.call("POST", f"/api/v1/orcamentos/{orcamento['id']}/aprovar")
        print(f"  ✔ cliente aprovou o orçamento #{orcamento['id']} (R$ {orcamento['valor_total']})")
        pagamento = esperar("cobrança criada no gateway", lambda: next(
            iter(billing.call("GET", f"/api/v1/pagamentos/?orcamento_id={orcamento['id']}")), None))
        billing.call("POST", f"/api/v1/pagamentos/{pagamento['id']}/simular", {"status": "approved"})
        print(f"  ✔ pagamento #{pagamento['id']} aprovado (gateway fake / webhook simulado)")

    print("== Cenário 1: caminho feliz")
    os_id = abrir_os(2)
    aprovar_e_pagar(os_id)
    esperar("OS aguardando execução", lambda: status_os(os_api, os_id) == "aguardando_execucao")
    esperar("saga IN_EXECUTION", lambda: os_api.call(
        "GET", f"/api/v1/ordens-servico/{os_id}/saga")["state"] == "IN_EXECUTION")
    for acao in ("iniciar-diagnostico", "iniciar-reparo", "finalizar"):
        execution.call("POST", f"/api/v1/execucoes/{os_id}/{acao}", {"observacao": f"E2E {acao}"})
        print(f"  ✔ mecânico: {acao}")
    esperar("OS finalizada", lambda: status_os(os_api, os_id) == "finalizada")
    saga = os_api.call("GET", f"/api/v1/ordens-servico/{os_id}/saga")
    assert saga["state"] == "COMPLETED", saga
    os_api.call("POST", f"/api/v1/ordens-servico/{os_id}/entregar", {"observacao": "Retirado"})
    assert status_os(os_api, os_id) == "entregue"
    estoque = execution.call("GET", f"/api/v1/estoque/{peca['id']}")
    assert (estoque["disponivel"], estoque["reservada"]) == (3, 0), estoque
    print(f"  ✔ OS #{os_id} entregue; saga COMPLETED; estoque {estoque['disponivel']} disponíveis")

    print("== Cenário 2: estoque insuficiente -> estorno -> cancelamento")
    os_id = abrir_os(10)
    aprovar_e_pagar(os_id)
    esperar("OS cancelada pela compensação", lambda: status_os(os_api, os_id) == "cancelada", 90)
    saga = os_api.call("GET", f"/api/v1/ordens-servico/{os_id}/saga")
    tipos = [s["message_type"] for s in saga["steps"] if s["message_type"]]
    assert saga["state"] == "CANCELLED", saga
    assert "ReservaFalhou" in tipos and "EstornarPagamento" in tipos and "CancelarOrcamento" in tipos, tipos
    pagamentos = billing.call("GET", f"/api/v1/pagamentos/?orcamento_id={saga['orcamento_id']}")
    assert pagamentos[-1]["status"] == "estornado", pagamentos
    print(f"  ✔ OS #{os_id} cancelada; pagamento estornado; motivo: {saga['failure_reason']}")
    print("\nE2E OK ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
