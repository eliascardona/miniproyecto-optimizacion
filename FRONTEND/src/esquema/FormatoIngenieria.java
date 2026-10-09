package esquema;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

/**
 * Valores en notación de ingeniería: 1.5e-8 F -> "15 nF", 5.6e7 Ω -> "56 MΩ", 4700 Ω -> "4.7 kΩ".
 * Tres cifras significativas, sin ceros sobrantes. Los símbolos especiales (Ω, µ, −) se escriben
 * como escapes unicode en el código, para no depender de la codificación del archivo fuente.
 */
public final class FormatoIngenieria {
    private FormatoIngenieria() {}

    private static final double[] FACTORES = {1e9, 1e6, 1e3, 1, 1e-3, 1e-6, 1e-9, 1e-12};
    private static final String[] PREFIJOS = {"G", "M", "k", "", "m", "\u00B5", "n", "p"};

    public static final String OHM = "\u03A9";
    public static final String MENOS = "\u2212";

    /** Valor con prefijo SI y unidad según el tipo de elemento ("R", "C", "L", "V"). */
    public static String valor(double v, String tipo) {
        String unidad = unidad(tipo);
        double abs = Math.abs(v);
        if (abs == 0) {
            return "0 " + unidad;
        }
        for (int i = 0; i < FACTORES.length; i++) {
            if (abs >= FACTORES[i] * 0.9999) {          // el 0.9999 evita "1000 Ω" por redondeo en el borde
                return cifras(v / FACTORES[i]) + " " + PREFIJOS[i] + unidad;
            }
        }
        return cifras(v) + " " + unidad;
    }

    /** Tensión con signo explícito: "+15 V", "−15 V" (con el signo menos tipográfico). */
    public static String tensionConSigno(double v) {
        return (v < 0 ? MENOS : "+") + cifras(Math.abs(v)) + " V";
    }

    public static String unidad(String tipo) {
        return switch (tipo) {
            case "R" -> OHM;
            case "C" -> "F";
            case "L" -> "H";
            case "V" -> "V";
            default -> "";
        };
    }

    /** Tres cifras significativas sin ceros de relleno: 15.0 -> "15", 0.5 -> "0.5", 100 -> "100". */
    private static String cifras(double x) {
        return new BigDecimal(x).round(new MathContext(3, RoundingMode.HALF_EVEN)).stripTrailingZeros().toPlainString();
    }
}