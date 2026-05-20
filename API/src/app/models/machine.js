class Machine {
    constructor({ _id, description, createdAt, updatedAt }) {
        this._id = _id;
        this.description = description;
        this.createdAt = createdAt || new Date().toISOString();
        this.updatedAt = updatedAt || new Date().toISOString();
    }
}

module.exports = Machine;
