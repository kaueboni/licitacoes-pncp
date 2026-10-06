"""Testes do servidor MCP com respostas simuladas da API do PNCP (sem rede)."""
import io
import sys
import zipfile
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/licitacoes-pncp/server"))


def _pdf(linhas):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i, linha in enumerate(linhas):
        c.drawString(50, 800 - 15 * i, linha)
    c.showPage()
    c.save()
    return buf.getvalue()


EDITAL = _pdf(["EDITAL PREGAO ELETRONICO 033/2026", "Objeto: aquisicao de generos alimenticios",
               "8.4 Habilitação técnica: atestado de capacidade técnica de 50%"])
_zip = io.BytesIO()
with zipfile.ZipFile(_zip, "w") as zf:
    zf.writestr("Anexos/TR.pdf", _pdf(["TERMO DE REFERENCIA", "Prazo de entrega: 5 dias uteis apos a ordem"]))
    zf.writestr("planilha.xlsx", b"PK..")
ANEXOS = _zip.getvalue()

SEARCH = {"total": 1, "items": [{
    "title": "Edital nº 00009826/2026", "description": "Merenda escolar",
    "orgao_cnpj": "111", "ano": "2026", "numero_sequencial": "30",
    "orgao_nome": "Prefeitura X", "municipio_nome": "Y", "uf": "MG",
    "modalidade_licitacao_nome": "Pregão - Eletrônico", "situacao_nome": "Divulgada no PNCP",
    "valor_total_estimado": 1004139.25, "srp": True, "data_publicacao_pncp": "2026-10-05T16:13:39",
    "data_fim_vigencia": "2026-10-16T13:00", "numero_controle_pncp": "111-1-000030/2026",
    "link_sistema_origem": "",
}]}
ARQUIVOS = [
    {"sequencialDocumento": 1, "statusAtivo": True, "titulo": "Edital_Generos%20Alimenticios.pdf",
     "tipoDocumentoNome": "Edital", "url": "https://pncp.gov.br/pncp-api/v1/orgaos/111/compras/2026/30/arquivos/1"},
    {"sequencialDocumento": 2, "statusAtivo": True, "titulo": "anexos", "tipoDocumentoNome": "Outros",
     "url": "https://pncp.gov.br/pncp-api/v1/orgaos/111/compras/2026/30/arquivos/2"},
]


def _handler(req: httpx.Request) -> httpx.Response:
    p = req.url.path
    if p == "/api/search/":
        assert req.url.params["q"] == "merenda"
        assert req.url.params["ufs"] == "MG"
        return httpx.Response(200, json=SEARCH)
    if p.endswith("/arquivos"):
        return httpx.Response(200, json=ARQUIVOS)
    if p.endswith("/arquivos/1"):
        return httpx.Response(200, content=EDITAL, headers={"content-type": "application/pdf"})
    if p.endswith("/arquivos/2"):
        return httpx.Response(200, content=ANEXOS, headers={
            "content-type": "application/zip", "content-disposition": 'attachment; filename="anexos.zip"'})
    if p.endswith("/itens"):
        return httpx.Response(200, json=[{
            "numeroItem": 1, "descricao": "ABACAXI", "quantidade": 156, "unidadeMedida": "UN",
            "valorUnitarioEstimado": 8.06, "valorTotal": 1257.36,
            "tipoBeneficioNome": "Sem benefício", "situacaoCompraItemNome": "Em andamento"}])
    if p == "/api/consulta/v1/orgaos/111/compras/2026/30":
        return httpx.Response(200, json={"objetoCompra": "Merenda", "srp": True})
    return httpx.Response(404)


@pytest.fixture()
def s(tmp_path, monkeypatch):
    monkeypatch.setenv("LICITACOES_DIR", str(tmp_path))
    import importlib

    import pncp_server

    mod = importlib.reload(pncp_server)
    monkeypatch.setattr(mod, "_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=True))
    return mod


def test_busca(s):
    r = s.buscar_licitacoes("merenda", uf="mg")
    assert r["total"] == 1
    item = r["resultados"][0]
    assert item["valor_estimado"] == "R$ 1.004.139,25"
    assert item["link"] == "https://pncp.gov.br/app/editais/111/2026/30"


def test_detalhar(s):
    d = s.detalhar_licitacao("111", 2026, 30)
    assert d["compra"]["objetoCompra"] == "Merenda"
    assert d["itens"][0]["valor_unitario_estimado"] == "R$ 8,06"


def test_listar_documentos_decodifica_titulo(s):
    docs = s.listar_documentos("111", 2026, 30)
    assert docs[0]["titulo"] == "Edital_Generos Alimenticios.pdf"


def test_baixar_extrai_pdf_e_zip(s):
    b = s.baixar_documento("111", 2026, 30)
    nomes = [Path(a["arquivo"]).name for a in b["arquivos"]]
    assert nomes == ["01_Edital_Generos_Alimenticios.pdf", "TR.pdf", "planilha.xlsx"]
    assert "texto" in b["arquivos"][0] and "texto" in b["arquivos"][1]
    assert "texto" not in b["arquivos"][2]

    t = b["arquivos"][0]["texto"]
    achados = s.ler_documento(t, buscar="habilitacao")  # busca ignora acento
    assert achados["ocorrencias"] == 1
    bloco = s.ler_documento(t, tamanho=1000)
    assert "EDITAL PREGAO" in bloco["texto"] and bloco["tem_mais"] is False


def test_ler_documento_bloqueia_fora_da_pasta(s):
    assert "erro" in s.ler_documento("/etc/passwd")


def test_listar_baixados(s):
    s.baixar_documento("111", 2026, 30, sequencial_documento=1)
    pastas = s.listar_baixados()
    assert len(pastas) == 1 and "01_Edital_Generos_Alimenticios.pdf" in pastas[0]["arquivos"]
