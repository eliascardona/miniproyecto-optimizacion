const { getDB } = require("../../config/database");
const User = require("../models/user");

class UserRepository {
    constructor() {
        this.collection = () => getDB().collection("users");
    }

    async ensureIndexes() {
        await this.collection().createIndex({ username: 1 }, { unique: true });
        await this.collection().createIndex({ email: 1 }, { unique: true, sparse: true });
    }

    async findByUsername(username) {
        const doc = await this.collection().findOne({ username });
        return doc ? new User(doc) : null;
    }

    async findByEmail(email) {
        const doc = await this.collection().findOne({ email });
        return doc ? new User(doc) : null;
    }

    async create({ username, email, passwordHash, roles = ["USER"] }) {
        const now = new Date().toISOString();
        const result = await this.collection().insertOne({ username, email, passwordHash, roles, createdAt: now, updatedAt: now });
        const doc = await this.collection().findOne({ _id: result.insertedId });
        return new User(doc);
    }
}

module.exports = UserRepository;
