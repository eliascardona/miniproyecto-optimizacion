package view;

import dto.OptimizationResult;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.Component;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Base64;

/**
 * Muestra en un diálogo aparte el PNG (matplotlib) que devuelve la API.
 * Antes: MainController.mostrarGraficaResultado.
 */
public final class OptimizationResultDialog {
    private OptimizationResultDialog() {}

    public static void show(Component parent, OptimizationResult result) {
        if (result.graficaPngBase64 == null || result.graficaPngBase64.isBlank()) {
            return;
        }

        try {
            byte[] bytes = Base64.getDecoder().decode(result.graficaPngBase64);
            BufferedImage image = ImageIO.read(new ByteArrayInputStream(bytes));

            if (image == null) {
                throw new IOException("El servidor devolvió datos que no son una imagen PNG válida.");
            }

            JLabel label = new JLabel(new ImageIcon(image));
            JOptionPane.showMessageDialog(parent, new JScrollPane(label),
                    "Resultado de la optimización (fitness = " + result.fitness + ")",
                    JOptionPane.PLAIN_MESSAGE);
        } catch (IOException | IllegalArgumentException ex) {
            JOptionPane.showMessageDialog(parent, "No se pudo mostrar la gráfica devuelta por la API: "
                    + ex.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
        }
    }
}
