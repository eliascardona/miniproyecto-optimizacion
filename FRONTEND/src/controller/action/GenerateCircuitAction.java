package controller.action;

import api_client.CircuitApiClient;
import catalogo.Catalogo;
import catalogo.Catalogo.Algoritmo;
import catalogo.Catalogo.Filtro;
import catalogo.Problema;
import catalogo.ValidadorPeticion;
import controller.ViewRefresher;
import dto.OptimizationResult;
import dto.PeticionOptimizacion;
import model.ModoEjecucion;
import model.Simulation;
import service.ObjetivosAIdealFilter;
import service.OptimizationService;
import view.AlgorithmSelectionPanel;
import view.LoadingDialog;
import view.MainFrame;
import view.OptimizacionFormPanel;
import view.OptimizationResultDialog;

import javax.swing.AbstractAction;
import javax.swing.JOptionPane;
import javax.swing.SwingWorker;
import java.awt.event.ActionEvent;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.function.Consumer;
import java.util.stream.Collectors;

/**
 * Menú Circuit > Generate circuit.
 *
 * Esta clase SOLO orquesta la interacción con el usuario (diálogos) y los hilos de fondo; el trabajo de
 * verdad está en:
 *   - service.OptimizationService   -> catálogo, llamada a la API y aplicar el resultado
 *   - view.OptimizacionFormPanel    -> el formulario, armado desde el catálogo
 *   - catalogo.ValidadorPeticion    -> las reglas (límites, orden de frecuencias, ...)
 *   - controller.ViewRefresher      -> repinta los paneles
 *   - view.OptimizationResultDialog -> muestra el PNG devuelto
 *
 * Flujo:
 *   1. Modo: "Try all algorithms" / "Choose an algorithm" / Cancel. "Try all algorithms" no está
 *      implementado: se avisa y se termina.
 *   2. Catálogo: se pide al backend la primera vez (con diálogo de espera) y se reutiliza.
 *   3. AlgorithmSelectionPanel: UN filtro y UN algoritmo, solo de lo que el catálogo dice que corre.
 *   4. OptimizacionFormPanel: modo, frecuencias, entorno, barrido y parámetros. Si hay errores no se
 *      envía (se explica y se vuelve al formulario); si solo hay avisos, el usuario decide.
 *   5. La petición se envía en un SwingWorker con LoadingDialog.
 *   6. Con el resultado: se dibuja el circuito, el entorno usado pasa a Simulation y, si el filtro lo
 *      permite, los objetivos pasan a IdealFilter.
 */
public class GenerateCircuitAction extends AbstractAction {
    private final MainFrame frame;
    private final OptimizationService optimizationService;
    private final ViewRefresher viewRefresher;

    public GenerateCircuitAction(MainFrame frame,
                                 OptimizationService optimizationService,
                                 ViewRefresher viewRefresher) {
        this.frame = frame;
        this.optimizationService = optimizationService;
        this.viewRefresher = viewRefresher;
    }

    // ------------------------------------------------------------------
    // Paso 1: modo
    // ------------------------------------------------------------------

    @Override
    public void actionPerformed(ActionEvent e) {
        ModoEjecucion modo = askExecutionMode();
        if (modo == null) {
            return; // Cancel, Esc, o cerró la ventana
        }

        if (modo == ModoEjecucion.TODOS_LOS_ALGORITMOS) {
            showNotAvailable(
                    "\"Try all algorithms\" is not implemented yet " +
                            "(there is no endpoint that runs all 4 algorithms and compares results). " +
                            "For now, use \"Choose an algorithm\".");
            return;
        }

        Catalogo enMemoria = optimizationService.catalogoEnMemoria();
        if (enMemoria != null) {
            elegirYOptimizar(enMemoria);
        } else {
            // La primera vez el catálogo viene del backend; puede tardar si el servidor está lento.
            ejecutarConEspera("Cargando el catálogo de filtros y algoritmos...",
                    optimizationService::catalogo, this::elegirYOptimizar);
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

    // ------------------------------------------------------------------
    // Pasos 3 y 4: elegir filtro/algoritmo y llenar el formulario
    // ------------------------------------------------------------------

    private void elegirYOptimizar(Catalogo catalogo) {
        if (catalogo.filtrosDisponibles().isEmpty()) {
            showNotAvailable("The server does not report any filter/algorithm combination it can run.");
            return;
        }

        AlgorithmSelectionPanel seleccion = new AlgorithmSelectionPanel(catalogo);
        int selectionOption = JOptionPane.showOptionDialog(
                frame,
                seleccion,
                "Selection",
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE,
                null,
                new Object[] {"Continue", "Cancel"},
                "Continue");

        if (selectionOption != JOptionPane.OK_OPTION) {
            return;
        }

        Filtro filtro = seleccion.filtroElegido();
        Algoritmo algoritmo = seleccion.algoritmoElegido();
        if (filtro == null || algoritmo == null || !catalogo.estaDisponible(filtro.id(), algoritmo.id())) {
            showNotAvailable("The server cannot run that filter/algorithm combination.");
            return;
        }

        OptimizacionFormPanel formulario = new OptimizacionFormPanel(catalogo, filtro, algoritmo, valoresBase());
        PeticionOptimizacion peticion = pedirPeticion(catalogo, formulario);
        if (peticion != null) {
            runOptimization(catalogo, peticion);
        }
    }

    /** Entorno y barrido que ya tiene la aplicación (los del arranque o los de la última optimización). */
    private Map<String, Double> valoresBase() {
        Simulation s = frame.circuit.getSimulation();
        Map<String, Double> base = new LinkedHashMap<>();
        base.put("v_fuente", s.getSupplyVoltage());
        base.put("r_fuente", (double) s.getSupplyResistance());
        base.put("r_carga", (double) s.getLoadResistance());
        base.put("f_inicial", (double) s.getInitialFrequency());
        base.put("f_final", (double) s.getFinalFrequency());
        return base;
    }

    /**
     * Muestra el formulario hasta que el usuario cancele (null) o acepte algo que se pueda enviar:
     * los errores se explican y devuelven al formulario; los avisos piden confirmación.
     */
    private PeticionOptimizacion pedirPeticion(Catalogo catalogo, OptimizacionFormPanel formulario) {
        while (true) {
            int option = JOptionPane.showOptionDialog(
                    frame,
                    formulario,
                    "Input",
                    JOptionPane.OK_CANCEL_OPTION,
                    JOptionPane.PLAIN_MESSAGE,
                    null,
                    new Object[] {"Generate", "Cancel"},
                    "Generate");

            if (option != JOptionPane.OK_OPTION) {
                return null;
            }

            PeticionOptimizacion peticion;
            try {
                peticion = formulario.leerPeticion();
            } catch (IllegalArgumentException ex) {
                showError(ex.getMessage());
                continue;
            }

            List<Problema> problemas = ValidadorPeticion.validar(catalogo, peticion);
            List<Problema> errores = problemas.stream().filter(Problema::esError).toList();
            List<Problema> avisos = problemas.stream().filter(p -> !p.esError()).toList();

            if (!errores.isEmpty()) {
                JOptionPane.showMessageDialog(frame, enLista("Fix these before generating:", errores),
                        "Check the values", JOptionPane.ERROR_MESSAGE);
                continue;
            }
            if (!avisos.isEmpty()) {
                int seguir = JOptionPane.showConfirmDialog(frame,
                        enLista("These values are outside the recommended settings:", avisos)
                                + "\n\nGenerate anyway?",
                        "Warnings", JOptionPane.YES_NO_OPTION, JOptionPane.WARNING_MESSAGE);
                if (seguir != JOptionPane.YES_OPTION) {
                    continue;
                }
            }
            return peticion;
        }
    }

    private static String enLista(String encabezado, List<Problema> problemas) {
        return encabezado + "\n\n" + problemas.stream().map(p -> "• " + p.mensaje()).collect(Collectors.joining("\n"));
    }

    // ------------------------------------------------------------------
    // Pasos 5 y 6: llamada a la API y resultado
    // ------------------------------------------------------------------

    private void runOptimization(Catalogo catalogo, PeticionOptimizacion peticion) {
        ejecutarConEspera("Optimizando circuito (puede tardar varios minutos)...",
                () -> optimizationService.optimize(peticion),
                result -> aplicarResultado(catalogo, peticion, result));
    }

    private void aplicarResultado(Catalogo catalogo, PeticionOptimizacion peticion, OptimizationResult result) {
        try {
            optimizationService.applyResult(result, frame.circuit);
        } catch (RuntimeException ex) {
            // Falla al traducir la respuesta al modelo (camino legacy, p. ej. un valor que no está en
            // ComponentTables). Antes esto escapaba sin ningún aviso al usuario.
            showError("No se pudo aplicar el resultado de la API al circuito: " + ex.getMessage());
            return;
        }

        // El resultado pertenece al entorno y a los objetivos con los que se pidió.
        Simulation s = frame.circuit.getSimulation();
        s.setSupplyVoltage(peticion.entorno().get("v_fuente").doubleValue());
        s.setSupplyResistance(aEntero(peticion.entorno().get("r_fuente")));
        s.setLoadResistance(aEntero(peticion.entorno().get("r_carga")));
        s.setInitialFrequency(aEntero(peticion.barrido().get("f_inicial")));
        s.setFinalFrequency(aEntero(peticion.barrido().get("f_final")));
        ObjetivosAIdealFilter.sincronizar(catalogo, peticion, frame.circuit.getIdealFilter());

        viewRefresher.refresh();
        OptimizationResultDialog.show(frame, result);
    }

    private static int aEntero(Number n) {
        return (int) Math.max(Integer.MIN_VALUE, Math.min(Integer.MAX_VALUE, n.longValue()));
    }

    /**
     * Corre `tarea` en un hilo de fondo con el diálogo de espera, y llama a `alTerminar` en el EDT con el
     * resultado. La llamada a la API puede tardar minutos, por eso no va en el EDT.
     */
    private <T> void ejecutarConEspera(String mensaje, Callable<T> tarea, Consumer<T> alTerminar) {
        LoadingDialog loadingDialog = new LoadingDialog(frame, mensaje);

        SwingWorker<T, Void> worker = new SwingWorker<>() {
            @Override
            protected T doInBackground() throws Exception {
                return tarea.call();
            }

            @Override
            protected void done() {
                loadingDialog.dispose();
                try {
                    alTerminar.accept(get());
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                } catch (ExecutionException ex) {
                    Throwable cause = ex.getCause() != null ? ex.getCause() : ex;
                    showError(cause.getMessage());
                }
            }
        };

        worker.execute();
        loadingDialog.setVisible(true); // se bloquea aquí hasta que done() llame a dispose()
    }

    private void showNotAvailable(String message) {
        JOptionPane.showMessageDialog(frame, message, "Not available yet",
                JOptionPane.INFORMATION_MESSAGE);
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(frame, message, "Error", JOptionPane.ERROR_MESSAGE);
    }
}