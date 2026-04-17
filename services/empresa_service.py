from utils.db import get_connection


def buscar_nome_empresa(empresa_id):
    if not empresa_id:
        return "Empresa"

    conn = get_connection()
    empresa = conn.execute(
        """
        SELECT nome_exibicao, nome_empresa
        FROM empresas
        WHERE id = ?
        """,
        (empresa_id,)
    ).fetchone()
    conn.close()

    if not empresa:
        return "Empresa"

    return empresa["nome_exibicao"] or empresa["nome_empresa"] or "Empresa"
