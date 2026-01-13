# Caso de Estudio: Arquitectura Híbrida de IA y Blockchain para Seguridad FinTech

![Status](https://img.shields.io/badge/Status-Completed-success)
![Python](https://img.shields.io/badge/Python-3.13.5-blue)
![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636)
![License](https://img.shields.io/badge/License-MIT-green)

> **Repositorio oficial de la Tesis de Maestría en Tecnología Informática**
>
> **Impacto de la Inteligencia Artificial y Blockchain en la Mejora de la Seguridad en Plataformas FinTech**
> 
> **UAI Universidad Abierta Interamericana**
> 
> **Autor:** Gabriel Ibarra
>  
> **Fecha:** Enero 2026


## 📖 Resumen del Proyecto

Se trata de una prueba de concepto (PoC) que implementa una arquitectura de seguridad híbrida diseñada para resolver el trilema de **privacidad**, **latencia** y **trazabilidad** en plataformas FinTech.

El sistema integra un modelo de **Machine Learning (Random Forest)** para la detección de fraude en tiempo real con contratos inteligentes en **Ethereum** para garantizar la inmutabilidad de los registros de auditoría, utilizando un esquema de *Privacy-by-Design* (hashing off-chain) que no expone datos sensibles (PII).

### 🚀 Características Clave
* **Detección en Tiempo Real:** Latencia de inferencia `p95 < 72ms`.
* **Privacidad (No-PII):** Registro on-chain exclusivo de hashes criptográficos (`decision_id`, `tx_ref`).
* **Observabilidad:** Dashboard interactivo para monitoreo de KPIs y eventos blockchain.
* **Reproducibilidad:** Entorno contenerizado y documentado para Windows (PowerShell).

---

## 🏗️ Arquitectura del Sistema

El flujo de datos sigue un ciclo **Percepción → Decisión → Acción**:

1.  **Percepción (Off-chain):** Ingesta de transacciones simuladas (Dataset Kaggle CreditCard).
2.  **Decisión (AI Agent):** Clasificación mediante Random Forest optimizado para datos desbalanceados.
3.  **Acción (On-chain):** Persistencia de decisiones "seguras" en la Blockchain mediante `TxRegistry.sol`.

*(Nota: Ver Figura 1.1 del documento de tesis para el diagrama detallado)*

---

## 🛠️ Requisitos Técnicos

Este proyecto ha sido validado en un entorno **Windows 10/11** con las siguientes especificaciones:

| Componente | Versión Requerida | Notas |
| :--- | :--- | :--- |
| **Python** | `3.13.5` | Intérprete principal |
| **Node.js** | `v22.20.0` | Para Hardhat y compilación de contratos |
| **NPM** | `10.9.3` | Gestor de paquetes de Node |
| **Ganache** | CLI o GUI v7+ | Blockchain local en puerto `8545` |

---

## ⚙️ Guía de Instalación y Despliegue

Sigue estos pasos secuenciales en **PowerShell (Administrador)** para replicar el entorno experimental.

### 1. Clonar y Preparar Entorno
```powershell
git clone [git clone https://github.com/gaboibarra/Tesis-IA-Blockchain.git](git clone https://github.com/gaboibarra/Tesis-IA-Blockchain.git)
cd Tesis-IA-Blockchain

# Crear entorno virtual Python
py -3.13 -m venv .venv

# Activar entorno
.\.venv\Scripts\Activate.ps1

# Instalar dependencias exactas (Auditadas)
pip install -r requirements.txt
```

### 1.1. Obtención del Dataset (Requerido)
El dataset **Credit Card Fraud Detection** no se incluye en el repositorio debido a su tamaño.

1. Descarga el dataset desde [Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud).
2. Descomprime el archivo zip descargado.
3. Mueve el archivo `creditcard.csv` a la carpeta `data/` en la raíz del proyecto.

> **Verificación:** Antes de continuar, asegúrate de que el archivo exista en la ruta: `.\data\creditcard.csv`


### 2. Compilar y Desplegar Smart Contracts
Asegúrate de que Ganache esté corriendo en http://127.0.0.1:8545 (Chain ID: 1337).

```powershell

cd hardhat
npm install
npx hardhat compile

# Despliegue en red local
npx hardhat run .\scripts\deploy.js --network localhost

```
Nota: El script de despliegue actualizará automáticamente el archivo .env en la raíz con la nueva CONTRACT_ADDRESS.

### 3. Pipeline de Datos y Entrenamiento (IA)

Ejecuta el preprocesamiento y entrenamiento del modelo con los hiperparámetros de la tesis:

```powershell

# Volver a la raíz
cd ..

# 1. Preprocesamiento (Split out-of-time + estratificación)
python .\src\data.py --input .\data\creditcard.csv --sample-frac 0.3

# 2. Entrenamiento (Random Forest con ajuste de umbral F1)
python .\src\train_rf.py --data-dir .\data\processed --k 100 500 --th-mode f1

```

### ▶️ Ejecución del Prototipo (E2E)

Para simular un entorno productivo, abre 3 terminales de PowerShell separadas:

### Terminal 1: API de Detección (Backend)
Expone el endpoint /score en el puerto 5000.

```powershell

# Activar entorno primero
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python -m api.app

```

### Terminal 2: Dashboard de Operaciones (Frontend)
Visualización en tiempo real en http://127.0.0.1:8050.

```powershell

.\.venv\Scripts\Activate.ps1
python .\dashboard\app.py

```
### Terminal 3: Generador de Tráfico (Cliente)

```powershell

.\.venv\Scripts\Activate.ps1
# Procesar 500 transacciones de prueba
python .\scripts\run_e2e.py --limit 500

```
### 📊 Resultados de la Validación

Métricas obtenidas en el conjunto de prueba (Test Set):

- Rendimiento del Modelo:
  - PR-AUC: 0.826 (vs Baseline reglas estáticas)
  - Recall@100: 0.833
- Eficiencia Operativa:
  - Latencia p95 (Scoring): ~71.7 ms
  - Latencia p95 (E2E con Blockchain): ~95.1 ms
- Integridad:
  - Correlación Decisión $\to$ Evento: 100%
 
## 📁 Estructura del Proyecto

```text
fraudchain/
├── api/            # API Flask y middleware Web3
├── contracts/      # Smart Contracts (Solidity)
├── dashboard/      # Interfaz gráfica (Dash / Plotly)
├── data/           # Datasets (raw / processed)
├── hardhat/        # Entorno de desarrollo Ethereum
├── models/         # Artefactos serializados (joblib)
├── reports/        # Métricas JSON y curvas de evaluación
├── scripts/        # Scripts de orquestación E2E
└── src/            # Lógica core de ML (entrenamiento / evaluación)
```


### ⚡ Quick Start (Automatización Windows)

Para facilitar la evaluación, la demo y la **reproducibilidad científica**, se incluyen scripts de PowerShell en la raíz del proyecto que orquestan todo el ciclo de vida.

> **Nota:** Estos scripts asumen que ya tienes instalado Python, Node.js y Ganache.

### 🟢 Opción A: "Zero to Hero" (Despliegue Completo)
El script `setup_and_run_all.ps1` realiza todo el proceso desde cero: crea el entorno virtual, instala dependencias, compila contratos, despliega en Ganache y lanza todos los servicios automáticamente.

```powershell
# Ejecutar en PowerShell como Administrador desde la raíz
Set-ExecutionPolicy -Scope Process Bypass
.\setup_and_run_all.ps1

```
### 🟢 Opción B: Ejecucion Modular

## 🛠️ Scripts disponibles

| Script              | Función |
|---------------------|---------|
| `start_all.ps1`     | Inicia Ganache, la API y el Dashboard en ventanas separadas. |
| `run_e2e.ps1`       | Ejecuta la simulación de tráfico y muestra métricas en consola. |
| `stop_all.ps1`      | Detiene todos los procesos (Python, Node y Ganache) para limpiar el entorno. |



### 🔧 Solución de Problemas Comunes

### 1. Error ModuleNotFoundError:

Asegúrate de ejecutar $env:PYTHONPATH = (Get-Location).Path en PowerShell antes de iniciar la API.

### 2. Error de codificación en Solidity:

Si Hardhat falla al compilar, verifica que TxRegistry.sol esté guardado con codificación UTF-8 sin BOM.

### 3. Puertos ocupados:

Libera los puertos 5000 (API) y 8050 (Dashboard) o modifícalos en api/app.py y dashboard/app.py.

---

## 📜 Licencia y Reconocimientos

Este proyecto se distribuye bajo la licencia **MIT**. Si utilizas este código o la arquitectura propuesta para tu propia investigación, se agradece la citación correspondiente al trabajo de tesis original.

> **Tesis de Maestría en Tecnología Informática**
> Universidad Abierta Interamericana (UAI) - Enero 2026

### 📩 Contacto
Para consultas académicas o técnicas sobre la implementación:

*  **Autor:** Gabriel Ibarra <img src="https://flagcdn.com/16x12/ve.png" alt="Venezuela" width="16" />
* **Perfil:** [github.com/gaboibarra](https://github.com/gaboibarra)

---
*Hecho con 🐍 Python, ⛓️ Solidity y mucho ☕ en Buenos Aires.*

























