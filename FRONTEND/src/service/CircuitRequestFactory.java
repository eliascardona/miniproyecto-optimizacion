package service;

import api_client.ApiConfig;
import dto.CircuitRequest;
import dto.GeneticParameters;
import model.Algoritmo;
import model.Circuit;
import model.IdealFilter;
import model.Simulation;
import model.TipoFiltro;

/**
 * Arma el dto.CircuitRequest a partir del estado actual del modelo.
 *
 * Antes esta lógica vivía en MainController.construirCircuitRequest y leía
 * los JSpinner directamente. Ahora solo conoce modelo (Circuit, Simulation,
 * IdealFilter) y valores planos (GeneticParameters): cero dependencias de
 * Swing.
 *
 * De dónde sale cada dato del request:
 *   - algoritmo               -> el enum elegido por el usuario
 *   - filtro                  -> IdealFilter.type FINAL (puede haber cambiado
 *                                en vivo dentro de GenerateCircuitPanel)
 *   - modo                    -> ApiConfig.MODO_AVANZADO
 *   - v_fuente/r_fuente/r_carga, f_inicial/f_final -> Simulation
 *   - f_aten/f_paso           -> IdealFilter
 *   - hiperparámetros del AG  -> GeneticParameters
 *
 * @throws IllegalArgumentException (lanzada por el constructor de
 *         CircuitRequest) si algún valor está fuera de rango.
 */
public class CircuitRequestFactory {

    public CircuitRequest create(Circuit circuit, Algoritmo algoritmo, GeneticParameters params) {
        Simulation simulacion = circuit.getSimulation();
        IdealFilter idealFilter = circuit.getIdealFilter();
        TipoFiltro tipoFiltroFinal = TipoFiltro.fromIdealFilterType(idealFilter.getType());

        return new CircuitRequest(
                algoritmo.valorApi,
                tipoFiltroFinal.valorApi,
                ApiConfig.MODO_AVANZADO,
                simulacion.getSupplyVoltage(),
                simulacion.getSupplyResistance(),
                simulacion.getLoadResistance(),
                simulacion.getInitialFrequency(),
                simulacion.getFinalFrequency(),
                idealFilter.getAttenuationFrequency(),
                idealFilter.getPassageFrequency(),
                params.tamPoblacion(),
                params.numGeneraciones(),
                params.probCruce(),
                params.probMutacion(),
                params.elitismo(),
                params.torneoK()
        );
    }
}
