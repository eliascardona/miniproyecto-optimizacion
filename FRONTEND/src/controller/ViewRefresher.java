package controller;

import view.MainFrame;

/**
 * Sincroniza los paneles de MainFrame con el estado actual de
 * frame.circuit. Antes: MainController.update() (privado, por eso cada
 * acción nueva no habría podido reutilizarlo).
 */
public class ViewRefresher {
    private final MainFrame frame;

    public ViewRefresher(MainFrame frame) {
        this.frame = frame;
    }

    public void refresh() {
        frame.codedCircuit.setText("Coded circuit: " + frame.circuit.getCodedCircuit());
        frame.circuitPanel.updateCircuit();

        frame.simulationPanel.simulation = frame.circuit.getSimulation();
        frame.simulationPanel.updateGraph();

        frame.frequencyPanel.simulation = frame.circuit.getSimulation();
        frame.frequencyPanel.updateTable();
    }
}