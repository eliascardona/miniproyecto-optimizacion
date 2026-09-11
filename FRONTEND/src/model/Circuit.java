package model;

import java.util.ArrayList;

/**
 * Description: this class is a model to the circuit. It contains a
 * list and number of elements, and fitness of circuit.
 *
 * @author BraulioMontoya
 * @version 1.0.0
 */

public class Circuit {
    /*
     * This array list contains the elements from the circuit.
     */
    private final ArrayList<Element> circuit;

    /*
     * 'simulation' contains the information of simulation.
     */
    private Simulation simulation;

    /*
     * 'idealFilter' contains the ideal filter params.
     */
    private IdealFilter idealFilter;

    /*
     * This string is the coded circuit.
     */
    private String codedCircuit;

    /*
     * The fitness is calculated based on the error between the
     * simulation and the ideal filter.
     */
    private double fitness;

    /*
     * 'elements' is the number of elements in the circuit.
     */
    private int elements;

    /*
     * 'order' only takes values of 1, 2 or 3. This value is based
     * on the cut band of generated filter.
     */
    private int order;

    /*
     * This variable is the width of circuit image.
     */
    private int width = 128;

    public Circuit() {
        circuit = new ArrayList<>();
    }

    /*
     * @return value of 'circuit'.
     */
    public ArrayList<Element> getCircuit() {
        return circuit;
    }

    /*
     * @return value of 'simulation'.
     */
    public Simulation getSimulation() {
        return simulation;
    }

    /*
     * It changes the value of 'simulation'
     * @param simulation
     */
    public void setSimulation(Simulation simulation) {
        this.simulation = simulation;
    }

    /*
     * @return value of 'idealFilter'.
     */
    public IdealFilter getIdealFilter() {
        return idealFilter;
    }

    /*
     * It changes the value of 'idealFilter'
     * @param idealFilter
     */
    public void setIdealFilter(IdealFilter idealFilter) {
        this.idealFilter = idealFilter;
    }

    /*
     * @return value of 'codedCircuit'.
     */
    public String getCodedCircuit() {
        return codedCircuit;
    }

    /*
     * It changes the value of 'codedCircuit'
     * @param codedCircuit
     */
    public void setCodedCircuit(String codedCircuit) {
        this.codedCircuit = codedCircuit;
    }

    /*
     * @return value of 'fitness'.
     */
    public double getFitness() {
        return fitness;
    }

    /*
     * It changes the value of 'fitness'
     * @param fitness
     */
    public void setFitness(double fitness) {
        this.fitness = fitness;
    }

    /*
     * @return value of 'elements'.
     */
    public int getElements() {
        return elements;
    }

    /*
     * It changes the value of 'elements'
     * @param elements
     */
    public void setElements(int elements) {
        this.elements = elements;
    }

    /*
     * @return value of 'order'.
     */
    public int getOrder() {
        return order;
    }

    /*
     * It changes the value of 'order'
     * @param order
     */
    public void setOrder(int order) {
        this.order = order;
    }

    /*
     * @return the width of circuit image.
     */
    public int getWidth() {
        if(circuit.isEmpty()) {
            return width;
        }

        int lastIndex = circuit.size() - 1;
        int lastElement = circuit.get(lastIndex).getNode2();

        if(lastElement == 0) {
            return width + 66;
        }

        return width;
    }

    /*
     * @return the height of circuit image.
     */
    public int getHeight() {
        return 132;
    }

    /*
     * It adds a new element to the circuit, and it updates the
     * width of circuit image.
     *
     * @param e
     *          it is a new element of circuit.
     */
    public void addElement(Element e) {
        if(circuit.isEmpty()) {
            if(e.getNode2() != 0) {
                width += 66;
            }

            circuit.add(e);
            return;
        }

        int lastIndex = circuit.size() - 1;
        int lastElement = circuit.get(lastIndex).getNode2();

        if(e.getNode2() != 0) {
            width += 66;
        } else if(lastElement == 0) {
            width += 66;
        }

        circuit.add(e);
    }

    /*
     * It deleted all elements of the circuit, and reseat the
     * width of circuit image.
     */
    public void clearCircuit() {
        circuit.clear();
        width = 128;
    }
}
