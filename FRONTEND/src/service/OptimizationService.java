package service;

import api_client.CircuitApiClient;
import catalogo.Catalogo;
import catalogo.Problema;
import catalogo.ValidadorPeticion;
import dto.OptimizationResult;
import dto.PeticionOptimizacion;
import format_converter.FormatConverter;
import model.Circuit;
import model.Element;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Fachada de la optimización: junta las tres partes del caso de uso
 * "generar un circuito con la API".
 *
 *   1. catalogo()        -> qué filtros, algoritmos y parámetros existen. Se pide al
 *                           backend la primera vez y se guarda mientras la aplicación
 *                           siga abierta. Bloqueante la primera vez: fuera del EDT.
 *   2. optimize(...)     -> llamada HTTP (delegada a CircuitApiClient).
 *                           Bloqueante: llamar fuera del EDT (SwingWorker).
 *   3. applyResult(...)  -> traduce la respuesta al modelo de dibujo y actualiza
 *                           Circuit. Debe llamarse en el EDT, porque el modelo lo
 *                           consumen los paneles Swing.
 *
 * No conoce ninguna clase de view.* ni de javax.swing: los diálogos, el
 * SwingWorker y el refresco de paneles son responsabilidad de quien la usa
 * (controller.action.GenerateCircuitAction).
 */
public class OptimizationService {

    private final CircuitApiClient apiClient;
    private volatile Catalogo catalogo;

    public OptimizationService() {
        this(new CircuitApiClient());
    }

    /** Constructor para inyectar un cliente falso en pruebas. */
    public OptimizationService(CircuitApiClient apiClient) {
        this.apiClient = apiClient;
    }

    /**
     * El catálogo del backend. Si ya se pidió con éxito, devuelve el guardado (no vuelve a la red);
     * si falló, el siguiente intento vuelve a pedirlo. Bloqueante la primera vez.
     */
    public Catalogo catalogo() throws CircuitApiClient.ApiException {
        Catalogo guardado = catalogo;
        if (guardado == null) {
            guardado = apiClient.obtenerCatalogo();
            catalogo = guardado;
        }
        return guardado;
    }

    /** El catálogo ya guardado, o null si todavía no se ha pedido. No usa la red: se puede llamar desde el EDT. */
    public Catalogo catalogoEnMemoria() {
        return catalogo;
    }

    /** Olvida el catálogo guardado (p. ej. si el usuario cambió de servidor o el backend se actualizó). */
    public void olvidarCatalogo() {
        catalogo = null;
    }

    /**
     * Optimiza lo que describe `request`. Antes de enviar se revisa contra el catálogo: una petición con
     * errores (clave de otro algoritmo, valor fuera de límites duros...) no sale del cliente. El
     * formulario ya lo revisa, así que esto solo protege a quien llame al servicio sin pasar por él.
     *
     * @throws IllegalArgumentException si la petición tiene errores según el catálogo.
     */
    public OptimizationResult optimize(PeticionOptimizacion request) throws CircuitApiClient.ApiException {
        List<Problema> errores = ValidadorPeticion.validar(catalogo(), request).stream().filter(Problema::esError).toList();
        if (!errores.isEmpty()) {
            throw new IllegalArgumentException("La petición no es válida: "
                    + errores.stream().map(Problema::mensaje).collect(Collectors.joining(" ")));
        }
        return apiClient.optimizar(request);
    }

    /**
     * Aplica el resultado de la API al modelo de dibujo. Hay dos caminos:
     *
     *   - Con ESQUEMA (lo normal con el backend actual): el circuito se guarda tal cual, listo para
     *     el renderer vectorial. No pasa por FormatConverter, así que no depende de las tablas
     *     legacy ni del tipo de filtro (op-amps y ramas paralelas incluidos). El "coded circuit" se
     *     sustituye por un resumen legible de los componentes.
     *   - SIN esquema (backend anterior, o esquema que no se pudo construir/leer): camino legacy,
     *     que traduce los componentes a Element con FormatConverter y los vuelca en circuit.
     *
     * @throws IllegalArgumentException (solo camino legacy) si algún componente no se puede
     *         traducir (tipo desconocido o valor fuera de ComponentTables).
     */
    public void applyResult(OptimizationResult result, Circuit circuit) {
        if (result.esquema != null) {
            applySchematic(result, circuit);
            return;
        }
        if (result.esquemaError != null) {
            System.err.println("[AVISO] Sin esquema; se dibuja con el camino legacy. Motivo: " + result.esquemaError);
        }
        applyLegacy(result, circuit);
    }

    private void applySchematic(OptimizationResult result, Circuit circuit) {
        circuit.clearCircuit();                       // también descarta el esquema anterior
        circuit.setSchematic(result.esquema);

        circuit.setCodedCircuit(result.esquema.resumen());
        circuit.setFitness(result.fitness);
        circuit.setElements(result.esquema.numeroComponentes());

        // Simulation.values se llena en una fase posterior con respuesta_frecuencia; mientras tanto
        // se deja vacío para no dibujar una curva inventada (la real es el PNG de la respuesta).
        circuit.getSimulation().clearValues();
    }

    private void applyLegacy(OptimizationResult result, Circuit circuit) {
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