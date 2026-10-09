package catalogo;

import catalogo.Catalogo.Algoritmo;
import catalogo.Catalogo.Campo;
import catalogo.Catalogo.Filtro;
import catalogo.Catalogo.FrecuenciasDeModo;
import catalogo.Catalogo.Relacion;
import catalogo.Catalogo.Severidad;
import catalogo.Catalogo.Tipo;
import dto.PeticionOptimizacion;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Aplica a una {@link PeticionOptimizacion} las reglas que declara el {@link Catalogo}. No tiene ninguna
 * regla escrita a mano por filtro o algoritmo: todo sale del catálogo, así que cubre las 16 combinaciones
 * (y las que se agreguen) sin cambios.
 *
 * Qué revisa, en este orden:
 *   1. que la combinación exista y esté disponible, y que el modo exista;
 *   2. que vengan EXACTAMENTE las claves que pide el catálogo (ni de más ni de menos);
 *   3. por campo: límites duros (ERROR), enteros con decimales (ERROR), rango recomendado y serie E12 (AVISO);
 *   4. relaciones entre campos: barrido, orden de las frecuencias y las propias del algoritmo (con la severidad
 *      que declara cada una);
 *   5. el margen de una década entre las frecuencias de interés y el barrido (con la severidad de la regla).
 *
 * Los ERROR bloquean el envío; los AVISO se muestran y el usuario decide.
 */
public final class ValidadorPeticion {
    private ValidadorPeticion() {}

    public static List<Problema> validar(Catalogo catalogo, PeticionOptimizacion p) {
        List<Problema> problemas = new ArrayList<>();

        Filtro filtro = buscarFiltro(catalogo, p.filtro());
        Algoritmo algoritmo = buscarAlgoritmo(catalogo, p.algoritmo());
        FrecuenciasDeModo frecuencias = null;

        if (filtro == null) {
            problemas.add(error("combinacion", "El catálogo no tiene el filtro '" + p.filtro() + "'."));
        }
        if (algoritmo == null) {
            problemas.add(error("combinacion", "El catálogo no tiene el algoritmo '" + p.algoritmo() + "'."));
        }
        if (filtro != null && algoritmo != null && !catalogo.estaDisponible(filtro.id(), algoritmo.id())) {
            problemas.add(error("combinacion", "El servidor no ejecuta todavía " + algoritmo.etiqueta()
                    + " con el filtro " + filtro.etiqueta() + "."));
        }
        boolean modoValido = catalogo.modos().stream().anyMatch(m -> m.id().equals(p.modo()));
        if (!modoValido) {
            problemas.add(error("modo", "El modo '" + p.modo() + "' no existe."));
        } else if (filtro != null) {
            frecuencias = filtro.frecuencias(p.modo());
        }

        // 1) Entorno y barrido son comunes a todo.
        revisarGrupo(catalogo.entorno(), p.entorno(), problemas);
        revisarGrupo(catalogo.barrido().campos(), p.barrido(), problemas);
        revisarRelaciones(catalogo.barrido().relaciones(), p.barrido(), problemas);

        // 2) Frecuencias: dependen del filtro y del modo.
        if (frecuencias != null) {
            revisarGrupo(frecuencias.campos(), p.frecuencias(), problemas);
            revisarRelaciones(frecuencias.relaciones(), p.frecuencias(), problemas);
            revisarMargenDecada(catalogo, frecuencias, p, problemas);
        }

        // 3) Hiperparámetros: dependen solo del algoritmo.
        if (algoritmo != null) {
            revisarGrupo(algoritmo.parametros(), p.parametros(), problemas);
            revisarRelaciones(algoritmo.relaciones(), p.parametros(), problemas);
        }

        return problemas;
    }

    public static boolean hayErrores(List<Problema> problemas) {
        return problemas.stream().anyMatch(Problema::esError);
    }

    // ------------------------------------------------------------------
    // Campos
    // ------------------------------------------------------------------

    private static void revisarGrupo(List<Campo> campos, Map<String, Number> valores, List<Problema> problemas) {
        Set<String> esperadas = new LinkedHashSet<>();
        for (Campo campo : campos) {
            esperadas.add(campo.clave());
            Number valor = valores.get(campo.clave());
            if (valor == null) {
                problemas.add(error(campo.clave(), "Falta " + campo.etiqueta() + " (" + campo.clave() + ")."));
                continue;
            }
            revisarCampo(campo, valor.doubleValue(), problemas);
        }
        for (String clave : valores.keySet()) {
            if (!esperadas.contains(clave)) {
                problemas.add(error(clave, "La clave '" + clave + "' no corresponde a esta combinación (se esperaba "
                        + esperadas + ")."));
            }
        }
    }

    private static void revisarCampo(Campo campo, double v, List<Problema> problemas) {
        String nombre = campo.etiqueta() + " (" + campo.clave() + ")";
        String unidad = campo.unidad() == null ? "" : " " + campo.unidad();

        if (Double.isNaN(v) || Double.isInfinite(v)) {
            problemas.add(error(campo.clave(), nombre + " no es un número válido."));
            return;
        }
        if (campo.tipo() == Tipo.ENTERO && v != Math.rint(v)) {
            problemas.add(error(campo.clave(), nombre + " debe ser un número entero y es " + num(v) + "."));
        }

        boolean duroOk = true;
        Double min = campo.minimo();
        if (min != null && (v < min || (campo.minimoExclusivo() && v == min))) {
            duroOk = false;
            problemas.add(error(campo.clave(), nombre + " debe ser " + (campo.minimoExclusivo() ? "mayor que " : "al menos ")
                    + num(min) + unidad + " y es " + num(v) + "."));
        }
        Double max = campo.maximo();
        if (max != null && (v > max || (campo.maximoExclusivo() && v == max))) {
            duroOk = false;
            problemas.add(error(campo.clave(), nombre + " debe ser " + (campo.maximoExclusivo() ? "menor que " : "como máximo ")
                    + num(max) + unidad + " y es " + num(v) + "."));
        }

        // Los avisos solo tienen sentido si el valor ya pasó las reglas duras (si no, el error ya lo dice todo).
        if (!duroOk) {
            return;
        }
        Double idealMin = campo.idealMin();
        Double idealMax = campo.idealMax();
        if ((idealMin != null && v < idealMin) || (idealMax != null && v > idealMax)) {
            String rango;
            if (idealMin != null && idealMax != null) {
                rango = num(idealMin) + " a " + num(idealMax) + unidad;
            } else if (idealMin != null) {
                rango = "desde " + num(idealMin) + unidad;
            } else {
                rango = "hasta " + num(idealMax) + unidad;
            }
            problemas.add(aviso(campo.clave(), nombre + " = " + num(v) + " está fuera del rango recomendado (" + rango + ")."));
        }
        if ("E12".equals(campo.serie()) && !SerieE12.contiene(v)) {
            problemas.add(aviso(campo.clave(), nombre + " = " + num(v) + " no pertenece a la serie comercial E12."));
        }
    }

    // ------------------------------------------------------------------
    // Relaciones y margen
    // ------------------------------------------------------------------

    private static void revisarRelaciones(List<Relacion> relaciones, Map<String, Number> valores, List<Problema> problemas) {
        for (Relacion r : relaciones) {
            Number izquierda = valores.get(r.izquierda());
            Number derecha = valores.get(r.derecha());
            if (izquierda == null || derecha == null) {
                continue;               // la falta de la clave ya se informó en revisarGrupo
            }
            double a = izquierda.doubleValue();
            double b = derecha.doubleValue();
            if (Double.isNaN(a) || Double.isNaN(b) || r.seCumple(a, b)) {
                continue;
            }
            problemas.add(new Problema(r.severidad(), r.izquierda(),
                    r.mensaje() + " (" + r.izquierda() + " = " + num(a) + ", " + r.derecha() + " = " + num(b) + ")"));
        }
    }

    private static void revisarMargenDecada(Catalogo catalogo, FrecuenciasDeModo frecuencias, PeticionOptimizacion p,
                                            List<Problema> problemas) {
        Number inicial = p.barrido().get("f_inicial");
        Number fin = p.barrido().get("f_final");
        Number minima = p.frecuencias().get(frecuencias.claveMinima());
        Number maxima = p.frecuencias().get(frecuencias.claveMaxima());
        if (inicial == null || fin == null || minima == null || maxima == null) {
            return;
        }
        double factor = catalogo.margenDecada().factor();
        Severidad severidad = catalogo.margenDecada().severidad();

        // Si el valor ya es un error (p. ej. 0 Hz), avisar además del margen sería ruido.
        if (minima.doubleValue() < inicial.doubleValue() * factor && !hayError(problemas, frecuencias.claveMinima())) {
            problemas.add(new Problema(severidad, frecuencias.claveMinima(),
                    "La frecuencia más baja (" + frecuencias.claveMinima() + " = " + num(minima.doubleValue())
                            + " Hz) debería quedar al menos una década (×" + num(factor) + ") por encima del inicio del barrido ("
                            + num(inicial.doubleValue()) + " Hz), o la pendiente se mide fuera del rango simulado."));
        }
        if (maxima.doubleValue() > fin.doubleValue() / factor && !hayError(problemas, frecuencias.claveMaxima())) {
            problemas.add(new Problema(severidad, frecuencias.claveMaxima(),
                    "La frecuencia más alta (" + frecuencias.claveMaxima() + " = " + num(maxima.doubleValue())
                            + " Hz) debería quedar al menos una década (÷" + num(factor) + ") por debajo del final del barrido ("
                            + num(fin.doubleValue()) + " Hz), o la pendiente se mide fuera del rango simulado."));
        }
    }

    // ------------------------------------------------------------------
    // Utilidades
    // ------------------------------------------------------------------

    private static boolean hayError(List<Problema> problemas, String clave) {
        return problemas.stream().anyMatch(q -> q.esError() && q.clave().equals(clave));
    }

    private static Filtro buscarFiltro(Catalogo c, String id) {
        return c.filtros().stream().filter(f -> f.id().equals(id)).findFirst().orElse(null);
    }

    private static Algoritmo buscarAlgoritmo(Catalogo c, String id) {
        return c.algoritmos().stream().filter(a -> a.id().equals(id)).findFirst().orElse(null);
    }

    private static Problema error(String clave, String mensaje) {
        return new Problema(Severidad.ERROR, clave, mensaje);
    }

    private static Problema aviso(String clave, String mensaje) {
        return new Problema(Severidad.AVISO, clave, mensaje);
    }

    /** 5 → "5"; 0.001 → "0.001"; 4294967295 → "4294967295"; 1.5E-4 → "0.00015". Sin separadores de miles. */
    static String num(double v) {
        if (v == Math.rint(v) && Math.abs(v) < 1e15) {
            return String.valueOf((long) v);
        }
        String s = String.format(Locale.ROOT, "%.8f", v);
        s = s.replaceAll("0+$", "");
        return s.endsWith(".") ? s.substring(0, s.length() - 1) : s;
    }
}