const express = require('express')
const MachineService = require('../services/machineService');
const MachineFilter = require("../models/filters/machineFilter");
const { formatPaginationOptions } = require('../../utils/pagination');

class MachineController {
    constructor() {
        this.machineService = new MachineService();
        this.router = express.Router()
    }

    getAllMachines = async (req, res) => {
        try {
            const {
                // Attributes to filter
                status,
                createdFrom,
                createdTo,
                query,
                // Pagination options
                page,
                size,
                sort,
                direction
            } = req.query;

            const machineFilter = new MachineFilter()
                .withStatus(status)
                .withCreatedFrom(createdFrom)
                .withCreatedTo(createdTo)
                .withQuery(query)
                .build();

            const pagination = formatPaginationOptions({
                page,
                size,
                sort,
                direction
            })

            const machinesPage = await this.machineService.findAll(machineFilter, pagination)

            return res.status(200).json({
                success: true,
                data: machinesPage
            })

        } catch (error) {
            if (error.message)
                return res.status(500).json({
                    success: false,
                    message: `${error.message}`
                })
        }
    }
}

module.exports = MachineController;
