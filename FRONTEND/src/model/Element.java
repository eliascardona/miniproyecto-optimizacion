package model;

/**
 * Description: this class is a model to every element of a circuit.
 * An element contains two parts, a topology part and a size part.
 * The topology part is connections in the circuit, and the size
 * part is capacity of component.
 *
 * @author BraulioMontoya
 * @version 1.0.0
 */

public class Element {
    /*
     * This class is implemented in the 'Circuit' class as a list of
     * elements for building a circuit.
     */

    /*
     * 'node1' takes a value of 1, if the element is first, else it
     * takes the value of 'nodeA' from the previous element.
     */
    private int node1;

    /*
     * 'node2' only takes values of 0 or 'node1' + 1. If value is 0,
     * then element is connecting a ground. If value is 'node1' + 1,
     * then element is connecting to the next element.
     */
    private int node2;

    /*
     + If 'nodeA' is 0, then 'nodeA' takes value of 'node1', else
     * 'nodeA' takes value of 'node2'.
     */
    private int nodeA;

    /*
     * 'type' only takes values of 0, 1 or 2. Where 0 is capacitance, 1
     * is resistance and 2 is inductance
     */
    private int type;

    /*
     * If 'type' is 0, then 'value' only takes values between 0 and 5,
     * else then 'value' only takes values between 0 and 11.
     */
    private int value;

    /*
     * If 'type' is 0, then 'decade' only takes values between 0 and 4,
     * else then 'decade' only takes values between 0 and 5.
     */
    private int decade;

    public Element(int node1, int node2, int nodeA, int type, int value, int decade) {
        this.node1 = node1;
        this.node2 = node2;
        this.nodeA = nodeA;
        this.type = type;
        this.value = value;
        this.decade = decade;
    }

    /*
     * @return value of 'node1'.
     */
    public int getNode1() {
        return node1;
    }

    /*
     * It changes the value of 'node1'
     * @param node1
     */
    public void setNode1(int node1) {
        this.node1 = node1;
    }

    /*
     * @return value of 'node2'.
     */
    public int getNode2() {
        return node2;
    }

    /*
     * It changes the value of 'node2'
     * @param node2
     */
    public void setNode2(int node2) {
        this.node2 = node2;
    }

    /*
     * @return value of 'nodeA'.
     */
    public int getNodeA() {
        return nodeA;
    }

    /*
     * It changes the value of 'nodeA'
     * @param nodeA
     */
    public void setNodeA(int nodeA) {
        this.nodeA = nodeA;
    }

    /*
     * @return value of 'type'.
     */
    public int getType() {
        return type;
    }

    /*
     * It changes the value of 'type'
     * @param type
     */
    public void setType(int type) {
        this.type = type;
    }

    /*
     * @return value of 'value'.
     */
    public int getValue() {
        return value;
    }

    /*
     * It changes the value of 'value'
     * @param value
     */
    public void setValue(int value) {
        this.value = value;
    }

    /*
     * @return value of 'decade'.
     */
    public int getDecade() {
        return decade;
    }

    /*
     * It changes the value of 'decade'
     * @param decade
     */
    public void setDecade(int decade) {
        this.decade = decade;
    }
}
