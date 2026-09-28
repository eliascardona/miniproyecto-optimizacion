package controller.action;

import controller.FileDialogs;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Save > Circuit (imagen del diagrama). */
public class SaveCircuitImageAction extends AbstractAction {
    private final FileDialogs fileDialogs;

    public SaveCircuitImageAction(FileDialogs fileDialogs) {
        this.fileDialogs = fileDialogs;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        fileDialogs.saveCircuitImage();
    }
}