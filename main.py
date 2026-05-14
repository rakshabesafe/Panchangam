from fastapi import FastAPI
from pydantic import BaseModel
import datetime
import swisseph as swe
import pytz
from timezonefinder import TimezoneFinder

app = FastAPI(title="Panchang API")
tf = TimezoneFinder()


class Location(BaseModel):
    lat: float
    lon: float


# Set Lahiri Ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

TITHI_NAMES = [
    "Prathama", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Prathama", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"
]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

TELUGU_MONTHS = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwayuja", "Karthika", "Margashira", "Pushya", "Magha", "Phalguna"
]

RITU_NAMES = [
    "Vasantha", "Greeshma", "Varsha", "Sharad", "Hemanta", "Shishira"
]

TELUGU_YEARS = [
    "Prabhava", "Vibhava", "Shukla", "Pramodoota", "Prajotapatti", "Aangirasa", "Shrimukha", "Bhaava", "Yuva", "Dhaatu",
    "Eeshwara", "Bahudhanya", "Pramadi", "Vikrama", "Vrusha", "Chitrabhanu", "Svabhanu", "Taarana", "Paarthiva", "Vyaya",
    "Sarvajit", "Sarvadhari", "Virodhi", "Vikruti", "Khara", "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukhi",
    "Hevilambi", "Vilambi", "Vikari", "Sharvari", "Plava", "Shubhakrit", "Shobhakrit", "Krodhi", "Vishvaavasu", "Parabhava",
    "Plavanga", "Keelaka", "Saumya", "Sadharana", "Virodhikrut", "Paridhavi", "Pramaadee", "Aananda", "Rakshasa", "Nala",
    "Pingala", "Kalayukti", "Siddharthi", "Raudri", "Durmati", "Dundubhi", "Rudhirodgaari", "Raktaakshi", "Krodhana", "Akshaya"
]

def get_positions(jd):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    # Using FLG_MOSEPH as fallback since SWIEPH files might not be available in serverless environments
    sun_pos = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
    moon_pos = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
    return sun_pos[0][0], moon_pos[0][0]

def calculate_tithi(sun_lon, moon_lon):
    diff = moon_lon - sun_lon
    if diff < 0:
        diff += 360
    tithi_index = int(diff / 12)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    return f"{paksha} {TITHI_NAMES[tithi_index]}"

def calculate_nakshatra(moon_lon):
    nakshatra_index = int(moon_lon / (360 / 27.0))
    return NAKSHATRA_NAMES[nakshatra_index]

def get_telugu_year(year):
    index = (year - 1987) % 60
    return TELUGU_YEARS[index]

def get_ritu(month_index):
    return RITU_NAMES[(month_index) // 2 % 6]

@app.post("/panchang")
def get_panchang(location: Location):
    timezone_str = tf.timezone_at(lng=location.lon, lat=location.lat)
    if not timezone_str:
        timezone_str = "UTC"

    tz = pytz.timezone(timezone_str)
    now = datetime.datetime.now(tz)
    now_utc = now.astimezone(pytz.utc)

    jd = swe.julday(now_utc.year, now_utc.month, now_utc.day, now_utc.hour + now_utc.minute/60.0 + now_utc.second/3600.0)

    sun_lon, moon_lon = get_positions(jd)

    tithi = calculate_tithi(sun_lon, moon_lon)
    nakshatra = calculate_nakshatra(moon_lon)

    diff = moon_lon - sun_lon
    if diff < 0:
        diff += 360

    days_since_new_moon = diff / 12.0
    jd_new_moon = jd - days_since_new_moon

    jd_full_moon = jd_new_moon + 14.76
    sun_lon_mid_month, _ = get_positions(jd_full_moon)

    month_index = int(sun_lon_mid_month / 30)
    month_name = TELUGU_MONTHS[month_index % 12]
    ritu = get_ritu(month_index % 12)

    year = now.year
    if now.month < 3 or (now.month == 3 and month_index >= 10):
        year -= 1
    elif now.month == 4 and month_index >= 10:
        year -= 1

    telugu_year = get_telugu_year(year)

    return {
        "tithi": tithi,
        "nakshatra": nakshatra,
        "telugu_month": month_name,
        "ritu": ritu,
        "telugu_year": telugu_year
    }
