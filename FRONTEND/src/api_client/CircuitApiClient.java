package api_client;

import catalogo.Catalogo;
import catalogo.CatalogoParser;
import dto.OptimizationResult;
import dto.PeticionOptimizacion;
import esquema.Esquema;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.StringJoiner;

/**
 * Cliente HTTP hacia la API de optimización de circuitos (FastAPI + algoritmos en Python).
 *
 * Usa java.net.http.HttpClient (incluido en el JDK desde la versión 11, no
 * requiere ninguna librería externa) porque este proyecto no tiene
 * Maven/Gradle configurado.
 *
 * No conoce model.Circuit ni model.IdealFilter ni model.Simulation, y no
 * sabe nada de filtros ni algoritmos concretos: pide el catálogo
 * ({@link #obtenerCatalogo()}), optimiza lo que le describa una
 * {@link PeticionOptimizacion} ({@link #optimizar}) y pide el dibujo base de
 * un filtro ({@link #obtenerEsquema}). Las tres llamadas son bloqueantes:
 * hay que hacerlas fuera del EDT (SwingWorker).
 */
public class CircuitApiClient {

    /** Se lanza cuando la API responde con error (4xx/5xx), no se puede alcanzar, o responde con un cuerpo inesperado. */
    public static class ApiException extends Exception {
        public ApiException(String message) {
            super(message);
        }

        public ApiException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private final HttpClient httpClient;
    private final String baseUrl;

    public CircuitApiClient() {
        this(ApiConfig.BASE_URL);
    }

    /** Constructor con URL base propia (p. ej. un servidor local en pruebas). */
    public CircuitApiClient(String baseUrl) {
        this.baseUrl = baseUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(ApiConfig.CONNECT_TIMEOUT_SECONDS))
                .build();
    }

    /**
     * Pide el catálogo (GET /api/catalogo): qué se puede optimizar y con qué parámetros.
     * Lanza ApiException si el servidor no responde o si el catálogo es ilegible/incoherente.
     */
    public Catalogo obtenerCatalogo() throws ApiException {
        String cuerpo = enviar(HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + ApiConfig.CATALOG_ENDPOINT))
                .timeout(Duration.ofSeconds(ApiConfig.CONNECT_TIMEOUT_SECONDS * 3L))
                .GET());
        try {
            return CatalogoParser.parse(MiniJsonParser.parse(cuerpo));
        } catch (RuntimeException e) {
            throw new ApiException("El catálogo recibido no tiene el formato esperado: " + e.getMessage(), e);
        }
    }

    /**
     * Optimiza el filtro con el algoritmo que describe `peticion` (POST /api/optimizar). Puede tardar
     * minutos: el servidor corre el algoritmo completo antes de responder.
     */
    public OptimizationResult optimizar(PeticionOptimizacion peticion) throws ApiException {
        String cuerpo = enviar(HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + ApiConfig.OPTIMIZE_ENDPOINT))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(ApiConfig.REQUEST_TIMEOUT_SECONDS))
                .POST(HttpRequest.BodyPublishers.ofString(MiniJsonParser.write(peticion.aCuerpo()))));
        try {
            return OptimizationResultParser.parse(cuerpo);
        } catch (RuntimeException e) {
            throw new ApiException(
                    "La respuesta de la API no tiene el formato esperado: " + e.getMessage(), e);
        }
    }

    /**
     * Pide el esquema (dibujo) de un filtro con los valores base de su plantilla
     * (GET /api/circuitos/{filtro}); sirve para mostrar el circuito antes de optimizar.
     */
    public Esquema obtenerEsquema(String filtro) throws ApiException {
        String cuerpo = enviar(HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + ApiConfig.CIRCUITS_ENDPOINT + "/" + filtro))
                .timeout(Duration.ofSeconds(ApiConfig.CONNECT_TIMEOUT_SECONDS * 3L))
                .GET());
        try {
            return OptimizationResultParser.parseEsquema(cuerpo);
        } catch (RuntimeException e) {
            throw new ApiException(
                    "El esquema recibido no tiene el formato esperado: " + e.getMessage(), e);
        }
    }

    // ------------------------------------------------------------------
    // Transporte común
    // ------------------------------------------------------------------

    /** Envía la petición y devuelve el cuerpo si la respuesta es 2xx; si no, lanza ApiException con el motivo. */
    private String enviar(HttpRequest.Builder constructor) throws ApiException {
        HttpRequest peticion = constructor.version(HttpClient.Version.HTTP_1_1).build();

        HttpResponse<String> response;
        try {
            response = httpClient.send(peticion, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new ApiException(
                    "No se pudo conectar con la API en " + baseUrl + ". ¿Está corriendo el servidor?", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ApiException("La petición a la API fue interrumpida.", e);
        }

        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new ApiException(
                    "La API respondió con error " + response.statusCode() + ": " + motivo(response.body()));
        }
        return response.body();
    }

    /**
     * FastAPI responde los errores como {"detail": ...}: un texto (HTTPException) o una lista de
     * {loc, msg, ...} (validación de Pydantic). Se resume en una línea legible; si el cuerpo no tiene esa
     * forma, se muestra tal cual.
     */
    static String motivo(String cuerpo) {
        try {
            Object detalle = MiniJsonParser.parseObject(cuerpo).get("detail");
            if (detalle instanceof String texto) {
                return texto;
            }
            if (detalle instanceof List<?> errores && !errores.isEmpty()) {
                StringJoiner union = new StringJoiner("; ");
                for (Object error : errores) {
                    if (error instanceof Map<?, ?> m && m.get("msg") != null) {
                        Object ubicacion = m.get("loc");
                        union.add((ubicacion instanceof List<?> l ? String.join(".", l.stream().map(String::valueOf).toList()) + ": " : "")
                                + m.get("msg"));
                    } else {
                        union.add(String.valueOf(error));
                    }
                }
                return union.toString();
            }
        } catch (RuntimeException ignorada) {
            // No era JSON o no tenía "detail": se devuelve el cuerpo crudo.
        }
        return cuerpo;
    }
}