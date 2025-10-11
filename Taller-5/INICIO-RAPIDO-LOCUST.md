# 🚀 Inicio Rápido - Pruebas de Carga con Locust

Guía rápida para ejecutar pruebas de carga del modelo Covertype con Locust.

## ⚡ Comandos Esenciales

### 1. Verificar Dependencias

```bash
# Verificar que Docker esté instalado
docker --version
docker-compose --version

# Verificar que curl esté disponible
curl --version
```

### 2. Iniciar Servicios

```bash
# Opción 1: Con Makefile (recomendado)
make -f Makefile.locust up

# Opción 2: Con Docker Compose
docker-compose -f docker-compose.locust.yml up -d
```

### 3. Verificar Estado

```bash
# Ver estado de los servicios
make -f Makefile.locust status

# Ver logs en tiempo real
make -f Makefile.locust logs
```

### 4. Ejecutar Pruebas

```bash
# Prueba rápida (500 usuarios, 5 minutos)
make -f Makefile.locust test-quick

# Prueba media (2000 usuarios, 10 minutos)
make -f Makefile.locust test-medium

# Todas las pruebas
make -f Makefile.locust test-load
```

### 5. Ver Resultados

```bash
# Los resultados se guardan en:
ls -la load_test_results/

# Ver reporte consolidado
cat load_test_results/consolidated_report.md
```

### 6. Detener Servicios

```bash
# Detener todos los servicios
make -f Makefile.locust down

# Limpiar contenedores y volúmenes
make -f Makefile.locust clean
```

## 🌐 Accesos Web

Una vez iniciados los servicios, puedes acceder a:

- **Locust Web UI**: http://localhost:8089
- **API de Inferencia**: http://localhost:8000
- **MLflow**: http://localhost:5002
- **MySQL**: localhost:3306

## 📊 Ejemplo de Uso

### Prueba Básica

```bash
# 1. Iniciar servicios
make -f Makefile.locust up

# 2. Esperar a que estén listos (30-60 segundos)
make -f Makefile.locust status

# 3. Ejecutar prueba rápida
make -f Makefile.locust test-quick

# 4. Ver resultados
ls -la load_test_results/
```

### Prueba Personalizada

```bash
# Prueba con 1000 usuarios por 10 minutos
./run_load_tests.sh --users 1000 --time 10m

# Prueba con configuración específica de recursos
./run_load_tests.sh --config 1.0/1G
```

## 🔧 Comandos de Diagnóstico

### Ver Logs

```bash
# Todos los logs
make -f Makefile.locust logs

# Solo logs de la API
make -f Makefile.locust logs-api

# Solo logs de Locust
make -f Makefile.locust logs-locust
```

### Ver Estadísticas

```bash
# Estado de contenedores
make -f Makefile.locust stats

# Información del sistema
make -f Makefile.locust info
```

### Escalar Workers

```bash
# Escalar a 2 workers
make -f Makefile.locust scale-2

# Escalar a 3 workers
make -f Makefile.locust scale-3
```

## 🚨 Solución de Problemas Rápidos

### Servicios no inician

```bash
# Ver logs de error
docker-compose -f docker-compose.locust.yml logs

# Limpiar y reiniciar
make -f Makefile.locust clean
make -f Makefile.locust up
```

### API no responde

```bash
# Verificar health check
curl http://localhost:8000/health

# Ver logs de la API
make -f Makefile.locust logs-api
```

### Puerto ocupado

```bash
# Ver qué está usando el puerto
lsof -i :8089
lsof -i :8000
lsof -i :5002

# Cambiar puertos en docker-compose.locust.yml
```

## 📈 Interpretación de Resultados

### Archivos Generados

- `test_*_users_*_cpu_*_mem_*.csv` - Datos detallados
- `test_*_users_*_cpu_*_mem_*.html` - Reporte visual
- `consolidated_report.md` - Reporte consolidado

### Métricas Importantes

- **RPS**: Peticiones por segundo
- **Response Time**: Tiempo de respuesta promedio
- **95th Percentile**: 95% de peticiones responden en este tiempo
- **Error Rate**: Porcentaje de peticiones fallidas

## 🎯 Configuraciones Recomendadas

### Para Desarrollo

```bash
# Configuración ligera
make -f Makefile.locust test-025  # 0.25 CPU, 256M RAM
```

### Para Testing

```bash
# Configuración media
make -f Makefile.locust test-05   # 0.5 CPU, 512M RAM
```

### Para Producción

```bash
# Configuración robusta
make -f Makefile.locust test-1    # 1.0 CPU, 1G RAM
make -f Makefile.locust test-2    # 2.0 CPU, 2G RAM
```

## 🔄 Flujo de Trabajo Típico

1. **Iniciar servicios**: `make -f Makefile.locust up`
2. **Verificar estado**: `make -f Makefile.locust status`
3. **Ejecutar prueba**: `make -f Makefile.locust test-quick`
4. **Ver resultados**: `ls -la load_test_results/`
5. **Detener servicios**: `make -f Makefile.locust down`

## 📝 Notas Importantes

- El modelo utiliza 12 features de covertype
- Los resultados se guardan automáticamente
- Se puede ejecutar en modo headless o con Web UI
- Soporte para múltiples workers de Locust
- Configuración de recursos ajustable

## 🆘 Ayuda Adicional

Para más información:

- **Documentación completa**: `README-LOCUST.md`
- **Comandos disponibles**: `make -f Makefile.locust help`
- **Script de pruebas**: `./run_load_tests.sh --help`

---

**¡Listo para empezar!** 🚀
