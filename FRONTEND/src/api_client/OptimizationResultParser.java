package api_client;

import dto.ComponenteDTO;
import dto.OptimizationResult;
import esquema.Esquema;
import esquema.EsquemaParser;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Convierte el cuerpo JSON de POST /api/optimizar en un {@link OptimizationResult}, y el de
 * GET /api/circuitos/{filtro} en un {@link Esquema}. Antes vivía como método privado de
 * CircuitApiClient; está aparte para poder probarlo con respuestas reales sin levantar HTTP.
 *
 * Tolerante con lo que sobra (campos que este cliente no conoce se ignoran) y estricto con lo que
 * necesita. Una regla importante: un esquema ilegible NUNCA descarta el resto del resultado; se
 * deja {@code esquema = null} y se explica en {@code esquemaError} (ver OptimizationService).
 */
public final class OptimizationResultParser {
    private OptimizationResultParser() {}

    @SuppressWarnings("unchecked")
    public static OptimizationResult parse(String json) {
        Map<String, Object> root = MiniJsonParser.parseObject(json);

        OptimizationResult result = new OptimizationResult();
        result.fitness = numero(root.get("fitness"), "fitness");

        List<Object> frecuenciasObtenidas = (List<Object>) root.get("frecuencias_obtenidas");
        if (frecuenciasObtenidas != null) {
            for (Object item : frecuenciasObtenidas) {
                Map<String, Object> par = (Map<String, Object>) item;
                String clave = (String) par.get("clave");
                double valor = numero(par.get("valor"), "frecuencias_obtenidas[].valor");
                result.frecuenciasObtenidas.put(clave, valor);
            }
        }

        List<Object> componentesOptimizados = (List<Object>) root.get("componentes_optimizados");
        List<ComponenteDTO> componentes = new ArrayList<>();
        if (componentesOptimizados != null) {
            for (Object item : componentesOptimizados) {
                Map<String, Object> c = (Map<String, Object>) item;

                ComponenteDTO dto = new ComponenteDTO();
                dto.nombre = (String) c.get("nombre");
                dto.tipo = (String) c.get("tipo");
                dto.valor = numero(c.get("valor"), "componentes_optimizados[].valor");
                dto.conexionTierra = Boolean.TRUE.equals(c.get("conexion_tierra"));
                componentes.add(dto);
            }
        }
        result.componentesOptimizados = componentes;

        result.graficaPngBase64 = (String) root.get("grafica_png_base64");

        Object motivo = root.get("esquema_error");
        result.esquemaError = motivo instanceof String texto && !texto.isBlank() ? texto : null;

        Object esquemaCrudo = root.get("esquema");
        if (esquemaCrudo != null) {
            try {
                result.esquema = EsquemaParser.parse(esquemaCrudo);
                result.esquemaError = null;
            } catch (RuntimeException e) {
                result.esquema = null;
                result.esquemaError = "No se pudo interpretar el esquema recibido: " + e.getMessage();
            }
        }

        return result;
    }

    /** Cuerpo de GET /api/circuitos/{filtro}. Lanza IllegalArgumentException si no es un esquema válido. */
    public static Esquema parseEsquema(String json) {
        return EsquemaParser.parse(MiniJsonParser.parseObject(json));
    }

    private static double numero(Object value, String campo) {
        if (!(value instanceof Number)) {
            throw new IllegalArgumentException("Se esperaba un número en '" + campo + "' y llegó: " + value);
        }
        return ((Number) value).doubleValue();
    }
}