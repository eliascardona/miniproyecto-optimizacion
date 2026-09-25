package format_converter;

import dto.ComponenteDTO;
import model.ComponentTables;
import model.Element;

import java.util.ArrayList;
import java.util.List;

/**
 * Traduce la lista de componentes optimizados que devuelve la API de Python
 * (dto.ComponenteDTO: nombre, tipo, valor, conexionTierra) al modelo de
 * dibujo que ya existía en este proyecto (model.Element: node1/node2/nodeA
 * + índices type/value/decade).
 *
 * La API entrega el valor físico real (p. ej. 6.8e-08) y si el componente
 * conecta o no a tierra (dato tomado directamente del netlist .cir, no
 * inferido del nombre). Element, en cambio, no guarda el valor físico: guarda
 * ÍNDICES dentro de las tablas fijas de ComponentTables, que es justo lo que
 * ya usa CircuitPanel para dibujar cada elemento y su etiqueta. Por eso aquí
 * se hace la búsqueda inversa (valor físico -> índice) antes de construir
 * cada Element.
 *
 * Encadenamiento de nodos: Element.node1 del elemento i es igual a
 * Element.nodeA del elemento i-1 (así lo documenta el propio Element.java).
 * Ese es el "enlace con el siguiente" en este modelo; no existe (ni hace
 * falta) un campo de nombre/referencia explícito como "componente_siguiente".
 */
public final class FormatConverter {
    private FormatConverter() {}

    /** Tolerancia relativa para casar un valor optimizado con un valor comercial de la tabla. */
    private static final double TOLERANCIA_RELATIVA = 1e-6;

    public static List<Element> convertir(List<ComponenteDTO> componentes) {
        List<Element> elementos = new ArrayList<>();
        int nodoActual = 1;

        for (ComponenteDTO c : componentes) {
            int type = tipoToElementType(c.tipo);
            int[] valueDecadeIdx = buscarEnTabla(c.valor, type, c.nombre);

            int node1 = nodoActual;
            int node2 = c.conexionTierra ? 0 : node1 + 1;
            int nodeA = c.conexionTierra ? node1 : node2;

            elementos.add(new Element(node1, node2, nodeA, type, valueDecadeIdx[0], valueDecadeIdx[1]));
            nodoActual = nodeA;
        }
        return elementos;
    }

    /**
     * Reconstruye el string "circuito codificado" en el mismo formato que ya
     * usa InputCircuitController ("[node1|node2|nodeA|type|value|decade]->..."),
     * para que el resto de la app (la etiqueta de MainFrame, "Save Full File",
     * reabrir/editar el circuito a mano) siga funcionando igual sin importar
     * si el circuito vino del archivo viejo o de la API nueva.
     */
    public static String toCodedCircuitString(List<Element> elementos) {
        StringBuilder sb = new StringBuilder();
        for (Element e : elementos) {
            sb.append('[')
                    .append(e.getNode1()).append('|')
                    .append(e.getNode2()).append('|')
                    .append(e.getNodeA()).append('|')
                    .append(e.getType()).append('|')
                    .append(e.getValue()).append('|')
                    .append(e.getDecade())
                    .append("]->");
        }
        return sb.toString();
    }

    private static int tipoToElementType(String tipo) {
        if (tipo == null) {
            throw new IllegalArgumentException("Componente sin 'tipo'.");
        }
        return switch (tipo.toUpperCase()) {
            case "C" -> 0;
            case "R" -> 1;
            default -> throw new IllegalArgumentException(
                    "Tipo de componente no soportado por el visor: '" + tipo + "' " +
                            "(el modelo Element solo dibuja R y C con los datos que da esta API; " +
                            "L=2 existe en Element pero el backend de pasa-altas no genera inductores).");
        };
    }

    /**
     * Busca, dentro de ComponentTables, la combinación (índice de valor,
     * índice de década) cuyo valor reconstruido
     * (values[type][v] * 10^decades[type][d]) coincide con el valor real
     * optimizado, dentro de una tolerancia relativa.
     */
    private static int[] buscarEnTabla(double valorReal, int type, String nombreComponente) {
        int[] valores = ComponentTables.VALUES[type];
        int[] decadas = ComponentTables.DECADES[type];

        for (int d = 0; d < decadas.length; d++) {
            for (int v = 0; v < valores.length; v++) {
                double candidato = valores[v] * Math.pow(10, decadas[d]);
                double diferencia = Math.abs(candidato - valorReal);
                double tolerancia = Math.max(TOLERANCIA_RELATIVA * Math.abs(valorReal), 1e-15);

                if (diferencia <= tolerancia) {
                    return new int[]{v, d};
                }
            }
        }

        throw new IllegalArgumentException(
                "No se encontró un valor comercial en ComponentTables para '" + nombreComponente +
                        "' = " + valorReal + ". Verifica que las series (E12/E6) del backend Python " +
                        "coincidan con ComponentTables en Java.");
    }
}
