import asyncio
import streamlit as st
from py_gasbuddy import GasBuddy

# Configures the web page title and icon
st.set_page_config(page_title="NW Ohio Gas Watcher", page_icon="⛽", layout="centered")

MY_FAVORITES = ["Sheetz", "Speedway", "BP"]

# Expanded regional mapping tracking multiple cluster ZIP codes per hub
CITIES = {
    "Findlay Area": [45840, 45839, 45814],
    "Lima Area": [45801, 45804, 45805],
    "Toledo Area": [43604, 43612, 43615],
    "Dayton Area": [45402, 45414, 45431],
    "Columbus Area": [43215, 43240, 43201]
}

# Caches the gas price data for 20 minutes
@st.cache_data(ttl=1200)  
def fetch_gas_data(zip_list):
    gb = GasBuddy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    all_stations = []
    seen_ids = set()
    
    # Scan all overlapping ZIP codes for the city cluster
    for zip_code in zip_list:
        try:
            search_result = loop.run_until_complete(gb.location_search(zipcode=zip_code))
            stations = search_result.get("results", [])
            for s in stations:
                s_id = s.get("id") or s.get("station_id")
                if s_id and s_id not in seen_ids:
                    seen_ids.add(s_id)
                    all_all_stations.append(s)
        except Exception:
            continue
            
    loop.close()
    
    favorite_matches = []
    all_other_stations = []

    for s in all_stations:
        name = s.get("name", "Unknown Station")
        address = s.get("address", {}).get("line1", "No Address")
        fuels = s.get("fuels", [])
        
        regular_price = None
        for f in fuels:
            if isinstance(f, dict):
                if f.get("fuel_type_id") == 1 or f.get("key") == "regular_gas":
                    regular_price = f.get("price")
                    break
            elif hasattr(f, "fuel_type_id"):
                if f.fuel_type_id == 1 or getattr(f, "key", "") == "regular_gas":
                    regular_price = getattr(f, "price", None)
                    break

        if regular_price is None or regular_price <= 0:
            continue

        station_info = {"name": name, "address": address, "price": regular_price}
        
        # Check if the station name matches Sheetz, Speedway, or BP
        is_fav = any(fav.lower() in name.lower() for fav in MY_FAVORITES)
        if is_fav:
            favorite_matches.append(station_info)
        else:
            all_other_stations.append(station_info)

    # Sort choices by cheapest price
    favorite_matches.sort(key=lambda x: x["price"])
    
    cheapest_competitor = None
    if all_other_stations:
        all_other_stations.sort(key=lambda x: x["price"])
        cheapest_competitor = all_other_stations[0]

    return favorite_matches, cheapest_competitor

# ==========================================
# WEBSITE GRAPHICS & LAYOUT
# ==========================================
st.title("⛽ NW Ohio Regional Gas Tracker")
st.write("Track regular gas prices across major nearby hubs.")

# Creates the drop-down menu at the top
selected_city_name = st.selectbox("🗺️ Select a City Region to Inspect:", list(CITIES.keys()))
target_zips = CITIES[selected_city_name]

st.divider()

# Runs the background scraper loop
with st.spinner(f"Scanning pumps in {selected_city_name}..."):
    favs, wildcard = fetch_gas_data(target_zips)

# 1. Shows your preferred stations
st.subheader("📋 Preferred Brands (Sheetz / Speedway / BP)")
if favs:
    for f in favs:
        col1, col2 = st.columns()
        with col1:
            st.markdown(f"**{f['name']}**  \n*{f['address']}*")
        with col2:
            st.subheader(f"${f['price']:.2f}")
        st.divider()
else:
    st.info("No active brand data found in this expanded area cluster right now.")

# 2. Shows the Wildcard Alert if a competitor is cheaper
if wildcard:
    lowest_fav_price = favs[0]["price"] if favs else float("inf")
    
    if wildcard["price"] < lowest_fav_price:
        st.success("🔥 **Better Deal Alert!**")
        st.markdown(
            f"A nearby competitor is currently beating your preferred brands in this area!  \n"
            f"👉 **{wildcard['name']}** ({wildcard['address']}) is currently **${wildcard['price']:.2f}/gal**."
        )
    else:
        st.info("✅ Your preferred brands currently hold the best deal in this local area.")
