package view;

import javax.swing.*;
import java.awt.*;

/**
 * Diálogo modal simple con una barra de progreso indeterminada, usado
 * mientras se espera la respuesta de la API (puede tardar varios minutos
 * porque el algoritmo genético corre completo del lado del servidor antes
 * de responder).
 */
public class LoadingDialog extends JDialog {
    public LoadingDialog(Frame owner, String message) {
        super(owner, "Procesando", true);
        this.setDefaultCloseOperation(JDialog.DO_NOTHING_ON_CLOSE);

        JPanel panel = new JPanel(new BorderLayout(10, 10));
        panel.setBorder(BorderFactory.createEmptyBorder(15, 20, 15, 20));

        panel.add(new JLabel(message), BorderLayout.NORTH);

        JProgressBar progressBar = new JProgressBar();
        progressBar.setIndeterminate(true);
        panel.add(progressBar, BorderLayout.CENTER);

        this.setContentPane(panel);
        this.setSize(340, 100);
        this.setLocationRelativeTo(owner);
        this.setResizable(false);
    }
}
