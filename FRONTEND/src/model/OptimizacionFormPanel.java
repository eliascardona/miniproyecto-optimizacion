package view;

import catalogo.Catalogo;
import catalogo.Catalogo.Algoritmo;
import catalogo.Catalogo.Campo;
import catalogo.Catalogo.Filtro;
import catalogo.Catalogo.FrecuenciasDeModo;
import catalogo.Catalogo.Modo;
import catalogo.Catalogo.Severidad;
import catalogo.Catalogo.Tipo;
import catalogo.Problema;
import catalogo.ValidadorPeticion;
import dto.PeticionOptimizacion;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSpinner;
import javax.swing.SpinnerNumberModel;
import javax.swing.border.Border;
import javax.swing.border.TitledBorder;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.Insets;
import java.math.BigDecimal;
import java.math.MathContext;
import java.text.ParseException;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Formulario de UNA optimización (un filtro con un algoritmo), armado por completo a partir del
 * {@link Catalogo}: sirve igual para las 16 combinaciones porque no contiene ningún campo escrito a mano.
 *
 * Qué se muestra y de dónde sale:
 *   · Modo (básico / avanzado)         -> catalogo.modos()
 *   · Frecuencias objetivo             -> filtro.frecuencias(modo)   (cambian al cambiar el modo)
 *   · Parámetros del algoritmo         -> algoritmo.parametros()     (los mismos para todos los filtros)
 *   · Entorno físico y barrido AC      -> catalogo.entorno() y catalogo.barrido() (comunes a todo)
 *
 * Los controles NO imponen los límites del catálogo (sus topes son solo "muy anchos"): la validación
 * vive en un único lugar, {@link ValidadorPeticion}, y su resultado se muestra en vivo debajo del
 * formulario con el motivo exacto, en vez de que un control rechace un valor en silencio.
 * Los controles con un problema se marcan con borde rojo (error) o naranja (aviso).
 *
 * Lo que el usuario capturó en cada modo se recuerda mientras el diálogo está abierto: al cambiar de
 * modo y volver no se pierde.
 */
public class OptimizacionFormPanel extends JPanel {
    private static final double LIMITE_UI = 1e12;      // tope "infinito" de los spinners; los límites reales los valida el catálogo
    private static final int ANCHO_ETIQUETA = 230;
    private static final Color COLOR_ERROR = new Color(0xB00020);
    private static final Color COLOR_AVISO = new Color(0xB26A00);
    private static final Color COLOR_OK = new Color(0x2E7D32);

    public final Catalogo catalogo;
    public final Filtro filtro;
    public final Algoritmo algoritmo;

    public final JComboBox<Modo> modo;
    private final JLabel descripcionModo = new JLabel(" ");

    private final Map<String, JSpinner> spinnersEntorno = new LinkedHashMap<>();
    private final Map<String, JSpinner> spinnersBarrido = new LinkedHashMap<>();
    private final Map<String, JSpinner> spinnersParametros = new LinkedHashMap<>();
    private Map<String, JSpinner> spinnersFrecuencias = new LinkedHashMap<>();

    private final JPanel panelFrecuencias = new JPanel(new GridBagLayout());
    private final JLabel estado = new JLabel();
    private final Map<JSpinner, Border> bordeOriginal = new HashMap<>();
    private final Map<String, Map<String, Double>> memoriaPorModo = new HashMap<>();
    private final int filasMaximasDeFrecuencias;

    private String modoMostrado;
    private boolean reconstruyendo;

    /**
     * @param valoresBase valores iniciales de entorno y barrido por clave ("v_fuente", "r_fuente", "r_carga",
     *                    "f_inicial", "f_final"); lo que falte se rellena con un valor razonable del catálogo.
     */
    public OptimizacionFormPanel(Catalogo catalogo, Filtro filtro, Algoritmo algoritmo, Map<String, Double> valoresBase) {
        this.catalogo = catalogo;
        this.filtro = filtro;
        this.algoritmo = algoritmo;

        Catalogo.Combinacion combinacion = catalogo.combinacion(filtro.id(), algoritmo.id());
        if (combinacion == null) {
            throw new IllegalArgumentException("El catálogo no define " + filtro.id() + " con " + algoritmo.id());
        }

        this.filasMaximasDeFrecuencias = filtro.frecuencias().stream().mapToInt(f -> f.campos().size()).max().orElse(1);

        setLayout(new BorderLayout(8, 8));
        setBorder(BorderFactory.createEmptyBorder(4, 4, 4, 4));

        add(encabezado(), BorderLayout.NORTH);

        modo = new JComboBox<>(catalogo.modos().toArray(new Modo[0]));
        modo.setSelectedItem(catalogo.modos().stream().filter(m -> m.id().equals("AVANZADO")).findFirst().orElse(catalogo.modos().get(0)));

        JPanel izquierda = new JPanel();
        izquierda.setLayout(new BoxLayout(izquierda, BoxLayout.Y_AXIS));
        izquierda.add(panelModo());
        izquierda.add(panelFrecuencias);
        izquierda.add(panelDeCampos("Entorno físico", catalogo.entorno(), valoresBase, spinnersEntorno));
        izquierda.add(panelDeCampos("Barrido AC", catalogo.barrido().campos(), valoresBase, spinnersBarrido));

        JPanel derecha = new JPanel(new BorderLayout());
        derecha.add(panelDeCampos("Parámetros del algoritmo: " + algoritmo.etiqueta(), algoritmo.parametros(),
                combinacion.valoresIniciales(), spinnersParametros), BorderLayout.NORTH);

        JPanel centro = new JPanel(new GridLayout(1, 2, 8, 0));
        centro.add(izquierda);
        centro.add(derecha);
        add(centro, BorderLayout.CENTER);

        estado.setVerticalAlignment(JLabel.TOP);
        JScrollPane desplazable = new JScrollPane(estado);
        desplazable.setBorder(new TitledBorder("Revisión"));
        desplazable.setPreferredSize(new Dimension(760, 120));
        add(desplazable, BorderLayout.SOUTH);

        modo.addActionListener(e -> cambiarModo());
        mostrarFrecuenciasDe(((Modo) modo.getSelectedItem()).id());
        actualizarEstado();
    }

    // ------------------------------------------------------------------
    // API para quien usa el formulario
    // ------------------------------------------------------------------

    /** Lo que hay ahora en pantalla, como petición. Primero confirma lo que se esté escribiendo. */
    public PeticionOptimizacion leerPeticion() {
        confirmarEdiciones();
        return new PeticionOptimizacion(
                filtro.id(), algoritmo.id(), ((Modo) modo.getSelectedItem()).id(),
                leer(catalogo.entorno(), spinnersEntorno),
                leer(catalogo.barrido().campos(), spinnersBarrido),
                leer(algoritmo.parametros(), spinnersParametros),
                leer(frecuenciasDelModoActual().campos(), spinnersFrecuencias));
    }

    public List<Problema> problemas() {
        return ValidadorPeticion.validar(catalogo, leerPeticion());
    }

    /** Control de un campo por su clave (entorno, barrido, frecuencias del modo actual o parámetros); null si no existe. */
    public JSpinner spinnerDe(String clave) {
        for (Map<String, JSpinner> grupo : List.of(spinnersEntorno, spinnersBarrido, spinnersFrecuencias, spinnersParametros)) {
            if (grupo.containsKey(clave)) {
                return grupo.get(clave);
            }
        }
        return null;
    }

    /** Escribe un valor en el control de esa clave (lo mismo que teclearlo y confirmar). */
    public void fijarValor(String clave, double valor) {
        JSpinner spinner = spinnerDe(clave);
        if (spinner == null) {
            throw new IllegalArgumentException("El formulario no tiene el campo '" + clave + "' en el modo actual");
        }
        spinner.setValue(spinner.getValue() instanceof Long ? (Object) Long.valueOf((long) Math.rint(valor)) : (Object) Double.valueOf(valor));
    }

    public void seleccionarModo(String id) {
        modo.setSelectedItem(catalogo.modo(id));
    }

    // ------------------------------------------------------------------
    // Construcción
    // ------------------------------------------------------------------

    private JComponent encabezado() {
        JLabel titulo = new JLabel("<html><b>" + escapar(filtro.etiqueta()) + "</b> (" + escapar(filtro.descripcion())
                + ") &nbsp;&mdash;&nbsp; <b>" + escapar(algoritmo.etiqueta()) + "</b></html>");
        titulo.setToolTipText(ajustar(algoritmo.descripcion()));
        return titulo;
    }

    private JPanel panelModo() {
        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new TitledBorder("Modo de optimización"));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(2, 4, 2, 4);
        c.gridx = 0;
        c.gridy = 0;
        c.fill = GridBagConstraints.HORIZONTAL;
        c.weightx = 1;
        panel.add(modo, c);
        c.gridy = 1;
        descripcionModo.setFont(descripcionModo.getFont().deriveFont(java.awt.Font.ITALIC, 11f));
        panel.add(descripcionModo, c);
        return panel;
    }

    private JPanel panelDeCampos(String titulo, List<Campo> campos, Map<String, Double> iniciales, Map<String, JSpinner> destino) {
        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new TitledBorder(titulo));
        for (int fila = 0; fila < campos.size(); fila++) {
            Campo campo = campos.get(fila);
            JSpinner spinner = crearSpinner(campo, valorInicial(campo, iniciales));
            destino.put(campo.clave(), spinner);
            agregarFila(panel, fila, campo, spinner);
        }
        return panel;
    }

    private void agregarFila(JPanel panel, int fila, Campo campo, JSpinner spinner) {
        GridBagConstraints c = new GridBagConstraints();
        c.gridy = fila;
        c.insets = new Insets(2, 4, 2, 4);

        JLabel etiqueta = new JLabel(campo.etiquetaConUnidad() + ":");
        etiqueta.setPreferredSize(new Dimension(ANCHO_ETIQUETA, etiqueta.getPreferredSize().height));
        etiqueta.setToolTipText(ajustar(textoDeAyuda(campo)));
        spinner.setToolTipText(ajustar(textoDeAyuda(campo)));

        c.gridx = 0;
        c.anchor = GridBagConstraints.EAST;
        panel.add(etiqueta, c);
        c.gridx = 1;
        c.anchor = GridBagConstraints.WEST;
        c.fill = GridBagConstraints.HORIZONTAL;
        c.weightx = 1;
        panel.add(spinner, c);
    }

    private JSpinner crearSpinner(Campo campo, double valor) {
        SpinnerNumberModel modelo;
        String formato;
        if (campo.tipo() == Tipo.ENTERO) {
            modelo = new SpinnerNumberModel((long) Math.rint(valor), -(long) LIMITE_UI, (long) LIMITE_UI,
                    Math.max(1L, Math.round(campo.paso())));
            formato = "0";
        } else {
            modelo = new SpinnerNumberModel(valor, -LIMITE_UI, LIMITE_UI, campo.paso());
            formato = "0.######";
        }
        JSpinner spinner = new JSpinner(modelo);
        JSpinner.NumberEditor editor = new JSpinner.NumberEditor(spinner, formato);
        editor.getTextField().setColumns(9);
        spinner.setEditor(editor);
        bordeOriginal.put(spinner, spinner.getBorder());
        spinner.addChangeListener(e -> {
            if (!reconstruyendo) {
                actualizarEstado();
            }
        });
        return spinner;
    }

    // ------------------------------------------------------------------
    // Modo y frecuencias
    // ------------------------------------------------------------------

    private FrecuenciasDeModo frecuenciasDelModoActual() {
        return filtro.frecuencias(((Modo) modo.getSelectedItem()).id());
    }

    private void cambiarModo() {
        if (modoMostrado != null) {
            guardarEnMemoria(modoMostrado);
        }
        mostrarFrecuenciasDe(((Modo) modo.getSelectedItem()).id());
        actualizarEstado();
    }

    private void guardarEnMemoria(String id) {
        Map<String, Double> valores = new HashMap<>();
        for (Map.Entry<String, JSpinner> e : spinnersFrecuencias.entrySet()) {
            valores.put(e.getKey(), ((Number) e.getValue().getValue()).doubleValue());
        }
        memoriaPorModo.put(id, valores);
    }

    private void mostrarFrecuenciasDe(String id) {
        reconstruyendo = true;
        try {
            FrecuenciasDeModo definicion = filtro.frecuencias(id);
            Map<String, Double> valores = memoriaPorModo.getOrDefault(id, definicion.valoresIniciales());

            panelFrecuencias.removeAll();
            panelFrecuencias.setBorder(new TitledBorder("Frecuencias objetivo"));
            spinnersFrecuencias = new LinkedHashMap<>();
            int fila = 0;
            for (Campo campo : definicion.campos()) {
                JSpinner spinner = crearSpinner(campo, valorInicial(campo, valores));
                spinnersFrecuencias.put(campo.clave(), spinner);
                agregarFila(panelFrecuencias, fila++, campo, spinner);
            }
            // Filas de relleno: la altura del panel no cambia al pasar de un modo con 1 frecuencia a uno con 4,
            // así el diálogo no tiene que cambiar de tamaño.
            for (; fila < filasMaximasDeFrecuencias; fila++) {
                GridBagConstraints c = new GridBagConstraints();
                c.gridy = fila;
                c.insets = new Insets(2, 4, 2, 4);
                panelFrecuencias.add(Box.createRigidArea(new Dimension(1, new JSpinner().getPreferredSize().height)), c);
            }
            descripcionModo.setText("<html>" + escapar(catalogo.modo(id).descripcion()) + "</html>");
            modoMostrado = id;
            panelFrecuencias.revalidate();
            panelFrecuencias.repaint();
        } finally {
            reconstruyendo = false;
        }
    }

    // ------------------------------------------------------------------
    // Lectura y revisión
    // ------------------------------------------------------------------

    private void confirmarEdiciones() {
        for (Map<String, JSpinner> grupo : List.of(spinnersEntorno, spinnersBarrido, spinnersFrecuencias, spinnersParametros)) {
            for (JSpinner spinner : grupo.values()) {
                try {
                    spinner.commitEdit();
                } catch (ParseException ignorada) {
                    // Texto a medio escribir: se conserva el último valor válido, igual que al perder el foco.
                }
            }
        }
    }

    private Map<String, Number> leer(List<Campo> campos, Map<String, JSpinner> spinners) {
        Map<String, Number> valores = new LinkedHashMap<>();
        for (Campo campo : campos) {
            double v = redondear(((Number) spinners.get(campo.clave()).getValue()).doubleValue());
            valores.put(campo.clave(), campo.normalizar(v));
        }
        return valores;
    }

    /** Quita el ruido de coma flotante de los pasos del spinner (0.1 + 0.2 = 0.30000000000000004). */
    public static double redondear(double v) {
        return v == 0 ? 0 : new BigDecimal(v).round(new MathContext(12)).doubleValue();
    }

    private void actualizarEstado() {
        List<Problema> problemas = problemas();

        Map<String, Severidad> peor = new HashMap<>();
        for (Problema p : problemas) {
            peor.merge(p.clave(), p.severidad(), (a, b) -> a == Severidad.ERROR || b == Severidad.ERROR ? Severidad.ERROR : Severidad.AVISO);
        }
        for (Map<String, JSpinner> grupo : List.of(spinnersEntorno, spinnersBarrido, spinnersFrecuencias, spinnersParametros)) {
            for (Map.Entry<String, JSpinner> e : grupo.entrySet()) {
                marcar(e.getValue(), peor.get(e.getKey()));
            }
        }

        StringBuilder html = new StringBuilder("<html><body style='width:700px'>");
        if (problemas.isEmpty()) {
            html.append("<font color='").append(hex(COLOR_OK)).append("'>Todo en orden: los valores cumplen las reglas del catálogo.</font>");
        }
        for (Problema p : problemas) {
            html.append("<font color='").append(hex(p.esError() ? COLOR_ERROR : COLOR_AVISO)).append("'><b>")
                    .append(p.esError() ? "Error" : "Aviso").append(":</b> ").append(escapar(p.mensaje())).append("</font><br>");
        }
        html.append("</body></html>");
        estado.setText(html.toString());
    }

    private void marcar(JSpinner spinner, Severidad severidad) {
        Border original = bordeOriginal.get(spinner);
        if (severidad == null) {
            spinner.setBorder(original);
        } else {
            Color color = severidad == Severidad.ERROR ? COLOR_ERROR : COLOR_AVISO;
            spinner.setBorder(BorderFactory.createLineBorder(color, 2));
        }
    }

    // ------------------------------------------------------------------
    // Utilidades
    // ------------------------------------------------------------------

    private static double valorInicial(Campo campo, Map<String, Double> iniciales) {
        Double v = iniciales == null ? null : iniciales.get(campo.clave());
        if (v != null) {
            return v;
        }
        if (campo.idealMin() != null) {
            return campo.idealMin();
        }
        if (campo.minimo() != null) {
            return campo.minimoExclusivo() ? campo.minimo() + campo.paso() : campo.minimo();
        }
        return 1;
    }

    private static String textoDeAyuda(Campo campo) {
        return campo.descripcion().isBlank() ? campo.etiqueta() : campo.descripcion();
    }

    private static String ajustar(String texto) {
        return "<html><body style='width:320px'>" + escapar(texto) + "</body></html>";
    }

    private static String escapar(String texto) {
        return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static String hex(Color c) {
        return String.format("#%06X", c.getRGB() & 0xFFFFFF);
    }
}