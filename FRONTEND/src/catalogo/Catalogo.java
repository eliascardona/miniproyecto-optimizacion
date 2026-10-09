package catalogo;

import java.util.List;
import java.util.Map;

/**
 * Catálogo de lo que el backend sabe optimizar (GET /api/catalogo): qué filtros, algoritmos y modos
 * existen, qué datos pide cada uno y con qué límites, y qué combinaciones filtro × algoritmo corren de
 * verdad. Con él se arma el formulario y la petición SIN que este cliente conozca ningún filtro ni
 * algoritmo de antemano: agregar uno en el backend no obliga a tocar el frontend.
 *
 * Todo es inmutable. Se construye con {@link CatalogoParser}.
 *
 * Qué depende de qué (verificado contra el código del backend):
 *   · los HIPERPARÁMETROS dependen solo del ALGORITMO      -> {@link Algoritmo#parametros()}
 *   · las FRECUENCIAS objetivo dependen del FILTRO y el MODO -> {@link Filtro#frecuencias(String)}
 *   · entorno físico y barrido son comunes a todo            -> {@link #entorno()} y {@link #barrido()}
 */
public record Catalogo(
        int version,
        List<Modo> modos,
        List<Campo> entorno,
        Barrido barrido,
        MargenDecada margenDecada,
        List<Filtro> filtros,
        List<Algoritmo> algoritmos,
        List<Combinacion> combinaciones) {

    public static final int VERSION_SOPORTADA = 1;

    public Catalogo {
        modos = List.copyOf(modos);
        entorno = List.copyOf(entorno);
        filtros = List.copyOf(filtros);
        algoritmos = List.copyOf(algoritmos);
        combinaciones = List.copyOf(combinaciones);
    }

    /** "error" bloquea el envío; "aviso" solo advierte. */
    public enum Severidad { ERROR, AVISO }

    public enum Tipo { ENTERO, DECIMAL }

    public record Modo(String id, String etiqueta, String descripcion) {
        @Override
        public String toString() {
            return etiqueta;
        }
    }

    /**
     * Un dato numérico que pide la API. {@code minimo}/{@code maximo} son límites DUROS (null = sin límite);
     * {@code idealMin}/{@code idealMax} son el rango RECOMENDADO (fuera de él solo se avisa); {@code serie}
     * es una serie comercial que se pide (hoy solo "E12"; fuera de ella solo se avisa).
     */
    public record Campo(
            String clave, String etiqueta, Tipo tipo, String unidad,
            Double minimo, boolean minimoExclusivo, Double maximo, boolean maximoExclusivo,
            Double idealMin, Double idealMax, String serie, double paso, String descripcion) {

        /** "Tensión de la fuente (V)". */
        public String etiquetaConUnidad() {
            return unidad == null || unidad.isBlank() ? etiqueta : etiqueta + " (" + unidad + ")";
        }

        /**
         * El número tal como debe viajar en el JSON: Long para un campo entero, Double para uno decimal.
         * Un entero con decimales (30.5) es un error de programación o de captura, no se redondea en silencio.
         */
        public Number normalizar(double valor) {
            if (Double.isNaN(valor) || Double.isInfinite(valor)) {
                throw new IllegalArgumentException(clave + ": no es un número finito");
            }
            if (tipo == Tipo.ENTERO) {
                if (valor != Math.rint(valor)) {
                    throw new IllegalArgumentException(clave + " debe ser entero y llegó " + valor);
                }
                return (long) valor;
            }
            return valor;
        }
    }

    /** Compara dos campos entre sí (orden de frecuencias, elitismo &lt; población...). */
    public record Relacion(String izquierda, String operador, String derecha, Severidad severidad, String mensaje) {
        public boolean seCumple(double valorIzquierda, double valorDerecha) {
            return "<".equals(operador) ? valorIzquierda < valorDerecha : valorIzquierda <= valorDerecha;
        }
    }

    public record Barrido(List<Campo> campos, List<Relacion> relaciones) {
        public Barrido {
            campos = List.copyOf(campos);
            relaciones = List.copyOf(relaciones);
        }
    }

    /** Regla: la frecuencia de interés más baja ≥ f_inicial × factor y la más alta ≤ f_final / factor. */
    public record MargenDecada(double factor, Severidad severidad, String descripcion) {}

    /** Las frecuencias objetivo de un filtro en un modo, en orden ascendente de frecuencia. */
    public record FrecuenciasDeModo(
            String modo, List<Campo> campos, List<Relacion> relaciones,
            String claveMinima, String claveMaxima, Map<String, Double> valoresIniciales) {
        public FrecuenciasDeModo {
            campos = List.copyOf(campos);
            relaciones = List.copyOf(relaciones);
            valoresIniciales = Map.copyOf(valoresIniciales);
        }
    }

    public record Filtro(String id, String etiqueta, String familia, String descripcion,
                         List<FrecuenciasDeModo> frecuencias) {
        public Filtro {
            frecuencias = List.copyOf(frecuencias);
        }

        public FrecuenciasDeModo frecuencias(String modo) {
            for (FrecuenciasDeModo f : frecuencias) {
                if (f.modo().equals(modo)) {
                    return f;
                }
            }
            throw new IllegalArgumentException("El filtro '" + id + "' no define frecuencias para el modo '" + modo + "'");
        }

        @Override
        public String toString() {
            return etiqueta;
        }
    }

    public record Algoritmo(String id, String etiqueta, String descripcion, List<Campo> parametros,
                            List<Relacion> relaciones) {
        public Algoritmo {
            parametros = List.copyOf(parametros);
            relaciones = List.copyOf(relaciones);
        }

        @Override
        public String toString() {
            return etiqueta;
        }
    }

    public record Combinacion(String filtro, String algoritmo, boolean disponible, Map<String, Double> valoresIniciales) {
        public Combinacion {
            valoresIniciales = Map.copyOf(valoresIniciales);
        }
    }

    // ------------------------------------------------------------------
    // Consultas
    // ------------------------------------------------------------------

    public Filtro filtro(String id) {
        for (Filtro f : filtros) {
            if (f.id().equals(id)) {
                return f;
            }
        }
        throw new IllegalArgumentException("El catálogo no tiene el filtro '" + id + "'");
    }

    public Algoritmo algoritmo(String id) {
        for (Algoritmo a : algoritmos) {
            if (a.id().equals(id)) {
                return a;
            }
        }
        throw new IllegalArgumentException("El catálogo no tiene el algoritmo '" + id + "'");
    }

    public Modo modo(String id) {
        for (Modo m : modos) {
            if (m.id().equals(id)) {
                return m;
            }
        }
        throw new IllegalArgumentException("El catálogo no tiene el modo '" + id + "'");
    }

    /** La combinación (filtro, algoritmo), o null si el catálogo no la menciona. */
    public Combinacion combinacion(String filtro, String algoritmo) {
        for (Combinacion c : combinaciones) {
            if (c.filtro().equals(filtro) && c.algoritmo().equals(algoritmo)) {
                return c;
            }
        }
        return null;
    }

    public boolean estaDisponible(String filtro, String algoritmo) {
        Combinacion c = combinacion(filtro, algoritmo);
        return c != null && c.disponible();
    }

    /** Los algoritmos que el servidor ejecuta de verdad para ese filtro, en el orden del catálogo. */
    public List<Algoritmo> algoritmosDisponibles(String filtro) {
        return algoritmos.stream().filter(a -> estaDisponible(filtro, a.id())).toList();
    }

    /** Los filtros que tienen al menos un algoritmo disponible, en el orden del catálogo. */
    public List<Filtro> filtrosDisponibles() {
        return filtros.stream().filter(f -> !algoritmosDisponibles(f.id()).isEmpty()).toList();
    }
}