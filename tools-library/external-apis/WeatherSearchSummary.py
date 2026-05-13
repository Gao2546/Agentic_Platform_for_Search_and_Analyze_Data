import argparse
import requests
import json
from datetime import datetime, timezone
from utils.udtp_data_manager import UDTPDataManager

# Helper to convert WMO codes from Open-Meteo into text descriptions
def get_weather_desc(code):
    mapping = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return mapping.get(code, "Unknown conditions")

parser = argparse.ArgumentParser(description='Fetch weather data and generate summary using Open-Meteo.')
# Required system arguments
parser.add_argument('--scope_id', type=str, required=True, help='Scope ID from scheduling system')
parser.add_argument('--schedule_id', type=str, required=True, help='Schedule ID from scheduling system')
parser.add_argument('--task_id', type=str, required=True, help='Task ID from scheduling system')
# Weather-specific arguments
parser.add_argument('--location', type=str, required=True, help='Location: city name or lat,lon coordinates')
parser.add_argument('--api_key', type=str, required=False, help='Ignored. Kept for Airflow compatibility.')
parser.add_argument('--units', type=str, default='metric', choices=['metric', 'imperial'], help='Temperature units: metric (Celsius) or imperial (Fahrenheit)')

args = parser.parse_args()

# Initialize UDTP Data Manager
manager = UDTPDataManager()

# Unit configurations
unit_label = '°C' if args.units == 'metric' else '°F'
temp_unit_param = 'celsius' if args.units == 'metric' else 'fahrenheit'
wind_unit_param = 'ms' if args.units == 'metric' else 'mph'

# Prepare base data structure
data_to_save = {
    'location': args.location,
    'units': args.units,
    'fetch_timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'status': 'pending'
}

try:
    # ---------------------------------------------------------
    # 1. GEOCODING STEP: Resolve Location to Lat/Lon
    # ---------------------------------------------------------
    lat, lon = None, None
    city_name = args.location
    country_code = ""

    # Check if the user passed lat,lon (e.g., "13.5834,100.8568")
    if ',' in args.location and any(char.isdigit() for char in args.location):
        try:
            parts = [p.strip() for p in args.location.split(',')]
            lat, lon = float(parts[0]), float(parts[1])
            location_display = f"Lat: {lat}, Lon: {lon}"
        except ValueError:
            pass

    # If it's a city name, use Open-Meteo's free Geocoding API
    if not lat or not lon:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={args.location}&count=1&format=json"
        geo_resp = requests.get(geo_url)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        if 'results' not in geo_data or not geo_data['results']:
            raise ValueError(f"Could not resolve coordinates for location: {args.location}")

        result = geo_data['results'][0]
        lat = result['latitude']
        lon = result['longitude']
        city_name = result['name']
        country_code = result.get('country_code', '')
        location_display = f"{city_name}, {country_code}"

    # ---------------------------------------------------------
    # 2. FETCH WEATHER: Open-Meteo API
    # ---------------------------------------------------------
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
        f"&temperature_unit={temp_unit_param}&wind_speed_unit={wind_unit_param}&timezone=auto"
    )
    
    resp = requests.get(weather_url)
    resp.raise_for_status()
    data = resp.json()

    # ---------------------------------------------------------
    # 3. PROCESS DATA
    # ---------------------------------------------------------
    current_data = data['current']
    current_temp = current_data['temperature_2m']
    feels_like = current_data['apparent_temperature']
    humidity = current_data['relative_humidity_2m']
    wind_speed = current_data['wind_speed_10m']
    conditions = get_weather_desc(current_data['weather_code'])

    # Process forecast data (Get the next 3 days)
    forecast_list = []
    daily_data = data['daily']
    for i in range(3):
        forecast_list.append({
            'date': daily_data['time'][i],
            'temp_min': daily_data['temperature_2m_min'][i],
            'temp_max': daily_data['temperature_2m_max'][i],
            'conditions': get_weather_desc(daily_data['weather_code'][i])
        })

    # Generate human-readable summary
    wind_unit_label = 'm/s' if args.units == 'metric' else 'mph'
    summary = f"Weather for {location_display}:\n"
    summary += f"Current: {current_temp}{unit_label}, {conditions}. Feels like {feels_like}{unit_label}. Humidity: {humidity}%, Wind: {wind_speed} {wind_unit_label}.\n"
    summary += "3-Day Forecast:\n"
    for day in forecast_list:
        summary += f"  {day['date']}: {day['temp_min']}-{day['temp_max']}{unit_label}, {day['conditions']}\n"

    # Update data structure with processed info
    data_to_save['status'] = 'success'
    data_to_save['current_weather'] = {
        'temp': current_temp,
        'feels_like': feels_like,
        'humidity': humidity,
        'conditions': conditions,
        'wind_speed': wind_speed
    }
    data_to_save['forecast'] = forecast_list
    data_to_save['summary'] = summary.strip()

    # Save data via UDTP
    saved_path = manager.save_data(
        data=data_to_save,
        stage='2_ETL',
        scope_id=args.scope_id,
        schedule_id=args.schedule_id,
        task_id=args.task_id,
        file_extension='json'
    )

    # Print success output
    print(f"✅ Weather data for {location_display} fetched and saved successfully via Open-Meteo.")
    print(f"Summary:\n{summary.strip()}")
    print(f"Saved to UDTP path: {saved_path}")

    # Output structured result for scheduling system
    output = {
        'status': 'success',
        'location': args.location,
        'weather_summary': summary.strip(),
        'saved_file_path': saved_path,
        'current_temp': current_temp,
        'conditions': conditions
    }
    print(json.dumps(output))

except requests.exceptions.RequestException as e:
    error_msg = f"Weather API request failed: {str(e)}"
    print(f"❌ {error_msg}")
    data_to_save['status'] = 'failure'
    data_to_save['error'] = error_msg
    output = {
        'status': 'failure',
        'location': args.location,
        'error_message': error_msg
    }
    print(json.dumps(output))
    exit(1)
except (KeyError, ValueError, IndexError) as e:
    error_msg = f"Data processing error: {str(e)}"
    print(f"❌ {error_msg}")
    output = {
        'status': 'failure',
        'location': args.location,
        'error_message': error_msg
    }
    print(json.dumps(output))
    exit(1)