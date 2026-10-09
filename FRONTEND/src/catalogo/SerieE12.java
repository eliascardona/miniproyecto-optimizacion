package catalogo;

/**
 * Serie comercial E12 (la que usan las resistencias del circuito): mantisa × 10^n con mantisa en
 * {1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2}.
 */
public final class SerieE12 {
    private SerieE12() {}

    private static final double[] MANTISAS = {1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2};
    private static final double TOLERANCIA_RELATIVA = 1e-6;

    public static boolean contiene(double valor) {
        if (!(valor > 0) || Double.isInfinite(valor)) {
            return false;
        }
        double decada = Math.pow(10, Math.floor(Math.log10(valor)));
        double mantisa = valor / decada;
        // log10 puede errar por un ulp justo en una potencia de 10 y dar una década de menos (mantisa ≈ 10):
        // se prueba también esa mantisa ÷ 10 (≈ 1.0).
        return coincide(mantisa) || coincide(mantisa / 10);
    }

    private static boolean coincide(double mantisa) {
        for (double m : MANTISAS) {
            if (Math.abs(mantisa - m) <= m * TOLERANCIA_RELATIVA) {
                return true;
            }
        }
        return false;
    }
}