# Instrucciones de ejecución del programa

## Software necesario

- Tener instalado Node.js
- Tener instalado PostgreSQL versión 17.x.x

### Proceso de instalación de Postgres 17

**Requisitos**

- Windows 11
- Windows PowerShell en correcto estado
- acceso a internet
- permisos de usuario normales




### Proceso de instalación de Node.js

**Requisitos**

- Windows 11
- Windows PowerShell en correcto estado
- acceso a internet
- permisos de usuario normales

# Paso 1 — Abrir PowerShell

Abrir:

```
PowerShell
```

Recomendado:
Ejecutar como usuario normal y NO como administrador

---

# Paso 2 — Permitir scripts locales

Ejecutar:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Confirmar con:

```
Y (yes) o S (sí)
```


# Paso 3 — Descargar scoop utilizando un comando de PowerShell contenido en la documentación oficial

Ejecutar:

```
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

---

# Paso 4 — Instalar NodeJS Version Manager (NVM) para Windows

## Instalar

```
scoop install nvm
```

---

# Paso 5 — Instalar Node.js usando NVM

## Instalar versión LTS

Ejemplo:

```
nvm install 22
```

---

## Paso 6 – Activar versión instalada

```
nvm use 22
```

---

# Paso 7 — Verificar Node.js

```
node -v
```

```
npm -v
```

Salida esperada:

```txt id="rjrf0v"
v22.x.x
10.x.x
```

---

# ADICIONAL: Ver instalaciones disponibles

```
nvm list
```

---

# ADICIONAL: Cambiar de versión Node.js

Ejemplo:

```
nvm use <VERSION_NUMBER>
```
