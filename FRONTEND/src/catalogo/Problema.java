package catalogo;

import catalogo.Catalogo.Severidad;

/**
 * Un hallazgo de la validación de una petición.
 *
 * @param severidad ERROR bloquea el envío; AVISO solo advierte.
 * @param clave     el campo al que se refiere (p. ej. "r_fuente", "f_paso"), o "combinacion" / "modo" si el
 *                  problema es de toda la petición. Sirve para marcar el control en la pantalla.
 * @param mensaje   texto para el usuario.
 */
public record Problema(Severidad severidad, String clave, String mensaje) {
    public boolean esError() {
        return severidad == Severidad.ERROR;
    }

    @Override
    public String toString() {
        return (esError() ? "ERROR: " : "AVISO: ") + mensaje;
    }
}