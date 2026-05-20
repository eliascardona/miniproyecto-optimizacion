const express = require("express");
const { requireAuth } = require("../../middlewares/auth");
const AuthController = require("../controllers/authController");

const router = express.Router();
const controller = new AuthController();

router.post("/register", controller.register);
router.post("/login", controller.login);
router.get("/me", requireAuth, controller.me);

module.exports = router;
