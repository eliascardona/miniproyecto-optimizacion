const MachineRepository = require("../repository/machineRepository");

class MachineService {
    constructor() {
        this.repo = new MachineRepository();
    }

    async findAll(filter, pagination) {
        return this.repo.findAll(filter, pagination);
    }
}

module.exports = MachineService;
