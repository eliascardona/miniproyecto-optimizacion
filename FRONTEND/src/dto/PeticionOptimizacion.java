package dto;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Lo que el usuario pidió optimizar: UN filtro con UN algoritmo en UN modo, con todos los valores que la
 * API necesita. Reemplaza al antiguo CircuitRequest (16 campos fijos para AG + pasa-altas): aquí los
 * datos viajan en mapas clave → valor, cuyas claves y tipos dicta el catálogo (catalogo.Catalogo), así
 * que sirve igual para las 16 combinaciones.
 *
 * Los valores son Long (campos enteros) o Double (decimales) para que el JSON salga como la API lo espera
 * ("tam_poblacion": 30, no 30.0). Es inmutable; los mapas conservan el orden de inserción.
 *
 * Forma del JSON que produce {@link #aCuerpo()} (POST /api/optimizar):
 *
 * {
 *   "filtro": "rechaza_banda",
 *   "algoritmo": "enjambre_particulas",
 *   "entorno": {                                   <- el "entorno" de nivel superior es la configuración completa
 *     "modo": "AVANZADO",
 *     "entorno": { "v_fuente": 5, "r_fuente": 470, "r_carga": 470 },
 *     "barrido_ac": { "f_inicial": 1, "f_final": 100000 },
 *     "parametros_optimizador": [ { "clave": "num_particulas", "valor": 30 }, ... ],
 *     "frecuencias": [ { "clave": "f_paso_1", "valor": 10 }, ... ]
 *   }
 * }
 */
public record PeticionOptimizacion(
        String filtro,
        String algoritmo,
        String modo,
        Map<String, Number> entorno,
        Map<String, Number> barrido,
        Map<String, Number> parametros,
        Map<String, Number> frecuencias) {

    public PeticionOptimizacion {
        requiereTexto(filtro, "filtro");
        requiereTexto(algoritmo, "algoritmo");
        requiereTexto(modo, "modo");
        entorno = copiar(entorno, "entorno");
        barrido = copiar(barrido, "barrido");
        parametros = copiar(parametros, "parametros");
        frecuencias = copiar(frecuencias, "frecuencias");
    }

    /** El cuerpo JSON como estructura de Map / List, listo para api_client.MiniJsonParser.write. */
    public Map<String, Object> aCuerpo() {
        Map<String, Object> configuracion = new LinkedHashMap<>();
        configuracion.put("modo", modo);
        configuracion.put("entorno", new LinkedHashMap<String, Object>(entorno));
        configuracion.put("barrido_ac", new LinkedHashMap<String, Object>(barrido));
        configuracion.put("parametros_optimizador", paresClaveValor(parametros));
        configuracion.put("frecuencias", paresClaveValor(frecuencias));

        Map<String, Object> cuerpo = new LinkedHashMap<>();
        cuerpo.put("filtro", filtro);
        cuerpo.put("algoritmo", algoritmo);
        cuerpo.put("entorno", configuracion);
        return cuerpo;
    }

    private static List<Object> paresClaveValor(Map<String, Number> valores) {
        List<Object> pares = new ArrayList<>();
        for (Map.Entry<String, Number> e : valores.entrySet()) {
            Map<String, Object> par = new LinkedHashMap<>();
            par.put("clave", e.getKey());
            par.put("valor", e.getValue());
            pares.add(par);
        }
        return pares;
    }

    private static Map<String, Number> copiar(Map<String, Number> original, String nombre) {
        if (original == null) {
            throw new IllegalArgumentException(nombre + " no puede ser null");
        }
        for (Map.Entry<String, Number> e : original.entrySet()) {
            if (e.getValue() == null) {
                throw new IllegalArgumentException(nombre + "." + e.getKey() + " no puede ser null");
            }
        }
        return Collections.unmodifiableMap(new LinkedHashMap<>(original));
    }

    private static void requiereTexto(String valor, String nombre) {
        if (valor == null || valor.isBlank()) {
            throw new IllegalArgumentException(nombre + " no puede estar vacío.");
        }
    }
}