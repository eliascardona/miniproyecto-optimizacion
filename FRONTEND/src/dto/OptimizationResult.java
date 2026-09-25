package dto;

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
}