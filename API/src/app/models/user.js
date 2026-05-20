class User {
    constructor({ _id, username, email, passwordHash, roles = ["USER"], createdAt, updatedAt }) {
        this.id = _id;
        this.username = username;
        this.email = email;
        this.passwordHash = passwordHash;
        this.roles = roles;
        this.createdAt = createdAt || new Date().toISOString();
        this.updatedAt = updatedAt || new Date().toISOString();
    }
}

module.exports = User;
