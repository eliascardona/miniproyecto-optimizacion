const express = require('express')
const { requireAuth } = require('../../middlewares/auth');
const MachineController = require('../controllers/machineController')

const router = express.Router()
const machineController = new MachineController();

router.get('/get', requireAuth, machineController.getAllMachines);

module.exports = router
