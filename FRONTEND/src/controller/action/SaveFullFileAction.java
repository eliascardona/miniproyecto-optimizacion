package controller.action;

import controller.FileDialogs;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Save > Full file. */
public class SaveFullFileAction extends AbstractAction {
    private final FileDialogs fileDialogs;

    public SaveFullFileAction(FileDialogs fileDialogs) {
        this.fileDialogs = fileDialogs;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        fileDialogs.saveFullFile();
    }
}