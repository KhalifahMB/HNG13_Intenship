import requests
import random
from decimal import Decimal
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import os
from django.conf import settings


class ExternalAPIError(Exception):
    pass


def fetch_countries_data():
    url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ExternalAPIError("Request to REST Countries API timed out")
    except requests.exceptions.RequestException as e:
        raise ExternalAPIError(f"Could not fetch data from REST Countries API: {str(e)}")


def fetch_exchange_rates():
    primary = "https://open.er-api.com/v6/latest/USD"
    fallback = "https://api.exchangerate.host/latest?base=USD"

    # Try primary endpoint first, then fallback. If both fail return a small static map
    try:
        response = requests.get(primary, timeout=10)
        response.raise_for_status()
        data = response.json()
        rates = data.get('rates', {})
        if rates:
            return rates
    except requests.exceptions.RequestException:
        try:
            response = requests.get(fallback, timeout=10)
            response.raise_for_status()
            data = response.json()
            rates = data.get('rates', {})
            if rates:
                return rates
        except requests.exceptions.RequestException:
            # last resort: local fallback rates for common currencies (useful for offline tests)
            return {
                'USD': 1.0,
                'NGN': 1600.0,
                'GBP': 0.75,
                'EUR': 0.9,
            }


def calculate_estimated_gdp(population, exchange_rate):
    if population is None or exchange_rate is None:
        return None

    try:
        population_f = float(population)
        exchange_f = float(exchange_rate)
        if exchange_f == 0:
            return None

        random_multiplier = float(random.uniform(1000, 2000))
        estimated_gdp = (population_f * random_multiplier) / exchange_f
        return round(float(estimated_gdp), 2)
    except Exception:
        return None


def extract_currency_code(currencies):
    if not currencies or len(currencies) == 0:
        return None

    first_currency = currencies[0]
    return first_currency.get('code', None)


def generate_summary_image(total_countries, top_5_countries, timestamp):
    # Ensure cache directory exists
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # Image dimensions
    width = 800
    height = 600
    background_color = (255, 255, 255)
    text_color = (0, 0, 0)
    header_color = (41, 128, 185)

    # Create image
    image = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(image)

    # Try to use a nice font, fall back to default if not available
    try:
        font_path = os.path.join(settings.BASE_DIR, 'countries_api/static/fonts/arial.ttf')
        title_font = ImageFont.truetype(font_path, 32)
        header_font = ImageFont.truetype(font_path, 24)
        text_font = ImageFont.truetype(font_path, 18)
        small_font = ImageFont.truetype(font_path, 14)
    except IOError:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw title
    title = "Country Currency & Exchange Summary"
    draw.text((50, 30), title, fill=header_color, font=title_font)

    # Draw total countries
    y_position = 100
    draw.text((50, y_position), f"Total Countries: {total_countries}", fill=text_color, font=header_font)

    # Draw last updated
    y_position += 30
    draw.text((50, y_position), f"Last Updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}", fill=text_color, font=small_font)

    # Draw top 5 countries header
    y_position += 40
    draw.text((50, y_position), "Top 5 Countries by Estimated GDP:", fill=header_color, font=header_font)

    # Draw top 5 countries
    y_position += 40
    for idx, country in enumerate(top_5_countries, 1):
        country_name = country.get('name', 'N/A')
        estimated_gdp = country.get('estimated_gdp', 0)

        if estimated_gdp:
            gdp_formatted = f"${estimated_gdp:,.2f}"
        else:
            gdp_formatted = "N/A"

        text = f"{idx}. {country_name}: {gdp_formatted}"
        draw.text((70, y_position), text, fill=text_color, font=text_font)
        y_position += 35

    # Draw timestamp
    y_position += 40
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if timestamp else "N/A"
    draw.text((50, y_position), f"Last Refreshed: {timestamp_str}", fill=text_color, font=text_font)

    # Save image
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    image_path = os.path.join(cache_dir, 'summary.png')
    image.save(image_path, 'PNG')

    return image_path


def get_summary_image_path():
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    image_path = os.path.join(cache_dir, 'summary.png')

    if os.path.exists(image_path):
        return image_path

    return None
