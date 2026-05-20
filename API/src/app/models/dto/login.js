class LoginDTO {
    constructor() {
        this.accessToken = null;
        this.refreshToken = null;
        this.tokenType = "Bearer";
        this.expiresIn = null;
        this.user = null;
    }

    withAccessToken(token) {
        this.accessToken = token;
        return this;
    }

    withRefreshToken(token) {
        this.refreshToken = token;
        return this;
    }

    withTokenType(type) {
        this.tokenType = type;
        return this;
    }

    withExpiresIn(seconds) {
        this.expiresIn = seconds;
        return this;
    }

    withUser(userData) {
        this.user = { ...userData };
        return this;
    }

    build() {
        if (!this.accessToken) {
            throw new Error("El accessToken es obligatorio");
        }
        if (!this.tokenType) {
            throw new Error("El tokenType es obligatorio");
        }
        if (!this.expiresIn) {
            throw new Error("El expiresIn es obligatorio");
        }
        if (!this.user._id || !this.user.username || !this.user.email) {
            throw new Error("El usuario debe tener _id, username y email");
        }

        const response = {
            accessToken: this.accessToken,
            tokenType: this.tokenType,
            expiresIn: this.expiresIn,
            user: this.user
        };

        if (this.refreshToken) {
            response.refreshToken = this.refreshToken;
        }

        return response;
    }
}

module.exports = LoginDTO;
