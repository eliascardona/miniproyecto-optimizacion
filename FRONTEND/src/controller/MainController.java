package controller;

import controller.action.ExitAction;
import controller.action.GenerateCircuitAction;
import controller.action.OpenFileAction;
import controller.action.SaveCircuitImageAction;
import controller.action.SaveFrequencyTableAction;
import controller.action.SaveFullFileAction;
import controller.action.SaveSimulationImageAction;
import controller.legacy.LegacyInputCircuitAction;
import service.CircuitRequestFactory;
import service.OptimizationService;
import view.MainFrame;

/**
 * Raíz de composición de la ventana principal: crea las piezas compartidas
 * y conecta cada ítem del menú con SU acción. Ya no contiene lógica de
 * negocio ni de diálogos.
 *
 * Se usa addActionListener (y no JMenuItem.setAction) a propósito:
 * setAction sobrescribe el texto y el ícono del ítem con los de la acción,
 * y MainFrame ya define ambos (p. ej. el ícono de "Open circuit").
 *
 * Main.java sigue usando `controller.frame`, por eso el campo es público.
 */
public class MainController {
    public final MainFrame frame;

    public MainController(MainFrame frame) {
        this.frame = frame;

        ViewRefresher viewRefresher = new ViewRefresher(frame);
        FileDialogs fileDialogs = new FileDialogs(frame, viewRefresher);

        // File
        frame.open.addActionListener(new OpenFileAction(fileDialogs));
        frame.saveFullFile.addActionListener(new SaveFullFileAction(fileDialogs));
        frame.saveCircuit.addActionListener(new SaveCircuitImageAction(fileDialogs));
        frame.saveSimulation.addActionListener(new SaveSimulationImageAction(fileDialogs));
        frame.saveTable.addActionListener(new SaveFrequencyTableAction(fileDialogs));
        frame.exit.addActionListener(new ExitAction(frame));

        // Circuit
        frame.generateCircuit.addActionListener(new GenerateCircuitAction(
                frame, new OptimizationService(), new CircuitRequestFactory(), viewRefresher));
        frame.inputCircuit.addActionListener(new LegacyInputCircuitAction(frame, viewRefresher));
    }
}