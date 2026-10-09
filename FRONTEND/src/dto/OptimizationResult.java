package dto;

import esquema.Esquema;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Espejo en Java de CircuitoOptimizadoResponse (Pydantic, backend Python).
 *
 * Corresponde a este JSON:
 * {
 *   "fitness": 0.9559675102947252,
 *   "frecuencias_obtenidas": [
 *     {"clave": "amp_paso_obtenida", "valor": 4.45707941},
 *     {"clave": "amp_aten_obtenida", "valor": 0.0618855648}
 *   ],
 *   "componentes_optimizados": [
 *     {"nombre": "C1_1", "tipo": "C", "valor": 6.8e-08, "conexion_tierra": false},
 *     ...
 *   ],
 *   "grafica_png_base64": "..."
 * }
 */
public class OptimizationResult {
    public double fitness;

    /** Conserva el orden de llegada: "fc_obtenida", o "amp_paso_obtenida"/"amp_aten_obtenida". */
    public Map<String, Double> frecuenciasObtenidas = new LinkedHashMap<>();

    public List<ComponenteDTO> componentesOptimizados;

    public String graficaPngBase64;

    /**
     * Esquema (dibujo) del circuito OPTIMIZADO, con los valores finales de cada componente. Es null si
     * el backend no lo envió (versión anterior) o no se pudo construir/interpretar; en ese caso el
     * circuito se dibuja con el camino legacy y {@link #esquemaError} explica por qué.
     */
    public Esquema esquema;

    /** Motivo por el que no hay {@link #esquema} (null si lo hay o si el backend no dijo nada). */
    public String esquemaError;
}