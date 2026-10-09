package catalogo;

import catalogo.Catalogo.Algoritmo;
import catalogo.Catalogo.Barrido;
import catalogo.Catalogo.Campo;
import catalogo.Catalogo.Combinacion;
import catalogo.Catalogo.Filtro;
import catalogo.Catalogo.FrecuenciasDeModo;
import catalogo.Catalogo.MargenDecada;
import catalogo.Catalogo.Modo;
import catalogo.Catalogo.Relacion;
import catalogo.Catalogo.Severidad;
import catalogo.Catalogo.Tipo;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Convierte el JSON ya leído (lo que devuelve api_client.MiniJsonParser: Map / List / String / Double /
 * Boolean / null) en un {@link Catalogo}.
 *
 * Es ESTRICTO, igual que esquema.EsquemaParser: un campo que falta, un tipo equivocado o un catálogo
 * incoherente consigo mismo lanzan IllegalArgumentException con la RUTA exacta del problema
 * (p. ej. "catalogo.algoritmos[1].parametros[0].tipo"). Las incoherencias se revisan aquí para que el
 * formulario nunca tenga que lidiar con una clave que no existe.
 */
public final class CatalogoParser {
    private CatalogoParser() {}

    public static Catalogo parse(Object raiz) {
        Map<String, Object> o = objeto(raiz, "catalogo");

        int version = entero(o, "version_catalogo", "catalogo");
        if (version != Catalogo.VERSION_SOPORTADA) {
            throw new IllegalArgumentException("catalogo: versión " + version
                    + " no soportada (este cliente lee la versión " + Catalogo.VERSION_SOPORTADA + ")");
        }

        List<Modo> modos = new ArrayList<>();
        List<Object> listaModos = lista(o, "modos", "catalogo");
        for (int i = 0; i < listaModos.size(); i++) {
            String ruta = "catalogo.modos[" + i + "]";
            Map<String, Object> m = objeto(listaModos.get(i), ruta);
            modos.add(new Modo(texto(m, "id", ruta), texto(m, "etiqueta", ruta), texto(m, "descripcion", ruta)));
        }
        if (modos.isEmpty()) {
            throw new IllegalArgumentException("catalogo.modos: la lista está vacía");
        }
        Set<String> idsModo = new LinkedHashSet<>();
        modos.forEach(m -> idsModo.add(m.id()));

        List<Campo> entorno = campos(lista(o, "entorno", "catalogo"), "catalogo.entorno");

        Map<String, Object> rawBarrido = objeto(requerido(o, "barrido_ac", "catalogo"), "catalogo.barrido_ac");
        List<Campo> camposBarrido = campos(lista(rawBarrido, "campos", "catalogo.barrido_ac"), "catalogo.barrido_ac.campos");
        List<Relacion> relacionesBarrido = relaciones(lista(rawBarrido, "relaciones", "catalogo.barrido_ac"),
                "catalogo.barrido_ac.relaciones", claves(camposBarrido, "catalogo.barrido_ac.campos"));
        Barrido barrido = new Barrido(camposBarrido, relacionesBarrido);

        Map<String, Object> rawReglas = objeto(requerido(o, "reglas", "catalogo"), "catalogo.reglas");
        Map<String, Object> rawMargen = objeto(requerido(rawReglas, "margen_decada", "catalogo.reglas"), "catalogo.reglas.margen_decada");
        double factor = numero(rawMargen, "factor", "catalogo.reglas.margen_decada");
        if (factor <= 1) {
            throw new IllegalArgumentException("catalogo.reglas.margen_decada.factor: debe ser mayor que 1 y llegó " + factor);
        }
        MargenDecada margen = new MargenDecada(factor, severidad(rawMargen, "catalogo.reglas.margen_decada"),
                texto(rawMargen, "descripcion", "catalogo.reglas.margen_decada"));

        List<Filtro> filtros = new ArrayList<>();
        List<Object> listaFiltros = lista(o, "filtros", "catalogo");
        for (int i = 0; i < listaFiltros.size(); i++) {
            filtros.add(filtro(listaFiltros.get(i), "catalogo.filtros[" + i + "]", idsModo));
        }

        List<Algoritmo> algoritmos = new ArrayList<>();
        List<Object> listaAlgoritmos = lista(o, "algoritmos", "catalogo");
        for (int i = 0; i < listaAlgoritmos.size(); i++) {
            algoritmos.add(algoritmo(listaAlgoritmos.get(i), "catalogo.algoritmos[" + i + "]"));
        }

        List<Combinacion> combinaciones = new ArrayList<>();
        List<Object> listaCombinaciones = lista(o, "combinaciones", "catalogo");
        Set<String> vistas = new LinkedHashSet<>();
        for (int i = 0; i < listaCombinaciones.size(); i++) {
            String ruta = "catalogo.combinaciones[" + i + "]";
            Map<String, Object> c = objeto(listaCombinaciones.get(i), ruta);
            String filtroId = texto(c, "filtro", ruta);
            String algoritmoId = texto(c, "algoritmo", ruta);
            Filtro f = buscar(filtros, filtroId, Filtro::id);
            Algoritmo a = buscar(algoritmos, algoritmoId, Algoritmo::id);
            if (f == null) {
                throw new IllegalArgumentException(ruta + ".filtro: '" + filtroId + "' no está en catalogo.filtros");
            }
            if (a == null) {
                throw new IllegalArgumentException(ruta + ".algoritmo: '" + algoritmoId + "' no está en catalogo.algoritmos");
            }
            if (!vistas.add(filtroId + "/" + algoritmoId)) {
                throw new IllegalArgumentException(ruta + ": la combinación " + filtroId + "/" + algoritmoId + " está repetida");
            }
            Map<String, Double> iniciales = valores(objeto(requerido(c, "valores_iniciales", ruta), ruta + ".valores_iniciales"),
                    ruta + ".valores_iniciales");
            mismasClaves(iniciales.keySet(), claves(a.parametros(), ruta), ruta + ".valores_iniciales");
            combinaciones.add(new Combinacion(filtroId, algoritmoId, booleano(c, "disponible", ruta), iniciales));
        }

        return new Catalogo(version, modos, entorno, barrido, margen, filtros, algoritmos, combinaciones);
    }

    // ------------------------------------------------------------------
    // Secciones
    // ------------------------------------------------------------------

    private static Filtro filtro(Object valor, String ruta, Set<String> idsModo) {
        Map<String, Object> f = objeto(valor, ruta);
        List<FrecuenciasDeModo> porModo = new ArrayList<>();
        List<Object> lista = lista(f, "frecuencias", ruta);
        Set<String> vistos = new LinkedHashSet<>();
        for (int i = 0; i < lista.size(); i++) {
            String rutaModo = ruta + ".frecuencias[" + i + "]";
            Map<String, Object> m = objeto(lista.get(i), rutaModo);
            String modo = texto(m, "modo", rutaModo);
            if (!idsModo.contains(modo)) {
                throw new IllegalArgumentException(rutaModo + ".modo: '" + modo + "' no está en catalogo.modos");
            }
            if (!vistos.add(modo)) {
                throw new IllegalArgumentException(rutaModo + ".modo: '" + modo + "' está repetido");
            }
            List<Campo> campos = campos(lista(m, "campos", rutaModo), rutaModo + ".campos");
            if (campos.isEmpty()) {
                throw new IllegalArgumentException(rutaModo + ".campos: la lista está vacía");
            }
            Set<String> clavesCampos = claves(campos, rutaModo + ".campos");
            List<Relacion> relaciones = relaciones(lista(m, "relaciones", rutaModo), rutaModo + ".relaciones", clavesCampos);
            Map<String, Object> extremos = objeto(requerido(m, "extremos", rutaModo), rutaModo + ".extremos");
            String minima = texto(extremos, "minima", rutaModo + ".extremos");
            String maxima = texto(extremos, "maxima", rutaModo + ".extremos");
            for (String clave : new String[] {minima, maxima}) {
                if (!clavesCampos.contains(clave)) {
                    throw new IllegalArgumentException(rutaModo + ".extremos: '" + clave + "' no es un campo de " + clavesCampos);
                }
            }
            Map<String, Double> iniciales = valores(objeto(requerido(m, "valores_iniciales", rutaModo), rutaModo + ".valores_iniciales"),
                    rutaModo + ".valores_iniciales");
            mismasClaves(iniciales.keySet(), clavesCampos, rutaModo + ".valores_iniciales");
            porModo.add(new FrecuenciasDeModo(modo, campos, relaciones, minima, maxima, iniciales));
        }
        if (!vistos.equals(idsModo)) {
            throw new IllegalArgumentException(ruta + ".frecuencias: debe definir exactamente los modos " + idsModo
                    + " y define " + vistos);
        }
        return new Filtro(texto(f, "id", ruta), texto(f, "etiqueta", ruta), texto(f, "familia", ruta),
                texto(f, "descripcion", ruta), porModo);
    }

    private static Algoritmo algoritmo(Object valor, String ruta) {
        Map<String, Object> a = objeto(valor, ruta);
        List<Campo> parametros = campos(lista(a, "parametros", ruta), ruta + ".parametros");
        Set<String> clavesParametros = claves(parametros, ruta + ".parametros");
        return new Algoritmo(texto(a, "id", ruta), texto(a, "etiqueta", ruta), texto(a, "descripcion", ruta), parametros,
                relaciones(lista(a, "relaciones", ruta), ruta + ".relaciones", clavesParametros));
    }

    private static List<Campo> campos(List<Object> lista, String ruta) {
        List<Campo> campos = new ArrayList<>();
        for (int i = 0; i < lista.size(); i++) {
            campos.add(campo(lista.get(i), ruta + "[" + i + "]"));
        }
        return campos;
    }

    private static Campo campo(Object valor, String ruta) {
        Map<String, Object> c = objeto(valor, ruta);
        String tipoTexto = texto(c, "tipo", ruta);
        Tipo tipo = switch (tipoTexto) {
            case "entero" -> Tipo.ENTERO;
            case "decimal" -> Tipo.DECIMAL;
            default -> throw new IllegalArgumentException(ruta + ".tipo: '" + tipoTexto + "' no es 'entero' ni 'decimal'");
        };
        Double minimo = numeroOpcional(c, "minimo", ruta);
        Double maximo = numeroOpcional(c, "maximo", ruta);
        Double idealMin = numeroOpcional(c, "ideal_min", ruta);
        Double idealMax = numeroOpcional(c, "ideal_max", ruta);
        if (minimo != null && maximo != null && minimo > maximo) {
            throw new IllegalArgumentException(ruta + ": minimo (" + minimo + ") es mayor que maximo (" + maximo + ")");
        }
        if (idealMin != null && idealMax != null && idealMin > idealMax) {
            throw new IllegalArgumentException(ruta + ": ideal_min (" + idealMin + ") es mayor que ideal_max (" + idealMax + ")");
        }
        double paso = numero(c, "paso", ruta);
        if (paso <= 0) {
            throw new IllegalArgumentException(ruta + ".paso: debe ser positivo y llegó " + paso);
        }
        String serie = textoOpcional(c, "serie", ruta);
        if (serie != null && !"E12".equals(serie)) {
            throw new IllegalArgumentException(ruta + ".serie: '" + serie + "' no está soportada (solo E12)");
        }
        return new Campo(texto(c, "clave", ruta), texto(c, "etiqueta", ruta), tipo, textoOpcional(c, "unidad", ruta),
                minimo, booleano(c, "minimo_exclusivo", ruta), maximo, booleano(c, "maximo_exclusivo", ruta),
                idealMin, idealMax, serie, paso, texto(c, "descripcion", ruta));
    }

    private static List<Relacion> relaciones(List<Object> lista, String ruta, Set<String> clavesValidas) {
        List<Relacion> relaciones = new ArrayList<>();
        for (int i = 0; i < lista.size(); i++) {
            String r = ruta + "[" + i + "]";
            Map<String, Object> m = objeto(lista.get(i), r);
            String izquierda = texto(m, "izquierda", r);
            String derecha = texto(m, "derecha", r);
            String operador = texto(m, "operador", r);
            if (!"<".equals(operador) && !"<=".equals(operador)) {
                throw new IllegalArgumentException(r + ".operador: '" + operador + "' no es '<' ni '<='");
            }
            for (String clave : new String[] {izquierda, derecha}) {
                if (!clavesValidas.contains(clave)) {
                    throw new IllegalArgumentException(r + ": la relación nombra '" + clave + "', que no es un campo de " + clavesValidas);
                }
            }
            relaciones.add(new Relacion(izquierda, operador, derecha, severidad(m, r), texto(m, "mensaje", r)));
        }
        return relaciones;
    }

    private static Severidad severidad(Map<String, Object> padre, String ruta) {
        String s = texto(padre, "severidad", ruta);
        return switch (s) {
            case "error" -> Severidad.ERROR;
            case "aviso" -> Severidad.AVISO;
            default -> throw new IllegalArgumentException(ruta + ".severidad: '" + s + "' no es 'error' ni 'aviso'");
        };
    }

    private static Set<String> claves(List<Campo> campos, String ruta) {
        Set<String> claves = new LinkedHashSet<>();
        for (Campo c : campos) {
            if (!claves.add(c.clave())) {
                throw new IllegalArgumentException(ruta + ": la clave '" + c.clave() + "' está repetida");
            }
        }
        return claves;
    }

    private static void mismasClaves(Set<String> recibidas, Set<String> esperadas, String ruta) {
        if (!recibidas.equals(esperadas)) {
            throw new IllegalArgumentException(ruta + ": las claves " + recibidas + " no coinciden con las esperadas " + esperadas);
        }
    }

    private static Map<String, Double> valores(Map<String, Object> o, String ruta) {
        Map<String, Double> valores = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : o.entrySet()) {
            if (!(e.getValue() instanceof Number n) || Double.isNaN(n.doubleValue()) || Double.isInfinite(n.doubleValue())) {
                throw new IllegalArgumentException(ruta + "." + e.getKey() + ": se esperaba un número finito y llegó " + describir(e.getValue()));
            }
            valores.put(e.getKey(), n.doubleValue());
        }
        return valores;
    }

    private static <T> T buscar(List<T> lista, String id, java.util.function.Function<T, String> idDe) {
        for (T t : lista) {
            if (idDe.apply(t).equals(id)) {
                return t;
            }
        }
        return null;
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
        Object valor = requerido(padre, clave, rutaPadre);
        if (!(valor instanceof String)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba texto y llegó " + describir(valor));
        }
        return (String) valor;
    }

    /** Texto o null; si la clave no viene se considera un error (el backend siempre la manda, aunque sea null). */
    private static String textoOpcional(Map<String, Object> padre, String clave, String rutaPadre) {
        if (!padre.containsKey(clave)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": falta el campo");
        }
        Object valor = padre.get(clave);
        if (valor == null) {
            return null;
        }
        if (!(valor instanceof String)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": se esperaba texto o null y llegó " + describir(valor));
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

    private static Double numeroOpcional(Map<String, Object> padre, String clave, String rutaPadre) {
        if (!padre.containsKey(clave)) {
            throw new IllegalArgumentException(rutaPadre + "." + clave + ": falta el campo");
        }
        return padre.get(clave) == null ? null : numero(padre, clave, rutaPadre);
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

    private static String describir(Object valor) {
        return valor == null ? "null" : valor.getClass().getSimpleName();
    }
}