package esquema;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * ESQUEMA de un circuito: el circuito descrito con datos listos para dibujar. Es el espejo en
 * Java del JSON que entrega el backend (ver esquema_schema.py), tanto en la respuesta de
 * POST /api/optimizar como en GET /api/circuitos/{filtro}.
 *
 * Coordenadas en UNIDADES DE REJILLA (x hacia la derecha, y hacia ABAJO, como en Java2D); cuántos
 * píxeles vale una unidad lo decide quien dibuja (ver {@link EsquemaRenderer}). Cada elemento trae
 * su RUTA (polilínea) y {@code seg}, el índice del segmento donde va su símbolo: quien dibuja solo
 * pinta, no necesita conocer la topología.
 *
 * Inmutable: todas las listas y mapas son de solo lectura.
 *
 * Valores de {@code tipo}: "R", "C", "L", "V".
 * Valores de {@code rol}: "fuente", "resistencia_fuente", "serie", "derivacion", "realimentacion", "carga".
 */
public record Esquema(
        int version,
        String filtro,                       // puede ser null
        String titulo,
        String nodoFuente,
        String nodoEntrada,
        String nodoSalida,
        int numEtapas,
        List<Alimentacion> alimentacion,
        Map<String, Punto> nodos,
        List<Elemento> elementos,
        List<OpAmp> opamps,
        List<List<Punto>> cables,
        List<Punto> tierras,
        List<Punto> uniones,
        Salida salida,
        Limites limites) {

    /** Versión del formato que este cliente sabe leer. */
    public static final int VERSION_SOPORTADA = 1;

    public record Punto(double x, double y) {}

    public record Elemento(String nombre, String tipo, double valor, List<String> nodos, String rol, int etapa,
                           boolean optimizable, List<Punto> ruta, int seg) {
        public Elemento {
            nodos = List.copyOf(nodos);
            ruta = List.copyOf(ruta);
        }
    }

    public record OpAmp(String nombre, String modelo, int etapa,
                        String nodoInP, String nodoInN, String nodoOut,
                        Punto pinInP, Punto pinInN, Punto pinOut,
                        List<Punto> triangulo, String nodoVPos, String nodoVNeg) {
        public OpAmp {
            triangulo = List.copyOf(triangulo);
        }
    }

    public record Alimentacion(String nombre, String nodo, double valor) {}

    public record Salida(String nodo, List<Punto> ruta) {
        public Salida {
            ruta = List.copyOf(ruta);
        }
    }

    public record Limites(double xMin, double xMax, double yMin, double yMax) {}

    public Esquema {
        alimentacion = List.copyOf(alimentacion);
        nodos = Collections.unmodifiableMap(new LinkedHashMap<>(nodos));
        elementos = List.copyOf(elementos);
        opamps = List.copyOf(opamps);
        List<List<Punto>> copiaCables = new ArrayList<>();
        for (List<Punto> cable : cables) {
            copiaCables.add(List.copyOf(cable));
        }
        cables = Collections.unmodifiableList(copiaCables);
        tierras = List.copyOf(tierras);
        uniones = List.copyOf(uniones);
    }

    /** Cuántos componentes ajusta el optimizador (R, C y L que no son fuente ni carga). */
    public int numeroComponentes() {
        int n = 0;
        for (Elemento e : elementos) {
            if (e.optimizable()) {
                n++;
            }
        }
        return n;
    }

    /** Tensión de una fuente de alimentación por su nodo (p. ej. "Vp"), o null si no existe. */
    public Double tensionDeNodo(String nodo) {
        for (Alimentacion a : alimentacion) {
            if (a.nodo().equals(nodo)) {
                return a.valor();
            }
        }
        return null;
    }

    /**
     * Texto de una línea con los componentes optimizados y su valor ("C1_1=15 nF  R2_1=470 Ω ..."),
     * en el orden en que aparecen en el circuito. Sustituye al "coded circuit" legacy, que no puede
     * expresar op-amps.
     */
    public String resumen() {
        StringBuilder sb = new StringBuilder();
        for (Elemento e : elementos) {
            if (!e.optimizable()) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append("  ");
            }
            sb.append(e.nombre()).append('=').append(FormatoIngenieria.valor(e.valor(), e.tipo()));
        }
        return sb.toString();
    }
}