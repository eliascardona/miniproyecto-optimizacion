package esquema;

import esquema.Esquema.Alimentacion;
import esquema.Esquema.Elemento;
import esquema.Esquema.Limites;
import esquema.Esquema.OpAmp;
import esquema.Esquema.Punto;
import esquema.Esquema.Salida;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Convierte el JSON ya leído (lo que devuelve api_client.MiniJsonParser: Map / List / String /
 * Double / Boolean / null) en un {@link Esquema}.
 *
 * Es ESTRICTO: si falta un campo, tiene el tipo equivocado o la geometría es incoherente, lanza
 * IllegalArgumentException con la RUTA exacta del problema (p. ej. "esquema.elementos[3].ruta").
 * Quien lo usa decide qué hacer (la respuesta de optimización lo atrapa y cae al dibujo legacy;
 * nunca descarta el resto del resultado).
 */
public final class EsquemaParser {
    private EsquemaParser() {}

    public static Esquema parse(Object raiz) {
        Map<String, Object> o = objeto(raiz, "esquema");

        int version = entero(o, "version_esquema", "esquema");
        if (version != Esquema.VERSION_SOPORTADA) {
            throw new IllegalArgumentException("esquema: versión " + version
                    + " no soportada (este cliente lee la versión " + Esquema.VERSION_SOPORTADA + ")");
        }

        List<Alimentacion> alimentacion = new ArrayList<>();
        List<Object> listaAlim = lista(o, "alimentacion", "esquema");
        for (int i = 0; i < listaAlim.size(); i++) {
            String ruta = "esquema.alimentacion[" + i + "]";
            Map<String, Object> a = objeto(listaAlim.get(i), ruta);
            alimentacion.add(new Alimentacion(texto(a, "nombre", ruta), texto(a, "nodo", ruta), numero(a, "valor", ruta)));
        }

        Map<String, Punto> nodos = new LinkedHashMap<>();
        Map<String, Object> rawNodos = objeto(requerido(o, "nodos", "esquema"), "esquema.nodos");
        for (Map.Entry<String, Object> n : rawNodos.entrySet()) {
            String ruta = "esquema.nodos." + n.getKey();
            Map<String, Object> p = objeto(n.getValue(), ruta);
            nodos.put(n.getKey(), new Punto(numero(p, "x", ruta), numero(p, "y", ruta)));
        }

        List<Elemento> elementos = new ArrayList<>();
        List<Object> listaElem = lista(o, "elementos", "esquema");
        for (int i = 0; i < listaElem.size(); i++) {
            String ruta = "esquema.elementos[" + i + "]";
            Map<String, Object> e = objeto(listaElem.get(i), ruta);
            List<Punto> puntos = puntos(e, "ruta", ruta, 2);
            int seg = entero(e, "seg", ruta);
            if (seg < 0 || seg >= puntos.size() - 1) {
                throw new IllegalArgumentException(ruta + ".seg: " + seg + " fuera de rango para una ruta de "
                        + puntos.size() + " puntos");
            }
            List<String> nodosElem = new ArrayList<>();
            for (Object n : lista(e, "nodos", ruta)) {
                nodosElem.add(texto(n, ruta + ".nodos"));
            }
            elementos.add(new Elemento(texto(e, "nombre", ruta), texto(e, "tipo", ruta), numero(e, "valor", ruta),
                    nodosElem, texto(e, "rol", ruta), entero(e, "etapa", ruta),
                    booleano(e, "optimizable", ruta), puntos, seg));
        }

        List<OpAmp> opamps = new ArrayList<>();
        List<Object> listaOp = lista(o, "opamps", "esquema");
        for (int i = 0; i < listaOp.size(); i++) {
            String ruta = "esquema.opamps[" + i + "]";
            Map<String, Object> op = objeto(listaOp.get(i), ruta);
            Map<String, Object> nodosOp = objeto(requerido(op, "nodos", ruta), ruta + ".nodos");
            Map<String, Object> pines = objeto(requerido(op, "pines", ruta), ruta + ".pines");
            Map<String, Object> alim = objeto(requerido(op, "alimentacion", ruta), ruta + ".alimentacion");
            opamps.add(new OpAmp(texto(op, "nombre", ruta), texto(op, "modelo", ruta), entero(op, "etapa", ruta),
                    texto(nodosOp, "in_p", ruta + ".nodos"), texto(nodosOp, "in_n", ruta + ".nodos"),
                    texto(nodosOp, "out", ruta + ".nodos"),
                    punto(requerido(pines, "in_p", ruta + ".pines"), ruta + ".pines.in_p"),
                    punto(requerido(pines, "in_n", ruta + ".pines"), ruta + ".pines.in_n"),
                    punto(requerido(pines, "out", ruta + ".pines"), ruta + ".pines.out"),
                    puntos(op, "triangulo", ruta, 3),
                    texto(alim, "v_pos", ruta + ".alimentacion"), texto(alim, "v_neg", ruta + ".alimentacion")));
        }

        List<List<Punto>> cables = new ArrayList<>();
        List<Object> listaCables = lista(o, "cables", "esquema");
        for (int i = 0; i < listaCables.size(); i++) {
            cables.add(puntosDe(listaCables.get(i), "esquema.cables[" + i + "]", 2));
        }

        Map<String, Object> rawSalida = objeto(requerido(o, "salida", "esquema"), "esquema.salida");
        Salida salida = new Salida(texto(rawSalida, "nodo", "esquema.salida"), puntos(rawSalida, "ruta", "esquema.salida", 2));

        Map<String, Object> l = objeto(requerido(o, "limites", "esquema"), "esquema.limites");
        Limites limites = new Limites(numero(l, "x_min", "esquema.limites"), numero(l, "x_max", "esquema.limites"),
                numero(l, "y_min", "esquema.limites"), numero(l, "y_max", "esquema.limites"));
        if (limites.xMax() <= limites.xMin() || limites.yMax() <= limites.yMin()) {
            throw new IllegalArgumentException("esquema.limites: la caja está vacía o invertida");
        }

        Object filtro = o.get("filtro");
        return new Esquema(version, filtro == null ? null : texto(filtro, "esquema.filtro"),
                texto(o, "titulo", "esquema"), texto(o, "nodo_fuente", "esquema"), texto(o, "nodo_entrada", "esquema"),
                texto(o, "nodo_salida", "esquema"), entero(o, "num_etapas", "esquema"),
                alimentacion, nodos, elementos, opamps, cables,
                puntosDe(requerido(o, "tierras", "esquema"), "esquema.tierras", 1),
                puntosDe(requerido(o, "uniones", "esquema"), "esquema.uniones", 0),
                salida, limites);
    }

    // ------------------------------------------------------------------
    // Lectura con tipo y ruta de error
    // ------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private static Map<String, Object> objeto(Object valor, String ruta) {
        if (!(valor instanceof Map)) {
            throw new IllegalArgumentException(ruta + ": se esperaba un objeto y llegó " + describir(valor));
        }
        return (Map<String, Object>) valor;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> lista(Map<String, Object> padre, String clave, String rutaPadre) {
        Object valor = requerido(padre, clave, rutaPadre);
        if (!(valor instanceof List)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba una lista y llegó " + describir(valor));
        }
        return (List<Object>) valor;
    }

    private static Object requerido(Map<String, Object> padre, String clave, String rutaPadre) {
        Object valor = padre.get(clave);
        if (valor == null) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": falta el campo");
        }
        return valor;
    }

    private static String texto(Map<String, Object> padre, String clave, String rutaPadre) {
        return texto(requerido(padre, clave, rutaPadre), rutaPadre + "." + clave);
    }

    private static String texto(Object valor, String ruta) {
        if (!(valor instanceof String)) {
            throw new IllegalArgumentException(ruta + ": se esperaba texto y llegó " + describir(valor));
        }
        return (String) valor;
    }

    private static double numero(Map<String, Object> padre, String clave, String rutaPadre) {
        Object valor = requerido(padre, clave, rutaPadre);
        if (!(valor instanceof Number n) || Double.isNaN(n.doubleValue()) || Double.isInfinite(n.doubleValue())) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba un número finito y llegó " + describir(valor));
        }
        return n.doubleValue();
    }

    private static int entero(Map<String, Object> padre, String clave, String rutaPadre) {
        double d = numero(padre, clave, rutaPadre);
        if (d != Math.rint(d)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba un entero y llegó " + d);
        }
        return (int) d;
    }

    private static boolean booleano(Map<String, Object> padre, String clave, String rutaPadre) {
        Object valor = requerido(padre, clave, rutaPadre);
        if (!(valor instanceof Boolean)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba true/false y llegó " + describir(valor));
        }
        return (Boolean) valor;
    }

    private static Punto punto(Object valor, String ruta) {
        if (!(valor instanceof List<?> par) || par.size() != 2
                || !(par.get(0) instanceof Number x) || !(par.get(1) instanceof Number y)) {
            throw new IllegalArgumentException(ruta + ": se esperaba un punto [x, y] y llegó " + describir(valor));
        }
        return new Punto(x.doubleValue(), y.doubleValue());
    }

    private static List<Punto> puntos(Map<String, Object> padre, String clave, String rutaPadre, int minimo) {
        return puntosDe(requerido(padre, clave, rutaPadre), rutaPadre + "." + clave, minimo);
    }

    private static List<Punto> puntosDe(Object valor, String ruta, int minimo) {
        if (!(valor instanceof List<?> lista)) {
            throw new IllegalArgumentException(ruta + ": se esperaba una lista de puntos y llegó " + describir(valor));
        }
        if (lista.size() < minimo) {
            throw new IllegalArgumentException(ruta + ": se esperaban al menos " + minimo + " puntos y hay " + lista.size());
        }
        List<Punto> puntos = new ArrayList<>();
        for (int i = 0; i < lista.size(); i++) {
            puntos.add(punto(lista.get(i), ruta + "[" + i + "]"));
        }
        return puntos;
    }

    private static String describir(Object valor) {
        return valor == null ? "null" : valor.getClass().getSimpleName();
    }
}