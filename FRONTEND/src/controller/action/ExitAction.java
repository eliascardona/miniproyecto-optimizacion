package controller.action;

import view.MainFrame;

import javax.swing.AbstractAction;
import java.awt.event.ActionEvent;

/** Menú File > Exit. */
public class ExitAction extends AbstractAction {
    private final MainFrame frame;

    public ExitAction(MainFrame frame) {
        this.frame = frame;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        frame.dispose();
    }
}