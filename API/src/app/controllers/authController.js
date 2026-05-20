const express = require("express");
const UserService = require("../services/userService");
const LoginDTO = require("../models/dto/login");

class AuthController {
    constructor() {
        this.userService = new UserService();
        this.router = express.Router();
    }

    register = async (req, res) => {
        try {
            const { username, email, password } = req.body || {};
            if (!username || !password) return res.status(400).json({ success: false, message: "username y password son obligatorios" });

            const user = await this.userService.register({ username, email, password });
            return res.status(201).json({ success: true, user });
        } catch (err) {
            const code = String(err.message || "").includes("duplicate") ? 409 : 400;
            return res.status(code).json({ success: false, message: err.message || "Error en registro" });
        }
    };

    login = async (req, res) => {
        try {
            const { username, password } = req.body || {};
            if (!username || !password) return res.status(400).json({ success: false, message: "username y password son obligatorios" });

            const { token, user } = await this.userService.login({ username, password });

            const authResponse = new LoginDTO()
                .withAccessToken(token)
                .withTokenType("Bearer")
                .withExpiresIn(3600)
                .withUser(user)
                .build();

            return res.status(200).json({
                success: true,
                data: authResponse
            });
        } catch (err) {
            return res.status(401).json({ success: false, message: err.message || "Credenciales inválidas" });
        }
    };

    me = async (req, res) => {
        return res.status(200).json({ success: true, user: req.user });
    };
}

module.exports = AuthController;
