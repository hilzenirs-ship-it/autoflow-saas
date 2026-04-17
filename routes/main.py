from flask import Blueprint


main_bp = Blueprint("main", __name__)


def registrar_aliases_endpoints_legados(app, blueprint_name="main"):
    prefixo = f"{blueprint_name}."
    regras_blueprint = [
        regra
        for regra in list(app.url_map.iter_rules())
        if regra.endpoint.startswith(prefixo)
    ]

    for regra in regras_blueprint:
        endpoint_legado = regra.endpoint[len(prefixo):]
        if endpoint_legado in app.view_functions:
            continue

        metodos = sorted((regra.methods or set()) - {"HEAD", "OPTIONS"})
        app.add_url_rule(
            regra.rule,
            endpoint=endpoint_legado,
            view_func=app.view_functions[regra.endpoint],
            methods=metodos,
            defaults=regra.defaults,
            strict_slashes=regra.strict_slashes,
        )
