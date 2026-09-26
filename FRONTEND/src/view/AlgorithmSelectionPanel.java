package view;

import model.Algoritmo;
import model.ModoEjecucion;
import model.TipoFiltro;

import javax.swing.*;
import javax.swing.border.TitledBorder;
import java.awt.*;

/**
 * Segundo paso del menú inicial de "Generate circuit": el usuario SIEMPRE
 * elige el tipo de filtro; el combo de algoritmo solo aparece en modo
 * ALGORITMO_ESPECIFICO (en modo TODOS_LOS_ALGORITMOS el backend decidirá
 * cuál usar, así que no tiene sentido pedirlo aquí — aunque hoy ese modo
 * ni siquiera está implementado en el backend, ver MainController).
 */
public class AlgorithmSelectionPanel extends JPanel {
    public final ModoEjecucion modo;
    public JComboBox<TipoFiltro> tipoFiltro;
    public JComboBox<Algoritmo> algoritmo; // null si modo == TODOS_LOS_ALGORITMOS

    public AlgorithmSelectionPanel(ModoEjecucion modo) {
        this.modo = modo;
        this.setLayout(new GridBagLayout());
        this.initComponent();
    }

    private void initComponent() {
        GridBagConstraints constraints = new GridBagConstraints();
        constraints.insets = new Insets(4, 4, 4, 8);

        this.setBorder(new TitledBorder(
                modo == ModoEjecucion.TODOS_LOS_ALGORITMOS
                        ? "Try all algorithms"
                        : "Choose algorithm"));

        constraints.gridx = 0;
        constraints.gridy = 0;
        constraints.anchor = GridBagConstraints.EAST;
        this.add(new JLabel("Filter:"), constraints);

        tipoFiltro = new JComboBox<>(TipoFiltro.values());
        tipoFiltro.setSelectedItem(TipoFiltro.PASA_ALTAS); // única implementada hoy
        constraints.gridx = 1;
        constraints.fill = GridBagConstraints.HORIZONTAL;
        this.add(tipoFiltro, constraints);

        if (modo == ModoEjecucion.ALGORITMO_ESPECIFICO) {
            constraints.gridx = 0;
            constraints.gridy = 1;
            constraints.fill = GridBagConstraints.NONE;
            constraints.anchor = GridBagConstraints.EAST;
            this.add(new JLabel("Algorithm:"), constraints);

            algoritmo = new JComboBox<>(Algoritmo.values());
            algoritmo.setSelectedItem(Algoritmo.ALGORITMO_GENETICO); // único implementado hoy
            constraints.gridx = 1;
            constraints.fill = GridBagConstraints.HORIZONTAL;
            this.add(algoritmo, constraints);
        }
    }
}
