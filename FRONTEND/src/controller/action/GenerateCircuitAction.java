package controller.action;

import controller.GenerateCircuitController;
import controller.ViewRefresher;
import dto.CircuitRequest;
import dto.GeneticParameters;
import dto.OptimizationResult;
import model.Algoritmo;
import model.ModoEjecucion;
import model.TipoFiltro;
import service.CircuitRequestFactory;
import service.OptimizationService;
import view.AlgorithmSelectionPanel;
import view.GenerateCircuitPanel;
import view.LoadingDialog;
import view.MainFrame;
import view.OptimizationResultDialog;

import javax.swing.AbstractAction;
import javax.swing.JOptionPane;
import javax.swing.SwingWorker;
import java.awt.event.ActionEvent;
import java.util.concurrent.ExecutionException;

/**
 * Menú Circuit > Generate circuit.
 *
 * Esta clase SOLO orquesta la interacción con el usuario (diálogos) y el
 * hilo de fondo; el trabajo de verdad está en:
 *   - service.CircuitRequestFactory -> arma el CircuitRequest
 *   - service.OptimizationService   -> llama a la API y aplica el resultado
 *   - controller.ViewRefresher      -> repinta los paneles
 *   - view.OptimizationResultDialog -> muestra el PNG devuelto
 *
 * Flujo (idéntico al de MainController antes del refactor):
 *   1. Modo: "Try all algorithms" / "Choose an algorithm" / Cancel.
 *   2. AlgorithmSelectionPanel: filtro (siempre) y algoritmo (solo modo específico).
 *   3. Se bloquea lo que el backend aún no implementa.
 *   4. GenerateCircuitPanel: entorno físico + hiperparámetros.
 *   5. Si acepta, se llama a la API en un SwingWorker con LoadingDialog.
 */
public class GenerateCircuitAction extends AbstractAction {
    private final MainFrame frame;
    private final OptimizationService optimizationService;
    private final CircuitRequestFactory requestFactory;
    private final ViewRefresher viewRefresher;

    public GenerateCircuitAction(MainFrame frame,
                                 OptimizationService optimizationService,
                                 CircuitRequestFactory requestFactory,
                                 ViewRefresher viewRefresher) {
        this.frame = frame;
        this.optimizationService = optimizationService;
        this.requestFactory = requestFactory;
        this.viewRefresher = viewRefresher;
    }

    // ------------------------------------------------------------------
    // Paso 1-4: diálogos
    // ------------------------------------------------------------------

    @Override
    public void actionPerformed(ActionEvent e) {
        ModoEjecucion modo = askExecutionMode();
        if (modo == null) {
            return; // Cancel, Esc, o cerró la ventana
        }

        AlgorithmSelectionPanel selectionPanel = new AlgorithmSelectionPanel(modo);
        int selectionOption = JOptionPane.showOptionDialog(
                frame,
                selectionPanel,
                "Selection",
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE,
                null,
                new Object[] {"Continue", "Cancel"},
                "Continue");

        if (selectionOption != JOptionPane.OK_OPTION) {
            return;
        }

        TipoFiltro tipoFiltroElegido = (TipoFiltro) selectionPanel.tipoFiltro.getSelectedItem();

        if (modo == ModoEjecucion.TODOS_LOS_ALGORITMOS) {
            showNotAvailable(
                    "\"Try all algorithms\" is not implemented in the backend yet " +
                            "(there is no endpoint that runs all 4 algorithms and compares results). " +
                            "For now, use \"Choose an algorithm\".");
            return;
        }

        Algoritmo algoritmoElegido = (Algoritmo) selectionPanel.algoritmo.getSelectedItem();
        if (!algoritmoElegido.implementadoEnBackend) {
            showNotAvailable(
                    "\"" + algoritmoElegido + "\" is not implemented in the backend yet " +
                            "(GeneticController.SERVICE_MAP only registers algoritmo_genetico). " +
                            "Choose \"Genetic algorithm\" for now.");
            return;
        }

        if (!tipoFiltroElegido.implementadoEnBackend) {
            showNotAvailable(
                    "\"" + tipoFiltroElegido + "\" is not implemented in the backend yet " +
                            "(GeneticController.SERVICE_MAP only registers pasa_altas). " +
                            "Choose \"High Passes\" for now.");
            return;
        }

        // Punto de partida de IdealFilter; GenerateCircuitController lo sigue
        // recalculando en vivo según las frecuencias mientras el diálogo esté abierto.
        frame.circuit.getIdealFilter().setType(tipoFiltroElegido.idealFilterType);

        GenerateCircuitController generateCircuitController = new GenerateCircuitController(
                new GenerateCircuitPanel(frame.circuit));

        int option = JOptionPane.showOptionDialog(
                null,
                generateCircuitController.generateCircuitPanel,
                "Input",
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE,
                null,
                new Object[] {"Generate", "Cancel"},
                "Cancel");

        if (option == JOptionPane.OK_OPTION) {
            runOptimization(generateCircuitController.generateCircuitPanel, algoritmoElegido);
        }
    }

    /** @return el modo elegido, o null si el usuario canceló. */
    private ModoEjecucion askExecutionMode() {
        int modoOption = JOptionPane.showOptionDialog(
                frame,
                "What do you want to do?",
                "Generate circuit",
                JOptionPane.DEFAULT_OPTION,
                JOptionPane.QUESTION_MESSAGE,
                null,
                new Object[] {"Try all algorithms", "Choose an algorithm", "Cancel"},
                "Choose an algorithm");

        return switch (modoOption) {
            case 0 -> ModoEjecucion.TODOS_LOS_ALGORITMOS;
            case 1 -> ModoEjecucion.ALGORITMO_ESPECIFICO;
            default -> null;
        };
    }

    private void showNotAvailable(String message) {
        JOptionPane.showMessageDialog(frame, message, "Not available yet",
                JOptionPane.INFORMATION_MESSAGE);
    }

    // ------------------------------------------------------------------
    // Paso 5: llamada a la API
    // ------------------------------------------------------------------

    private void runOptimization(GenerateCircuitPanel panel, Algoritmo algoritmoElegido) {
        // Segundo chequeo del tipo de filtro: GenerateCircuitController pudo
        // recalcular IdealFilter.type mientras el diálogo estuvo abierto.
        TipoFiltro tipoFiltroFinal = TipoFiltro.fromIdealFilterType(frame.circuit.getIdealFilter().getType());
        if (!tipoFiltroFinal.implementadoEnBackend) {
            JOptionPane.showMessageDialog(frame,
                    "\"" + tipoFiltroFinal + "\" is not implemented in the backend yet. " +
                            "Adjust the passage/attenuation frequencies so the final filter " +
                            "type stays \"High Passes\".",
                    "Not available yet", JOptionPane.ERROR_MESSAGE);
            return;
        }

        CircuitRequest request;
        try {
            request = requestFactory.create(frame.circuit, algoritmoElegido, readGeneticParameters(panel));
        } catch (IllegalArgumentException ex) {
            // CircuitRequest valida rangos en su constructor.
            JOptionPane.showMessageDialog(frame, ex.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        LoadingDialog loadingDialog = new LoadingDialog(frame,
                "Optimizando circuito (puede tardar varios minutos)...");

        // La llamada HTTP puede tardar minutos: va en un hilo de fondo para no congelar el EDT.
        SwingWorker<OptimizationResult, Void> worker = new SwingWorker<>() {
            @Override
            protected OptimizationResult doInBackground() throws Exception {
                return optimizationService.optimize(request);
            }

            @Override
            protected void done() {
                loadingDialog.dispose();
                try {
                    OptimizationResult result = get();
                    optimizationService.applyResult(result, frame.circuit);
                    viewRefresher.refresh();
                    OptimizationResultDialog.show(frame, result);
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                } catch (ExecutionException ex) {
                    Throwable cause = ex.getCause() != null ? ex.getCause() : ex;
                    showError(cause.getMessage());
                } catch (RuntimeException ex) {
                    // Falla al traducir la respuesta al modelo (p. ej. un valor
                    // que no está en ComponentTables). Antes esto escapaba de
                    // done() sin ningún aviso al usuario.
                    showError("No se pudo aplicar el resultado de la API al circuito: " + ex.getMessage());
                }
            }
        };

        worker.execute();
        loadingDialog.setVisible(true); // se bloquea aquí hasta que done() llame a dispose()
    }

    /** Único punto donde se lee la vista: 6 spinners -> valores planos. */
    private GeneticParameters readGeneticParameters(GenerateCircuitPanel panel) {
        return new GeneticParameters(
                (int) panel.tamPoblacion.getValue(),
                (int) panel.numGeneraciones.getValue(),
                (double) panel.probCruce.getValue(),
                (double) panel.probMutacion.getValue(),
                (int) panel.elitismo.getValue(),
                (int) panel.torneoK.getValue()
        );
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(frame, message, "Error", JOptionPane.ERROR_MESSAGE);
    }
}
