const { getDB } = require("../../config/database");
const Machine = require("../models/machine");

class MachineRepository {
    constructor() {
        this.collection = () => getDB().collection("maquina");
    }

    async findAll(filter, pagination) {
        const { page, size, sort, direction } = pagination;

        const skip = page * size;
        const sortOrder = direction === "asc" ? 1 : -1;

        const totalElements = await this.collection().countDocuments(filter);
        const totalPages = Math.ceil(totalElements / size);

        const limit = size ?? 10;

        const docs = await this.collection()
            .find(filter)
            .sort({ [sort]: sortOrder })
            .skip(skip)
            .limit(limit)
            .toArray();

        return {
            content: docs.map((d) => new Machine(d)),
            totalPages,
            totalElements,
            size,
            number: page,
            first: page === 0,
            last: page >= totalPages - 1,
            numberOfElements: docs.length,
            empty: docs.length === 0
        };
    }
}

module.exports = MachineRepository;
