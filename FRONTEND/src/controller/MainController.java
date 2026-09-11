package controller;

import model.Circuit;
import model.Simulation;
import view.GenerateCircuitPanel;
import view.InputCircuitPanel;
import view.MainFrame;

import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

public class MainController implements ActionListener {
    public MainFrame frame;

    private String currentPath;

    public MainController(MainFrame frame) {
        this.frame = frame;

        //Action listener for file menu.
        this.frame.open.addActionListener(this);
        this.frame.saveFullFile.addActionListener(this);
        this.frame.saveCircuit.addActionListener(this);
        this.frame.saveSimulation.addActionListener(this);
        this.frame.saveTable.addActionListener(this);
        this.frame.exit.addActionListener(this);
        this.frame.generateCircuit.addActionListener(this);
        this.frame.inputCircuit.addActionListener(this);

        this.currentPath = "";
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        if(frame.open.equals(e.getSource())) {
            //File chooser for search the circuit file.
            showOpenDialog();
        }

        if(frame.saveFullFile.equals(e.getSource())) {
            //File chooser for save the full file.
            showSaveDialog(frame.circuit);
        }

        if(frame.saveCircuit.equals(e.getSource())) {
            //File chooser for save the circuit image.
            showSaveDialog("circuit", frame.circuitPanel.getImage());
        }

        if(frame.saveSimulation.equals(e.getSource())) {
            //File chooser for save the simulation image.
            showSaveDialog("simulation", frame.simulationPanel.getImage());
        }

        if(frame.saveTable.equals(e.getSource())) {
            //File chooser for save the frequency table.
            showSaveDialog(frame.circuit.getSimulation());
        }

        if(frame.exit.equals(e.getSource())) {
            //Destroy frame.
            frame.dispose();
        }

        if(frame.generateCircuit.equals(e.getSource())) {
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

            if(option == JOptionPane.OK_OPTION) {
                try {
                    String[] command = {"src\\resource\\algorithm\\main.exe", "-g",
                            String.valueOf(frame.circuit.getIdealFilter().getPassageVoltage()),
                            String.valueOf(frame.circuit.getIdealFilter().getAttenuationVoltage()),
                            String.valueOf(frame.circuit.getIdealFilter().getPassageFrequency()),
                            String.valueOf(frame.circuit.getIdealFilter().getAttenuationFrequency()),
                            String.valueOf(frame.circuit.getIdealFilter().getType()),
                            String.valueOf(frame.circuit.getSimulation().getSupplyVoltage()),
                            String.valueOf(frame.circuit.getSimulation().getSupplyResistance()),
                            String.valueOf(frame.circuit.getSimulation().getLoadResistance()),
                            String.valueOf(frame.circuit.getSimulation().getInitialFrequency()),
                            String.valueOf(frame.circuit.getSimulation().getFinalFrequency())};

                    Process process = getProcess(command);

                    while(process.isAlive()) {
                        System.out.println("Loading . . .");
                    }

                    FileController.readFile("src\\resource\\algorithm\\mejorIndividuo.txt", frame.circuit);
                    update();
                } catch (IOException ex) {
                    JOptionPane.showMessageDialog(null, ex.getMessage(),
                            "Error", JOptionPane.ERROR_MESSAGE);
                }
            }
        }

        if(frame.inputCircuit.equals(e.getSource())) {
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

            if(option == JOptionPane.OK_OPTION) {
                frame.circuit.setCodedCircuit(checkCodedCircuit(frame.circuit.getCodedCircuit()));
                try {
                    String[] command = {"src\\resource\\algorithm\\main.exe", "-e",
                            String.valueOf(frame.circuit.getSimulation().getSupplyVoltage()),
                            String.valueOf(frame.circuit.getSimulation().getSupplyResistance()),
                            String.valueOf(frame.circuit.getSimulation().getLoadResistance()),
                            String.valueOf(frame.circuit.getSimulation().getInitialFrequency()),
                            String.valueOf(frame.circuit.getSimulation().getFinalFrequency()),
                            frame.circuit.getCodedCircuit(), "evaluation"};

                    Process process = getProcess(command);

                    while(process.isAlive()) {
                        System.out.println("Loading . . .");
                    }

                    FileController.readFile("src\\resource\\algorithm\\evaluation.txt", frame.circuit);
                    update();
                } catch (IOException ex) {
                    JOptionPane.showMessageDialog(null, ex.getMessage(),
                            "Error", JOptionPane.ERROR_MESSAGE);
                }
            }
        }
    }

    private void update() {
        frame.codedCircuit.setText("Coded circuit: " + frame.circuit.getCodedCircuit());
        frame.circuitPanel.updateCircuit();

        frame.simulationPanel.simulation = frame.circuit.getSimulation();
        frame.simulationPanel.updateGraph();

        frame.frequencyPanel.simulation = frame.circuit.getSimulation();
        frame.frequencyPanel.updateTable();
    }

    private void showOpenDialog() {
        //File chooser for search the circuit file.
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        fileChooser.setFileFilter(new FileNameExtensionFilter("txt", "txt"));

        if(fileChooser.showOpenDialog(frame) == JFileChooser.APPROVE_OPTION) {
            currentPath = fileChooser.getSelectedFile().getPath();

            if(FileController.readFile(currentPath, frame.circuit)) {
                update();
            }
        }
    }

    private void showSaveDialog(Circuit circuit) {
        //File chooser for save image.
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        fileChooser.setFileFilter(new FileNameExtensionFilter("txt", "txt"));

        boolean flag = false;
        String path = currentPath.replace(".txt", "-") + "circuitFullFile";
        fileChooser.setSelectedFile(new File(path));

        while(!flag) {
            flag = true;

            if(fileChooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                path = fileChooser.getSelectedFile().getPath();
                path += "." + fileChooser.getFileFilter().getDescription();
                flag = FileController.saveFullFile(path, circuit);
            }
        }
    }

    private void showSaveDialog(String replace, BufferedImage image) {
        //File chooser for save image.
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        fileChooser.setFileFilter(new FileNameExtensionFilter("jpg", "jpg"));
        fileChooser.setFileFilter(new FileNameExtensionFilter("png", "png"));

        boolean flag = false;
        String path = currentPath.replace(".txt", "-") + replace;
        fileChooser.setSelectedFile(new File(path));

        while(!flag) {
            flag = true;

            if(fileChooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                path = fileChooser.getSelectedFile().getPath();
                path += "." + fileChooser.getFileFilter().getDescription();
                flag = FileController.saveImage(path, image);
            }
        }
    }

    private void showSaveDialog(Simulation simulation) {
        //File chooser for save file.
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        fileChooser.setFileFilter(new FileNameExtensionFilter("txt", "txt"));
        fileChooser.setFileFilter(new FileNameExtensionFilter("csv", "csv"));

        boolean flag = false;
        String path = currentPath.replace(".txt", "-") + "frequency";
        fileChooser.setSelectedFile(new File(path));

        while(!flag) {
            flag = true;

            if(fileChooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                path = fileChooser.getSelectedFile().getPath();
                path += "." + fileChooser.getFileFilter().getDescription();
                flag = FileController.saveFile(path, simulation);
            }
        }
    }

    private Process getProcess(String[] command) throws IOException {
        String directory = "src\\resource\\algorithm";

        ProcessBuilder processBuilder = new ProcessBuilder();
        processBuilder.directory(new File(directory));
        processBuilder.command(command);

        return processBuilder.start();
    }

    private String checkCodedCircuit(String codedCircuit) {
        StringBuilder newCodedCircuit = new StringBuilder();
        String change = "";

        String[] element;
        String[] elements = codedCircuit.replace(" ", "").split("->");

        for(int i = elements.length - 1; i >= 0; i--) {
            element = elements[i].replace("[", "")
                    .replace("]", "").split("\\|");

            if(change.isEmpty()) {
                change = element[2];
            }

            for(int j = 0; j < 3; j++) {
                if(element[j].equals(change)) {
                    element[j] = "1002";
                }
            }

            newCodedCircuit.insert(0, "[" + element[0] + "|" + element[1] + "|" + element[2] + "|"
                    + element[3] + "|" + element[4] + "|" + element[5] + "]->");
        }

        return newCodedCircuit.toString();
    }
}
