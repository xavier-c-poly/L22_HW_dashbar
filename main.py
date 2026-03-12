import streamlit as st
import requests
from requests import Response
import pandas as pd
import numpy as np

# Weather api data
base_url: str = "https://api.openweathermap.org/data/2.5"
weather_url: str = "/weather"  # current weather for a given city or coordinates
forecast_url: str = "/forecast"  # 5 day / 3-hour forecast data
API_KEY: str = st.secrets["OPENWEATHER_API_KEY"]
np.random.seed(16)


@st.cache_data
def get_coords(
    city_name: str, state_code: str, country_code: str, api_key: str
) -> tuple:
    try:
        limit: int = 1
        geo_request_url: str = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},{state_code},{country_code}&limit={limit}&appid={api_key}"

        r: Response = requests.get(geo_request_url)
        if r.status_code == 200:
            data = r.json()[0]
            return data["lat"], data["lon"]
    except Exception:
        st.error("Could not obtain coordinates.")
    return (None, None)


@st.cache_data
def fetch_data(
    api_url: str,
    endpoint: str,
    lat: float,
    lon: float,
    api_key: str,
    is_fahrenheit: bool = True,
) -> dict:
    try:
        if is_fahrenheit:
            units: str = "imperial"
        else:
            units: str = "metric"

        request_url = (
            f"{api_url}{endpoint}?lat={lat}&lon={lon}&units={units}&appid={api_key}"
        )

        r: Response = requests.get(request_url)
        if r.status_code == 200:
            data = r.json()
            return data
    except Exception:
        st.error("Cannot fetch data.")

    return {}


def fetch_weather_data(
    lat: float, lon: float, api_key: str, is_fahrenheit: bool = True
) -> dict:
    global base_url
    global weather_url
    return fetch_data(base_url, weather_url, lat, lon, api_key, is_fahrenheit)


def fetch_random_weather_data(api_key: str, is_fahrenheit: bool = True) -> dict:
    global base_url
    global weather_url
    lat: float = np.random.randint(-900000, 900000) * 0.0001
    lon: float = np.random.randint(-900000, 900000) * 0.0001
    return fetch_data(base_url, weather_url, lat, lon, api_key, is_fahrenheit)


@st.cache_data
def fetch_forecast(
    lat: float, lon: float, api_key: str, is_fahrenheit: bool = True
) -> dict:
    global base_url
    global forecast_url
    return fetch_data(base_url, forecast_url, lat, lon, api_key, is_fahrenheit)
    # # The forecast endpoint provides the time-series data needed for the requirement
    # url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units={units}&appid={api_key}"
    # r = requests.get(url)
    # if r.status_code == 200:
    #     return r.json()
    # return {}


def extract_clean_weather_data(
    df: pd.DataFrame, city_name: str, is_fahrenheit: bool = True
) -> pd.DataFrame:
    df_pretty: pd.DataFrame = pd.DataFrame()

    if is_fahrenheit:
        temp_unit = "F"
        speed_unit = "m"
    else:
        temp_unit = "C"
        speed_unit = "k"

    try:
        temp = df["main.temp"].iloc[0]
        humidity = df["main.humidity"].iloc[0]
        wind = df["wind.speed"].iloc[0]
        desc = str(df["weather"][0][0]["description"]).title()

        clean_data = {
            "City": city_name,
            "Condition": desc,
            f"Temperature (°{temp_unit})": f"{temp}",
            "Humidity (%)": f"{humidity}",
            f"Wind Speed ({speed_unit}ph)": wind,
        }

        df_pretty = pd.DataFrame([clean_data]).T
        df_pretty.columns = ["Value"]
    except Exception:
        st.error("Something went wrong cleaning the data.")

    return df_pretty


def extract_clean_forecast_data(df_forecast: pd.DataFrame):
    # Convert to datetime and rename the temperature column to a more polished name
    df_forecast["dt_txt"] = pd.to_datetime(df_forecast["dt_txt"])
    df_forecast = df_forecast.rename(columns={"main.temp": "Temperature"})

    # Make sure temperature is numeric
    df_forecast["Temperature"] = pd.to_numeric(df_forecast["Temperature"])

    # Create clean dataframe
    chart_data = df_forecast[["dt_txt", "Temperature"]].set_index("dt_txt")

    return chart_data


# App Greetings
st.title("Weather App!")
st.subheader("Enter city, state, and country to find its LIVE weather!")
st.text("Please refer to the ISO-3166 standard when entering state/country names.")

# Inputs with some input sanitization
geo_city_input: str = st.text_input("City name:").strip().title()
geo_state_input: str = st.text_input("State name:").strip().upper()
geo_country_input: str = st.text_input("Country name:").strip().upper()

# Get coordinates for inputted location
geo_lat, geo_lon = get_coords(
    geo_city_input, geo_state_input, geo_country_input, API_KEY
)


if st.button("Get weather!"):
    if not geo_city_input or not geo_state_input or not geo_country_input:
        st.warning("Please enter all fields in first.")
    elif geo_lat is None:
        st.error("Could not find that location. Please check your spelling!")
    else:
        st.subheader(
            f"Weather for {geo_city_input} {geo_state_input}, {geo_country_input}:"
        )

        # Get weather info
        weather_result: dict = fetch_weather_data(geo_lat, geo_lon, API_KEY)
        df: pd.DataFrame = pd.json_normalize(weather_result)

        # Display current weather fancily
        st.metric("Current Temp", f"{df['main.temp'].iloc[0]}°F")

        # Clean weather info
        df_pretty: pd.DataFrame = extract_clean_weather_data(df, str(df["name"][0]))
        st.table(df_pretty)

        # Get 5-day forecast
        forecast_raw = fetch_forecast(geo_lat, geo_lon, API_KEY)
        if "list" in forecast_raw:
            df_forecast = pd.json_normalize(forecast_raw["list"])
            df_forecast_pretty = extract_clean_forecast_data(df_forecast)
            st.markdown("##### 5-Day Temperature Forecast")
            st.line_chart(df_forecast_pretty)
        else:
            st.error("Forecast data could not be retrieved.")


st.write("")
st.write("")
st.write("")
st.write("")
st.write("")


num_random_weathers: int = st.slider("Number of random weathers to pull", 1, 20, 3)

if st.button("Get random weather!"):
    generated: int = 0

    # Loop through until it has generated the specified random weathers
    while generated < num_random_weathers:
        # Get weather info
        weather_result: dict = fetch_random_weather_data(API_KEY)
        df: pd.DataFrame = pd.json_normalize(weather_result)

        # Ensure that only named locations are shown
        if df["name"][0] == "":
            continue

        st.subheader(
            f"Random Weather #{generated + 1} | {df['name'][0]}, {df['sys.country'][0]}"
        )

        # Display current weather fancily
        st.metric("Current Temp", f"{df['main.temp'].iloc[0]}°F")

        # Clean weather info
        df_pretty: pd.DataFrame = extract_clean_weather_data(df, str(df["name"][0]))
        st.table(df_pretty)

        # Get 5-day forecast
        random_lat: float = float(df["coord.lat"].iloc[0])
        random_lon: float = float(df["coord.lon"].iloc[0])
        forecast_raw = fetch_forecast(random_lat, random_lon, API_KEY)
        if "list" in forecast_raw:
            df_forecast = pd.json_normalize(forecast_raw["list"])
            df_forecast_pretty = extract_clean_forecast_data(df_forecast)
            st.markdown("##### 5-Day Temperature Forecast")
            st.line_chart(df_forecast_pretty)
        else:
            st.error("Forecast data could not be retrieved.")

        generated += 1
        st.divider()
