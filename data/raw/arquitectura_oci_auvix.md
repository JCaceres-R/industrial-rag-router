# Guía de Arquitectura de Red y Despliegue de Modelos de Machine Learning en OCI

**Código de documento:** AUVIX-CLD-OCI-002
**Versión:** 1.0
**Área responsable:** Arquitectura Cloud - Oracle Cloud Infrastructure (OCI)

---

## 1. Objetivo y Alcance

Esta guía define la arquitectura de red y el procedimiento estandarizado de Auvix para el despliegue de modelos de Machine Learning empaquetados como aplicaciones web (Streamlit) sobre instancias **Ampere A1 (ARM)** dentro de la capa **Always Free** de Oracle Cloud Infrastructure (OCI). El documento cubre la creación de la VCN, la configuración de subredes, las Listas de Seguridad requeridas y los comandos de despliegue de la aplicación en el sistema operativo de la instancia.

**Alcance:**

- Topología de red (VCN, subredes, gateways).
- Configuración de Listas de Seguridad para exponer el puerto de la aplicación.
- Aprovisionamiento de instancia de cómputo Ampere A1.
- Despliegue de la aplicación Python/Streamlit mediante entorno virtual y ejecución persistente con `nohup` o `tmux`.

---

## 2. Topología de Red

### 2.1 Creación de la VCN (Virtual Cloud Network)

La VCN es el contenedor lógico de red que aloja los recursos de cómputo del proyecto de Machine Learning. Se recomienda crear una VCN dedicada para los despliegues de modelos, separada de la VCN de producción de planta.

**Parámetros recomendados:**

- **Nombre:** `vcn-auvix-ml`
- **Bloque CIDR:** `10.0.0.0/16`
- **DNS resolution:** habilitada
- **Compartimento:** `ml-deployments`

La VCN puede crearse desde la consola de OCI (`Networking > Virtual Cloud Networks > Create VCN`) o mediante el asistente **VCN Wizard** con la opción *Create VCN with Internet Connectivity*, la cual aprovisiona automáticamente el Internet Gateway y las tablas de ruteo asociadas.

### 2.2 Subred Pública

Para el despliegue de la aplicación Streamlit se requiere una subred pública, dado que la interfaz web debe ser accesible desde fuera de la VCN.

**Parámetros recomendados:**

- **Nombre:** `subnet-public-ml`
- **Bloque CIDR:** `10.0.1.0/24`
- **Tipo:** Pública (Public Subnet)
- **Tabla de ruteo:** asociada al Internet Gateway (`ig-auvix-ml`)
- **DHCP Options:** por defecto

### 2.3 Internet Gateway y Tabla de Rutas

El Internet Gateway (`ig-auvix-ml`) debe estar asociado a la tabla de rutas de la subred pública, con la siguiente entrada:

| Destino CIDR | Tipo de destino | Destino |
|---|---|---|
| `0.0.0.0/0` | Internet Gateway | `ig-auvix-ml` |

### 2.4 Listas de Seguridad (Security Lists)

Las Listas de Seguridad actúan como firewall a nivel de subred. Para permitir el acceso a la aplicación Streamlit (puerto **8501**), además del acceso administrativo por SSH, se debe configurar la siguiente Lista de Seguridad sobre `subnet-public-ml`.

**Reglas de entrada (Ingress Rules):**

| Origen (Source) | Protocolo | Puerto destino | Descripción |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `22` | Acceso administrativo SSH |
| `0.0.0.0/0` | TCP | `8501` | Acceso a la aplicación Streamlit |

**Reglas de salida (Egress Rules):**

| Destino | Protocolo | Puerto destino | Descripción |
|---|---|---|---|
| `0.0.0.0/0` | Todos | Todos | Salida sin restricción |

> **Nota:** El puerto **8501** corresponde al puerto por defecto del servidor de Streamlit. Es imprescindible habilitar esta regla tanto en la Lista de Seguridad de la subred como en el firewall interno del sistema operativo de la instancia (`iptables` o `firewalld`), ya que OCI aplica ambos niveles de filtrado de forma independiente.

---

## 3. Aprovisionamiento de la Instancia de Cómputo

### 3.1 Selección del Shape: Ampere A1 (ARM) - Always Free

Auvix estandariza el uso de instancias **Ampere A1 Compute** (arquitectura ARM) para el despliegue de modelos de Machine Learning ligeros y aplicaciones de inferencia, aprovechando la capa **Always Free** de OCI.

**Parámetros recomendados de la instancia:**

- **Shape:** `VM.Standard.A1.Flex`
- **OCPUs:** hasta 4 (límite agregado de la capa Always Free)
- **Memoria:** hasta 24 GB (límite agregado de la capa Always Free)
- **Imagen:** Ubuntu 22.04 (ARM64) o Oracle Linux 8 (ARM64)
- **Subred:** `subnet-public-ml`
- **Asignación de IP pública:** habilitada

> **Nota:** La capa Always Free de OCI para Ampere A1 permite un total combinado de hasta 4 OCPUs y 24 GB de RAM, distribuibles entre una o varias instancias. Se recomienda documentar en el inventario de Auvix la distribución de recursos utilizada por cada despliegue de modelo.

### 3.2 Clave SSH

Durante la creación de la instancia se debe asociar la clave pública SSH generada para el equipo de arquitectura cloud de Auvix, conforme al procedimiento interno de gestión de credenciales.

---

## 4. Despliegue de la Aplicación (Python + Streamlit)

### 4.1 Preparación del Entorno Virtual

Una vez aprovisionada la instancia y verificada la conectividad SSH, se procede a instalar el entorno de ejecución de Python en modo aislado (virtual environment).

```bash
# Actualización de paquetes del sistema
sudo apt update && sudo apt upgrade -y

# Instalación de Python3, pip y el módulo venv
sudo apt install -y python3 python3-pip python3-venv git tmux

# Creación del entorno virtual del proyecto
python3 -m venv ~/venv-ml-auvix

# Activación del entorno virtual
source ~/venv-ml-auvix/bin/activate

# Instalación de dependencias del modelo y de Streamlit
pip install --upgrade pip
pip install streamlit scikit-learn pandas numpy
```

### 4.2 Apertura del Puerto en el Firewall del Sistema Operativo

```bash
# Habilitar el puerto 8501 en el firewall interno de la instancia (Ubuntu/iptables)
sudo iptables -I INPUT -p tcp --dport 8501 -j ACCEPT
sudo netfilter-persistent save
```

### 4.3 Ejecución Persistente de la Aplicación

Auvix admite dos mecanismos equivalentes para mantener la aplicación en ejecución tras cerrar la sesión SSH: `nohup` o `tmux`.

**Opción A: Ejecución con `nohup`**

```bash
# Ejecutar la aplicación en segundo plano, con salida redirigida a un log
nohup streamlit run app_modelo.py \
  --server.port 8501 \
  --server.address 0.0.0.0 > streamlit.log 2>&1 &

# Verificar que el proceso quedó activo
ps aux | grep streamlit
```

**Opción B: Ejecución con `tmux`**

```bash
# Crear una nueva sesión de tmux dedicada al despliegue
tmux new -s ml-auvix

# Dentro de la sesión de tmux, activar el entorno y lanzar la aplicación
source ~/venv-ml-auvix/bin/activate
streamlit run app_modelo.py --server.port 8501 --server.address 0.0.0.0

# Desacoplarse de la sesión sin detener el proceso: Ctrl+B, luego D
```

Para retomar la sesión de `tmux` en una conexión posterior:

```bash
tmux attach -t ml-auvix
```

### 4.4 Verificación del Despliegue

Una vez en ejecución, la aplicación queda disponible en la dirección IP pública de la instancia:

```
http://<IP_PUBLICA_INSTANCIA>:8501
```

---

## 5. Consideraciones Operativas

- **Persistencia tras reinicio:** para entornos productivos se recomienda migrar de `nohup`/`tmux` a un servicio `systemd` que garantice el reinicio automático de la aplicación ante un reinicio de la instancia.
- **Actualización de modelos:** el reemplazo de artefactos de modelo (`.pkl`, `.joblib`, `.onnx`) debe realizarse con la aplicación detenida, siguiendo el procedimiento de control de cambios del área de Machine Learning de Auvix.
- **Monitoreo de recursos:** dado que la capa Always Free tiene límites fijos de OCPU y memoria, se recomienda monitorear el consumo de la instancia Ampere A1 mediante los paneles de métricas nativos de OCI (`Monitoring > Metrics Explorer`).
- **Seguridad de red:** se recomienda restringir progresivamente el origen (`Source`) de la regla de ingreso del puerto `8501` a rangos IP conocidos, una vez finalizada la fase de validación inicial, en lugar de mantener `0.0.0.0/0` de forma indefinida.

---

*Fin de la Guía de Arquitectura de Red y Despliegue de Modelos de Machine Learning en OCI — Documento AUVIX-CLD-OCI-002.*
