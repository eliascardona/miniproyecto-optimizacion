package controller;

import view.MainFrame;

import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.List;
import java.util.function.Predicate;

/**
 * Todos los JFileChooser de la aplicación (abrir circuito y las 4 variantes
 * de "Save"). Antes eran 4 métodos showSaveDialog/showOpenDialog casi
 * idénticos dentro de MainController.
 *
 * Guarda `currentPath` (la última ruta abierta), que se usa para proponer el
 * nombre por defecto al guardar. Por eso las 5 acciones de archivo comparten
 * UNA instancia de esta clase (la crea MainController).
 *
 * La lectura/escritura real de archivos sigue en FileController.
 */
public class FileDialogs {
    private final MainFrame frame;
    private final ViewRefresher viewRefresher;

    private String currentPath = "";

    public FileDialogs(MainFrame frame, ViewRefresher viewRefresher) {
        this.frame = frame;
        this.viewRefresher = viewRefresher;
    }

    public void openCircuit() {
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        fileChooser.setFileFilter(new FileNameExtensionFilter("txt", "txt"));

        if (fileChooser.showOpenDialog(frame) == JFileChooser.APPROVE_OPTION) {
            currentPath = fileChooser.getSelectedFile().getPath();

            if (FileController.readFile(currentPath, frame.circuit)) {
                viewRefresher.refresh();
            }
        }
    }

    public void saveFullFile() {
        showSaveDialog("circuitFullFile",
                List.of(new FileNameExtensionFilter("txt", "txt")),
                path -> FileController.saveFullFile(path, frame.circuit));
    }

    public void saveCircuitImage() {
        saveImage("circuit", frame.circuitPanel.getImage());
    }

    public void saveSimulationImage() {
        saveImage("simulation", frame.simulationPanel.getImage());
    }

    public void saveFrequencyTable() {
        // Se aplican en este orden; el último (csv) queda como filtro activo,
        // igual que en el código original.
        showSaveDialog("frequency",
                List.of(new FileNameExtensionFilter("txt", "txt"),
                        new FileNameExtensionFilter("csv", "csv")),
                path -> FileController.saveFile(path, frame.circuit.getSimulation()));
    }

    private void saveImage(String suffix, BufferedImage image) {
        showSaveDialog(suffix,
                List.of(new FileNameExtensionFilter("jpg", "jpg"),
                        new FileNameExtensionFilter("png", "png")),
                path -> FileController.saveImage(path, image));
    }

    /**
     * @param suffix  se añade al nombre propuesto (currentPath sin ".txt" + "-" + suffix)
     * @param filters se aplican en orden con setFileFilter (el último queda activo)
     * @param saver   recibe la ruta final (con extensión) y devuelve true si
     *                se guardó bien; si devuelve false se vuelve a mostrar el
     *                diálogo. Si el usuario cancela, termina.
     */
    private void showSaveDialog(String suffix, List<FileNameExtensionFilter> filters, Predicate<String> saver) {
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        for (FileNameExtensionFilter filter : filters) {
            fileChooser.setFileFilter(filter);
        }
        fileChooser.setSelectedFile(new File(currentPath.replace(".txt", "-") + suffix));

        boolean retry = true;
        while (retry) {
            retry = false;

            if (fileChooser.showSaveDialog(frame) == JFileChooser.APPROVE_OPTION) {
                String path = fileChooser.getSelectedFile().getPath()
                        + "." + fileChooser.getFileFilter().getDescription();
                retry = !saver.test(path);
            }
        }
    }
}
