package esquema;

import java.awt.Color;

/**
 * Apariencia con la que se dibuja un {@link Esquema}. Inmutable.
 *
 * @param escala            píxeles que vale una unidad de rejilla (36 da un circuito de 4.º orden de ~800 px)
 * @param etiquetasDeNodo   si se rotulan los números de nodo (los del .cir) en gris
 * @param cable             color de cables y símbolos
 * @param optimizable       color de las etiquetas de los componentes que ajusta el optimizador
 * @param fijo              color de las etiquetas de los componentes fijos (fuente, Rs, Rl)
 * @param nodo              color de los números de nodo
 */
public record EstiloEsquema(double escala, boolean etiquetasDeNodo, Color cable, Color optimizable, Color fijo,
                            Color nodo) {

    public static EstiloEsquema porDefecto() {
        return new EstiloEsquema(36, true, new Color(0x111111), new Color(0x1D4ED8), new Color(0x374151),
                new Color(0x777777));
    }

    public EstiloEsquema conEscala(double nuevaEscala) {
        if (!(nuevaEscala > 0)) {
            throw new IllegalArgumentException("La escala debe ser mayor que 0: " + nuevaEscala);
        }
        return new EstiloEsquema(nuevaEscala, etiquetasDeNodo, cable, optimizable, fijo, nodo);
    }

    public EstiloEsquema conEtiquetasDeNodo(boolean mostrar) {
        return new EstiloEsquema(escala, mostrar, cable, optimizable, fijo, nodo);
    }
}