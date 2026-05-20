require("dotenv").config();
const express = require("express");
const morgan = require("morgan");
const { corsMiddleware } = require("./middlewares/cors.js");
const { notFoundMiddleware } = require("./middlewares/notFound.js");
const { connectDB, disconnectDB } = require("./config/database");
const UserRepository = require("./app/repository/userRepository");

const authRoutes = require("./app/routes/authRoutes.js");
const machinesRoutes = require("./app/routes/machinesRoutes.js");

const app = express();

// Global Middlewares
app.use(morgan("common"));
app.use(express.json());
// CORS
app.use((req, res, next) => { corsMiddleware(req, res); next(); });

// Rutas
app.use("/auth", authRoutes);
app.use("/machines", machinesRoutes);

// 404 al final
app.use(notFoundMiddleware);

// Error handler
app.use((err, req, res, next) => {
	console.error("❌ Error catched by global middleware:", err);
	res.status(500).json({ message: "A server error has happened" });
});

const PORT = process.env.PORT || 8082;

(async () => {
	try {
		await connectDB();

		// Asegurar índices únicos de usuario
		const ur = new UserRepository();
		await ur.ensureIndexes();

		app.listen(PORT, () => {
			console.log(`✅ Servicio MVC en puerto ${PORT}`);
		});
	} catch (err) {
		console.error("❌ No se pudo iniciar el servidor:", err);
		process.exit(1);
	}
})();

process.on("SIGINT", async () => {
	await disconnectDB();
	process.exit(0);
});
