from pathlib import Path

ARQUIVOS = [
    "app.py",
    "templates/agendamentos.html",
    "templates/base.html",
    "templates/cadastro.html",
    "templates/configuracoes.html",
    "templates/contatos.html",
    "templates/conversa_detalhe.html",
    "templates/conversas.html",
    "templates/dashboard.html",
    "templates/editar_contatos.html",
    "templates/editar_regra.html",
    "templates/fluxo_editor.html",
    "templates/fluxos.html",
    "templates/login.html",
    "templates/metricas.html",
    "templates/novo_contato.html",
    "templates/regras.html",
    "static/style.css",
]

SUBSTITUICOES = {
    "Ã¡": "á",
    "Ã ": "à",
    "Ã¢": "â",
    "Ã£": "ã",
    "Ã¤": "ä",
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã­": "í",
    "Ã¬": "ì",
    "Ã®": "î",
    "Ã¯": "ï",
    "Ã³": "ó",
    "Ã²": "ò",
    "Ã´": "ô",
    "Ãµ": "õ",
    "Ã¶": "ö",
    "Ãº": "ú",
    "Ã¹": "ù",
    "Ã»": "û",
    "Ã¼": "ü",
    "Ã": "Á",
    "Ã€": "À",
    "Ã‚": "Â",
    "Ãƒ": "Ã",
    "Ã„": "Ä",
    "Ã‰": "É",
    "Ãˆ": "È",
    "ÃŠ": "Ê",
    "Ã‹": "Ë",
    "Ã": "Í",
    "ÃŒ": "Ì",
    "ÃŽ": "Î",
    "Ã": "Ï",
    "Ã“": "Ó",
    "Ã’": "Ò",
    "Ã”": "Ô",
    "Ã•": "Õ",
    "Ã–": "Ö",
    "Ãš": "Ú",
    "Ã™": "Ù",
    "Ã›": "Û",
    "Ãœ": "Ü",
    "Ã§": "ç",
    "Ã‡": "Ç",
    "Ã±": "ñ",
    "Ã‘": "Ñ",
    "â€“": "–",
    "â€”": "—",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€¦": "…",
    "â€¢": "•",
    "âœ¨": "✨",
    "â°": "⏰",
    "âœ…": "✅",
    "âŒ": "❌",
    "âš ": "⚠",
    "ðŸ’œ": "💖",
    "ðŸ˜Š": "😊",
    "ðŸ“": "📍",
    "ðŸ’³": "💳",
    "ðŸ¤": "🤍",
    "ðŸ“…": "📅",
}

CORRECOES_EXATAS = {
    "JÃ¡": "Já",
    "NÃ£o": "Não",
    "VocÃª": "Você",
    "serviÃ§o": "serviço",
    "horÃ¡rio": "horário",
    "horÃ¡rios": "horários",
    "localizaÃ§Ã£o": "localização",
    "opÃ§Ã£o": "opção",
    "opÃ§Ãµes": "opções",
    "aÃ§Ã£o": "ação",
    "aÃ§Ãµes": "ações",
    "automaÃ§Ã£o": "automação",
    "informaÃ§Ã£o": "informação",
    "informaÃ§Ãµes": "informações",
    "conversÃ£o": "conversão",
    "cartÃ£o": "cartão",
    "UsuÃ¡rio": "Usuário",
    "usuÃ¡rio": "usuário",
    "invÃ¡lida": "inválida",
    "ReferÃªncia": "Referência",
    "prÃ³xima": "próxima",
    "mÃ©tricas": "métricas",
    "MÃ‰TRICAS": "MÉTRICAS",
    "MEMÃ“RIA": "MEMÓRIA",
    "AUTOMÃTICO": "AUTOMÁTICO",
    "OlÃ¡": "Olá",
    "endereÃ§o": "endereço",
    "perÃ­odo": "período",
}

def tentar_recuperar_mojibake(texto: str) -> str:
    try:
        recuperado = texto.encode("latin1").decode("utf-8")
        if recuperado.count("Ã") < texto.count("Ã"):
            texto = recuperado
    except Exception:
        pass
    return texto

def corrigir_texto(texto: str) -> str:
    texto = tentar_recuperar_mojibake(texto)

    for errado, certo in CORRECOES_EXATAS.items():
        texto = texto.replace(errado, certo)

    for errado, certo in SUBSTITUICOES.items():
        texto = texto.replace(errado, certo)

    return texto

def processar_arquivo(caminho_str: str) -> None:
    caminho = Path(caminho_str)
    if not caminho.exists():
        print(f"[pulado] {caminho}")
        return

    bruto = caminho.read_text(encoding="utf-8", errors="replace")
    corrigido = corrigir_texto(bruto)

    if corrigido != bruto:
        backup = caminho.with_suffix(caminho.suffix + ".bak")
        if not backup.exists():
            backup.write_text(bruto, encoding="utf-8")
        caminho.write_text(corrigido, encoding="utf-8", newline="\n")
        print(f"[corrigido] {caminho}")
    else:
        print(f"[ok] {caminho}")

def main() -> None:
    for arquivo in ARQUIVOS:
        processar_arquivo(arquivo)

if __name__ == "__main__":
    main()