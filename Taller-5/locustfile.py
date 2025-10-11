#!/usr/bin/env python3
"""
Archivo de configuración de Locust para pruebas de carga del modelo Covertype.
Este archivo define las tareas de usuario que simularán el comportamiento real
de los usuarios haciendo predicciones con el modelo de covertype.
"""

import random
import json
from locust import HttpUser, task, between


class CovertypeInferenceUser(HttpUser):
    """
    Clase de usuario para simular el comportamiento de usuarios reales
    que hacen predicciones con el modelo de covertype.
    
    El modelo de covertype utiliza 12 features:
    - elevation: elevación en metros (1800-3800)
    - aspect: orientación en grados (0-360)
    - slope: pendiente en grados (0-65)
    - horizontal_distance_to_hydrology: distancia horizontal a hidrología (0-1400)
    - vertical_distance_to_hydrology: distancia vertical a hidrología (-170-600)
    - horizontal_distance_to_roadways: distancia horizontal a carreteras (0-7000)
    - hillshade_9am: sombra a las 9am (0-255)
    - hillshade_noon: sombra al mediodía (0-255)
    - hillshade_3pm: sombra a las 3pm (0-255)
    - horizontal_distance_to_fire_points: distancia horizontal a puntos de fuego (0-7000)
    - wilderness_area: área silvestre (0-3)
    - soil_type: tipo de suelo (0-40)
    """
    
    # Tiempo de espera entre tareas (1-3 segundos)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Método llamado cuando un usuario inicia una sesión."""
        print(f"Usuario {self.client} iniciando sesión...")
    
    @task(10)
    def predict_covertype(self):
        """
        Tarea principal: hacer predicciones de covertype.
        Peso 10: se ejecuta 10 veces más frecuentemente que el health check.
        """
        # Generar datos aleatorios para las 12 features del modelo covertype
        prediction_data = {
            "elevation": random.randint(1800, 3800),
            "aspect": random.randint(0, 360),
            "slope": random.randint(0, 65),
            "horizontal_distance_to_hydrology": random.randint(0, 1400),
            "vertical_distance_to_hydrology": random.randint(-170, 600),
            "horizontal_distance_to_roadways": random.randint(0, 7000),
            "hillshade_9am": random.randint(0, 255),
            "hillshade_noon": random.randint(0, 255),
            "hillshade_3pm": random.randint(0, 255),
            "horizontal_distance_to_fire_points": random.randint(0, 7000),
            "wilderness_area": random.randint(0, 3),
            "soil_type": random.randint(0, 40)
        }
        
        # Headers para la petición
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Realizar petición POST al endpoint de predicción
        with self.client.post(
            "/predict",
            json=prediction_data,
            headers=headers,
            catch_response=True,
            name="predict_covertype"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "prediction" in result:
                        response.success()
                        print(f"Predicción exitosa: {result['prediction']}")
                    else:
                        response.failure("Respuesta sin campo 'prediction'")
                except json.JSONDecodeError:
                    response.failure("Respuesta no es JSON válido")
            elif response.status_code == 422:
                response.failure("Datos de entrada inválidos")
            elif response.status_code == 500:
                response.failure("Error interno del servidor")
            else:
                response.failure(f"Error HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """
        Tarea de verificación de salud del servicio.
        Peso 1: se ejecuta menos frecuentemente que las predicciones.
        """
        with self.client.get(
            "/health",
            catch_response=True,
            name="health_check"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Servicio no está healthy")
                except json.JSONDecodeError:
                    response.failure("Respuesta de health no es JSON válido")
            else:
                response.failure(f"Health check falló con código {response.status_code}")
    
    def on_stop(self):
        """Método llamado cuando un usuario termina una sesión."""
        print(f"Usuario {self.client} terminando sesión...")


# Configuración adicional para Locust
class WebsiteUser(CovertypeInferenceUser):
    """
    Alias para la clase principal de usuario.
    Mantiene compatibilidad con configuraciones existentes.
    """
    pass
