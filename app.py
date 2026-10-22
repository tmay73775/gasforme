import asyncio
import streamlit as st
from py_gasbuddy import GasBuddy

# Configures the web page title and icon
st.set_page_config(page_title="NW Ohio Gas Watcher", page_icon="⛽", layout="centered")

MY_FAVORITES = ["Sheetz", "Speedway", "BP"]

# Search terms that work directly with GasBuddy's location engine
CITIES = {
    "Findlay, OH": "Findlay, OH",
    "Lima, OH": "Lima, OH",
    "Toledo, OH": "Toledo, OH",
    "Dayton, OH": "Dayton, OH",
    "Columbus, OH": "Columbus, OH"
}

@st.cache_data(ttl=900)  
def fetch_gas_data(search_query):
    gb = GasBuddy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    favorite_matches = []
    all_other_stations = []
    
    try:
        # Search by city name text directly (e.g., "Findlay, OH")
        search_result = loop.run_until_complete(gb.location_search(search=search_query))
        stations = search_result.get("results", [])
        
        for s in stations:
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
            
            # Check if it matches a favorite brand
            is_fav = any(fav.lower() in name.lower() for fav in MY_FAVORITES)
            if is_fav:
                favorite_matches.append(station_info)
            else:
                all_other_stations.append(station_info)
    except Exception as e:
        st.error(f"Data lookup failed: {e}")
        
    loop.close()

    # Sort choices by cheapest price
    favorite_matches.sort(key=lambda x: x["price"])
    all_other_stations.sort(key=lambda x: x["price"])
    
    cheapest_competitor = all_other_stations[0] if all_other_stations else None

    return favorite_matches, cheapest_competitor, all_other_stations

# ==========================================
# WEBSITE GRAPHICS & LAYOUT
# ==========================================
st.title("⛽ NW Ohio Regional Gas Tracker")
st.write("Track regular gas prices across major nearby hubs.")

# Creates the drop-down menu at the top
selected_city = st.selectbox("🗺️ Select a City Region to Inspect:", list(CITIES.keys()))

st.divider()

# Runs the background scraper loop
with st.spinner(f"Scanning all pumps in {selected_city}..."):
    favs, wildcard, everyone = fetch_gas_data(selected_city)

# 1. Shows your preferred stations
st.subheader("📋 Preferred Brands (Sheetz / Speedway / BP)")
if favs:
    for f in favs:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{f['name']}**  \n*{f['address']}*")
        with col2:
            st.subheader(f"${f['price']:.2f}")
        st.divider()
else:
    st.info("No active Sheetz, Speedway, or BP stations returned in the immediate search results. Showing general local options below instead.")

# 2. Shows the Wildcard Alert if a competitor is cheaper
if wildcard:
    lowest_fav_price = favs[0]["price"] if favs else float("inf")
    
    if wildcard["price"] < lowest_fav_price:
        st.success("🔥 **Better Deal Alert!**")
        st.markdown(
            f"A nearby competitor is currently beating your preferred brands!  \n"
            f"👉 **{wildcard['name']}** ({wildcard['address']}) is currently **${wildcard['price']:.2f}/gal**."
        )
    else:
        st.info("✅ Your preferred brands currently hold the best deal in this area.")

# 3. Fallback View: Show the overall local leaderboard if favorites are empty
if not favs and everyone:
    st.subheader("🗺️ All Available Local Stations")
    for s in everyone[:5]:  # Show top 5 cheapest overall
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{s['name']}**  \n*{s['address']}*")
        with col2:
            st.markdown(f"**${s['price']:.2f}**")
        st.divider()
