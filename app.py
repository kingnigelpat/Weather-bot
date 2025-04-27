from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import re
import os

app = Flask(__name__)

# Note: Hardcoding API key is insecure. Use environment variables in production, e.g., os.getenv('WEATHER_API_KEY')
API_KEY = 'bbaebd02555b4df19ba54725251904'

@app.route('/')
def index():
    return render_template('index.html')

def get_weather():
    # Corrected coordinates for Oghara, Nigeria: 5.5867,6.1002
    weather_url = f"https://api.weatherapi.com/v1/current.json?key={API_KEY}&q=5.5867,6.1002"
    try:
        response = requests.get(weather_url)
        weather_data = response.json()

        if "error" in weather_data:
            return "Couldn't fetch weather. Please try again later."
        else:
            temp = weather_data["current"]["temp_c"]
            condition = weather_data["current"]["condition"]["text"]
            humidity = weather_data["current"]["humidity"]
            wind = weather_data["current"]["wind_kph"]

            reply = (
                f"🌤️ Current Weather in Oghara:\n"
                f"Temperature: {temp}°C\n"
                f"Condition: {condition}\n"
                f"Humidity: {humidity}%\n"
                f"Wind Speed: {wind} kph"
            )
            return reply
    except Exception as e:
        print("Weather fetch error:", e)
        return "Error fetching weather data."

def get_forecast(forecast_day=0):
    # Corrected coordinates for Oghara, Nigeria: 5.5867,6.1002
    # days=forecast_day+1 to ensure we get data for the requested day (0=today, 1=tomorrow)
    forecast_url = f"https://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q=5.5867,6.1002&days={forecast_day+1}&aqi=no&alerts=no"
    try:
        response = requests.get(forecast_url)
        data = response.json()
        if "error" in data:
            return None
        return data
    except Exception as e:
        print("Forecast fetch error:", e)
        return None

def get_day_weather(forecast_day=0):
    forecast_data = get_forecast(forecast_day)
    if not forecast_data:
        return "I couldn't get the forecast data. Here's the current weather:\n\n" + get_weather()

    day_str = "today" if forecast_day == 0 else "tomorrow"
    forecast = forecast_data['forecast']['forecastday'][forecast_day]
    hourly_data = forecast['hour']

    # Calculate average temperature and most common condition
    temps = [hour['temp_c'] for hour in hourly_data]
    conditions = [hour['condition']['text'] for hour in hourly_data]
    rain_chances = [hour['chance_of_rain'] for hour in hourly_data]
    avg_temp = round(sum(temps) / len(temps), 1)
    max_rain_chance = max(rain_chances)
    most_common_condition = max(set(conditions), key=conditions.count)

    return (
        f"🌤️ Weather forecast for {day_str} in Oghara:\n"
        f"Average Temperature: {avg_temp}°C\n"
        f"Main Condition: {most_common_condition}\n"
        f"Max Chance of Rain: {max_rain_chance}%"
    )

def get_weather_at_time(time_query, forecast_day=0):
    forecast_data = get_forecast(forecast_day)
    if not forecast_data:
        return "I couldn't check the weather forecast. Here's the current weather:\n\n" + get_weather()

    time_keywords = {
        "morning": [6, 7, 8, 9, 10, 11],
        "afternoon": [12, 13, 14, 15, 16, 17],
        "evening": [18, 19, 20, 21],
        "night": [22, 23, 0, 1, 2, 3, 4, 5],
        "noon": [12],
        "midnight": [0]
    }

    specific_time = None
    # Updated regex to handle "9 o'clock pm" by including optional o'clock
    am_pm_match = re.search(r'(\d+)\s*(?:o[\'"]?clock)?\s*(am|pm)', time_query.lower())
    hour_match = re.search(r'(\d+)\s*o[\'"]?clock', time_query.lower())

    if am_pm_match:
        hour = int(am_pm_match.group(1))
        am_pm = am_pm_match.group(2)
        if am_pm == "pm" and hour < 12:
            hour += 12
        elif am_pm == "am" and hour == 12:
            hour = 0
        specific_time = [hour]
    elif hour_match:
        hour = int(hour_match.group(1))
        if "night" in time_query.lower() and hour < 12:
            hour += 12
        specific_time = [hour]
    else:
        for period, hours in time_keywords.items():
            if period in time_query.lower():
                specific_time = hours
                break

    if not specific_time:
        return "I'm not sure what time you're asking about. Here's the current weather:\n\n" + get_weather()

    # Access the correct forecast day (0 for today, 1 for tomorrow)
    hourly_forecast = forecast_data['forecast']['forecastday'][forecast_day]['hour']
    weather_reports = []

    for hour_data in hourly_forecast:
        hour_time = datetime.fromisoformat(hour_data['time'].replace('Z', '+00:00'))
        if hour_time.hour in specific_time:
            hour_12 = hour_time.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "AM" if hour_time.hour < 12 else "PM"
            weather_reports.append({
                'time': f"{hour_12} {am_pm}",
                'temp': hour_data['temp_c'],
                'condition': hour_data['condition']['text'],
                'chance_of_rain': hour_data.get('chance_of_rain', 0),
                'wind': hour_data['wind_kph']
            })

    if not weather_reports and isinstance(specific_time, list) and len(specific_time) == 1:
        for hour_data in hourly_forecast:
            hour_time = datetime.fromisoformat(hour_data['time'].replace('Z', '+00:00'))
            if hour_time.hour == specific_time[0]:
                hour_12 = hour_time.hour % 12
                if hour_12 == 0:
                    hour_12 = 12
                am_pm = "AM" if hour_time.hour < 12 else "PM"
                weather_reports.append({
                    'time': f"{hour_12} {am_pm}",
                    'temp': hour_data['temp_c'],
                    'condition': hour_data['condition']['text'],
                    'chance_of_rain': hour_data.get('chance_of_rain', 0),
                    'wind': hour_data['wind_kph']
                })

    if weather_reports:
        if len(weather_reports) == 1:
            report = weather_reports[0]
            day_str = "today" if forecast_day == 0 else "tomorrow"
            return (
                f"🌤️ Weather at {report['time']} {day_str} in Oghara:\n"
                f"Temperature: {report['temp']}°C\n"
                f"Condition: {report['condition']}\n"
                f"Chance of Rain: {report['chance_of_rain']}%\n"
                f"Wind Speed: {report['wind']} kph"
            )
        else:
            day_str = "today" if forecast_day == 0 else "tomorrow"
            response = f"🌤️ Weather forecast for the specified time {day_str} in Oghara:\n\n"
            for report in weather_reports:
                response += (
                    f"● {report['time']}:\n"
                    f"  Temperature: {report['temp']}°C\n"
                    f"  Condition: {report['condition']}\n"
                    f"  Chance of Rain: {report['chance_of_rain']}%\n"
                    f"  Wind Speed: {report['wind']} kph\n\n"
                )
            return response
    else:
        return "I couldn't find weather data for that specific time. Here's the current weather:\n\n" + get_weather()

def will_it_rain_on_day(forecast_day=0):
    forecast_data = get_forecast(forecast_day)
    if not forecast_data:
        return "I couldn't get the forecast data. Here's the current weather:\n\n" + get_weather()
    forecast = forecast_data['forecast']['forecastday'][forecast_day]
    will_rain = any(hour['chance_of_rain'] > 30 for hour in forecast['hour'])
    day_str = "today" if forecast_day == 0 else "tomorrow"
    if will_rain:
        return f"Yes, it looks like there's a chance of rain {day_str} 🌧️"
    else:
        return f"No significant rain expected {day_str} 🌤️"

def when_will_rain_fall_on_day(forecast_day=0):
    forecast_data = get_forecast(forecast_day)
    if not forecast_data:
        return "I couldn't get the forecast data. Here's the current weather:\n\n" + get_weather()
    rain_times = []
    for hour_data in forecast_data['forecast']['forecastday'][forecast_day]['hour']:
        if hour_data['chance_of_rain'] > 50:
            hour_time = datetime.fromisoformat(hour_data['time'].replace('Z', '+00:00'))
            hour_12 = hour_time.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "AM" if hour_time.hour < 12 else "PM"
            rain_times.append({
                'time': f"{hour_12} {am_pm}",
                'chance': hour_data['chance_of_rain']
            })
    day_str = "today" if forecast_day == 0 else "tomorrow"
    if rain_times:
        response = f"Rain is likely at the following times {day_str} 🌧️:\n"
        for rain in rain_times:
            response += f"● {rain['time']}: {rain['chance']}% chance\n"
        return response
    return f"No rain expected {day_str} based on the current forecast 🌤️"

def get_forecast_day(user_input):
    """Determine if the user is asking for today or tomorrow."""
    user_input = user_input.lower()
    if "tomorrow" in user_input or "tmrw" in user_input:
        return 1
    return 0

def process_user_input(user_input):
    user_input = user_input.lower()
    forecast_day = get_forecast_day(user_input)

    if "check weather" in user_input or "weather" in user_input:
        time_indicators = ["at", "in the", "during", "for", "tonight", "this morning",
                          "this afternoon", "this evening", "morning", "afternoon",
                          "evening", "night", "noon", "midnight", "o'clock", "am", "pm"]
        # Handle general weather queries for today or tomorrow
        if "weather tomorrow" in user_input or user_input.strip() == "tomorrow" or user_input.strip() == "weather":
            return get_day_weather(forecast_day)
        for indicator in time_indicators:
            if indicator in user_input:
                return get_weather_at_time(user_input, forecast_day)
        return get_weather()
    elif "would it rain" in user_input or "rain today" in user_input or "will it rain" in user_input:
        return will_it_rain_on_day(forecast_day)
    elif "when will rain fall" in user_input or "when will it rain" in user_input:
        return when_will_rain_fall_on_day(forecast_day)
    else:
        return "I'm not sure how to reply to that yet. But I'll learn it soon!"

@app.route('/get', methods=['POST'])
def chat():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400
    user_input = data.get("user_input", "")
    if not user_input:
        return jsonify({"error": "Missing 'user_input' in request"}), 400
    bot_response = process_user_input(user_input)
    return jsonify({"bot_response": bot_response})

if __name__ == '__main__':
    app.run(debug=True)