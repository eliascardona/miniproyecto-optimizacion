package controller;

import model.Element;
import view.InputCircuitPanel;

import javax.swing.*;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class InputCircuitController implements ChangeListener, ActionListener {
    public InputCircuitPanel inputCircuitPanel;

    private int initialFrequency;
    private int finalFrequency;

    private final Integer[][] values = {{10, 15, 22, 33, 47, 68}, {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82},
            {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}};
    private final Integer[][] decades = {{-5, -6, -7, -8, -9}, {1, 2, 3, 4, 5, 6}, {-1, -2, -3, -4, -5, -6}};
    private int nodeA = 1;
    private int indexSelected;

    public InputCircuitController(InputCircuitPanel inputCircuitPanel) {
        this.inputCircuitPanel = inputCircuitPanel;

        this.inputCircuitPanel.supplyVoltage.addChangeListener(this);
        this.inputCircuitPanel.initialFrequency.addChangeListener(this);
        this.inputCircuitPanel.finalFrequency.addChangeListener(this);

        this.inputCircuitPanel.type.addActionListener(this);
        this.inputCircuitPanel.add.addActionListener(this);
        this.inputCircuitPanel.edit.addActionListener(this);

        initialFrequency = this.inputCircuitPanel.simulation.getInitialFrequency();
        finalFrequency = this.inputCircuitPanel.simulation.getFinalFrequency();
    }

    @Override
    public void stateChanged(ChangeEvent e) {
        if(inputCircuitPanel.supplyVoltage.equals(e.getSource())) {
            double supplyVoltage = (double) inputCircuitPanel.supplyVoltage.getValue();
            inputCircuitPanel.simulation.setSupplyVoltage(supplyVoltage);
        }

        if(inputCircuitPanel.initialFrequency.equals(e.getSource())) {
            int max = inputCircuitPanel.idealFilter.getType() == 1 ?
                    inputCircuitPanel.idealFilter.getPassageFrequency() :
                    inputCircuitPanel.idealFilter.getAttenuationFrequency();

            initialFrequency = (int) inputCircuitPanel.initialFrequency.getValue();

            if(initialFrequency >= max - 10) {
                initialFrequency = max - 10;
                inputCircuitPanel.initialFrequency.setValue(initialFrequency);
            }

            inputCircuitPanel.simulation.setInitialFrequency(initialFrequency);
        }

        if(inputCircuitPanel.finalFrequency.equals(e.getSource())) {
            int min = inputCircuitPanel.idealFilter.getType() == 1 ?
                    inputCircuitPanel.idealFilter.getPassageFrequency() :
                    inputCircuitPanel.idealFilter.getAttenuationFrequency();

            finalFrequency = (int) inputCircuitPanel.finalFrequency.getValue();

            if(finalFrequency <= min + 10) {
                finalFrequency = min + 10;
                inputCircuitPanel.finalFrequency.setValue(finalFrequency);
            }

            inputCircuitPanel.simulation.setFinalFrequency(finalFrequency);
        }
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        if(inputCircuitPanel.type.equals(e.getSource())) {
            int type = inputCircuitPanel.type.getSelectedIndex();

            inputCircuitPanel.value.removeAllItems();
            inputCircuitPanel.decade.removeAllItems();

            for(Integer i : values[type]) {
                inputCircuitPanel.value.addItem(i);
            }

            for(Integer i : decades[type]) {
                inputCircuitPanel.decade.addItem(i);
            }
        }

        if(inputCircuitPanel.add.equals(e.getSource())) {
            inputCircuitPanel.circuit.addElement(new Element(
                    nodeA,
                    inputCircuitPanel.connection.getSelectedIndex() == 0 ? 0 : nodeA + 1,
                    inputCircuitPanel.connection.getSelectedIndex() == 0 ? nodeA : nodeA + 1,
                    inputCircuitPanel.type.getSelectedIndex(),
                    inputCircuitPanel.value.getSelectedIndex(),
                    inputCircuitPanel.decade.getSelectedIndex()
            ));

            int lastIndex = inputCircuitPanel.circuit.getCircuit().size() - 1;
            nodeA = inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNodeA();

            String s = "[" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNode1()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNode2()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNodeA()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getType()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getValue()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getDecade() + "]->";

            inputCircuitPanel.circuit.setCodedCircuit(inputCircuitPanel.circuit.getCodedCircuit() + s);

            inputCircuitPanel.elements.add(new JButton(s));
            inputCircuitPanel.elements.get(lastIndex).addActionListener(this);

            inputCircuitPanel.codedCircuit.add(inputCircuitPanel.elements.get(lastIndex));
            inputCircuitPanel.scrollPane.setViewportView(inputCircuitPanel.codedCircuit);

            inputCircuitPanel.circuitPanel.updateCircuit();
        }

        if(inputCircuitPanel.edit.equals(e.getSource())) {
            inputCircuitPanel.circuit.getCircuit().get(indexSelected).setNode2(
                    inputCircuitPanel.connection.getSelectedIndex() == 0 ? 0 :
                            inputCircuitPanel.circuit.getCircuit().get(indexSelected).getNode1() + 1
            );
            inputCircuitPanel.circuit.getCircuit().get(indexSelected).setNodeA(
                    inputCircuitPanel.connection.getSelectedIndex() == 0 ?
                            inputCircuitPanel.circuit.getCircuit().get(indexSelected).getNode1() :
                            inputCircuitPanel.circuit.getCircuit().get(indexSelected).getNode1() + 1
            );

            inputCircuitPanel.circuit.getCircuit().get(indexSelected).setType(inputCircuitPanel.type.getSelectedIndex());
            inputCircuitPanel.circuit.getCircuit().get(indexSelected).setValue(inputCircuitPanel.value.getSelectedIndex());
            inputCircuitPanel.circuit.getCircuit().get(indexSelected).setDecade(inputCircuitPanel.decade.getSelectedIndex());

            int lastIndex = inputCircuitPanel.circuit.getCircuit().size() - 1;
            nodeA = inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNodeA();

            String s = "[" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNode1()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNode2()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getNodeA()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getType()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getValue()
                    + "|" + inputCircuitPanel.circuit.getCircuit().get(lastIndex).getDecade() + "]->";

            inputCircuitPanel.circuit.setCodedCircuit(inputCircuitPanel.circuit.getCodedCircuit().replace(
                    inputCircuitPanel.elements.get(indexSelected).getText(), s));

            inputCircuitPanel.elements.get(indexSelected).setText(s);

            inputCircuitPanel.add.setVisible(true);
            inputCircuitPanel.edit.setVisible(false);

            inputCircuitPanel.circuitPanel.updateCircuit();
        }

        for(JButton b : inputCircuitPanel.elements) {
            if(b.equals(e.getSource())) {
                String[] s = b.getText().replace("[", "")
                        .replace("]", "")
                        .replace("->", "")
                        .split("\\|");

                if(s[1].equals("0")) {
                    inputCircuitPanel.connection.setSelectedIndex(0);
                } else {
                    inputCircuitPanel.connection.setSelectedIndex(1);
                }

                inputCircuitPanel.type.setSelectedIndex(Integer.parseInt(s[3]));
                inputCircuitPanel.value.setSelectedIndex(Integer.parseInt(s[4]));
                inputCircuitPanel.decade.setSelectedIndex(Integer.parseInt(s[5]));

                indexSelected = inputCircuitPanel.elements.indexOf(b);

                inputCircuitPanel.add.setVisible(false);
                inputCircuitPanel.edit.setVisible(true);

                break;
            }
        }
    }
}
