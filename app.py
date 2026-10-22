import asyncio
import streamlit as st
from py_gasbuddy import GasBuddy

# Configures the web page title and icon
st.set_page_config(page_title="NW Ohio Gas Watcher", page_icon="⛽", layout="centered")

MY_FAVORITES = ["Sheetz", "Speedway", "BP"]

# The list of cities and their central ZIP codes
CITIES = {
    "Findlay (45840)": 45840,
    "Lima (45801)": 45801,
    "Toledo (43604)": 43604,
    "Dayton (45402)": 45402,
    "Columbus (43215)": 43215
}

# Caches the gas price data for 30 minutes so the page loads instantly
@st.cache_data(ttl=1800)  
def fetch_gas_data(zip_code):
    gb = GasBuddy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    search_result = loop.run_until_complete(gb.location_search(zipcode=zip_code))
    loop.close()
    
    stations = search_result.get("results", [])
    favorite_matches = []
    all_other_stations = []

    for s in stations:
        name = s.get("name", "Unknown Station")
        address = s.get("address", {}).get("line1", "No Address")
        fuels = s.get("fuels", [])
        
        regular_price = None
        for f in fuels:
            if f.get("fuel_type_id") == 1 or f.get("key") == "regular_gas":
                regular_price = f.get("price")
                break

        if regular_price is None or regular_price <= 0:
            continue

        station_info = {"name": name, "address": address, "price": regular_price}
        
        # Checks if the station name matches Sheetz, Speedway, or BP
        is_fav = any(fav.lower() in name.lower() for fav in MY_FAVORITES)
        if is_fav:
            favorite_matches.append(station_info)
        else:
            all_other_stations.append(station_info)

    # Sort choices so the cheapest is at the top
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
selected_city_name = st.selectbox("🗺️ Select a City to Inspect:", list(CITIES.keys()))
target_zip = CITIES[selected_city_name]

st.divider()

# Runs the background scraper loop
with st.spinner(f"Scanning pumps in {selected_city_name}..."):
    favs, wildcard = fetch_gas_data(target_zip)

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
    st.info("No active brand data found in this specific area right now.")

# 2. Shows the Wildcard Alert if a competitor is cheaper
if wildcard:
    lowest_fav_price = favs[0]["price"] if favs else float("inf")
    
    if wildcard["price"] < lowest_fav_price:
        st.success("🔥 **Better Deal Alert!**")
        st.markdown(
            f"A nearby competitor is currently beating your preferred brands in this city!  \n"
            f"👉 **{wildcard['name']}** ({wildcard['address']}) is currently **${wildcard['price']:.2f}/gal**."
        )
    else:
        st.info("✅ Your preferred brands currently hold the best deal in this local area.")
