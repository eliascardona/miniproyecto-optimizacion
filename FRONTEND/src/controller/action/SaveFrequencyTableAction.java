package controller.action;

import controller.FileDialogs;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Save > Frequency table (txt/csv). */
public class SaveFrequencyTableAction extends AbstractAction {
    private final FileDialogs fileDialogs;

    public SaveFrequencyTableAction(FileDialogs fileDialogs) {
        this.fileDialogs = fileDialogs;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        fileDialogs.saveFrequencyTable();
    }
}