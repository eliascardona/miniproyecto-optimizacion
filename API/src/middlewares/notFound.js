const HTMLNotFoundPage = `
	<!DOCTYPE html>
	<html lang="es">
	<head>
	<meta charset="UTF-8">
	<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>404 - Not Found Page</title>
	<style>
		body {
			font-family: Arial, sans-serif;
			background-color: #f3f4f6;
			color: #333;
			margin: 0;
			padding: 0;
			display: flex;
			justify-content: center;
			align-items: center;
			height: 100vh;
		}
		.container {
			text-align: center;
			padding: 20px;
			background-color: #fff;
			border-radius: 8px;
			box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
		}
		h1 {
			font-size: 3rem;
			margin: 0 0 10px;
			color: #ff6b6b;
		}
		p {
			font-size: 1.2em;
			margin: 0 0 20px;
		}
	</style>
</head>
<body>
	<div class="container">
		<h1>404</h1>
		<p>Lo sentimos, la página que buscas no existe.</p>
		<p><a href="/">Regresar a la página principal</a></p>
	</div>
</body>
</html>
`

const notFoundMiddleware = (req, res, next) => {
	res.status(404).send(HTMLNotFoundPage)
}

module.exports = { notFoundMiddleware }
