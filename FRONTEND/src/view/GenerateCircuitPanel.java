package view;

import model.Circuit;
import model.IdealFilter;
import model.Simulation;

import javax.swing.*;
import javax.swing.border.TitledBorder;
import java.awt.*;

public class GenerateCircuitPanel extends JPanel {
    public JSpinner passageVoltage;
    public JSpinner attenuationVoltage;
    public JSpinner passageFrequency;
    public JSpinner attenuationFrequency;
    public JComboBox<String> type;

    public JSpinner supplyVoltage;
    public JSpinner supplyResistance;
    public JSpinner loadResistance;
    public JSpinner initialFrequency;
    public JSpinner finalFrequency;

    public Circuit circuit;
    public IdealFilter idealFilter;
    public Simulation simulation;
    public SimulationPanel simulationPanel;

    public GenerateCircuitPanel(Circuit circuit) {
        this.setSize(400, 300);

        this.setLayout(new BorderLayout());

        this.circuit = circuit;

        this.initComponent();
    }

    private void initComponent() {
        idealFilter = circuit.getIdealFilter();
        simulation = circuit.getSimulation();

        JPanel panel = new JPanel(new BorderLayout());
        panel.add(filterProperties(), BorderLayout.WEST);
        panel.add(simulationProperties(), BorderLayout.EAST);

        this.add(panel, BorderLayout.NORTH);

        simulationPanel = new SimulationPanel(circuit);
        this.add(simulationPanel, BorderLayout.CENTER);
    }

    private JPanel filterProperties() {
        GridBagConstraints constraints = new GridBagConstraints();

        String[] properties = {"Passage voltage:", "Attenuation voltage:", "Passage frequency:",
                "Attenuation frequency:", "Filter type:"};
        String[] values = {"V", "V", "Hz", "Hz"};
        String[] types = {"Low Passes", "High Passes"};

        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new TitledBorder("Filter properties"));

        constraints.gridx = 0;
        constraints.anchor = GridBagConstraints.EAST;
        constraints.insets = new Insets(0, 0, 2, 5);

        for(int i = 0; i < properties.length; i++) {
            constraints.gridy = i;
            panel.add(new JLabel(properties[i]), constraints);
        }

        passageVoltage = new JSpinner(
                new SpinnerNumberModel(idealFilter.getPassageVoltage(), 0,
                        simulation.getSupplyVoltage(), 0.1)
        );

        constraints.gridx = 1;
        constraints.gridy = 0;
        constraints.fill = GridBagConstraints.HORIZONTAL;
        panel.add(passageVoltage, constraints);

        attenuationVoltage = new JSpinner(
                new SpinnerNumberModel(idealFilter.getAttenuationVoltage(), 0,
                        simulation.getSupplyVoltage(), 0.1)
        );

        constraints.gridy = 1;
        panel.add(attenuationVoltage, constraints);

        passageFrequency = new JSpinner(
                new SpinnerNumberModel(idealFilter.getPassageFrequency(), 1,
                        simulation.getFinalFrequency(), 1)
        );

        constraints.gridy = 2;
        panel.add(passageFrequency, constraints);

        attenuationFrequency = new JSpinner(
                new SpinnerNumberModel(idealFilter.getAttenuationFrequency(), 1,
                        simulation.getFinalFrequency(), 1)
        );

        constraints.gridy = 3;
        panel.add(attenuationFrequency, constraints);

        type = new JComboBox<>(types);
        type.setSelectedIndex(idealFilter.getType());
        type.setEnabled(false);

        constraints.gridy = 4;
        panel.add(type, constraints);

        constraints.gridx = 2;
        constraints.anchor = GridBagConstraints.WEST;

        for(int i = 0; i < values.length; i++) {
            constraints.gridy = i;
            panel.add(new JLabel(values[i]), constraints);
        }

        return panel;
    }

    private JPanel simulationProperties() {
        GridBagConstraints constraints = new GridBagConstraints();

        String[] properties = {"Supply voltage:", "Supply resistance:", "Load resistance:",
                "Initial frequency:", "Final frequency:"};
        String[] values = {"V", "omhs", "omhs", "Hz", "Hz"};

        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new TitledBorder("Simulation properties"));

        constraints.gridx = 0;
        constraints.anchor = GridBagConstraints.EAST;
        constraints.insets = new Insets(0, 0, 2, 5);

        for(int i = 0; i < properties.length; i++) {
            constraints.gridy = i;
            panel.add(new JLabel(properties[i]), constraints);
        }

        supplyVoltage = new JSpinner(
                new SpinnerNumberModel(simulation.getSupplyVoltage(), 1,
                15, 0.1)
        );

        constraints.gridx = 1;
        constraints.gridy = 0;
        constraints.fill = GridBagConstraints.HORIZONTAL;
        panel.add(supplyVoltage, constraints);

        supplyResistance = new JSpinner(
                new SpinnerNumberModel(simulation.getSupplyResistance(), 1,
                1000, 1)
        );

        constraints.gridy = 1;
        panel.add(supplyResistance, constraints);

        loadResistance = new JSpinner(
                new SpinnerNumberModel(simulation.getLoadResistance(), 1,
                1000, 1)
        );

        constraints.gridy = 2;
        panel.add(loadResistance, constraints);

        initialFrequency = new JSpinner(
                new SpinnerNumberModel(simulation.getInitialFrequency(), 1,
                        100000, 1)
        );

        constraints.gridy = 3;
        panel.add(initialFrequency, constraints);

        finalFrequency = new JSpinner(
                new SpinnerNumberModel(simulation.getFinalFrequency(), 1,
                        100000, 1)
        );

        constraints.gridy = 4;
        panel.add(finalFrequency, constraints);

        constraints.gridx = 2;
        constraints.anchor = GridBagConstraints.WEST;

        for(int i = 0; i < values.length; i++) {
            constraints.gridy = i;
            panel.add(new JLabel(values[i]), constraints);
        }

        return panel;
    }
}
