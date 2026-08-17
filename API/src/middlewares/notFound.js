/**
 * Middleware para rutas no encontradas (404).
 *
 * Se registra despues de todas las rutas validas.
 * Devuelve una pagina HTML amigable en vez de un JSON crudo.
 */

const HTMLNotFoundPage = `
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - No encontrado</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { text-align: center; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { font-size: 3rem; color: #ff6b6b; margin: 0 0 10px; }
        p { font-size: 1.2em; margin: 0 0 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>404</h1>
        <p>Lo sentimos, la pagina que buscas no existe.</p>
    </div>
</body>
</html>
`;

const notFoundMiddleware = (req, res, next) => {
    res.status(404).send(HTMLNotFoundPage);
};

module.exports = { notFoundMiddleware };
