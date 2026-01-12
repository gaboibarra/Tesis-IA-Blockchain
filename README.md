# FraudChain: Arquitectura Híbrida de IA y Blockchain para Seguridad FinTech

![Status](https://img.shields.io/badge/Status-Completed-success)
![Python](https://img.shields.io/badge/Python-3.13.5-blue)
![Solidity](https://img.shields.io/badge/Solidity-0.8.20-363636)
![License](https://img.shields.io/badge/License-MIT-green)

> **Repositorio oficial de la Tesis de Maestría en Tecnología Informática**
>
> **Autor:** Gabriel Ibarra
> **Fecha:** Enero 2026

## 📖 Resumen del Proyecto

**FraudChain** es una prueba de concepto (PoC) que implementa una arquitectura de seguridad híbrida diseñada para resolver el trilema de **privacidad**, **latencia** y **trazabilidad** en plataformas FinTech.

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
git clone [https://github.com/TU_USUARIO/Tesis-IA-Blockchain.git](https://github.com/TU_USUARIO/Tesis-IA-Blockchain.git)
cd Tesis-IA-Blockchain

# Crear entorno virtual Python
py -3.13 -m venv .venv

# Activar entorno
.\.venv\Scripts\Activate.ps1

# Instalar dependencias exactas (Auditadas)
pip install -r requirements.txt
```

### 2. Compilar y Desplegar Smart Contracts







