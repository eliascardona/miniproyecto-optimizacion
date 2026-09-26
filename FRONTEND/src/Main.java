import controller.FileController;
import controller.MainController;
import model.Circuit;
import model.Simulation;
import view.MainFrame;
import view.SimulationSetupPanel;

import javax.swing.*;
import javax.swing.plaf.nimbus.NimbusLookAndFeel;
import java.awt.*;

public class Main {
    public static void main(String[] args) {
        Circuit circuit = new Circuit();
        FileController.readFile("src\\resource\\circuit.txt", circuit);

        EventQueue.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(new NimbusLookAndFeel());

                pedirValoresSimulacionAlUsuario(circuit.getSimulation());

                MainController controller = new MainController(new MainFrame(circuit));
                controller.frame.setVisible(true);
            } catch (UnsupportedLookAndFeelException e) {
                throw new RuntimeException(e);
            }
        });
    }

    /**
     * Muestra el formulario de arranque para que el usuario ingrese los
     * valores de simulación (antes venían fijos del archivo estático
     * src/resource/circuit.txt, vía FileController.readFile). Si el usuario
     * cancela ("Use file defaults"), se conservan los valores que ya trajo
     * ese archivo — la app nunca se queda sin un Simulation utilizable.
     *
     * Muta el mismo objeto Simulation que circuit ya trae (no crea uno
     * nuevo), así que todo lo que ya depende de circuit.getSimulation()
     * (MainFrame, GenerateCircuitPanel, CircuitApiClient a través de
     * CircuitRequest) ve los valores nuevos sin más cambios.
     */
    private static void pedirValoresSimulacionAlUsuario(Simulation simulation) {
        SimulationSetupPanel panel = new SimulationSetupPanel();

        while (true) {
            int option = JOptionPane.showOptionDialog(
                    null,
                    panel,
                    "Simulation setup",
                    JOptionPane.OK_CANCEL_OPTION,
                    JOptionPane.PLAIN_MESSAGE,
                    null,
                    new Object[] {"Start", "Use file defaults"},
                    "Start");

            if (option != JOptionPane.OK_OPTION) {
                return;
            }

            double supplyVoltage = (double) panel.supplyVoltage.getValue();
            int supplyResistance = (int) panel.supplyResistance.getValue();
            int loadResistance = (int) panel.loadResistance.getValue();
            int initialFrequency = (int) panel.initialFrequency.getValue();
            int finalFrequency = (int) panel.finalFrequency.getValue();

            if (initialFrequency >= finalFrequency) {
                JOptionPane.showMessageDialog(null,
                        "La frecuencia inicial debe ser menor que la final.",
                        "Error", JOptionPane.ERROR_MESSAGE);
                continue;
            }

            simulation.setSupplyVoltage(supplyVoltage);
            simulation.setSupplyResistance(supplyResistance);
            simulation.setLoadResistance(loadResistance);
            simulation.setInitialFrequency(initialFrequency);
            simulation.setFinalFrequency(finalFrequency);
            return;
        }
    }
}