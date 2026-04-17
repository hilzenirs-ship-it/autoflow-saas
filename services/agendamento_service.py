import re
import unicodedata


def normalizar_texto(texto):
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def normalizar_horario_agendamento(horario_texto):
    texto = normalizar_texto(horario_texto)
    if not texto:
        return None, "Informe um horario para o agendamento."

    texto = texto.replace(" horas", "h").replace(" hora", "h")
    match = re.match(r"^(\d{1,2})(?::|h)?(\d{2})?$", texto)
    if not match:
        return None, "Use um horario valido, por exemplo 14:30."

    hora = int(match.group(1))
    minuto = int(match.group(2) or 0)
    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
        return None, "Horario invalido."

    return f"{hora:02d}:{minuto:02d}", None
