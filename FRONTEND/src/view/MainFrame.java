package view;

import model.Circuit;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;

public class MainFrame extends JFrame {
    public Circuit circuit;

    public JLabel codedCircuit;
    public CircuitPanel circuitPanel;
    public SimulationPanel simulationPanel;
    public FrequencyPanel frequencyPanel;

    public JMenuItem open;
    public JMenuItem saveFullFile;
    public JMenuItem saveCircuit;
    public JMenuItem saveSimulation;
    public JMenuItem saveTable;
    public JMenuItem generateCircuit;
    public JMenuItem inputCircuit;
    public JMenuItem exit;

    public MainFrame(Circuit circuit) {
        super("Passive Analog Circuits v8");
        this.setMinimumSize(new Dimension(800, 600));
        this.setSize(800, 600);

        this.getContentPane().setLayout(new BorderLayout());
        this.setLocationRelativeTo(null);
        this.setDefaultCloseOperation(EXIT_ON_CLOSE);

        this.circuit = circuit;

        this.initComponent();
    }

    private void initComponent() {
        this.setJMenuBar(initMenuBar());

        //This label show a coded circuit.
        codedCircuit = new JLabel("Coded circuit: " + circuit.getCodedCircuit());
        JScrollPane scrollPane = new JScrollPane(codedCircuit);
        scrollPane.setPreferredSize(new Dimension(800, 60));
        scrollPane.setBorder(new EmptyBorder(new Insets(5, 10, 5, 10)));

        this.getContentPane().add(scrollPane, BorderLayout.NORTH);

        JPanel panel = new JPanel(new GridBagLayout());
        GridBagConstraints constraints = new GridBagConstraints();

        constraints.gridx = 0;
        constraints.gridy = 0;
        constraints.insets = new Insets(5, 10, 5, 5);
        panel.add(new Label("Simulation"), constraints);

        constraints.gridx = 1;
        constraints.insets = new Insets(5, 5, 5, 10);
        panel.add(new Label("Frequency table"), constraints);

        //This panel show a frequency vs voltage graph, with the objective and generated filter.
        simulationPanel = new SimulationPanel(circuit);

        constraints.gridx = 0;
        constraints.gridy = 1;
        constraints.weightx = 1;
        constraints.weighty = 1;
        constraints.fill = GridBagConstraints.BOTH;
        constraints.insets = new Insets(5, 10, 5, 5);
        panel.add(simulationPanel, constraints);

        //This panel show a frequency table of simulation.
        frequencyPanel = new FrequencyPanel(circuit.getSimulation());

        constraints.gridx = 1;
        constraints.weightx = 0.5;
        constraints.insets = new Insets(5, 5, 5, 10);
        panel.add(frequencyPanel, constraints);

        constraints.gridx = 0;
        constraints.gridy = 2;
        constraints.gridwidth = 2;
        constraints.weightx = 0;
        constraints.weighty = 0;
        constraints.fill = GridBagConstraints.NONE;
        constraints.insets = new Insets(5, 10, 5, 10);
        panel.add(new Label("Circuit"), constraints);

        this.getContentPane().add(panel, BorderLayout.CENTER);

        //This panel show the circuit diagram.
        circuitPanel = new CircuitPanel(circuit);
        circuitPanel.setBorder(new EmptyBorder(new Insets(5, 10, 10, 10)));
        this.getContentPane().add(circuitPanel, BorderLayout.SOUTH);
    }

    private JMenuBar initMenuBar() {
        JMenuBar menuBar = new JMenuBar();
        JMenu file = new JMenu("File");
        JMenu circuitMenu = new JMenu("Circuit");

        //This menu item open the circuit file.
        open = new JMenuItem("Open circuit");
        open.setIcon(UIManager.getIcon("Tree.openIcon"));
        file.add(open);

        //This menu save the image of circuit or simulation.
        JMenu save = new JMenu("Save");
        save.setIcon(UIManager.getIcon("FileView.floppyDriveIcon"));
        saveFullFile = new JMenuItem("Full file");
        save.add(saveFullFile);
        saveCircuit = new JMenuItem("Circuit");
        save.add(saveCircuit);
        saveSimulation = new JMenuItem("Simulation");
        save.add(saveSimulation);
        //This menu save the frequency table in csv file.
        saveTable = new JMenuItem("Frequency table");
        save.add(saveTable);
        file.add(save);

        //This menu item exit the application
        exit = new JMenuItem("Exit");
        file.add(exit);
        menuBar.add(file);

        //This menu item open frame for input circuit properties.
        generateCircuit = new JMenuItem("Generate circuit");
        circuitMenu.add(generateCircuit);
        //This menu item open frame for input circuit.
        inputCircuit = new JMenuItem("Input circuit");
        circuitMenu.add(inputCircuit);
        menuBar.add(circuitMenu);

        return menuBar;
    }
}
