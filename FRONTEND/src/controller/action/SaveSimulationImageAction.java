package controller.action;

import controller.FileDialogs;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Save > Simulation (imagen de la gráfica). */
public class SaveSimulationImageAction extends AbstractAction {
    private final FileDialogs fileDialogs;

    public SaveSimulationImageAction(FileDialogs fileDialogs) {
        this.fileDialogs = fileDialogs;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        fileDialogs.saveSimulationImage();
    }
}