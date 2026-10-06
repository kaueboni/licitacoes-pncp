# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "httpx>=0.27", "pypdf>=4.0"]
# ///
"""
Servidor MCP para o PNCP (Portal Nacional de Contratações Públicas).

Ferramentas:
  - buscar_licitacoes   : busca por palavra-chave (mesma busca do site pncp.gov.br)
  - detalhar_licitacao  : dados da contratação + itens
  - listar_documentos   : arquivos publicados (edital, termo de referência, anexos)
  - baixar_documento    : baixa um arquivo, descompacta ZIP e extrai o texto (PDF/DOCX/TXT)
  - ler_documento       : lê o texto extraído em blocos, para análise pelo Claude
  - listar_baixados     : lista o que já foi baixado

Os arquivos ficam em $LICITACOES_DIR (padrão: ~/Licitacoes).
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE = "https://pncp.gov.br"
SEARCH_URL = f"{BASE}/api/search/"
PNCP_API = f"{BASE}/api/pncp/v1"
CONSULTA_API = f"{BASE}/api/consulta/v1"

DATA_DIR = Path(os.environ.get("LICITACOES_DIR", Path.home() / "Licitacoes")).expanduser()
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
HEADERS = {"User-Agent": "licitacoes-pncp-mcp/1.0", "Accept": "application/json"}

MODALIDADES = {
    "1": "Leilão - Eletrônico", "2": "Diálogo Competitivo", "3": "Concurso",
    "4": "Concorrência - Eletrônica", "5": "Concorrência - Presencial",
    "6": "Pregão - Eletrônico", "7": "Pregão - Presencial",
    "8": "Dispensa de Licitação", "9": "Inexigibilidade",
    "10": "Manifestação de Interesse", "11": "Pré-qualificação",
    "12": "Credenciamento", "13": "Leilão - Presencial",
}

mcp = FastMCP("licitacoes-pncp")


# ----------------------------------------------------------------- utilidades
def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True)


def _get_json(url: str, params: dict | None = None) -> Any:
    with _client() as c:
        r = c.get(url, params=params)
        if r.status_code == 204 or not r.content:
            return None
        r.raise_for_status()
        return r.json()


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w.\-]+", "_", s).strip("_")
    return s[:120] or "arquivo"


def _pasta(cnpj: str, ano: int | str, seq: int | str) -> Path:
    p = DATA_DIR / f"{cnpj}-{ano}-{seq}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _brl(v: Any) -> str:
    if v in (None, ""):
        return "não informado"
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v)


def _texto_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    partes = []
    for i, page in enumerate(reader.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception as e:  # página corrompida não derruba o resto
            t = f"[erro ao extrair página: {e}]"
        partes.append(f"\n\n===== Página {i} =====\n{t}")
    return "".join(partes)


def _texto_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    txt = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"\n{3,}", "\n\n", txt)


def _extrair(nome: str, data: bytes) -> str | None:
    ext = Path(nome).suffix.lower()
    if ext == ".pdf" or data[:4] == b"%PDF":
        return _texto_pdf(data)
    if ext == ".docx":
        return _texto_docx(data)
    if ext in {".txt", ".csv", ".md", ".html", ".htm", ".xml"}:
        return data.decode("utf-8", "ignore")
    return None


def _salvar_e_extrair(pasta: Path, nome: str, data: bytes, resultado: list[dict]) -> None:
    """Salva o arquivo; se for ZIP, abre recursivamente; gera .txt quando possível."""
    nome = _slug(nome)
    destino = pasta / nome
    destino.write_bytes(data)

    if zipfile.is_zipfile(io.BytesIO(data)) and Path(nome).suffix.lower() != ".docx":
        sub = pasta / (Path(nome).stem + "_zip")
        sub.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                _salvar_e_extrair(sub, Path(info.filename).name, z.read(info), resultado)
        return

    item: dict[str, Any] = {"arquivo": str(destino), "bytes": len(data)}
    try:
        texto = _extrair(nome, data)
    except Exception as e:
        texto, item["erro_extracao"] = None, str(e)
    if texto is not None:
        txt_path = destino.with_suffix(destino.suffix + ".txt")
        txt_path.write_text(texto, encoding="utf-8")
        paginas = max(1, texto.count("===== Página "))
        chars = len(re.sub(r"\s|=+ Página \d+ =+", "", texto))
        item.update(texto=str(txt_path), caracteres=len(texto))
        if destino.suffix.lower() == ".pdf" and chars / paginas < 40:
            item["aviso"] = "PDF praticamente sem texto (provavelmente escaneado). Abra o PDF diretamente no Claude para leitura visual."
    else:
        item.setdefault("aviso", "Formato sem extração de texto automática; abra o arquivo original no Claude.")
    resultado.append(item)


# ------------------------------------------------------------------ ferramentas
@mcp.tool()
def buscar_licitacoes(
    palavra_chave: str,
    status: str = "recebendo_proposta",
    uf: str | None = None,
    modalidade: str | None = None,
    tipo_documento: str = "edital",
    pagina: int = 1,
    tam_pagina: int = 20,
) -> dict:
    """Busca contratações no PNCP por palavra-chave (mesma busca do site pncp.gov.br).

    Args:
        palavra_chave: termos de busca, ex. "merenda escolar", "software de gestão".
        status: recebendo_proposta | em_julgamento | encerradas | todos.
        uf: sigla do estado para filtrar, ex. "SP" (opcional; várias separadas por vírgula).
        modalidade: código da modalidade, ex. "6" = Pregão Eletrônico, "8" = Dispensa (opcional).
        tipo_documento: edital | ata | contrato.
        pagina: página de resultados (começa em 1).
        tam_pagina: resultados por página (máx. 100).

    Retorna lista resumida. Use cnpj/ano/sequencial nas outras ferramentas.
    """
    params: dict[str, Any] = {
        "q": palavra_chave,
        "tipos_documento": tipo_documento,
        "ordenacao": "-data",
        "pagina": pagina,
        "tam_pagina": max(1, min(tam_pagina, 100)),
    }
    if status and status != "todos":
        params["status"] = status
    if uf:
        params["ufs"] = uf.upper().replace(" ", "")
    if modalidade:
        params["modalidades"] = modalidade

    data = _get_json(SEARCH_URL, params) or {}
    itens = []
    for it in data.get("items", []):
        cnpj, ano, seq = it.get("orgao_cnpj"), it.get("ano"), it.get("numero_sequencial")
        itens.append({
            "titulo": it.get("title"),
            "objeto": (it.get("description") or "").strip(),
            "orgao": it.get("orgao_nome"),
            "municipio_uf": f"{it.get('municipio_nome')}/{it.get('uf')}",
            "modalidade": it.get("modalidade_licitacao_nome"),
            "situacao": it.get("situacao_nome"),
            "valor_estimado": _brl(it.get("valor_total_estimado")),
            "registro_de_precos": it.get("srp"),
            "publicacao": it.get("data_publicacao_pncp"),
            "fim_propostas": it.get("data_fim_vigencia"),
            "controle_pncp": it.get("numero_controle_pncp"),
            "cnpj": cnpj, "ano": ano, "sequencial": seq,
            "link": f"{BASE}/app/editais/{cnpj}/{ano}/{seq}",
            "sistema_origem": it.get("link_sistema_origem") or None,
        })
    return {"total": data.get("total", 0), "pagina": pagina, "resultados": itens}


@mcp.tool()
def detalhar_licitacao(cnpj: str, ano: int, sequencial: int, max_itens: int = 200) -> dict:
    """Dados completos de uma contratação do PNCP e a lista de itens (quantidades, valores).

    Args:
        cnpj: CNPJ do órgão (só números).
        ano: ano da compra.
        sequencial: número sequencial da compra no PNCP.
        max_itens: limite de itens retornados.
    """
    compra = _get_json(f"{CONSULTA_API}/orgaos/{cnpj}/compras/{ano}/{sequencial}") or {}
    itens: list[dict] = []
    pagina = 1
    while len(itens) < max_itens:
        lote = _get_json(
            f"{PNCP_API}/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens",
            {"pagina": pagina, "tamanhoPagina": 50},
        ) or []
        if not lote:
            break
        for i in lote:
            itens.append({
                "numero": i.get("numeroItem"),
                "descricao": i.get("descricao"),
                "quantidade": i.get("quantidade"),
                "unidade": i.get("unidadeMedida"),
                "valor_unitario_estimado": _brl(i.get("valorUnitarioEstimado")),
                "valor_total": _brl(i.get("valorTotal")),
                "beneficio_me_epp": i.get("tipoBeneficioNome"),
                "situacao": i.get("situacaoCompraItemNome"),
            })
        if len(lote) < 50:
            break
        pagina += 1
    return {"compra": compra, "itens": itens[:max_itens], "total_itens": len(itens)}


@mcp.tool()
def listar_documentos(cnpj: str, ano: int, sequencial: int) -> list[dict]:
    """Lista os arquivos publicados de uma contratação (edital, termo de referência, anexos).

    Use o campo `sequencial_documento` em `baixar_documento`.
    """
    docs = _get_json(f"{PNCP_API}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos") or []
    return [{
        "sequencial_documento": d.get("sequencialDocumento"),
        "titulo": urllib.parse.unquote(d.get("titulo") or ""),
        "tipo": d.get("tipoDocumentoNome"),
        "publicado_em": d.get("dataPublicacaoPncp"),
        "ativo": d.get("statusAtivo"),
        "url": d.get("url"),
    } for d in docs]


@mcp.tool()
def baixar_documento(
    cnpj: str, ano: int, sequencial: int, sequencial_documento: int | None = None
) -> dict:
    """Baixa documento(s) de uma contratação, descompacta ZIPs e extrai o texto.

    Args:
        sequencial_documento: qual arquivo baixar (de `listar_documentos`).
            Se omitido, baixa todos os arquivos ativos da contratação.

    Retorna caminhos do original e do .txt extraído; leia o texto com `ler_documento`.
    """
    docs = listar_documentos(cnpj, ano, sequencial)
    if sequencial_documento is not None:
        docs = [d for d in docs if d["sequencial_documento"] == sequencial_documento]
    else:
        docs = [d for d in docs if d.get("ativo", True)]
    if not docs:
        return {"erro": "Nenhum documento encontrado para essa contratação."}

    pasta = _pasta(cnpj, ano, sequencial)
    resultado: list[dict] = []
    with _client() as c:
        for d in docs:
            url = d["url"] or f"{PNCP_API}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/{d['sequencial_documento']}"
            r = c.get(url, headers={"Accept": "*/*"})
            r.raise_for_status()
            nome = d["titulo"] or ""
            cd = r.headers.get("content-disposition", "")
            m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
            if m:
                nome = urllib.parse.unquote(m.group(1))
            if not Path(nome).suffix:
                ct = r.headers.get("content-type", "")
                nome += ".pdf" if "pdf" in ct else ".zip" if "zip" in ct else ".bin"
            nome = f"{d['sequencial_documento']:02d}_{nome}"
            _salvar_e_extrair(pasta, nome, r.content, resultado)
    return {"pasta": str(pasta), "arquivos": resultado}


@mcp.tool()
def ler_documento(caminho: str, inicio: int = 0, tamanho: int = 40000, buscar: str | None = None) -> dict:
    """Lê o texto extraído de um documento baixado, em blocos.

    Args:
        caminho: caminho do .txt (campo `texto` de `baixar_documento`).
        inicio: posição (caractere) inicial.
        tamanho: quantidade de caracteres a ler (máx. 80000).
        buscar: se informado, devolve trechos ao redor de cada ocorrência do termo
            (ex. "habilitação", "garantia", "prazo de entrega") em vez de um bloco.
    """
    p = Path(caminho).expanduser()
    if not p.is_file() or DATA_DIR.resolve() not in p.resolve().parents:
        return {"erro": f"Arquivo não encontrado dentro de {DATA_DIR}."}
    texto = p.read_text(encoding="utf-8", errors="ignore")

    if buscar:
        norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
        alvo, base = norm(buscar), norm(texto)
        trechos, pos = [], 0
        while len(trechos) < 25:
            i = base.find(alvo, pos)
            if i < 0:
                break
            trechos.append({"posicao": i, "trecho": texto[max(0, i - 600): i + 1400]})
            pos = i + len(alvo)
        return {"total_caracteres": len(texto), "ocorrencias": len(trechos), "trechos": trechos}

    tamanho = max(1000, min(tamanho, 80000))
    fim = min(len(texto), inicio + tamanho)
    return {
        "total_caracteres": len(texto),
        "inicio": inicio,
        "fim": fim,
        "tem_mais": fim < len(texto),
        "texto": texto[inicio:fim],
    }


@mcp.tool()
def listar_baixados() -> list[dict]:
    """Lista as contratações e arquivos já baixados em ~/Licitacoes."""
    if not DATA_DIR.exists():
        return []
    saida = []
    for pasta in sorted(DATA_DIR.iterdir()):
        if pasta.is_dir():
            arquivos = sorted(str(f.relative_to(pasta)) for f in pasta.rglob("*") if f.is_file())
            saida.append({"pasta": str(pasta), "arquivos": arquivos})
    return saida


if __name__ == "__main__":
    mcp.run()
