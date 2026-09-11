package view;

import model.Circuit;
import model.IdealFilter;
import model.Simulation;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.border.TitledBorder;
import java.awt.*;
import java.util.ArrayList;

public class InputCircuitPanel extends JPanel {
    public JComboBox<String> type;
    public JComboBox<String> connection;
    public JComboBox<Integer> value;
    public JComboBox<Integer> decade;
    public JButton add;
    public JButton edit;

    public JSpinner supplyVoltage;
    public JSpinner supplyResistance;
    public JSpinner loadResistance;
    public JSpinner initialFrequency;
    public JSpinner finalFrequency;

    public Circuit circuit;
    public IdealFilter idealFilter;
    public Simulation simulation;
    public ArrayList<JButton> elements;

    public JScrollPane scrollPane;
    public JPanel codedCircuit;
    public CircuitPanel circuitPanel;

    public InputCircuitPanel(Circuit circuit) {
        this.setSize(400, 300);

        this.setLayout(new BorderLayout());

        this.circuit = circuit;
        this.circuit.setCodedCircuit("");

        this.initComponent();
    }

    private void initComponent() {
        idealFilter = circuit.getIdealFilter();
        simulation = circuit.getSimulation();
        elements = new ArrayList<>();

        JPanel panel = new JPanel(new BorderLayout());
        panel.add(elementProperties(), BorderLayout.WEST);
        panel.add(simulationProperties(), BorderLayout.EAST);

        this.add(panel, BorderLayout.NORTH);

        codedCircuit = new JPanel(new FlowLayout());
        codedCircuit.add(new JLabel("Coded circuit:"));

        scrollPane = new JScrollPane(codedCircuit);
        scrollPane.setPreferredSize(new Dimension(400, 70));
        scrollPane.setBorder(new EmptyBorder(new Insets(5, 10, 5, 10)));

        this.add(scrollPane, BorderLayout.CENTER);

        circuit.clearCircuit();
        circuitPanel = new CircuitPanel(circuit);

        this.add(circuitPanel, BorderLayout.SOUTH);
    }

    private JPanel elementProperties() {
        GridBagConstraints constraints = new GridBagConstraints();

        String[] properties = {"Type:", "Connection:", "Value:", "Decade:"};
        String[] types = {"Capacitance", "Resistance", "Inductance"};
        String[] connections = {"Parallel", "Series"};

        Integer[] values = {10, 15, 22, 33, 47, 68};
        Integer[] decades = {-5, -6, -7, -8, -9};

        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new TitledBorder("Element properties"));

        constraints.gridx = 0;
        constraints.anchor = GridBagConstraints.EAST;
        constraints.insets = new Insets(0, 0, 2, 5);

        for(int i = 0; i < properties.length; i++) {
            constraints.gridy = i;
            panel.add(new JLabel(properties[i]), constraints);
        }

        type = new JComboBox<>(types);

        constraints.gridx = 1;
        constraints.gridy = 0;
        constraints.fill = GridBagConstraints.HORIZONTAL;
        panel.add(type, constraints);

        connection = new JComboBox<>(connections);

        constraints.gridy = 1;
        panel.add(connection, constraints);

        value = new JComboBox<>(values);

        constraints.gridy = 2;
        panel.add(value, constraints);

        decade = new JComboBox<>(decades);

        constraints.gridy = 3;
        panel.add(decade, constraints);

        add = new JButton("Add");
        edit = new JButton("Edit");
        edit.setVisible(false);

        constraints.gridy = 4;
        panel.add(add, constraints);
        panel.add(edit, constraints);

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
