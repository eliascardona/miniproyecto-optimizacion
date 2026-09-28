package dto;

/**
 * Hiperparámetros del algoritmo genético tal como los capturó el usuario en
 * la sección "Optimizer properties" de GenerateCircuitPanel.
 *
 * Existe para que service.CircuitRequestFactory NO dependa de ninguna clase
 * de Swing (view.*): la vista se lee en un solo punto
 * (controller.action.GenerateCircuitAction) y de ahí en adelante viajan solo
 * valores planos. Eso permite probar la fábrica con JUnit sin levantar
 * ninguna interfaz.
 *
 * Es un record (Java 16+, el mismo nivel que ya exige FileController).
 * No valida rangos: esa validación vive en el constructor de CircuitRequest.
 */
public record GeneticParameters(
        int tamPoblacion,
        int numGeneraciones,
        double probCruce,
        double probMutacion,
        int elitismo,
        int torneoK
) {}
