package controller.legacy;

import controller.FileController;
import controller.InputCircuitController;
import controller.ViewRefresher;
import view.InputCircuitPanel;
import view.MainFrame;

import javax.swing.AbstractAction;
import javax.swing.JOptionPane;
import java.awt.event.ActionEvent;
import java.io.File;
import java.io.IOException;

/**
 * Menú Circuit > Input circuit: flujo LEGADO que evalúa un circuito escrito
 * a mano ejecutando el binario main.exe (Windows) y leyendo evaluation.txt.
 *
 * Se aisló en este paquete a propósito para que quede claro que no forma
 * parte del camino de la API. Si un día se elimina el binario, basta con
 * borrar el paquete controller.legacy y la línea que la registra en
 * MainController.
 *
 * Cambio respecto al original: el busy-wait
 *   while (process.isAlive()) System.out.println("Loading . . .");
 * (que consumía un núcleo al 100%) se reemplazó por process.waitFor().
 * El comportamiento sigue siendo bloqueante en el EDT, exactamente igual
 * que antes; si se quiere evitar eso hay que moverlo a un SwingWorker.
 */
public class LegacyInputCircuitAction extends AbstractAction {
    private static final String ALGORITHM_DIRECTORY = "src\\resource\\algorithm";
    private static final String EVALUATOR_EXE = "src\\resource\\algorithm\\main.exe";
    private static final String EVALUATION_OUTPUT = "src\\resource\\algorithm\\evaluation.txt";

    private final MainFrame frame;
    private final ViewRefresher viewRefresher;

    public LegacyInputCircuitAction(MainFrame frame, ViewRefresher viewRefresher) {
        this.frame = frame;
        this.viewRefresher = viewRefresher;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        InputCircuitController inputCircuitController = new InputCircuitController(
                new InputCircuitPanel(frame.circuit));

        int option = JOptionPane.showOptionDialog(
                null,
                inputCircuitController.inputCircuitPanel,
                "Input",
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE,
                null,
                new Object[] {"Evaluate", "Cancel"},
                "Cancel");

        if (option != JOptionPane.OK_OPTION) {
            return;
        }

        frame.circuit.setCodedCircuit(checkCodedCircuit(frame.circuit.getCodedCircuit()));
        try {
            Process process = startEvaluator();
            process.waitFor();

            FileController.readFile(EVALUATION_OUTPUT, frame.circuit);
            viewRefresher.refresh();
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(null, ex.getMessage(),
                    "Error", JOptionPane.ERROR_MESSAGE);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
        }
    }

    private Process startEvaluator() throws IOException {
        var simulation = frame.circuit.getSimulation();
        String[] command = {EVALUATOR_EXE, "-e",
                String.valueOf(simulation.getSupplyVoltage()),
                String.valueOf(simulation.getSupplyResistance()),
                String.valueOf(simulation.getLoadResistance()),
                String.valueOf(simulation.getInitialFrequency()),
                String.valueOf(simulation.getFinalFrequency()),
                frame.circuit.getCodedCircuit(), "evaluation"};

        ProcessBuilder processBuilder = new ProcessBuilder();
        processBuilder.directory(new File(ALGORITHM_DIRECTORY));
        processBuilder.command(command);

        return processBuilder.start();
    }

    private String checkCodedCircuit(String codedCircuit) {
        StringBuilder newCodedCircuit = new StringBuilder();
        String change = "";

        String[] element;
        String[] elements = codedCircuit.replace(" ", "").split("->");

        for (int i = elements.length - 1; i >= 0; i--) {
            element = elements[i].replace("[", "")
                    .replace("]", "").split("\\|");

            if (change.isEmpty()) {
                change = element[2];
            }

            for (int j = 0; j < 3; j++) {
                if (element[j].equals(change)) {
                    element[j] = "1002";
                }
            }

            newCodedCircuit.insert(0, "[" + element[0] + "|" + element[1] + "|" + element[2] + "|"
                    + element[3] + "|" + element[4] + "|" + element[5] + "]->");
        }

        return newCodedCircuit.toString();
    }
}
