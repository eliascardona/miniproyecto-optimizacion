package view;

import catalogo.Catalogo;
import catalogo.Catalogo.Algoritmo;
import catalogo.Catalogo.Filtro;

import javax.swing.BorderFactory;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.border.TitledBorder;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;

/**
 * Segundo paso de "Generate circuit": el usuario elige UN filtro y UN algoritmo.
 *
 * Las opciones salen del {@link Catalogo} que entrega el backend: solo aparecen los filtros que tienen al
 * menos un algoritmo disponible y, para el filtro elegido, solo los algoritmos que el servidor ejecuta de
 * verdad. Ya no hay banderas "implementado en el backend" escritas en el cliente que se puedan desfasar.
 */
public class AlgorithmSelectionPanel extends JPanel {
    public final Catalogo catalogo;
    public final JComboBox<Filtro> tipoFiltro;
    public final JComboBox<Algoritmo> algoritmo;
    private final JLabel descripcion = new JLabel(" ");

    public AlgorithmSelectionPanel(Catalogo catalogo) {
        this.catalogo = catalogo;
        this.tipoFiltro = new JComboBox<>(catalogo.filtrosDisponibles().toArray(new Filtro[0]));
        this.algoritmo = new JComboBox<>();

        setLayout(new GridBagLayout());
        setBorder(new TitledBorder("Choose filter and algorithm"));

        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(4, 4, 4, 8);

        c.gridx = 0;
        c.gridy = 0;
        c.anchor = GridBagConstraints.EAST;
        add(new JLabel("Filter:"), c);
        c.gridx = 1;
        c.fill = GridBagConstraints.HORIZONTAL;
        add(tipoFiltro, c);

        c.gridx = 0;
        c.gridy = 1;
        c.fill = GridBagConstraints.NONE;
        add(new JLabel("Algorithm:"), c);
        c.gridx = 1;
        c.fill = GridBagConstraints.HORIZONTAL;
        add(algoritmo, c);

        c.gridx = 0;
        c.gridy = 2;
        c.gridwidth = 2;
        descripcion.setBorder(BorderFactory.createEmptyBorder(4, 4, 0, 4));
        add(descripcion, c);

        tipoFiltro.addActionListener(e -> llenarAlgoritmos());
        algoritmo.addActionListener(e -> mostrarDescripcion());
        llenarAlgoritmos();
    }

    public Filtro filtroElegido() {
        return (Filtro) tipoFiltro.getSelectedItem();
    }

    public Algoritmo algoritmoElegido() {
        return (Algoritmo) algoritmo.getSelectedItem();
    }

    private void llenarAlgoritmos() {
        Filtro filtro = filtroElegido();
        Algoritmo anterior = algoritmoElegido();
        DefaultComboBoxModel<Algoritmo> modelo = new DefaultComboBoxModel<>();
        if (filtro != null) {
            catalogo.algoritmosDisponibles(filtro.id()).forEach(modelo::addElement);
        }
        algoritmo.setModel(modelo);
        if (anterior != null && modelo.getIndexOf(anterior) >= 0) {
            algoritmo.setSelectedItem(anterior);      // conserva la elección al cambiar de filtro
        }
        mostrarDescripcion();
    }

    private void mostrarDescripcion() {
        Filtro f = filtroElegido();
        Algoritmo a = algoritmoElegido();
        descripcion.setText(f == null || a == null ? " "
                : "<html><i>" + escapar(f.descripcion() + ". " + a.descripcion()) + "</i></html>");
    }

    private static String escapar(String texto) {
        return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}