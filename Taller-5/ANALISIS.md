Preguntas del Taller

### 1. ¿Cuál es la configuración mínima de recursos?

- Modelo Covertype: 0.5 CPU + 512MB para ~500 usuarios

### 2. ¿Cuántas peticiones puede soportar?

**Respuesta típica con imagen `ogaston/inference-g3:latest`:**
- 1 instancia (0.5 CPU, 512MB): ~50-100 RPS, 500 usuarios
- 2 instancia (1 CPU, 1GB): ~200-300 RPS, 2000 usuarios
- 4 instancia (2 CPU, 2GB): ~500-1000 RPS, 5000-10000 usuarios


### 3. Tabla aproximada de resultados para 10,000 usuarios con 500 de ramp up

| CPU | RAM | Users | RPS | P95 (ms) | Failures | Resultado |
|-----|-----|-------|-----|----------|----------|-----------|
| 0.5 | 512M | 500 | 45 | 250 | 0% | ✅ OK |
| 0.5 | 512M | 2000 | 180 | 850 | 2.5% | ⚠️ Límite |
| 1.0 | 1G | 2000 | 200 | 450 | 0.3% | ✅ OK |
| 1.0 | 1G | 5000 | 480 | 950 | 3.1% | ⚠️ Límite |
| 2.0 | 2G | 5000 | 500 | 400 | 0.5% | ✅ OK |
| 2.0 | 2G | 10000 | 950 | 600 | 0.8% | ✅ OK |


### 4. ¿Múltiples instancias vs más recursos?

| Aspecto | 1 Instancia Grande | 3 Instancias Pequeñas |
|---------|-------------------|----------------------|
| **Throughput** | Moderado | Alto |
| **Latencia** | Variable bajo carga | Más estable |
| **Disponibilidad** | Sin redundancia | Alta disponibilidad |
| **Escalabilidad** | Vertical | Horizontal |
| **Costo** | 1 máquina potente | 3 máquinas modestas |
| **Recomendación** | Dev/Testing | Producción |


## 👥 Equipo

- **Grupo 3**: Abel Albuez Sanchez, Omar Gaston Chalas, Mauricio Morales