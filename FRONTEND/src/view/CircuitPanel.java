package view;

import model.Circuit;
import model.Element;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

public class CircuitPanel extends JScrollPane {
    public Circuit circuit;

    public final JLabel label;

    public CircuitPanel(Circuit circuit) {
        this.setBorder(null);

        this.circuit = circuit;

        JPanel panel = new JPanel();
        panel.setLayout(new FlowLayout());

        label = new JLabel();
        this.updateCircuit();
        panel.add(label);

        this.setViewportView(panel);
    }

    public void updateCircuit() {
        BufferedImage image = new BufferedImage(circuit.getWidth(), circuit.getHeight(), BufferedImage.TYPE_INT_ARGB);
        Graphics graphics = image.getGraphics();

        drawCircuit(graphics);
        label.setIcon(new ImageIcon(image));
        label.setSize(image.getWidth(), image.getHeight());
    }

    public BufferedImage getImage() {
        BufferedImage image = new BufferedImage(circuit.getWidth(), circuit.getHeight(), BufferedImage.TYPE_INT_ARGB);
        Graphics graphics = image.getGraphics();

        drawCircuit(graphics);

        return image;
    }

    private void drawCircuit(Graphics g) {
        int[][] values = {{10, 15, 22, 33, 47, 68}, {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82},
                {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}};
        int[][] decades = {{-5, -6, -7, -8, -9}, {1, 2, 3, 4, 5, 6}, {-1, -2, -3, -4, -5, -6}};

        int index;
        Element next;

        int x = 30;
        double angle = Math.PI / 2;

        g.setColor(this.getBackground());
        g.fillRect(0, 0, circuit.getWidth(), circuit.getHeight());

        g.setColor(Color.black);
        //Draw supply and supply resistance.
        drawElement(g, 3, circuit.getSimulation().getSupplyVoltage() + "V", x + 31, 33, angle);
        drawElement(g, 4, "", x + 33, 99, 0);
        drawElement(g, 1, circuit.getSimulation().getSupplyResistance() + "Ω", x, 0, 0);
        g.fillRect(x, 97, 64, 2);
        x += 66;

        for(Element e : circuit.getCircuit()) {
            if(e.getNode2() != 0) {
                //Draw element with new connection.
                drawElement(g, e.getType(), values[e.getType()][e.getValue()] + "e"
                        + decades[e.getType()][e.getDecade()], x, 0, 0);
                g.fillRect(x, 97, 64, 2);
                x += 66;
            } else {
                //Draw element with ground connection.
                index = circuit.getCircuit().indexOf(e) + 1;

                drawElement(g, e.getType(), values[e.getType()][e.getValue()] + "e"
                        + decades[e.getType()][e.getDecade()], x + 31, 33, angle);

                if(circuit.getCircuit().size() > index) {
                    next = circuit.getCircuit().get(index);

                    if(next.getNode2() == 0) {
                        g.fillRect(x, 31, 64, 2);
                        g.fillRect(x, 97, 64, 2);
                        x += 66;
                    }
                }
            }
        }

        if(!circuit.getCircuit().isEmpty()) {
            index = circuit.getCircuit().size() - 1;
            next = circuit.getCircuit().get(index);

            if (next.getNode2() == 0) {
                g.fillRect(x, 31, 64, 2);
                g.fillRect(x, 97, 64, 2);
                x += 66;
            }
        }

        //Draw load resistance.
        drawElement(g, 1, circuit.getSimulation().getLoadResistance() + "Ω", x + 31, 33, angle);

        for(int i = 27; i < x; i = i + 66) {
            g.setColor(new Color(0, 114, 46));
            g.fillRect(i, 30, 4, 4);
            g.fillRect(i, 96, 4, 4);
        }
    }

    private void drawElement(Graphics g, int type, String s, int x, int y, double angle) {
        Graphics2D g2d = (Graphics2D) g;
        AffineTransform transform = g2d.getTransform();

        BufferedImage image;

        try {
            image = switch(type) {
                case 0 -> ImageIO.read(new File("src\\resource\\capacitance.png"));
                case 1 -> ImageIO.read(new File("src\\resource\\resistance.png"));
                case 2 -> ImageIO.read(new File("src\\resource\\inductance.png"));
                case 3 -> ImageIO.read(new File("src\\resource\\power.png"));
                default -> ImageIO.read(new File("src\\resource\\ground.png"));
            };

            g2d.rotate(angle, x, y);
            g2d.drawImage(image, x, y, null);

            int center = s.contains(".") ? (64 - ((s.length() - 1) * 7)) / 2 : (64 - (s.length() * 7)) / 2;

            g2d.drawString(s, x + center, y + 16);
            g2d.setTransform(transform);
        } catch (IOException e) {
            JOptionPane.showMessageDialog(null, e.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
        }
    }
}
