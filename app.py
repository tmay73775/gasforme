import asyncio
import streamlit as st
from py_gasbuddy import GasBuddy

# ==========================================
# APP CONFIGURATION
# ==========================================
st.set_page_config(page_title="Findlay Gas Watcher", page_icon="⛽", layout="centered")

ZIP_CODE = 45840
MY_FAVORITES = ["Sheetz", "Speedway", "BP"]

@st.cache_data(ttl=3600)  # Caches data for 1 hour so it loads instantly for visitors
def fetch_gas_data():
    gb = GasBuddy()
    # Run the async loop inside the cached function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    search_result = loop.run_until_complete(gb.location_search(zipcode=ZIP_CODE))
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
        
        is_fav = any(fav.lower() in name.lower() for fav in MY_FAVORITES)
        if is_fav:
            favorite_matches.append(station_info)
        else:
            all_other_stations.append(station_info)

    favorite_matches.sort(key=lambda x: x["price"])
    
    cheapest_competitor = None
    if all_other_stations:
        all_other_stations.sort(key=lambda x: x["price"])
        cheapest_competitor = all_other_stations[0]

    return favorite_matches, cheapest_competitor

# ==========================================
# WEB INTERFACE LAYOUT
# ==========================================
st.title("⛽ Findlay Gas Price Watchdog")
st.write(f"Showing live regular gas prices for ZIP code **{ZIP_CODE}**.")

# Fetch data
with st.spinner("Scanning local gas pumps..."):
    favs, wildcard = fetch_gas_data()

# 1. Display Favorite Stations
st.subheader("📋 Your Go-To Stations")
if favs:
    for f in favs:
        # Displays each station in a neat layout grid
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{f['name']}**  \n*{f['address']}*")
        with col2:
            st.subheader(f"${f['price']:.2f}")
        st.divider()
else:
    st.info("No active price updates found for Sheetz, Speedway, or BP right now.")

# 2. Display the Wildcard Deal Tracker
if wildcard:
    lowest_fav_price = favs[0]["price"] if favs else float("inf")
    
    if wildcard["price"] < lowest_fav_price:
        st.success("🔥 **Better Deal Alert!**")
        st.markdown(
            f"A nearby competitor is currently beating your preferred stations!  \n"
            f"👉 **{wildcard['name']}** ({wildcard['address']}) is currently **${wildcard['price']:.2f}/gal**."
        )
    else:
        st.info("✅ Your preferred stations currently have the best deal in the immediate area.")
