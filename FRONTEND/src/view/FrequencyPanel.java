package view;

import model.Simulation;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.util.ArrayList;

public class FrequencyPanel extends JScrollPane {
    public Simulation simulation;

    public JTable table;

    public FrequencyPanel(Simulation simulation) {
        this.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
        this.setBorder(null);

        this.simulation = simulation;

        table = new JTable() {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };

        this.updateTable();
        this.setViewportView(table);
    }

    public void updateTable() {
        Object[] identifiers = {"frequency", "input voltage", "output voltage", "gain"};

        DefaultTableModel tableModel = new DefaultTableModel();
        tableModel.setColumnIdentifiers(identifiers);

        for(double[] value : simulation.getValues()) {
            tableModel.addRow(new Object[] {
                    value[0],
                    value[1],
                    value[2],
                    value[3]
            });
        }

        table.setModel(tableModel);
    }
}
