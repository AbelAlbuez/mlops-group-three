#!/usr/bin/env python3
"""
Locust load test for Covertype Inference API.
Simulates users making predictions with the covertype model (12 features).
"""

from locust import HttpUser, task, between
import random


class CovertypeUser(HttpUser):
    """User class for load testing the covertype inference API."""
    
    wait_time = between(1, 3)
    
    def generate_payload(self):
        """Generate random covertype data (12 features)."""
        return {
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
    
    @task(10)
    def predict(self):
        """Make prediction (main task)."""
        with self.client.post(
            "/predict",
            json=self.generate_payload(),
            name="POST /predict",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "prediction" in result:
                        response.success()
                    else:
                        response.failure("No prediction field in response")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Check API health."""
        with self.client.get(
            "/health", 
            name="GET /health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("API not healthy")
                except:
                    response.failure("Invalid health response")
            else:
                response.failure(f"Health check failed: {response.status_code}")


# Alias para compatibilidad (comentado para evitar duplicados)
# WebsiteUser = CovertypeUser