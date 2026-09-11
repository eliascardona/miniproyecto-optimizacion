package controller;

import model.Circuit;
import model.Element;
import model.IdealFilter;
import model.Simulation;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.image.BufferedImage;
import java.io.*;

public record FileController() {
    public static boolean readFile(String path, Circuit circuit) {
        String noContains = "\nThe coded circuit\nThe simulation properties" +
                "\nThe filter properties\nThe simulation table";

        Boolean[] flags = {false, false, false, false};

        try {
            FileReader fileReader = new FileReader(path);
            BufferedReader bufferedReader = new BufferedReader(fileReader);

            Simulation simulation = new Simulation();
            IdealFilter idealFilter = new IdealFilter();

            String line;
            String[] values;

            circuit.clearCircuit();

            line = bufferedReader.readLine();

            while(line != null) {
                if(line.contains("Cir")) {
                    circuit.setCodedCircuit(line.replace(" ", "")
                            .replace("Cir", ""));

                    values = line.replace(" ", "").split("->");
                    values = values[values.length - 1]
                            .replace("[", "")
                            .replace("]", "")
                            .split("\\|");

                    circuit.setFitness(Double.parseDouble(values[0]));
                    circuit.setElements(Integer.parseInt(values[1]));
                    circuit.setOrder(Integer.parseInt(values[2]));

                    decodedCircuit(circuit);

                    flags[0] = true;
                    noContains = noContains.replace("\nThe coded circuit", "");

                    line = bufferedReader.readLine();
                    continue;
                }

                if(line.contains("Sim")) {
                    values = line.split(" ");

                    simulation.setSupplyVoltage(Double.parseDouble(values[1]));
                    simulation.setSupplyResistance(Integer.parseInt(values[2]));
                    simulation.setLoadResistance(Integer.parseInt(values[3]));
                    simulation.setInitialFrequency(Integer.parseInt(values[4]));
                    simulation.setFinalFrequency(Integer.parseInt(values[5]));

                    flags[1] = true;
                    noContains = noContains.replace("\nThe simulation properties", "");

                    line = bufferedReader.readLine();
                    continue;
                }

                if(line.contains("Fil")) {
                    values = line.split(" ");

                    idealFilter.setPassageVoltage(Double.parseDouble(values[1]));
                    idealFilter.setAttenuationVoltage(Double.parseDouble(values[2]));
                    idealFilter.setPassageFrequency(Integer.parseInt(values[3]));
                    idealFilter.setAttenuationFrequency(Integer.parseInt(values[4]));
                    idealFilter.setType(Integer.parseInt(values[5]));

                    flags[2] = true;
                    noContains = noContains.replace("\nThe filter properties", "");

                    line = bufferedReader.readLine();
                    continue;
                }

                if(line.contains(",")) {
                    values = line.split(",");

                    simulation.addValue(new double[]{
                            Double.parseDouble(values[0]),
                            Double.parseDouble(values[1]),
                            Double.parseDouble(values[2]),
                            Double.parseDouble(values[3])
                    });

                    flags[3] = true;
                    noContains = noContains.replace("\nThe simulation table", "");
                }

                line = bufferedReader.readLine();
            }

            circuit.setSimulation(simulation);
            circuit.setIdealFilter(idealFilter);

            fileReader.close();
        } catch (IOException e) {
            JOptionPane.showMessageDialog(null, e.getMessage(),
                    "Error",JOptionPane.ERROR_MESSAGE);
        }

        if(!flags[0] || !flags[1] || !flags[2] || !flags[3]) {
            JOptionPane.showMessageDialog(null,
                    "The file is incomplete, it does not contains:" + noContains,
                    "Error",JOptionPane.ERROR_MESSAGE);
            return false;
        }

        return true;
    }

    public static boolean saveFullFile(String path, Circuit circuit) {
        File file = new File(path);

        if (file.exists()) {
            if (JOptionPane.showOptionDialog(
                    null,
                    path + " already exists, do you want to replace it?",
                    "Confirm",
                    JOptionPane.YES_NO_OPTION,
                    JOptionPane.WARNING_MESSAGE,
                    null,
                    new Object[]{"Yes", "No"},
                    "No") == JOptionPane.NO_OPTION) {
                return false;
            }
        }

        try {
            BufferedWriter bufferedWriter = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file)));

            bufferedWriter.write("Cir " + circuit.getCodedCircuit() + "\n");

            bufferedWriter.write("Sim " + circuit.getSimulation().getSupplyVoltage());
            bufferedWriter.write(" " + circuit.getSimulation().getSupplyResistance());
            bufferedWriter.write(" " + circuit.getSimulation().getLoadResistance());
            bufferedWriter.write(" " + circuit.getSimulation().getInitialFrequency());
            bufferedWriter.write(" " + circuit.getSimulation().getFinalFrequency() + "\n");

            bufferedWriter.write("Fil " + circuit.getIdealFilter().getPassageVoltage());
            bufferedWriter.write(" " + circuit.getIdealFilter().getAttenuationVoltage());
            bufferedWriter.write(" " + circuit.getIdealFilter().getPassageFrequency());
            bufferedWriter.write(" " + circuit.getIdealFilter().getAttenuationFrequency());
            bufferedWriter.write(" " + circuit.getIdealFilter().getType() + "\n");

            for(double[] value : circuit.getSimulation().getValues()) {
                bufferedWriter.write(value[0] + ",");
                bufferedWriter.write(value[1] + ",");
                bufferedWriter.write(value[2] + ",");
                bufferedWriter.write(value[3] + "\n");
            }

            bufferedWriter.close();
        } catch (IOException e) {
            JOptionPane.showMessageDialog(null, e.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
        }

        return true;
    }

    public static boolean saveImage(String path, BufferedImage image) {
        File file = new File(path);

        if (file.exists()) {
            if (JOptionPane.showOptionDialog(
                    null,
                    path + " already exists, do you want to replace it?",
                    "Confirm",
                    JOptionPane.YES_NO_OPTION,
                    JOptionPane.WARNING_MESSAGE,
                    null,
                    new Object[]{"Yes", "No"},
                    "No") == JOptionPane.NO_OPTION) {
                return false;
            }
        }

        try {
            ImageIO.write(image, "png", new File(path));
        } catch (IOException e) {
            JOptionPane.showMessageDialog(null, e.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
        }

        return true;
    }

    public static boolean saveFile(String path, Simulation simulation) {
        File file = new File(path);

        if (file.exists()) {
            if (JOptionPane.showOptionDialog(
                    null,
                    path + " already exists, do you want to replace it?",
                    "Confirm",
                    JOptionPane.YES_NO_OPTION,
                    JOptionPane.WARNING_MESSAGE,
                    null,
                    new Object[]{"Yes", "No"},
                    "No") == JOptionPane.NO_OPTION) {
                return false;
            }
        }

        try {
            BufferedWriter bufferedWriter = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file)));

            bufferedWriter.write("frequency,input voltage,output voltage,gain\n");

            for(double[] value : simulation.getValues()) {
                bufferedWriter.write(value[0] + ",");
                bufferedWriter.write(value[1] + ",");
                bufferedWriter.write(value[2] + ",");
                bufferedWriter.write(value[3] + "\n");
            }

            bufferedWriter.close();
        } catch (IOException e) {
            JOptionPane.showMessageDialog(null, e.getMessage(),
                    "Error", JOptionPane.ERROR_MESSAGE);
        }

        return true;
    }

    private static void decodedCircuit(Circuit circuit) {
        String[] element;
        String[] elements = circuit.getCodedCircuit().replace(" ", "").split("->");

        for(int i = 0; i < circuit.getElements(); i++) {
            element = elements[i].replace("[", "")
                    .replace("]", "").split("\\|");

            circuit.addElement(new Element(
                    Integer.parseInt(element[0]),
                    Integer.parseInt(element[1]),
                    Integer.parseInt(element[2]),
                    Integer.parseInt(element[3]),
                    Integer.parseInt(element[4]),
                    Integer.parseInt(element[5])
            ));
        }
    }
}
