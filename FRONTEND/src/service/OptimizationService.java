package service;

import api_client.CircuitApiClient;
import dto.CircuitRequest;
import dto.OptimizationResult;
import format_converter.FormatConverter;
import model.Circuit;
import model.Element;

import java.util.List;

/**
 * Fachada de la optimización: junta las dos mitades del caso de uso
 * "generar un circuito con la API".
 *
 *   1. optimize(...)     -> llamada HTTP (delegada a CircuitApiClient).
 *                           Bloqueante: llamar fuera del EDT (SwingWorker).
 *   2. applyResult(...)  -> traduce la respuesta al modelo de dibujo
 *                           (FormatConverter -> Element) y actualiza Circuit.
 *                           Debe llamarse en el EDT, porque el modelo lo
 *                           consumen los paneles Swing.
 *
 * No conoce ninguna clase de view.* ni de javax.swing: los diálogos, el
 * SwingWorker y el refresco de paneles son responsabilidad de quien la usa
 * (controller.action.GenerateCircuitAction).
 */
public class OptimizationService {

    private final CircuitApiClient apiClient;

    public OptimizationService() {
        this(new CircuitApiClient());
    }

    /** Constructor para inyectar un cliente falso en pruebas. */
    public OptimizationService(CircuitApiClient apiClient) {
        this.apiClient = apiClient;
    }

    public OptimizationResult optimize(CircuitRequest request) throws CircuitApiClient.ApiException {
        return apiClient.optimizarPasaAltas(request);
    }

    /**
     * Aplica el resultado de la API al modelo de dibujo: construye la lista
     * de Element a partir de los componentes optimizados, la vuelca en
     * circuit (vía addElement, para que Circuit siga calculando bien el
     * ancho de la imagen) y reconstruye el string "coded circuit".
     *
     * @throws IllegalArgumentException si algún componente no se puede
     *         traducir (tipo desconocido o valor fuera de ComponentTables).
     */
    public void applyResult(OptimizationResult result, Circuit circuit) {
        // Se convierte ANTES de tocar el circuito: si FormatConverter lanza,
        // el circuito actual queda intacto en vez de a medias.
        List<Element> elementos = FormatConverter.convertir(result.componentesOptimizados);

        circuit.clearCircuit();
        for (Element elemento : elementos) {
            circuit.addElement(elemento);
        }

        circuit.setCodedCircuit(FormatConverter.toCodedCircuitString(elementos));
        circuit.setFitness(result.fitness);
        circuit.setElements(elementos.size());
        // circuit.order no se toca (ver nota original en MainController:
        // su semántica no calza con un filtro de 4to orden).

        // La API no devuelve el barrido punto a punto, solo escalares + PNG,
        // así que Simulation.values se deja vacío a propósito (no se dibuja
        // una curva inventada). La curva real es el PNG de la respuesta.
        circuit.getSimulation().clearValues();
    }
}
