package model;

import java.util.ArrayList;

/**
 * Description: this class is a model to the simulation of circuit.
 * It contains a table of frequencies and simulation params.
 *
 * @author BraulioMontoya
 * @version 1.0.0
 */

public class Simulation {
    /*
     * This array list contains the values from the simulation.
     */
    private final ArrayList<double[]> values;

    /*
     * 'supplyVoltage' is the voltage of supply.
     */
    private double supplyVoltage;

    /*
     * 'supplyResistance' is the resistance connected to the supply
     * and the first element of circuit.
     */
    private int supplyResistance;

    /*
     * 'loadResistance' is the resistance connected to the supply
     * and the ground.
     */
    private int loadResistance;

    /*
     + 'initialFrequency' is the frequency at which the simulation
     * is starting.
     */
    private int initialFrequency;

    /*
     + 'finalFrequency' is the frequency at which the simulation
     * is finishing.
     */
    private int finalFrequency;

    public Simulation() {
        values = new ArrayList<>();
    }

    /*
     * @return value of 'values'.
     */
    public ArrayList<double[]> getValues() {
        return values;
    }

    /*
     * @return value of 'supplyVoltage'.
     */
    public double getSupplyVoltage() {
        return supplyVoltage;
    }

    /*
     * It changes the value of 'supplyVoltage'
     * @param supplyVoltage
     */
    public void setSupplyVoltage(double supplyVoltage) {
        this.supplyVoltage = supplyVoltage;
    }

    /*
     * @return value of 'supplyResistance'.
     */
    public int getSupplyResistance() {
        return supplyResistance;
    }

    /*
     * It changes the value of 'supplyResistance'
     * @param supplyResistance
     */
    public void setSupplyResistance(int supplyResistance) {
        this.supplyResistance = supplyResistance;
    }

    /*
     * @return value of 'loadResistance'.
     */
    public int getLoadResistance() {
        return loadResistance;
    }

    /*
     * It changes the value of 'loadResistance'
     * @param loadResistance
     */
    public void setLoadResistance(int loadResistance) {
        this.loadResistance = loadResistance;
    }

    /*
     * @return value of 'initialFrequency'.
     */
    public int getInitialFrequency() {
        return initialFrequency;
    }

    /*
     * It changes the value of 'initialFrequency'
     * @param initialFrequency
     */
    public void setInitialFrequency(int initialFrequency) {
        this.initialFrequency = initialFrequency;
    }

    /*
     * @return value of 'finalFrequency'.
     */
    public int getFinalFrequency() {
        return finalFrequency;
    }

    /*
     * It changes the value of 'finalFrequency'
     * @param finalFrequency
     */
    public void setFinalFrequency(int finalFrequency) {
        this.finalFrequency = finalFrequency;
    }

    /*
     * It adds a new array values to the simulation.
     *
     * @param value
     *          it is a new array values.
     */
    public void addValue(double[] value) {
        values.add(value);
    }

    /*
     * It deleted all values of the simulation.
     */
    public void clearValues() {
        values.clear();
    }
}
