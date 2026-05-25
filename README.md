# Mini-proyecto de Optimización de Circuitos UAA 2026

## Introducción

De forma rápida deseamos introducir a este mini-proyecto de investigación con la siguiente descripción:

El presente mini-proyecto de investigación e ingeniería plantea el desarrollo de una plataforma automatizada para la sintonización y optimización de filtros analógicos activos. Mediante la sinergia de dos disciplinas, el sistema acopla un Motor de Optimización basado en Algoritmos Genéticos y simulación en SPICE (desarrollado en Python) con una Infraestructura de Servidor robusta y escalable (desarrollada en Node.js y PostgreSQL). El objetivo principal es ofrecer una solución computacional eficiente que calcule de manera exacta los valores óptimos de componentes comerciales ($R$ y $C$), minimizando el error de aptitud frente a especificaciones críticas de diseño como frecuencias de corte, ganancia y ancho de banda.

## Propósito del presente repositorio de código

Este repositorio se ha creado con la intención de generar un control de versiones para los códigos desarrollados para atender las necesidades del mini-proyecto.

## Estructura general del repositorio

```
    /ALGORITMO_GENETICO
        # carpeta que contiene los códigos dedicados a desarrollar el algoritmo encargado
        # de optimizar el circuito eléctrico en cuestión.

    /API
        # carpeta que contiene todo el código relativo a la API REST auxiliar del mini-proyecto,
        # misma que conectará al algoritmo en ejecución con una Interfaz de Aplicación capaz de interacturar
        # con aplicaciones amigables para el usuario (apps de frontend) por medio del protocolo HTTP.
    
    /DOCUMENTACION_GENERAL
        # toda la documentación interna que sea de utilidad para el equipo debería de permanecer
        # contenida dentro de esta carpeta.

    /DOCUMENTACION_TIPO_CHANGELOG
        # documentación dedicada a exponer de forma detallada los cambios más significativos que se
        # vayan aplicando al algoritmo o la API. aquí no se deberían de documentar absolutamente todos
        # los cambios aplicados a los artefactos que este repositorio de GitHub contiene, sino sólo
        # aquellos que impliquen cambios significativos al diseño de los productos de software
        # aquí manejados.

    /MODELOS_DE_DATOS
        # con tal de mejorar enormemente la trazabilidad de la evolución que tenga este mini-proyecto,
        # se buscará aplicar estrategias de versionado para los parámetros a utilizar en:
        #       - filtros y especificaciones técnicas de los circuitos
        #       - algoritmos de optimización
        #       - entre otros
        #
        # además, el añadir un versionado a mecanismos internos de la API, le agregará una enorme
        # mantenibilidad y legibilidad al código de la misma.
```

## Acerca de la documentación general del proyecto

En la carpeta de documentación general del proyecto se recomienda añadir sólo documentos de tipo
MARKDOWN o PDF, ya que son fáciles de leer en casi todos los dispotivos, sistemas operativos y aplicaciones
de uso común. Además, github los lee de forma automática en su formato visual.

Documentos con formatos más complejos como Excel, PowerPoint u otros deberán ser adjuntados en forma de enlace.
Por ejemplo, como colaborar de este repositorio, podrías crear un archivo markdown con nombre:

```
LINKS_DE_APOYO__19-05-2026.md
```

Dentro de ese archivo markdown dejas los links a archivos Excel o de otro tipo.
