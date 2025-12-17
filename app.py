import os
import requests
import json
import re
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from cities import FAMOUS_CITIES

# Load environment variables from .env file
load_dotenv(override=True)

app = Flask(__name__)

# Load Gemini API key
GEMINI_API_KEY1 = os.getenv("GEMINI_API_KEY1")

# -------------------------------
# Function to call Gemini API
# -------------------------------
def get_plan_from_llm(destination, days, people, interests, age_group, budget):
    """Sends a detailed travel prompt to Gemini and returns a structured JSON plan."""
    if not GEMINI_API_KEY1:
        return {"error": "API Key is not configured. Please check your .env file for GEMINI_API_KEY1."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY1}"

    prompt = f"""
    You are an expert travel planner. Generate a practical and creative day-by-day itinerary for the following trip:

    Destination: {destination}
    Duration: {days} days
    Travelers: {people} people
    Age Group: {age_group}
    Interests: {interests}
    Budget Style: {budget}

    Respond ONLY in clean JSON format with this structure:

    {{
      "plan": [
        {{
          "day": 1,
          "activities": "Short list of places or things to do",
          "description": "Detailed plan with timing and meals",
          "estimated_cost": "₹3500"
        }},
        ...
      ]
    }}
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        api_response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        api_response_text = api_response_text.strip().replace("json", "").replace("```", "")
        return json.loads(api_response_text)

    except Exception as e:
        print(f"LLM Error: {e}")
        return {"error": "Failed to generate a valid plan. Please try again."}

# -------------------------------
# ROUTES
# -------------------------------
@app.route('/')
def home():
    return render_template('home.html')   # landing page

@app.route('/planner', methods=['GET', 'POST'])
def planner():
    plan_data = None
    destination_name = ""
    if request.method == "POST":
        destination_name = request.form.get("destination")
        days = int(request.form.get("duration", 1))
        people = int(request.form.get("people", 1))
        age_group = request.form.get("age_group")
        interests = request.form.get("interests")
        budget = request.form.get("budget")

        plan_data = get_plan_from_llm(destination_name, days, people, interests, age_group, budget)

        if plan_data and 'plan' in plan_data:
            grand_total = 0
            for day in plan_data['plan']:
                cost_string = day.get("estimated_cost", "0")
                cost_numbers = re.findall(r'\d+', cost_string.replace(',', ''))
                if cost_numbers:
                    grand_total += int(cost_numbers[0])
            plan_data['grand_total'] = f"₹{grand_total:,}"

    return render_template("index.html", plan_data=plan_data, destination=destination_name)

@app.route('/get-cities', methods=['GET'])
def get_cities():
    """API endpoint to get city suggestions based on search query."""
    query = request.args.get('query', '').lower()
    if not query or len(query) < 1:
        return jsonify([])
    
    suggestions = [city for city in FAMOUS_CITIES if city.lower().startswith(query)]
    return jsonify(suggestions[:10])  # Return top 10 matches

# Route for Nearby Restaurants
@app.route('/restaurants')
def nearby_restaurants():
    restaurants = [
        {"name": "The Spice House", "location": "123 Main St", "directions": "https://maps.google.com/?q=123+Main+St"},
        {"name": "Ocean Breeze Cafe", "location": "456 Ocean Ave", "directions": "https://maps.google.com/?q=456+Ocean+Ave"},
        {"name": "Taj Express", "location": "789 Indian St", "directions": "https://maps.google.com/?q=789+Indian+St"},
        {"name": "Pizza Palace", "location": "321 Pizza Lane", "directions": "https://maps.google.com/?q=321+Pizza+Lane"}
    ]
    return render_template('restaurants.html', places=restaurants)

# Route for Nearby Hotels
@app.route('/hotels')
def nearby_hotels():
    hotels = [
        {"name": "Grand Plaza Hotel", "location": "789 Plaza Blvd", "directions": "https://maps.google.com/?q=789+Plaza+Blvd"},
        {"name": "Cozy Inn", "location": "101 Cozy Ln", "directions": "https://maps.google.com/?q=101+Cozy+Ln"},
        {"name": "Luxury Resort", "location": "456 Resort Way", "directions": "https://maps.google.com/?q=456+Resort+Way"},
        {"name": "Budget Stay Hotel", "location": "555 Economy St", "directions": "https://maps.google.com/?q=555+Economy+St"}
    ]
    return render_template('hotels.html', places=hotels)

# Route for Nearby Shopping
@app.route('/shopping')
def nearby_shopping():
    shopping_places = [
        {"name": "Mall of the City", "location": "202 Market St", "directions": "https://maps.google.com/?q=202+Market+St"},
        {"name": "Boutique Lane", "location": "303 Fashion Ave", "directions": "https://maps.google.com/?q=303+Fashion+Ave"},
        {"name": "Central Shopping Complex", "location": "414 Shopping Blvd", "directions": "https://maps.google.com/?q=414+Shopping+Blvd"},
        {"name": "Retail Paradise", "location": "525 Store Road", "directions": "https://maps.google.com/?q=525+Store+Road"}
    ]
    return render_template('shopping.html', places=shopping_places)

# Route to get nearby places based on location
@app.route('/get-nearby-places', methods=['POST'])
def get_nearby_places():
    """Get nearby places based on user's current location using Overpass API."""
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    place_type = data.get('type')  # 'restaurants', 'hotels', or 'shopping'
    
    # Define search queries for each place type
    overpass_queries = {
        'restaurants': f'[out:json][timeout:5];(node["amenity"="restaurant"](around:1500,{latitude},{longitude});way["amenity"="restaurant"](around:1500,{latitude},{longitude}););out center 5;',
        'hotels': f'[out:json][timeout:5];(node["tourism"="hotel"](around:1500,{latitude},{longitude});way["tourism"="hotel"](around:1500,{latitude},{longitude}););out center 5;',
        'shopping': f'[out:json][timeout:5];(node["shop"](around:1500,{latitude},{longitude});way["shop"](around:1500,{latitude},{longitude}););out center 5;'
    }
    
    try:
        # Build the Overpass query
        query = overpass_queries.get(place_type, overpass_queries['restaurants'])
        
        # Call Overpass API with shorter timeout
        overpass_url = "http://overpass-api.de/api/interpreter"
        response = requests.post(overpass_url, data=query, timeout=8)
        response.raise_for_status()
        
        places_data = response.json()
        nearby_places = []
        
        # Parse the response and extract places
        if 'elements' in places_data:
            for element in places_data['elements'][:8]:  # Limit to 8 results
                place_name = "Unknown Place"
                place_lat = latitude
                place_lon = longitude
                
                # Extract name
                if 'tags' in element and 'name' in element['tags']:
                    place_name = element['tags']['name']
                
                # Extract coordinates
                if 'lat' in element and 'lon' in element:
                    place_lat = element['lat']
                    place_lon = element['lon']
                elif 'center' in element:
                    place_lat = element['center']['lat']
                    place_lon = element['center']['lon']
                
                nearby_places.append({
                    'name': place_name,
                    'location': f"{place_lat:.4f}, {place_lon:.4f}",
                    'directions': f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}&zoom=17"
                })
        
        # If no results found, return helpful message
        if not nearby_places:
            nearby_places = [{
                'name': f'No {place_type} found in this area',
                'location': f'{latitude:.4f}, {longitude:.4f}',
                'directions': f'https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15'
            }]
        
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'place_type': place_type,
            'places': nearby_places
        })
    
    except requests.Timeout:
        print(f"Timeout: Overpass API took too long to respond")
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'place_type': place_type,
            'places': [{
                'name': 'Request timeout - API is slow',
                'location': f'{latitude:.4f}, {longitude:.4f}',
                'directions': f'https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15'
            }]
        }), 504
    
    except Exception as e:
        print(f"Error fetching nearby places: {e}")
        return jsonify({
            'latitude': latitude,
            'longitude': longitude,
            'place_type': place_type,
            'places': [{
                'name': f'Error loading {place_type}',
                'location': f'{latitude:.4f}, {longitude:.4f}',
                'directions': f'https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15'
            }]
        }), 500

# Route for About Page
@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(debug=True, port=5002, use_reloader=False)
