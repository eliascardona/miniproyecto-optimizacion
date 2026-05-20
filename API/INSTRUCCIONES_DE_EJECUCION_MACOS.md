# Instalación de Node.js en macOS

## Objetivo

Verificar o instalar:

* Homebrew
* Node Version Manager
* Node.js

# Paso 0 — Verificar Homebrew

Previo a todo, debes abrir:

```txt id="p4h8d0"
Terminal.app
```

Luego escribes el siguiente comando en tu terminal:

```
brew --version
```

Si en la terminal se muestra algún texto indicando una versión disponible
para brew, entonces ya está instalado en tu máquina MacOS.

---

# Paso 1 — Instalar Homebrew

Ejecutar:

```bash id="h9b0k1"
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

# Paso 2 — Configurar Homebrew para Apple Silicon

Agregar Homebrew al shell:

```bash id="jq81od"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
```

Aplicar cambios:

```bash id="qf7mre"
eval "$(/opt/homebrew/bin/brew shellenv)"
```

---

# Paso 3 — Verificar Homebrew

```bash id="wkl6g2"
brew --version
```

---

# Paso 4 — Instalar NVM

```bash id="g3k7v1"
brew install nvm
```

---

# Paso 5 — Crear directorio NVM

```bash id="7z0bri"
mkdir ~/.nvm
```

---

# Paso 6 — Configurar NVM

Agregar al shell:

```bash id="2vf4ew"
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.zshrc
echo '[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"' >> ~/.zshrc
```

Recargar shell:

```bash id="9kt4rw"
source ~/.zshrc
```

---

# Paso 7 — Instalar Node.js LTS

```bash id="m9h0qs"
nvm install --lts
```

---

# Paso 8 — Verificar instalación

```bash id="x2a8hy"
node -v
npm -v
```

---

# Ver versiones instaladas

```bash id="0w4nsh"
nvm list
```

---

# Cambiar versión Node.js

```bash id="e6pbxo"
nvm use 22
```

---

# Buenas prácticas

```txt id="9m0r2h"
✔ usar siempre versiones LTS
✔ usar NVM para aislar proyectos
✔ evitar instalar Node.js manualmente fuera de NVM
✔ Apple Silicon usa /opt/homebrew
```

---

# Recursos oficiales

* [Homebrew Official Website](https://brew.sh?utm_source=chatgpt.com)
* [NVM GitHub Repository](https://github.com/nvm-sh/nvm?utm_source=chatgpt.com)
* [Node.js Official Website](https://nodejs.org?utm_source=chatgpt.com)