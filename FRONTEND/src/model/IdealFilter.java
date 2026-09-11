package model;

/**
 * Description: this class is a model to the ideal filter.
 * It contains filter params, these are voltage and frequency
 * of passage and attenuation
 *
 * @author BraulioMontoya
 * @version 1.0.0
 */

public class IdealFilter {
    /*
     * It is passage voltage of ideal filter.
     */
    private double passageVoltage;

    /*
     * It is attenuation voltage of ideal filter.
     */
    private double attenuationVoltage;

    /*
     * It is passage frequency of ideal filter.
     */
    private int passageFrequency;

    /*
     * It is attenuation frequency of ideal filter.
     */
    private int attenuationFrequency;

    /*
     * It is type of ideal filter.
     */
    private int type;

    /*
     * @return value of 'passageVoltage'.
     */
    public double getPassageVoltage() {
        return passageVoltage;
    }

    /*
     * It changes the value of 'passageVoltage'
     * @param passageVoltage
     */
    public void setPassageVoltage(double passageVoltage) {
        this.passageVoltage = passageVoltage;
    }

    /*
     * @return value of 'attenuationVoltage'.
     */
    public double getAttenuationVoltage() {
        return attenuationVoltage;
    }

    /*
     * It changes the value of 'attenuationVoltage'
     * @param attenuationVoltage
     */
    public void setAttenuationVoltage(double attenuationVoltage) {
        this.attenuationVoltage = attenuationVoltage;
    }

    /*
     * @return value of 'passageFrequency'.
     */
    public int getPassageFrequency() {
        return passageFrequency;
    }

    /*
     * It changes the value of 'passageFrequency'
     * @param passageFrequency
     */
    public void setPassageFrequency(int passageFrequency) {
        this.passageFrequency = passageFrequency;
    }

    /*
     * @return value of 'attenuationFrequency'.
     */
    public int getAttenuationFrequency() {
        return attenuationFrequency;
    }

    /*
     * It changes the value of 'attenuationFrequency'
     * @param attenuationFrequency
     */
    public void setAttenuationFrequency(int attenuationFrequency) {
        this.attenuationFrequency = attenuationFrequency;
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
}
