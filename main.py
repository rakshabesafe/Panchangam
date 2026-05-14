from fastapi import FastAPI
from pydantic import BaseModel
import datetime
import swisseph as swe
import pytz
from timezonefinder import TimezoneFinder

app = FastAPI(title="Panchang API")
tf = TimezoneFinder()


from typing import Optional

from fastapi import Query

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

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti"
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
    "Shakuni", "Chatushpada", "Naga", "Kintughna"
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

def get_tithi_index(sun_lon, moon_lon):
    diff = moon_lon - sun_lon
    if diff < 0:
        diff += 360
    return int(diff / 12)

def get_nakshatra_index(sun_lon, moon_lon):
    return int(moon_lon / (360 / 27.0))

def get_yoga_index(sun_lon, moon_lon):
    total = sun_lon + moon_lon
    if total >= 360:
        total -= 360
    return int(total / (360 / 27.0))

def get_karana_index(sun_lon, moon_lon):
    diff = moon_lon - sun_lon
    if diff < 0:
        diff += 360
    k_index = int(diff / 6)
    if k_index == 0:
        return 10
    elif k_index >= 57:
        return k_index - 50
    else:
        return (k_index - 1) % 7

def find_transitions(start_jd, end_jd, get_index_func, get_name_func):
    transitions = []
    step = 1.0 / 24.0

    curr_jd = start_jd
    sun_lon, moon_lon = get_positions(curr_jd)
    curr_index = get_index_func(sun_lon, moon_lon)

    transitions.append({"name": get_name_func(curr_index), "start_time": None})

    while curr_jd < end_jd:
        next_jd = curr_jd + step
        if next_jd > end_jd:
            next_jd = end_jd

        s_lon, m_lon = get_positions(next_jd)
        next_index = get_index_func(s_lon, m_lon)

        if next_index != curr_index:
            low, high = curr_jd, next_jd
            for _ in range(15):
                mid = (low + high) / 2
                s_mid, m_mid = get_positions(mid)
                mid_index = get_index_func(s_mid, m_mid)
                if mid_index == curr_index:
                    low = mid
                else:
                    high = mid

            trans_jd = high
            transitions[-1]["end_time"] = trans_jd
            transitions.append({"name": get_name_func(next_index), "start_time": trans_jd})
            curr_index = next_index

        curr_jd = next_jd

    transitions[-1]["end_time"] = None
    return transitions

def format_time(jd, tz):
    if jd is None:
        return None
    dt = swe.revjul(jd)
    # revjul returns (year, month, day, hour (float))
    year, month, day, hours = dt
    h = int(hours)
    m = int((hours - h) * 60)
    s = int(((hours - h) * 60 - m) * 60)

    # create utc datetime
    utc_dt = datetime.datetime(year, month, day, h, m, s, tzinfo=pytz.utc)
    return utc_dt.astimezone(tz).strftime("%I:%M %p")

def get_telugu_year(year):
    index = (year - 1987) % 60
    return TELUGU_YEARS[index]

def get_ritu(month_index):
    return RITU_NAMES[(month_index) // 2 % 6]

def get_exact_new_moon(target_jd):
    sun_lon, moon_lon = get_positions(target_jd)
    diff = moon_lon - sun_lon
    if diff < 0: diff += 360

    days_since = diff / 12.0
    approx_nm_jd = target_jd - days_since

    low = approx_nm_jd - 2.0
    high = approx_nm_jd + 2.0

    for _ in range(20):
        mid = (low + high) / 2
        sl, ml = get_positions(mid)
        df = ml - sl
        if df < 0: df += 360

        if df < 180:
            high = mid
        else:
            low = mid

    return high

def get_amanta_month_index(jd):
    nm_jd = get_exact_new_moon(jd)

    curr_jd = nm_jd
    sl, _ = get_positions(curr_jd)
    current_sign = int(sl / 30)

    for d in range(1, 35):
        sl_next, _ = get_positions(curr_jd + d)
        next_sign = int(sl_next / 30)
        if next_sign != current_sign:
            return next_sign

    return current_sign

def get_ayana(jd):
    sun_pos = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
    sun_lon_tropical = sun_pos[0][0]
    if 90 <= sun_lon_tropical < 270:
        return "Dakshinayana"
    else:
        return "Uttarayana"

def get_sunrise_sunset(jd, lat, lon):
    swe.set_topo(lon, lat, 0)
    res_rise = swe.rise_trans(jd - 0.5, swe.SUN, swe.CALC_RISE, (lon, lat, 0), 0.0, 0.0, swe.FLG_MOSEPH)
    sunrise_jd = res_rise[1][0]
    res_set = swe.rise_trans(sunrise_jd, swe.SUN, swe.CALC_SET, (lon, lat, 0), 0.0, 0.0, swe.FLG_MOSEPH)
    sunset_jd = res_set[1][0]
    return sunrise_jd, sunset_jd

def get_rahu_kalam(sunrise_jd, sunset_jd, weekday):
    day_duration = sunset_jd - sunrise_jd
    segment = day_duration / 8.0
    segments = [2, 7, 5, 6, 4, 3, 8] # Mon to Sun
    seg_idx = segments[weekday] - 1
    start = sunrise_jd + seg_idx * segment
    end = start + segment
    return start, end

@app.get("/panchang/detailed")
def get_detailed_panchang(
    lat: float = Query(12.8242912, description="Latitude of the location", examples=[17.3850]),
    lon: float = Query(77.6875076, description="Longitude of the location", examples=[78.4867]),
    date: Optional[datetime.date] = Query(None, description="Date for which to calculate Panchang in YYYY-MM-DD format. Defaults to today.", examples=["2025-05-14"]),
    month_type: str = Query("amanta", description="Type of the lunar month system to use. Valid options: 'amanta' or 'poornimanta'", examples=["amanta"])
):
    timezone_str = tf.timezone_at(lng=lon, lat=lat)
    if not timezone_str:
        timezone_str = "UTC"
    tz = pytz.timezone(timezone_str)

    if date is None:
        target_date = datetime.datetime.now(tz).date()
    else:
        target_date = date

    start_dt = tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
    start_utc = start_dt.astimezone(pytz.utc)

    end_dt = start_dt + datetime.timedelta(days=1)
    end_utc = end_dt.astimezone(pytz.utc)

    start_jd = swe.julday(start_utc.year, start_utc.month, start_utc.day, start_utc.hour + start_utc.minute/60.0 + start_utc.second/3600.0)
    end_jd = swe.julday(end_utc.year, end_utc.month, end_utc.day, end_utc.hour + end_utc.minute/60.0 + end_utc.second/3600.0)

    sr_jd, ss_jd = get_sunrise_sunset(start_jd + 0.5, lat, lon)
    sunrise = format_time(sr_jd, tz)
    sunset = format_time(ss_jd, tz)

    rk_start, rk_end = get_rahu_kalam(sr_jd, ss_jd, target_date.weekday())

    tithi_name_func = lambda idx: f"{'Shukla' if idx < 15 else 'Krishna'} {TITHI_NAMES[idx]}"
    tithis = find_transitions(start_jd, end_jd, get_tithi_index, tithi_name_func)

    nakshatras = find_transitions(start_jd, end_jd, get_nakshatra_index, lambda idx: NAKSHATRA_NAMES[idx])
    yogas = find_transitions(start_jd, end_jd, get_yoga_index, lambda idx: YOGA_NAMES[idx])
    karanas = find_transitions(start_jd, end_jd, get_karana_index, lambda idx: KARANA_NAMES[idx])

    # Month calculation
    amanta_month_index = get_amanta_month_index(sr_jd)

    # Paksha
    sun_lon, moon_lon = get_positions(sr_jd)
    tithi_index = get_tithi_index(sun_lon, moon_lon)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"

    if month_type.lower() == "poornimanta" and paksha == "Krishna":
        # Poornimanta month starts a fortnight earlier than Amanta during Krishna Paksha
        month_index = (amanta_month_index + 1) % 12
    else:
        month_index = amanta_month_index % 12

    month_name = TELUGU_MONTHS[month_index]
    ritu = get_ritu(amanta_month_index % 12)
    ayana = get_ayana(sr_jd)

    # Year
    year = target_date.year
    if target_date.month < 3 or (target_date.month == 3 and amanta_month_index >= 10):
        year -= 1
    elif target_date.month == 4 and amanta_month_index >= 10:
        year -= 1
    telugu_year = get_telugu_year(year)

    # Format transitions
    def format_transitions(trans_list):
        for item in trans_list:
            item["start_time"] = format_time(item["start_time"], tz)
            item["end_time"] = format_time(item["end_time"], tz)
        return trans_list

    return {
        "date": target_date.isoformat(),
        "month_type": month_type,
        "telugu_year": telugu_year,
        "telugu_month": month_name,
        "paksha": paksha,
        "ritu": ritu,
        "ayana": ayana,
        "sunrise": sunrise,
        "sunset": sunset,
        "rahu_kalam": f"{format_time(rk_start, tz)} - {format_time(rk_end, tz)}",
        "tithis": format_transitions(tithis),
        "nakshatras": format_transitions(nakshatras),
        "yogas": format_transitions(yogas),
        "karanas": format_transitions(karanas)
    }

@app.get("/panchang")
def get_panchang(
    lat: float = Query(12.8242912, description="Latitude of the location", examples=[17.3850]),
    lon: float = Query(77.6875076, description="Longitude of the location", examples=[78.4867])
):
    timezone_str = tf.timezone_at(lng=lon, lat=lat)
    if not timezone_str:
        timezone_str = "UTC"

    tz = pytz.timezone(timezone_str)
    now = datetime.datetime.now(tz)
    now_utc = now.astimezone(pytz.utc)

    jd = swe.julday(now_utc.year, now_utc.month, now_utc.day, now_utc.hour + now_utc.minute/60.0 + now_utc.second/3600.0)

    sr_jd, ss_jd = get_sunrise_sunset(jd, lat, lon)
    sun_lon_sr, moon_lon_sr = get_positions(sr_jd)
    tithi_at_sunrise = calculate_tithi(sun_lon_sr, moon_lon_sr)

    sun_lon, moon_lon = get_positions(jd)
    tithi = calculate_tithi(sun_lon, moon_lon)
    nakshatra = calculate_nakshatra(moon_lon)

    amanta_month_index = get_amanta_month_index(jd)
    month_name = TELUGU_MONTHS[amanta_month_index % 12]
    ritu = get_ritu(amanta_month_index % 12)

    year = now.year
    if now.month < 3 or (now.month == 3 and amanta_month_index >= 10):
        year -= 1
    elif now.month == 4 and amanta_month_index >= 10:
        year -= 1

    telugu_year = get_telugu_year(year)

    return {
        "tithi": tithi,
        "tithi_at_sunrise": tithi_at_sunrise,
        "nakshatra": nakshatra,
        "telugu_month": month_name,
        "ritu": ritu,
        "telugu_year": telugu_year
    }
