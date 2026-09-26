package controller;

import api_client.ApiConfig;
import api_client.CircuitApiClient;
import dto.CircuitRequest;
import dto.OptimizationResult;
import format_converter.FormatConverter;
import model.Algoritmo;
import model.Circuit;
import model.Element;
import model.IdealFilter;
import model.ModoEjecucion;
import model.Simulation;
import model.TipoFiltro;
import view.AlgorithmSelectionPanel;
import view.GenerateCircuitPanel;
import view.InputCircuitPanel;
import view.LoadingDialog;
import view.MainFrame;

import javax.imageio.ImageIO;
import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.ExecutionException;

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
            generateCircuitFlow();
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

    // ------------------------------------------------------------------
    // Integración con la API de optimización (reemplaza al main.exe -g legado)
    // ------------------------------------------------------------------

    /**
     * Menú inicial de "Generate circuit": primero pregunta el modo
     * (probar los 4 algoritmos vs elegir uno puntual), luego muestra
     * AlgorithmSelectionPanel para elegir filtro (siempre) y algoritmo
     * (solo en modo específico), y recién después abre GenerateCircuitPanel
     * con el resto del formulario (entorno físico + hiperparámetros del AG),
     * igual que antes.
     *
     * "Probar todos los algoritmos" se deja armado en la interfaz (el
     * usuario ve la pantalla completa, incluyendo elegir el filtro, tal
     * como se pidió) pero se bloquea antes de llamar a la API, porque hoy
     * no existe un endpoint en el backend que corra los 4 algoritmos y
     * devuelva el mejor — GeneticController.SERVICE_MAP solo tiene
     * registrado ("pasa_altas", "algoritmo_genetico"). Cuando ese endpoint
     * exista, basta con quitar el primer "if" de abajo.
     */
    private void generateCircuitFlow() {
        int modoOption = JOptionPane.showOptionDialog(
                frame,
                "What do you want to do?",
                "Generate circuit",
                JOptionPane.DEFAULT_OPTION,
                JOptionPane.QUESTION_MESSAGE,
                null,
                new Object[] {"Try all algorithms", "Choose an algorithm", "Cancel"},
                "Choose an algorithm");

        if (modoOption != 0 && modoOption != 1) {
            return; // Cancel, Esc, o cerró la ventana
        }

        ModoEjecucion modo = modoOption == 0
                ? ModoEjecucion.TODOS_LOS_ALGORITMOS
                : ModoEjecucion.ALGORITMO_ESPECIFICO;

        AlgorithmSelectionPanel selectionPanel = new AlgorithmSelectionPanel(modo);
        int selectionOption = JOptionPane.showOptionDialog(
                frame,
                selectionPanel,
                "Selection",
                JOptionPane.OK_CANCEL_OPTION,
                JOptionPane.PLAIN_MESSAGE,
                null,
                new Object[] {"Continue", "Cancel"},
                "Continue");

        if (selectionOption != JOptionPane.OK_OPTION) {
            return;
        }

        TipoFiltro tipoFiltroElegido = (TipoFiltro) selectionPanel.tipoFiltro.getSelectedItem();

        if (modo == ModoEjecucion.TODOS_LOS_ALGORITMOS) {
            JOptionPane.showMessageDialog(frame,
                    "\"Try all algorithms\" is not implemented in the backend yet " +
                            "(there is no endpoint that runs all 4 algorithms and compares results). " +
                            "For now, use \"Choose an algorithm\".",
                    "Not available yet", JOptionPane.INFORMATION_MESSAGE);
            return;
        }

        Algoritmo algoritmoElegido = (Algoritmo) selectionPanel.algoritmo.getSelectedItem();
        if (!algoritmoElegido.implementadoEnBackend) {
            JOptionPane.showMessageDialog(frame,
                    "\"" + algoritmoElegido + "\" is not implemented in the backend yet " +
                            "(GeneticController.SERVICE_MAP only registers algoritmo_genetico). " +
                            "Choose \"Genetic algorithm\" for now.",
                    "Not available yet", JOptionPane.INFORMATION_MESSAGE);
            return;
        }

        if (!tipoFiltroElegido.implementadoEnBackend) {
            JOptionPane.showMessageDialog(frame,
                    "\"" + tipoFiltroElegido + "\" is not implemented in the backend yet " +
                            "(GeneticController.SERVICE_MAP only registers pasa_altas). " +
                            "Choose \"High Passes\" for now.",
                    "Not available yet", JOptionPane.INFORMATION_MESSAGE);
            return;
        }

        // Se usa como punto de partida de IdealFilter; GenerateCircuitController
        // lo sigue recalculando en vivo a partir de las frecuencias de
        // paso/atenuación mientras el diálogo de abajo está abierto, igual que
        // ya hacía antes de este cambio.
        frame.circuit.getIdealFilter().setType(tipoFiltroElegido.idealFilterType);

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

        if (option == JOptionPane.OK_OPTION) {
            generateCircuitViaApi(generateCircuitController.generateCircuitPanel, algoritmoElegido);
        }
    }

    /**
     * Sustituye la invocación al binario legado por una llamada HTTP a la API
     * de optimización en Python. Corre en un SwingWorker para no congelar la
     * interfaz (el "while(process.isAlive())" original bloqueaba el EDT; una
     * llamada de red que puede tardar varios minutos lo haría aún peor).
     *
     * @param generateCircuitPanel el diálogo que el usuario acaba de cerrar
     *                              con "Generate"; de ahí se leen los 6
     *                              spinners de hiperparámetros del AG.
     * @param algoritmoElegido     el algoritmo elegido en generateCircuitFlow().
     */
    private void generateCircuitViaApi(GenerateCircuitPanel generateCircuitPanel, Algoritmo algoritmoElegido) {
        // Segundo chequeo del mismo tipo de filtro: generateCircuitFlow() ya
        // validó esto antes de abrir GenerateCircuitPanel, pero
        // GenerateCircuitController puede haber recalculado IdealFilter.type
        // en vivo mientras ese diálogo estuvo abierto (según las frecuencias
        // de paso/atenuación que el usuario haya tecleado ahí), así que se
        // vuelve a comprobar con el valor final antes de llamar a la API.
        TipoFiltro tipoFiltroFinal = TipoFiltro.fromIdealFilterType(frame.circuit.getIdealFilter().getType());
        if (!tipoFiltroFinal.implementadoEnBackend) {
            JOptionPane.showMessageDialog(frame,
                    "\"" + tipoFiltroFinal + "\" is not implemented in the backend yet. " +
                            "Adjust the passage/attenuation frequencies so the final filter " +
                            "type stays \"High Passes\".",
                    "Not available yet", JOptionPane.ERROR_MESSAGE);
            return;
        }

        CircuitRequest request;
        try {
            request = construirCircuitRequest(generateCircuitPanel, algoritmoElegido);
        } catch (IllegalArgumentException ex) {
            // CircuitRequest valida rangos (prob_cruce entre 0 y 1, elitismo
            // <= tam_poblacion, etc.) en su propio constructor; si algo no
            // cuadra, se avisa aquí en vez de mandar una petición inválida.
            JOptionPane.showMessageDialog(frame, ex.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        CircuitApiClient apiClient = new CircuitApiClient();
        LoadingDialog loadingDialog = new LoadingDialog(frame,
                "Optimizando circuito (puede tardar varios minutos)...");

        SwingWorker<OptimizationResult, Void> worker = new SwingWorker<>() {
            @Override
            protected OptimizationResult doInBackground() throws Exception {
                return apiClient.optimizarPasaAltas(request);
            }

            @Override
            protected void done() {
                loadingDialog.dispose();
                try {
                    OptimizationResult result = get();
                    aplicarResultadoApi(result);
                    update();
                    mostrarGraficaResultado(result);
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                } catch (ExecutionException ex) {
                    Throwable cause = ex.getCause() != null ? ex.getCause() : ex;
                    JOptionPane.showMessageDialog(frame, cause.getMessage(),
                            "Error", JOptionPane.ERROR_MESSAGE);
                }
            }
        };

        worker.execute();
        loadingDialog.setVisible(true); // se bloquea aquí hasta que done() llame a dispose()
    }

    /**
     * Junta el entorno físico y el barrido (Simulation), las frecuencias
     * objetivo (IdealFilter) y los 6 hiperparámetros del AG (leídos
     * directamente de los spinners nuevos de GenerateCircuitPanel, sin
     * ChangeListener de por medio — ver el comentario en esa clase) en un
     * único CircuitRequest. El algoritmo y el filtro ya no son constantes de
     * ApiConfig: algoritmoElegido viene de generateCircuitFlow(), y el filtro
     * se deriva del IdealFilter.type final (que puede haber cambiado en vivo
     * dentro de GenerateCircuitPanel).
     */
    private CircuitRequest construirCircuitRequest(GenerateCircuitPanel generateCircuitPanel, Algoritmo algoritmoElegido) {
        Simulation simulacion = frame.circuit.getSimulation();
        IdealFilter idealFilter = frame.circuit.getIdealFilter();
        TipoFiltro tipoFiltroFinal = TipoFiltro.fromIdealFilterType(idealFilter.getType());

        return new CircuitRequest(
                algoritmoElegido.valorApi,
                tipoFiltroFinal.valorApi,
                ApiConfig.MODO_AVANZADO,
                simulacion.getSupplyVoltage(),
                simulacion.getSupplyResistance(),
                simulacion.getLoadResistance(),
                simulacion.getInitialFrequency(),
                simulacion.getFinalFrequency(),
                idealFilter.getAttenuationFrequency(),
                idealFilter.getPassageFrequency(),
                (int) generateCircuitPanel.tamPoblacion.getValue(),
                (int) generateCircuitPanel.numGeneraciones.getValue(),
                (double) generateCircuitPanel.probCruce.getValue(),
                (double) generateCircuitPanel.probMutacion.getValue(),
                (int) generateCircuitPanel.elitismo.getValue(),
                (int) generateCircuitPanel.torneoK.getValue()
        );
    }

    /**
     * Aplica el resultado de la API al modelo de dibujo: construye la lista de
     * Element a partir de los componentes optimizados (FormatConverter traduce
     * el valor físico real + conexión a tierra del JSON a los índices que
     * espera Element), la vuelca en frame.circuit (vía addElement, para que
     * Circuit siga calculando bien el ancho de la imagen), y reconstruye el
     * string "coded circuit" para que el resto de la app (la etiqueta de
     * MainFrame, "Save Full File") siga funcionando igual que con el flujo viejo.
     */
    private void aplicarResultadoApi(OptimizationResult result) {
        List<Element> elementos = FormatConverter.convertir(result.componentesOptimizados);

        frame.circuit.clearCircuit();
        for (Element elemento : elementos) {
            frame.circuit.addElement(elemento);
        }

        frame.circuit.setCodedCircuit(FormatConverter.toCodedCircuitString(elementos));
        frame.circuit.setFitness(result.fitness);
        frame.circuit.setElements(elementos.size());
        // circuit.order no se toca: nada en la UI lo lee hoy fuera del parser
        // de archivos legado, y su semántica original ("1, 2 o 3 según la
        // banda de corte") no calza claramente con un filtro de 4to orden.

        // La API no devuelve el barrido de frecuencias punto a punto (solo un
        // par de valores escalares -amp_paso/amp_aten, o fc- más el PNG ya
        // graficado), así que no hay datos con los que llenar Simulation.values
        // de forma honesta. Se deja vacío a propósito: SimulationPanel y
        // FrequencyPanel no dibujan/listan una curva generada falsa. La curva
        // real se ve en la imagen que devuelve la API (mostrarGraficaResultado).
        Simulation simulacion = frame.circuit.getSimulation();
        simulacion.clearValues();
    }

    /** Muestra el PNG (matplotlib) que ya devuelve la API, tal cual, en un diálogo aparte. */
    private void mostrarGraficaResultado(OptimizationResult result) {
        if (result.graficaPngBase64 == null || result.graficaPngBase64.isBlank()) {
            return;
        }

        try {
            byte[] bytes = Base64.getDecoder().decode(result.graficaPngBase64);
            BufferedImage image = ImageIO.read(new ByteArrayInputStream(bytes));

            if (image == null) {
                throw new IOException("El servidor devolvió datos que no son una imagen PNG válida.");
            }

            JLabel label = new JLabel(new ImageIcon(image));
            JOptionPane.showMessageDialog(frame, new JScrollPane(label),
                    "Resultado de la optimización (fitness = " + result.fitness + ")",
                    JOptionPane.PLAIN_MESSAGE);
        } catch (IOException | IllegalArgumentException ex) {
            JOptionPane.showMessageDialog(frame, "No se pudo mostrar la gráfica devuelta por la API: "
                    + ex.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    // ------------------------------------------------------------------
    // Resto del controller (sin cambios respecto al original)
    // ------------------------------------------------------------------

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