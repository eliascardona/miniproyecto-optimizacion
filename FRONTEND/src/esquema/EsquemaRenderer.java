package esquema;

import esquema.Esquema.Elemento;
import esquema.Esquema.OpAmp;
import esquema.Esquema.Punto;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.AffineTransform;
import java.awt.geom.Ellipse2D;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.awt.geom.Point2D;
import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;

/**
 * Dibuja un {@link Esquema} con Java2D, en vectores: sin PNG, sin leer archivos, sin depender de
 * ninguna clase de la interfaz. Sirve igual para un panel Swing (paintComponent / ImageIcon), para
 * exportar una imagen o para pruebas sin pantalla.
 *
 * Símbolos: resistencia, capacitor, inductor, fuente de AC, op-amp (triángulo con +/−), tierra,
 * puntos de unión y terminal de salida. Las etiquetas llevan nombre y valor en notación de
 * ingeniería; los componentes que ajusta el optimizador se rotulan en otro color y con el valor en
 * negrita, para distinguirlos de los fijos (fuente, Rs, Rl).
 *
 * El tamaño sale de {@code Esquema.limites()} más un margen para las etiquetas: nunca de contar
 * elementos.
 */
public final class EsquemaRenderer {
    private EsquemaRenderer() {}

    // Márgenes (en unidades de rejilla) alrededor de la caja de geometría, para las etiquetas.
    private static final double MARGEN_IZQ = 1.6;
    private static final double MARGEN_DER = 2.6;
    private static final double MARGEN_SUP = 2.0;
    private static final double MARGEN_INF = 1.6;

    private static final Color RELLENO_OPAMP = new Color(0xF4F4F4);

    // ------------------------------------------------------------------
    // API pública
    // ------------------------------------------------------------------

    /** Tamaño en píxeles de la imagen que produce {@link #dibujar} para este esquema y estilo. */
    public static Dimension tamano(Esquema e, EstiloEsquema estilo) {
        Esquema.Limites l = e.limites();
        double ancho = (l.xMax() - l.xMin() + MARGEN_IZQ + MARGEN_DER) * estilo.escala();
        double alto = (l.yMax() - l.yMin() + MARGEN_SUP + MARGEN_INF) * estilo.escala();
        return new Dimension((int) Math.ceil(ancho), (int) Math.ceil(alto));
    }

    /** Posición en píxeles (dentro de la imagen) de un punto de rejilla. */
    public static Point2D.Double aPixeles(Esquema e, EstiloEsquema estilo, Punto p) {
        return new Point2D.Double((p.x() - (e.limites().xMin() - MARGEN_IZQ)) * estilo.escala(),
                (p.y() - (e.limites().yMin() - MARGEN_SUP)) * estilo.escala());
    }

    /** Pinta fondo y circuito en {@code g}, con el origen en la esquina superior izquierda. */
    public static void dibujar(Graphics2D g, Esquema e, EstiloEsquema estilo, Color fondo) {
        Dimension tam = tamano(e, estilo);
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_FRACTIONALMETRICS, RenderingHints.VALUE_FRACTIONALMETRICS_ON);

        g.setColor(fondo);
        g.fillRect(0, 0, tam.width, tam.height);

        new Pincel(g, e, estilo, fondo).pintar();
    }

    /** Imagen lista para un JLabel/ImageIcon o para guardar como PNG. */
    public static BufferedImage aImagen(Esquema e, EstiloEsquema estilo, Color fondo) {
        Dimension tam = tamano(e, estilo);
        BufferedImage imagen = new BufferedImage(tam.width, tam.height, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = imagen.createGraphics();
        try {
            dibujar(g, e, estilo, fondo);
        } finally {
            g.dispose();
        }
        return imagen;
    }

    // ------------------------------------------------------------------
    // Implementación
    // ------------------------------------------------------------------

    private enum Horizontal { IZQUIERDA, CENTRO, DERECHA }

    private enum Vertical { ARRIBA, CENTRO, ABAJO }

    private static final class Pincel {
        private final Graphics2D g;
        private final Esquema e;
        private final EstiloEsquema st;
        private final Color fondo;
        private final double s;
        private final double ox;
        private final double oy;
        private final BasicStroke trazo;
        private final BasicStroke trazoGrueso;

        Pincel(Graphics2D g, Esquema e, EstiloEsquema st, Color fondo) {
            this.g = g;
            this.e = e;
            this.st = st;
            this.fondo = fondo;
            this.s = st.escala();
            this.ox = e.limites().xMin() - MARGEN_IZQ;
            this.oy = e.limites().yMin() - MARGEN_SUP;
            this.trazo = new BasicStroke((float) Math.max(1.0, 0.04 * s), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND);
            this.trazoGrueso = new BasicStroke((float) Math.max(1.5, 0.06 * s), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND);
        }

        private double px(double x) {
            return (x - ox) * s;
        }

        private double py(double y) {
            return (y - oy) * s;
        }

        void pintar() {
            for (Elemento el : e.elementos()) {
                simbolo(el);
            }
            for (List<Punto> cable : e.cables()) {
                cable(cable);
            }
            for (Punto t : e.tierras()) {
                tierra(t);
            }
            for (Punto u : e.uniones()) {
                union(u);
            }
            for (OpAmp op : e.opamps()) {
                opamp(op);
            }
            terminalDeSalida();
            if (st.etiquetasDeNodo()) {
                etiquetasDeNodo();
            }
        }

        // ---------- cables, tierra, uniones ----------

        private void cable(List<Punto> ruta) {
            if (ruta.size() < 2) {
                return;
            }
            Path2D.Double path = new Path2D.Double();
            path.moveTo(px(ruta.get(0).x()), py(ruta.get(0).y()));
            for (int i = 1; i < ruta.size(); i++) {
                path.lineTo(px(ruta.get(i).x()), py(ruta.get(i).y()));
            }
            g.setColor(st.cable());
            g.setStroke(trazo);
            g.draw(path);
        }

        private void tierra(Punto t) {
            g.setColor(st.cable());
            g.setStroke(trazo);
            double sentido = sentidoDeTierra(t);
            double[] mitades = {0.45, 0.30, 0.15};          // la raya más ancha queda pegada al cable
            for (int i = 0; i < mitades.length; i++) {
                double y = py(t.y() + sentido * (0.12 + i * 0.12));
                g.draw(new Line2D.Double(px(t.x() - mitades[i]), y, px(t.x() + mitades[i]), y));
            }
        }

        /**
         * +1 si la tierra va hacia abajo (lo normal) o -1 si va hacia arriba (derivaciones de la rama
         * superior de un circuito con ramas paralelas). Se deduce de la ruta del elemento que termina
         * en ese punto: si llega desde abajo, el símbolo se dibuja hacia arriba.
         */
        private double sentidoDeTierra(Punto t) {
            for (Elemento el : e.elementos()) {
                List<Punto> ruta = el.ruta();
                Punto fin = ruta.get(ruta.size() - 1);
                if (Math.abs(fin.x() - t.x()) < 1e-6 && Math.abs(fin.y() - t.y()) < 1e-6) {
                    return ruta.get(ruta.size() - 2).y() > t.y() ? -1.0 : 1.0;
                }
            }
            return 1.0;
        }

        private void union(Punto u) {
            double r = Math.max(2.0, 0.085 * s);
            g.setColor(st.cable());
            g.fill(new Ellipse2D.Double(px(u.x()) - r, py(u.y()) - r, 2 * r, 2 * r));
        }

        // ---------- elementos de dos terminales ----------

        private void simbolo(Elemento el) {
            List<Punto> ruta = el.ruta();
            Punto a = ruta.get(el.seg());
            Punto b = ruta.get(el.seg() + 1);
            double largo = Math.hypot(b.x() - a.x(), b.y() - a.y());
            double ux = (b.x() - a.x()) / largo;
            double uy = (b.y() - a.y()) / largo;
            double mx = (a.x() + b.x()) / 2;
            double my = (a.y() + b.y()) / 2;

            double mitad = switch (el.tipo()) {
                case "C" -> 0.12;
                case "L" -> 0.6;
                case "V" -> 0.45;
                default -> 0.5;
            };

            // cables a ambos lados del símbolo
            List<Punto> antes = new ArrayList<>(ruta.subList(0, el.seg() + 1));
            antes.add(new Punto(mx - ux * mitad, my - uy * mitad));
            List<Punto> despues = new ArrayList<>();
            despues.add(new Punto(mx + ux * mitad, my + uy * mitad));
            despues.addAll(ruta.subList(el.seg() + 1, ruta.size()));
            cable(antes);
            cable(despues);

            AffineTransform original = g.getTransform();
            g.translate(px(mx), py(my));
            g.rotate(Math.atan2(uy, ux));
            g.setColor(st.cable());
            switch (el.tipo()) {
                case "R" -> resistencia();
                case "C" -> capacitor();
                case "L" -> inductor();
                case "V" -> {
                    g.setTransform(original);          // la fuente se dibuja sin rotar
                    fuente(mx, my);
                }
                default -> resistencia();
            }
            g.setTransform(original);

            etiqueta(el, mx, my, uy);
        }

        private void resistencia() {
            Rectangle2D.Double cuerpo = new Rectangle2D.Double(-0.5 * s, -0.17 * s, 1.0 * s, 0.34 * s);
            g.setColor(fondo);
            g.fill(cuerpo);
            g.setColor(st.cable());
            g.setStroke(trazo);
            g.draw(cuerpo);
        }

        private void capacitor() {
            g.setStroke(trazoGrueso);
            for (int lado = -1; lado <= 1; lado += 2) {
                double x = 0.12 * s * lado;
                g.draw(new Line2D.Double(x, -0.45 * s, x, 0.45 * s));
            }
        }

        private void inductor() {
            g.setStroke(trazo);
            for (int i = 0; i < 4; i++) {
                double a0 = -0.6 + i * 0.3;
                Path2D.Double giro = new Path2D.Double();
                for (int j = 0; j <= 20; j++) {
                    double q = Math.PI * j / 20;
                    double x = (a0 + 0.15 - 0.15 * Math.cos(q)) * s;
                    double y = 0.18 * Math.sin(q) * s;
                    if (j == 0) {
                        giro.moveTo(x, y);
                    } else {
                        giro.lineTo(x, y);
                    }
                }
                g.draw(giro);
            }
        }

        private void fuente(double mx, double my) {
            double cx = px(mx);
            double cy = py(my);
            double r = 0.45 * s;
            Ellipse2D.Double circulo = new Ellipse2D.Double(cx - r, cy - r, 2 * r, 2 * r);
            g.setColor(fondo);
            g.fill(circulo);
            g.setColor(st.cable());
            g.setStroke(trazo);
            g.draw(circulo);

            Path2D.Double seno = new Path2D.Double();
            for (int i = 0; i <= 20; i++) {
                double q = i / 20.0;
                double x = cx + (-0.28 + 0.56 * q) * s;
                double y = cy + 0.14 * Math.sin(2 * Math.PI * q) * s;
                if (i == 0) {
                    seno.moveTo(x, y);
                } else {
                    seno.lineTo(x, y);
                }
            }
            g.setStroke(new BasicStroke((float) Math.max(1.0, 0.03 * s)));
            g.draw(seno);
        }

        // ---------- op-amp ----------

        private void opamp(OpAmp op) {
            Path2D.Double tri = new Path2D.Double();
            for (int i = 0; i < op.triangulo().size(); i++) {
                Punto p = op.triangulo().get(i);
                if (i == 0) {
                    tri.moveTo(px(p.x()), py(p.y()));
                } else {
                    tri.lineTo(px(p.x()), py(p.y()));
                }
            }
            tri.closePath();
            g.setColor(RELLENO_OPAMP);
            g.fill(tri);
            g.setColor(st.cable());
            g.setStroke(new BasicStroke((float) Math.max(1.2, 0.045 * s), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.draw(tri);

            Font signo = fuente(0.40, Font.BOLD);
            texto(new String[]{"+"}, new Font[]{signo}, new Color[]{st.cable()}, px(op.pinInP().x() + 0.12), py(op.pinInP().y()),
                    Horizontal.IZQUIERDA, Vertical.CENTRO);
            texto(new String[]{FormatoIngenieria.MENOS}, new Font[]{signo}, new Color[]{st.cable()},
                    px(op.pinInN().x() + 0.12), py(op.pinInN().y()), Horizontal.IZQUIERDA, Vertical.CENTRO);

            // nombre y tensiones de alimentación, centrados sobre el triángulo
            Double vp = e.tensionDeNodo(op.nodoVPos());
            Double vn = e.tensionDeNodo(op.nodoVNeg());
            String segunda = (vp != null && vn != null)
                    ? FormatoIngenieria.tensionConSigno(vp) + " / " + FormatoIngenieria.tensionConSigno(vn) : "";
            Font chica = fuente(0.30, Font.PLAIN);
            texto(new String[]{op.nombre(), segunda}, new Font[]{chica, chica}, new Color[]{st.fijo(), st.fijo()},
                    px(op.pinInP().x() + 0.9), py(-1.15), Horizontal.CENTRO, Vertical.ABAJO);
        }

        private void terminalDeSalida() {
            List<Punto> ruta = e.salida().ruta();
            cable(ruta);
            Punto fin = ruta.get(ruta.size() - 1);
            double r = Math.max(2.5, 0.09 * s);
            Ellipse2D.Double borne = new Ellipse2D.Double(px(fin.x()) - r, py(fin.y()) - r, 2 * r, 2 * r);
            g.setColor(fondo);
            g.fill(borne);
            g.setColor(st.cable());
            g.setStroke(trazo);
            g.draw(borne);
            texto(new String[]{"Vout"}, new Font[]{fuente(0.34, Font.PLAIN)}, new Color[]{st.cable()},
                    px(fin.x() + 0.15), py(fin.y()), Horizontal.IZQUIERDA, Vertical.CENTRO);
        }

        private void etiquetasDeNodo() {
            Font f = fuente(0.22, Font.PLAIN);
            for (java.util.Map.Entry<String, Punto> n : e.nodos().entrySet()) {
                if (n.getKey().equals(e.nodoFuente())) {
                    continue;
                }
                texto(new String[]{n.getKey()}, new Font[]{f}, new Color[]{st.nodo()},
                        px(n.getValue().x() - 0.05), py(n.getValue().y() - 0.2), Horizontal.DERECHA, Vertical.ABAJO);
            }
        }

        // ---------- etiquetas ----------

        /** Nombre y valor del componente, junto a su símbolo (la posición depende de la orientación y el rol). */
        private void etiqueta(Elemento el, double mx, double my, double uy) {
            Color color = el.optimizable() ? st.optimizable() : st.fijo();
            Font normal = fuente(0.34, Font.PLAIN);
            Font valor = fuente(0.34, el.optimizable() ? Font.BOLD : Font.PLAIN);
            String[] lineas = {el.nombre(), FormatoIngenieria.valor(el.valor(), el.tipo())};
            Font[] fuentes = {normal, valor};
            Color[] colores = {color, color};

            if (Math.abs(uy) < 0.5) {                          // elemento horizontal
                if ("realimentacion".equals(el.rol())) {
                    texto(lineas, fuentes, colores, px(mx), py(my - 0.5), Horizontal.CENTRO, Vertical.ABAJO);
                } else if (my < -0.1) {                        // rama superior: etiqueta hacia el centro
                    texto(lineas, fuentes, colores, px(mx), py(my + 0.5), Horizontal.CENTRO, Vertical.ARRIBA);
                } else {                                       // fila principal y rama inferior: etiqueta arriba
                    texto(lineas, fuentes, colores, px(mx), py(my - 0.5), Horizontal.CENTRO, Vertical.ABAJO);
                }
            } else if ("carga".equals(el.rol())) {
                texto(lineas, fuentes, colores, px(mx + 0.55), py(my), Horizontal.IZQUIERDA, Vertical.CENTRO);
            } else {
                texto(lineas, fuentes, colores, px(mx - 0.55), py(my), Horizontal.DERECHA, Vertical.CENTRO);
            }
        }

        private Font fuente(double relativa, int estilo) {
            return new Font(Font.SANS_SERIF, estilo, Math.max(7, (int) Math.round(relativa * s)));
        }

        /**
         * Texto de varias líneas anclado en (x, y) en píxeles. {@code vertical} indica de qué lado del
         * ancla queda el bloque: ABAJO = el bloque termina en el ancla (queda ARRIBA de ella).
         */
        private void texto(String[] lineas, Font[] fuentes, Color[] colores, double x, double y,
                           Horizontal horizontal, Vertical vertical) {
            List<String> visibles = new ArrayList<>();
            List<Font> fuentesVisibles = new ArrayList<>();
            List<Color> coloresVisibles = new ArrayList<>();
            for (int i = 0; i < lineas.length; i++) {
                if (lineas[i] != null && !lineas[i].isEmpty()) {
                    visibles.add(lineas[i]);
                    fuentesVisibles.add(fuentes[i]);
                    coloresVisibles.add(colores[i]);
                }
            }
            if (visibles.isEmpty()) {
                return;
            }

            double alturaLinea = 0;
            for (Font f : fuentesVisibles) {
                alturaLinea = Math.max(alturaLinea, g.getFontMetrics(f).getHeight() * 0.92);
            }
            double alto = alturaLinea * visibles.size();
            double arriba = switch (vertical) {
                case ABAJO -> y - alto;
                case CENTRO -> y - alto / 2;
                case ARRIBA -> y;
            };

            for (int i = 0; i < visibles.size(); i++) {
                FontMetrics fm = g.getFontMetrics(fuentesVisibles.get(i));
                double ancho = fm.stringWidth(visibles.get(i));
                double izquierda = switch (horizontal) {
                    case IZQUIERDA -> x;
                    case CENTRO -> x - ancho / 2;
                    case DERECHA -> x - ancho;
                };
                g.setFont(fuentesVisibles.get(i));
                g.setColor(coloresVisibles.get(i));
                g.drawString(visibles.get(i), (float) izquierda, (float) (arriba + alturaLinea * i + fm.getAscent()));
            }
        }
    }
}