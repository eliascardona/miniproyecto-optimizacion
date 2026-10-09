package service;

import catalogo.Catalogo;
import catalogo.Catalogo.FrecuenciasDeModo;
import dto.PeticionOptimizacion;
import model.IdealFilter;

/**
 * Pasa los objetivos de una petición al modelo IdealFilter, que es lo que dibuja la plantilla ideal en el
 * SimulationPanel principal.
 *
 * IdealFilter solo sabe de DOS frecuencias (paso y atenuación) y un tipo (pasa bajas / pasa altas), así que
 * solo puede representar un filtro de corte simple en modo avanzado. Para cualquier otro caso (modo básico,
 * pasa banda, rechaza banda) no se toca y el método devuelve false: mostrar una plantilla de otro filtro
 * sería peor que no mostrar ninguna. La lista de objetivos que sí cubre esos casos llega con la curva de
 * respuesta nativa.
 *
 * El tipo no se deduce del nombre del filtro: sale de la relación de orden del propio catálogo (si la
 * atenuación va antes que el paso, la banda de paso está en alta frecuencia: pasa altas).
 */
public final class ObjetivosAIdealFilter {
    private ObjetivosAIdealFilter() {}

    private static final int PASA_BAJAS = 0;       // IdealFilter.type
    private static final int PASA_ALTAS = 1;

    /** @return true si se actualizó el IdealFilter; false si esta petición no se puede representar con él. */
    public static boolean sincronizar(Catalogo catalogo, PeticionOptimizacion peticion, IdealFilter ideal) {
        FrecuenciasDeModo f = catalogo.filtro(peticion.filtro()).frecuencias(peticion.modo());
        if (f.campos().size() != 2 || f.relaciones().size() != 1
                || !peticion.frecuencias().containsKey("f_paso") || !peticion.frecuencias().containsKey("f_aten")) {
            return false;
        }
        int tipo = "f_aten".equals(f.relaciones().get(0).izquierda()) ? PASA_ALTAS : PASA_BAJAS;

        // El backend busca amplitud = v_fuente en la banda de paso y 0 en la de atenuación.
        ideal.setType(tipo);
        ideal.setPassageFrequency(redondear(peticion.frecuencias().get("f_paso").doubleValue()));
        ideal.setAttenuationFrequency(redondear(peticion.frecuencias().get("f_aten").doubleValue()));
        ideal.setPassageVoltage(peticion.entorno().get("v_fuente").doubleValue());
        ideal.setAttenuationVoltage(0.0);
        return true;
    }

    private static int redondear(double hz) {
        return (int) Math.max(1, Math.min(Integer.MAX_VALUE, Math.round(hz)));
    }
}