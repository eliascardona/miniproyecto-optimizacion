package view;

import model.Circuit;
import model.IdealFilter;
import model.Simulation;

import javax.swing.*;
import java.awt.*;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;

public class SimulationPanel extends JScrollPane {
    public IdealFilter idealFilter;
    public Simulation simulation;
    public JPanel panel;

    private int initialFrequency;
    private int finalFrequency;
    private int finalVoltage;

    private String frequency;
    private String voltage;

    private int margin;
    private int width, height;

    private JLabel x, y, g;

    public SimulationPanel(Circuit circuit) {
        this.setBorder(null);

        this.idealFilter = circuit.getIdealFilter();
        this.simulation = circuit.getSimulation();

        this.initComponent();
    }

    public void updateGrid() {
        g.setIcon(grid(g.getSize()));
    }

    public void updateGraph() {
        initialFrequency = (int) Math.log10(simulation.getInitialFrequency());
        finalFrequency = (int) Math.log10(simulation.getFinalFrequency());
        finalVoltage = (int) Math.ceil(simulation.getSupplyVoltage());

        frequency = String.valueOf(simulation.getFinalFrequency());
        voltage = String.valueOf(finalVoltage);

        width = (finalFrequency - initialFrequency) * 80;

        panel.setPreferredSize(new Dimension(width + margin + 25, height + 25));
        y.setBounds(0, height, width + margin + 25, 25);
        g.setBounds(25, 0, width, height);

        x.setIcon(axisX(x.getSize()));
        y.setIcon(axisY(y.getSize()));
        g.setIcon(grid(g.getSize()));
    }

    public BufferedImage getImage() {
        BufferedImage image = new BufferedImage(width + margin + 25, height + 25,
                BufferedImage.TYPE_INT_ARGB);
        Graphics graphics = image.getGraphics();

        panel.printAll(graphics);

        return image;
    }

    private void initComponent() {
        initialFrequency = (int) Math.log10(simulation.getInitialFrequency());
        finalFrequency = (int) Math.log10(simulation.getFinalFrequency());
        finalVoltage = (int) Math.ceil(simulation.getSupplyVoltage());

        frequency = String.valueOf(simulation.getFinalFrequency());
        voltage = String.valueOf(finalVoltage);

        width = (finalFrequency - initialFrequency) * 80;
        height = 180;

        margin = frequency.length() * 7 / 2;

        panel = new JPanel(null);
        panel.setPreferredSize(new Dimension(width + margin + 25, height + 25));

        x = new JLabel();
        x.setBounds(0, 0, 25, height);
        x.setIcon(axisX(x.getSize()));
        panel.add(x);

        y = new JLabel();
        y.setBounds(0, height, width + margin + 25, 25);
        y.setIcon(axisY(y.getSize()));
        panel.add(y);

        g = new JLabel();
        g.setBounds(25, 0, width, height);
        g.setIcon(grid(g.getSize()));
        panel.add(g);

        this.setViewportView(panel);
    }

    private ImageIcon axisX(Dimension d) {
        BufferedImage image = new BufferedImage(d.width, d.height, BufferedImage.TYPE_INT_ARGB);
        Graphics g = image.getGraphics();

        //Draw axis X (voltage axis).
        g.setColor(Color.black);
        g.drawLine(d.width - 1, 4, d.width - 1, d.height - 1);
        g.drawLine(d.width - 7, 4, d.width - 1, 4);
        g.drawString(voltage, d.width - 16, 9);

        Graphics2D g2d = (Graphics2D) g;
        AffineTransform transform = g2d.getTransform();
        int center = ((d.height - 1) / 2) + (7 * 6 / 2);

        g2d.rotate(- Math.PI / 2, 9, center);
        g2d.drawString("voltage", 9, center);
        g2d.setTransform(transform);

        return new ImageIcon(image);
    }

    private ImageIcon axisY(Dimension d) {
        BufferedImage image = new BufferedImage(d.width, d.height, BufferedImage.TYPE_INT_ARGB);
        Graphics g = image.getGraphics();

        //Draw axis Y (frequency axis).
        g.setColor(Color.black);
        g.drawLine(18, 0, d.width - margin - 1, 0);
        g.drawLine(24, 0, 24, 7);
        g.drawLine(d.width - margin - 1, 0, d.width - margin - 1, 7);
        
        int align = frequency.length() * 7;
        g.drawString(frequency, d.width - align - 1, d.height - 5);

        int center = ((d.width - 1) / 2) + (9 * 6 / 2);
        g.drawString("frequency", d.width - center, d.height - 1);

        return new ImageIcon(image);
    }

    private ImageIcon grid(Dimension d) {
        BufferedImage image = new BufferedImage(d.width, d.height, BufferedImage.TYPE_INT_ARGB);
        Graphics g = image.getGraphics();

        int x, y;

        //Draw graph grid.
        g.setColor(Color.gray);

        for(int i = 1; i <= finalFrequency; i++) {
            x = i * 100;
            g.drawLine(x - 1, 4, x - 1, d.height - 1);
        }

        for(int i = 0; i < finalVoltage; i++) {
            y = ((d.height - 5) * i) / finalVoltage;
            g.drawLine(0, y + 4, d.width - 1, y + 4);
        }

        double[] xObjective = new double[4];
        double[] yObjective = new double[4];

        xObjective[0] = 1;
        xObjective[3] = simulation.getFinalFrequency();

        if(idealFilter.getType() == 0) {
            xObjective[1] = idealFilter.getPassageFrequency();
            xObjective[2] = idealFilter.getAttenuationFrequency();

            yObjective[0] = yObjective[1] = idealFilter.getPassageVoltage();
            yObjective[2] = yObjective[3] = idealFilter.getAttenuationVoltage();
        } else {
            xObjective[1] = idealFilter.getAttenuationFrequency();
            xObjective[2] = idealFilter.getPassageFrequency();

            yObjective[0] = yObjective[1] = idealFilter.getAttenuationVoltage();
            yObjective[2] = yObjective[3] = idealFilter.getPassageVoltage();
        }

        //Draw filter objective.
        g.setColor(Color.blue);
        drawLineXY(g, d, xObjective, yObjective);

        if(simulation.getValues().isEmpty()) {
            return new ImageIcon(image);
        }

        double[] xGenerated = new double[simulation.getValues().size()];
        double[] yGenerated = new double[simulation.getValues().size()];

        for(int i = 0; i < simulation.getValues().size(); i++) {
            xGenerated[i] = simulation.getValues().get(i)[0];
            yGenerated[i] = simulation.getValues().get(i)[2];
        }

        //Draw filter generated with genetic algorithm.
        g.setColor(Color.red);
        drawLineXY(g, d, xGenerated, yGenerated);

        return new ImageIcon(image);
    }

    private void drawLineXY(Graphics g, Dimension d, double[] x, double[] y) {
        double aux;
        int f1, f2, v1, v2;

        aux = Math.log10(x[0]);
        f1 = (int) (aux * 100);
        v1 = (int) (((d.height - 5) * y[0]) / finalVoltage);

        v1 = d.height - v1 - 1;

        for (int i = 1; i < x.length; i++) {
            aux = Math.log10(x[i]) - initialFrequency;
            f2 = (int) (aux * 80);
            v2 = (int) (((d.height - 5) * y[i]) / finalVoltage);

            v2 = d.height - v2 - 1;

            g.drawLine(f1 - 1, v1, f2 - 1, v2);

            f1 = f2;
            v1 = v2;
        }
    }
}
