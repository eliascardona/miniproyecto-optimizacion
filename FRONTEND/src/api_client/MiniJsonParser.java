package api_client;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Parser y escritor de JSON minimalista, sin dependencias externas.
 *
 * Este proyecto no usa Maven/Gradle (es un módulo IntelliJ plano con el JDK
 * heredado; ver FinalProject.iml), así que no hay Jackson/Gson disponibles
 * sin agregar manualmente un .jar. En vez de eso, aquí hay un parser
 * recursivo-descendente estándar, suficiente para el contrato JSON conocido
 * entre esta app y la API de Python: objetos, arreglos, strings, números,
 * booleanos y null.
 *
 * No pretende ser un parser JSON "de propósito general" con todas las
 * validaciones estrictas del estándar, pero es correcto y robusto para el
 * uso previsto aquí (construir el cuerpo de la petición y leer la respuesta
 * de CircuitoOptimizadoResponse).
 */
public final class MiniJsonParser {
    private MiniJsonParser() {}

    // ------------------------------------------------------------------
    // Lectura: String JSON -> Map / List / String / Double / Boolean / null
    // ------------------------------------------------------------------

    public static Object parse(String json) {
        Parser p = new Parser(json);
        Object value = p.parseValue();
        return value;
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> parseObject(String json) {
        Object value = parse(json);
        if (!(value instanceof Map)) {
            throw new IllegalArgumentException(
                    "La respuesta JSON no es un objeto en la raíz: " + preview(json));
        }
        return (Map<String, Object>) value;
    }

    private static String preview(String json) {
        return json.length() > 200 ? json.substring(0, 200) + "..." : json;
    }

    private static final class Parser {
        private final String s;
        private int i;

        Parser(String s) {
            this.s = s;
            this.i = 0;
        }

        void skipWhitespace() {
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
                i++;
            }
        }

        char peek() {
            if (i >= s.length()) {
                throw new IllegalArgumentException("JSON incompleto/mal formado en posición " + i);
            }
            return s.charAt(i);
        }

        Object parseValue() {
            skipWhitespace();
            char c = peek();
            return switch (c) {
                case '{' -> parseObject();
                case '[' -> parseArray();
                case '"' -> parseString();
                case 't', 'f' -> parseBoolean();
                case 'n' -> parseNull();
                default -> parseNumber();
            };
        }

        Map<String, Object> parseObject() {
            Map<String, Object> map = new LinkedHashMap<>();
            expect('{');
            skipWhitespace();
            if (peek() == '}') {
                i++;
                return map;
            }
            while (true) {
                skipWhitespace();
                String key = parseString();
                skipWhitespace();
                expect(':');
                Object value = parseValue();
                map.put(key, value);
                skipWhitespace();
                char c = peek();
                if (c == ',') {
                    i++;
                } else if (c == '}') {
                    i++;
                    break;
                } else {
                    throw new IllegalArgumentException("Se esperaba ',' o '}' en posición " + i);
                }
            }
            return map;
        }

        List<Object> parseArray() {
            List<Object> list = new ArrayList<>();
            expect('[');
            skipWhitespace();
            if (peek() == ']') {
                i++;
                return list;
            }
            while (true) {
                Object value = parseValue();
                list.add(value);
                skipWhitespace();
                char c = peek();
                if (c == ',') {
                    i++;
                } else if (c == ']') {
                    i++;
                    break;
                } else {
                    throw new IllegalArgumentException("Se esperaba ',' o ']' en posición " + i);
                }
            }
            return list;
        }

        String parseString() {
            expect('"');
            StringBuilder sb = new StringBuilder();
            while (true) {
                char c = s.charAt(i++);
                if (c == '"') {
                    break;
                }
                if (c == '\\') {
                    char esc = s.charAt(i++);
                    switch (esc) {
                        case '"' -> sb.append('"');
                        case '\\' -> sb.append('\\');
                        case '/' -> sb.append('/');
                        case 'b' -> sb.append('\b');
                        case 'f' -> sb.append('\f');
                        case 'n' -> sb.append('\n');
                        case 'r' -> sb.append('\r');
                        case 't' -> sb.append('\t');
                        case 'u' -> {
                            String hex = s.substring(i, i + 4);
                            sb.append((char) Integer.parseInt(hex, 16));
                            i += 4;
                        }
                        default -> throw new IllegalArgumentException("Escape JSON inválido: \\" + esc);
                    }
                } else {
                    sb.append(c);
                }
            }
            return sb.toString();
        }

        Boolean parseBoolean() {
            if (s.startsWith("true", i)) {
                i += 4;
                return Boolean.TRUE;
            }
            if (s.startsWith("false", i)) {
                i += 5;
                return Boolean.FALSE;
            }
            throw new IllegalArgumentException("Literal booleano inválido en posición " + i);
        }

        Object parseNull() {
            if (s.startsWith("null", i)) {
                i += 4;
                return null;
            }
            throw new IllegalArgumentException("Literal 'null' inválido en posición " + i);
        }

        Double parseNumber() {
            int start = i;
            if (peek() == '-') {
                i++;
            }
            while (i < s.length() && isNumberChar(s.charAt(i))) {
                i++;
            }
            String numStr = s.substring(start, i);
            if (numStr.isEmpty() || numStr.equals("-")) {
                throw new IllegalArgumentException("Número JSON inválido en posición " + start);
            }
            return Double.parseDouble(numStr);
        }

        boolean isNumberChar(char c) {
            return Character.isDigit(c) || c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-';
        }

        void expect(char c) {
            if (peek() != c) {
                throw new IllegalArgumentException("Se esperaba '" + c + "' en posición " + i);
            }
            i++;
        }
    }

    // ------------------------------------------------------------------
    // Escritura: Map / List / String / Number / Boolean / null -> JSON
    // ------------------------------------------------------------------

    public static String write(Object value) {
        StringBuilder sb = new StringBuilder();
        writeValue(value, sb);
        return sb.toString();
    }

    private static void writeValue(Object value, StringBuilder sb) {
        if (value == null) {
            sb.append("null");
        } else if (value instanceof String str) {
            writeString(str, sb);
        } else if (value instanceof Boolean bool) {
            sb.append(bool.toString());
        } else if (value instanceof Number num) {
            sb.append(formatNumber(num));
        } else if (value instanceof Map<?, ?> map) {
            sb.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) {
                    sb.append(',');
                }
                first = false;
                writeString(String.valueOf(entry.getKey()), sb);
                sb.append(':');
                writeValue(entry.getValue(), sb);
            }
            sb.append('}');
        } else if (value instanceof List<?> list) {
            sb.append('[');
            boolean first = true;
            for (Object item : list) {
                if (!first) {
                    sb.append(',');
                }
                first = false;
                writeValue(item, sb);
            }
            sb.append(']');
        } else {
            throw new IllegalArgumentException(
                    "Tipo no soportado por MiniJsonParser: " + value.getClass().getName());
        }
    }

    private static String formatNumber(Number num) {
        if (num instanceof Integer || num instanceof Long) {
            return num.toString();
        }
        double d = num.doubleValue();
        if (d == Math.floor(d) && !Double.isInfinite(d)) {
            return String.valueOf((long) d);
        }
        return String.valueOf(d);
    }

    private static void writeString(String str, StringBuilder sb) {
        sb.append('"');
        for (int idx = 0; idx < str.length(); idx++) {
            char c = str.charAt(idx);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        sb.append('"');
    }
}