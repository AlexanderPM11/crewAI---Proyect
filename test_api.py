import requests

url = "http://localhost:8000/api/chat"
headers = {
    "Content-Type": "application/json",
    "x-api-key": "tri-tec-secret-123"
}
data = {
    "mensaje": "Hola, soy Alexander Polanco"
}

try:
    response = requests.post(url, json=data, headers=headers)
    print(f"Status Code: {response.status_code}")
    # Usar .encode('utf-8') para evitar errores de charmap en Windows si hay emojis
    print(f"Response Body: {response.text.encode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
