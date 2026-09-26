package view;

import javax.swing.*;
import javax.swing.border.TitledBorder;
import java.awt.*;

/**
 * Formulario de arranque para que el usuario ingrese los valores de
 * simulación (v_fuente, r_fuente, r_carga, f_inicial, f_final) de forma
 * dinámica, en vez de que siempre salgan del archivo estático
 * src/resource/circuit.txt.
 *
 * Se muestra una sola vez, en Main.java, antes de construir MainFrame. No
 * depende de Circuit/Simulation/IdealFilter porque en este punto del
 * arranque no hay todavía un Circuit "completo" con el que interactuar —
 * es un panel autónomo; quien lo use (Main.java) vuelca sus valores al
 * Simulation real después de leerlos.
 */
public class SimulationSetupPanel extends JPanel {
    public JSpinner supplyVoltage;
    public JSpinner supplyResistance;
    public JSpinner loadResistance;
    public JSpinner initialFrequency;
    public JSpinner finalFrequency;

    public SimulationSetupPanel() {
        this.setLayout(new GridBagLayout());
        this.initComponent();
    }

    private void initComponent() {
        GridBagConstraints constraints = new GridBagConstraints();

        String[] properties = {"Supply voltage:", "Supply resistance:", "Load resistance:",
                "Initial frequency:", "Final frequency:"};
        String[] values = {"V", "omhs", "omhs", "Hz", "Hz"};

        this.setBorder(new TitledBorder("Simulation values"));

        constraints.gridx = 0;
        constraints.anchor = GridBagConstraints.EAST;
        constraints.insets = new Insets(4, 4, 4, 5);

        for (int i = 0; i < properties.length; i++) {
            constraints.gridy = i;
            this.add(new JLabel(properties[i]), constraints);
        }

        // Los mismos rangos que ya usa GenerateCircuitPanel.simulationProperties(),
        // para no introducir un segundo criterio de límites en la app.
        supplyVoltage = new JSpinner(new SpinnerNumberModel(5.0, 1.0, 15.0, 0.1));
        constraints.gridx = 1;
        constraints.gridy = 0;
        constraints.fill = GridBagConstraints.HORIZONTAL;
        this.add(supplyVoltage, constraints);

        supplyResistance = new JSpinner(new SpinnerNumberModel(470, 1, 1000, 1));
        constraints.gridy = 1;
        this.add(supplyResistance, constraints);

        loadResistance = new JSpinner(new SpinnerNumberModel(470, 1, 1000, 1));
        constraints.gridy = 2;
        this.add(loadResistance, constraints);

        initialFrequency = new JSpinner(new SpinnerNumberModel(1, 1, 999999, 1));
        constraints.gridy = 3;
        this.add(initialFrequency, constraints);

        finalFrequency = new JSpinner(new SpinnerNumberModel(100000, 2, 1000000, 1));
        constraints.gridy = 4;
        this.add(finalFrequency, constraints);

        constraints.gridx = 2;
        constraints.anchor = GridBagConstraints.WEST;

        for (int i = 0; i < values.length; i++) {
            constraints.gridy = i;
            this.add(new JLabel(values[i]), constraints);
        }
    }
}
