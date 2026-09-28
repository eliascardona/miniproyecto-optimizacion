package controller.action;

import controller.FileDialogs;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Open circuit. */
public class OpenFileAction extends AbstractAction {
    private final FileDialogs fileDialogs;

    public OpenFileAction(FileDialogs fileDialogs) {
        this.fileDialogs = fileDialogs;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        fileDialogs.openCircuit();
    }
}
