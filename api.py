import requests
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем данные API из переменных окружения
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_TOKEN")
SERVER_ID = os.getenv("SERVER_ID")

# File path configuration
PLAYERS_JSON_PATH = "players.json"  # Path relative to server root
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory to store downloaded data

# Headers for API requests
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def download_file_from_server():
    """Download players.json file from the server using Pterodactyl API"""
    try:
        # Endpoint to download a file - using the correct format
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/files/contents"
        
        # Set the correct headers for file content download
        file_headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "text/plain"  # Important: use text/plain for file contents
        }
        
        # Add the file path as a query parameter
        params = {"file": PLAYERS_JSON_PATH}
        
        # Make the request
        response = requests.get(endpoint, headers=file_headers, params=params)
        
        # Check if request was successful
        if response.status_code == 200:
            # Check if response content is not empty
            if not response.text or response.text.isspace():
                print("Warning: Downloaded file is empty")
                return None
                
            fixed_filename = f"{OUTPUT_DIR}/latest_players.json"
            
            # Save to fixed location (overwrite)
            with open(fixed_filename, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            return response.text
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return None

def parse_player_data(json_data):
    """Parse the player data from JSON"""
    try:
        # If json_data is already a string, try to parse it
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
            
        # Check if data is a dictionary with a 'players' key
        if isinstance(data, dict) and 'players' in data:
            return data['players']
        # If data is already a list, return it directly
        elif isinstance(data, list):
            return data
        # If it's a string that couldn't be parsed as JSON, return a list with the string
        elif isinstance(json_data, str) and not json_data.startswith('{') and not json_data.startswith('['):
            return [json_data]
        else:
            print(f"Unexpected data format: {type(data)}")
            return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        # If we can't parse as JSON but have a string, return it as a single-item list
        if isinstance(json_data, str):
            return [json_data]
        return []
    except Exception as e:
        print(f"Error parsing player data: {str(e)}")
        return []

def add_player_to_whitelist(player_name):
    """Send command to add player to whitelist via Pterodactyl API"""
    try:
        # Endpoint for sending commands
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/command"
        
        # Command payload
        command_data = {
            "command": f"ce whitelist add {player_name}"
        }
        
        # Send the command
        response = requests.post(endpoint, headers=headers, json=command_data)
        
        if response.status_code == 204:  # Pterodactyl returns 204 on successful command execution
            return True
        else:
            print(f"Failed to add player to whitelist. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error adding player to whitelist: {str(e)}")
        return False

def download_cars_json():
    """Download cars.json file from the server using Pterodactyl API"""
    try:
        # Endpoint to download a file
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/files/contents"
        
        # Set the correct headers for file content download
        file_headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "text/plain"  # Important: use text/plain for file contents
        }
        
        # Add the file path as a query parameter
        params = {"file": "cars.json"}
        
        # Make the request
        response = requests.get(endpoint, headers=file_headers, params=params)
        
        # Check if request was successful
        if response.status_code == 200:
            # Check if response content is not empty
            if not response.text or response.text.isspace():
                print("Warning: Downloaded cars.json is empty")
                return {}
                
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                print("Warning: cars.json is not valid JSON, creating new file")
                return {}
        else:
            print(f"Failed to download cars.json. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            # If file doesn't exist, return empty dict to create it
            return {}
    
    except Exception as e:
        print(f"Error downloading cars.json: {str(e)}")
        return {}

def upload_cars_json(cars_data):
    """Upload modified cars.json file to the server using Pterodactyl API"""
    try:
        # Endpoint for uploading files
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/files/write"
        
        # Convert data to JSON string
        json_content = json.dumps(cars_data, indent=2)
        
        # Prepare the payload
        payload = {
            "file": "cars.json",
            "content": json_content
        }
        
        # Make the request
        response = requests.post(endpoint, headers=headers, json=payload)
        
        # Check if request was successful
        if response.status_code == 204:  # Pterodactyl returns 204 on successful file write
            print("Successfully updated cars.json on the server")
            return True
        else:
            print(f"Failed to upload cars.json. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"Error uploading cars.json: {str(e)}")
        return False

def add_car_to_player(player_name, car_name):
    try:
        # Endpoint for sending commands
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/command"
        
        # Command payload - format the command for the Lua script to handle
        command_data = {
            "command": f"mx addCar {player_name} {car_name}"
        }
        
        # Send the command
        response = requests.post(endpoint, headers=headers, json=command_data)
        
        if response.status_code == 204:  # Pterodactyl returns 204 on successful command execution
            print(f"Successfully sent command to add {car_name} to {player_name}")
            return True
        else:
            print(f"Failed to send add car command. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending add car command: {str(e)}")
        return False

def remove_car_from_player(player_name, car_name):
    """Remove a car from a player's collection by sending a console command
    
    Args:
        player_name (str): The name of the player
        car_name (str): The name of the car to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Endpoint for sending commands
        endpoint = f"{API_URL}api/client/servers/{SERVER_ID}/command"
        
        # Command payload - format the command for the Lua script to handle
        command_data = {
            "command": f"mx removeCar {player_name} {car_name}"
        }
        
        # Send the command
        response = requests.post(endpoint, headers=headers, json=command_data)
        
        if response.status_code == 204:  # Pterodactyl returns 204 on successful command execution
            print(f"Successfully sent command to remove {car_name} from {player_name}")
            return True
        else:
            print(f"Failed to send remove car command. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending remove car command: {str(e)}")
        return False


def main():
    """Main function to run the script"""
    # Download the file from server
    json_data = download_file_from_server()
    
    if json_data:
        # Parse and display the data
        player_data = parse_player_data(json_data)

if __name__ == "__main__":
    main()