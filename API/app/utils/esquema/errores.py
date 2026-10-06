"""Errores del módulo de esquemas. Todos heredan de ValueError (el controlador ya traduce ValueError a 422)."""


class EsquemaError(ValueError):
    """Base de los errores al construir o consultar un esquema."""


class NetlistInvalido(EsquemaError):
    """El texto del .cir no se pudo interpretar (línea mal formada, elemento no soportado...)."""


class TopologiaNoSoportada(EsquemaError):
    """El netlist es válido pero su topología queda fuera de lo que el esquema sabe dibujar.

    Es un error DELIBERADO: es preferible fallar de forma explícita (y que el
    cliente caiga a la tabla de componentes + la gráfica) que dibujar un
    circuito que no corresponde al .cir.
    """