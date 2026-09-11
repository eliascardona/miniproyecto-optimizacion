import controller.FileController;
import controller.MainController;
import model.Circuit;
import view.MainFrame;

import javax.swing.*;
import javax.swing.plaf.nimbus.NimbusLookAndFeel;
import java.awt.*;

public class Main {
    public static void main(String[] args) {
        Circuit circuit = new Circuit();
        FileController.readFile("src\\resource\\circuit.txt", circuit);

        EventQueue.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(new NimbusLookAndFeel());
                MainController controller = new MainController(new MainFrame(circuit));
                controller.frame.setVisible(true);
            } catch (UnsupportedLookAndFeelException e) {
                throw new RuntimeException(e);
            }
        });
    }
}