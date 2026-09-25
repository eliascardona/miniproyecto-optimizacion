package format_converter;

import dto.ComponenteDTO;
import model.Element;

import java.util.ArrayList;
import java.util.List;

public class FormatConverter {
    public static List<Element> convertir(List<ComponenteDTO> componentes) {
        List<Element> elementos = new ArrayList<>();
        int nodoActual = 1;

        for (ComponenteDTO c : componentes) {
            int type = c.tipo.equals("C") ? 0 : 1;
            int[] valueIdx_decadeIdx = {0}; // usa las tablas ya existentes

            int node1 = nodoActual;
            int node2 = c.conexionTierra ? 0 : node1 + 1;
            int nodeA = c.conexionTierra ? node1 : node2;

            elementos.add(new Element(node1, node2, nodeA, type, valueIdx_decadeIdx[0], valueIdx_decadeIdx[1]));
            nodoActual = nodeA;
        }
        return elementos;
    }
}