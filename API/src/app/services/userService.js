const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");
const UserRepository = require("../repository/userRepository");

class UserService {
    constructor() {
        this.repo = new UserRepository();
        // No awaits en constructor: llama a ensureIndexes() desde server.js tras connectDB()
    }

    async register({ username, email, password }) {
        const existing = await this.repo.findByUsername(username);
        if (existing) throw new Error("El usuario ya existe");

        const hash = await bcrypt.hash(password, 12);
        const user = await this.repo.create({ username, email, passwordHash: hash });
        return this.toPublicUser(user);
    }

    async login({ username, password }) {
        const user = await this.repo.findByUsername(username);
        if (!user) throw new Error("Credenciales inválidas");
        const ok = await bcrypt.compare(password, user.passwordHash);
        if (!ok) throw new Error("Credenciales inválidas");

        const token = this.generateToken(user);
        return { token, user: this.toPublicUser(user) };
    }

    generateToken(user) {
        const payload = { sub: String(user.id), username: user.username, roles: user.roles };
        const opts = { expiresIn: process.env.JWT_EXPIRES || "1h" };
        return jwt.sign(payload, process.env.JWT_SECRET || "dev_secret", opts);
    }

    toPublicUser(user) {
        return {
            _id: String(user.id),
            username: user.username,
            email: user.email,
            roles: user.roles,
            createdAt: user.createdAt,
            updatedAt: user.updatedAt
        };
    }
}

module.exports = UserService;
