package controller;

import view.GenerateCircuitPanel;

import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class GenerateCircuitController implements ChangeListener, ActionListener {
    public GenerateCircuitPanel generateCircuitPanel;

    private double passageVoltage;
    private double attenuationVoltage;
    private int passageFrequency;
    private int attenuationFrequency;

    private int initialFrequency;
    private int finalFrequency;

    public GenerateCircuitController(GenerateCircuitPanel generateCircuitPanel) {
        this.generateCircuitPanel = generateCircuitPanel;

        this.generateCircuitPanel.passageVoltage.addChangeListener(this);
        this.generateCircuitPanel.attenuationVoltage.addChangeListener(this);
        this.generateCircuitPanel.passageFrequency.addChangeListener(this);
        this.generateCircuitPanel.attenuationFrequency.addChangeListener(this);
        this.generateCircuitPanel.type.addActionListener(this);

        this.generateCircuitPanel.supplyVoltage.addChangeListener(this);
        this.generateCircuitPanel.initialFrequency.addChangeListener(this);
        this.generateCircuitPanel.finalFrequency.addChangeListener(this);

        passageVoltage = this.generateCircuitPanel.idealFilter.getPassageVoltage();
        attenuationVoltage = this.generateCircuitPanel.idealFilter.getAttenuationVoltage();
        passageFrequency = this.generateCircuitPanel.idealFilter.getPassageFrequency();
        attenuationFrequency = this.generateCircuitPanel.idealFilter.getAttenuationFrequency();

        initialFrequency = this.generateCircuitPanel.simulation.getInitialFrequency();
        finalFrequency = this.generateCircuitPanel.simulation.getFinalFrequency();
    }

    @Override
    public void stateChanged(ChangeEvent e) {
        if(generateCircuitPanel.passageVoltage.equals(e.getSource())) {
            passageVoltage = (double) generateCircuitPanel.passageVoltage.getValue();

            if(passageVoltage <= attenuationVoltage) {
                passageVoltage = attenuationVoltage + 0.1;
                generateCircuitPanel.passageVoltage.setValue(passageVoltage);
            }

            generateCircuitPanel.idealFilter.setPassageVoltage(passageVoltage);
        }

        if(generateCircuitPanel.attenuationVoltage.equals(e.getSource())) {
            attenuationVoltage = (double) generateCircuitPanel.attenuationVoltage.getValue();

            if(passageVoltage <= attenuationVoltage) {
                attenuationVoltage = passageVoltage - 0.1;
                generateCircuitPanel.attenuationVoltage.setValue(attenuationVoltage);
            }

            generateCircuitPanel.idealFilter.setAttenuationVoltage(attenuationVoltage);
        }

        if(generateCircuitPanel.passageFrequency.equals(e.getSource())) {
            passageFrequency = (int) generateCircuitPanel.passageFrequency.getValue();
            generateCircuitPanel.idealFilter.setPassageFrequency(passageFrequency);
        }

        if(generateCircuitPanel.attenuationFrequency.equals(e.getSource())) {
            attenuationFrequency = (int) generateCircuitPanel.attenuationFrequency.getValue();
            generateCircuitPanel.idealFilter.setAttenuationFrequency(attenuationFrequency);
        }

        if(passageFrequency == attenuationFrequency) {
            generateCircuitPanel.type.setEnabled(true);
        } else if(passageFrequency <= attenuationFrequency) {
            generateCircuitPanel.type.setEnabled(false);
            generateCircuitPanel.type.setSelectedIndex(0);
            generateCircuitPanel.idealFilter.setType(0);
        } else {
            generateCircuitPanel.type.setEnabled(false);
            generateCircuitPanel.type.setSelectedIndex(1);
            generateCircuitPanel.idealFilter.setType(1);
        }

        if(generateCircuitPanel.supplyVoltage.equals(e.getSource())) {
            double supplyVoltage = (double) generateCircuitPanel.supplyVoltage.getValue();
            generateCircuitPanel.simulation.setSupplyVoltage(supplyVoltage);
            generateCircuitPanel.simulationPanel.updateGraph();
        }

        if(generateCircuitPanel.initialFrequency.equals(e.getSource())) {
            int max = generateCircuitPanel.idealFilter.getType() == 0 ? passageFrequency : attenuationFrequency;

            initialFrequency = (int) generateCircuitPanel.initialFrequency.getValue();

            if(initialFrequency >= max - 10) {
                initialFrequency = max - 10;
                generateCircuitPanel.initialFrequency.setValue(initialFrequency);
            }

            generateCircuitPanel.simulation.setInitialFrequency(initialFrequency);
            generateCircuitPanel.simulationPanel.updateGraph();
        }

        if(generateCircuitPanel.finalFrequency.equals(e.getSource())) {
            int min = generateCircuitPanel.idealFilter.getType() == 1 ? passageFrequency : attenuationFrequency;

            finalFrequency = (int) generateCircuitPanel.finalFrequency.getValue();

            if(finalFrequency <= min + 10) {
                finalFrequency = min + 10;
                generateCircuitPanel.finalFrequency.setValue(finalFrequency);
            }

            generateCircuitPanel.simulation.setFinalFrequency(finalFrequency);
            generateCircuitPanel.simulationPanel.updateGraph();
        }

        generateCircuitPanel.simulationPanel.updateGrid();
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        if(generateCircuitPanel.type.equals(e.getSource())) {
            generateCircuitPanel.idealFilter.setType(
                    generateCircuitPanel.type.getSelectedIndex()
            );

            generateCircuitPanel.simulationPanel.updateGrid();
        }
    }
}
