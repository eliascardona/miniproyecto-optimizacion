const jwt = require("jsonwebtoken");

function extractBearerToken(header) {
    if (!header) return null;
    const [scheme, token] = header.split(" ");
    if (scheme !== "Bearer" || !token) return null;
    return token;
}

function requireAuth(req, res, next) {
    try {
        const token = extractBearerToken(req.headers.authorization);
        if (!token) {
            return res.status(401).json({ success: false, message: "Token requerido (Authorization: Bearer <token>)" });
        }

        const payload = jwt.verify(token, process.env.JWT_SECRET || "dev_secret");
        req.user = payload; // { sub, username, roles, iat, exp }
        next();
    } catch (err) {
        return res.status(401).json({ success: false, message: "Token inválido o expirado" });
    }
}

module.exports = { requireAuth };
