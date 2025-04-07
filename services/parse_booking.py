import json

def parse_flight(flight_offers):
    if isinstance(flight_offers, str):
        return json.dumps({"error": flight_offers})  # Return as JSON string

    parsed_results = []
    for offer in flight_offers:
        flight_id = offer.get("id", "N/A")
        price_info = offer.get("price", {})
        total_price = price_info.get("total", "N/A")
        currency = price_info.get("currency", "N/A")
        itineraries = offer.get("itineraries", [])

        itinerary_details = []
        for itinerary in itineraries:
            duration = itinerary.get("duration", "N/A")
            segments = itinerary.get("segments", [])
            segments_details = []
            for segment in segments:
                dep = segment.get("departure", {})
                arr = segment.get("arrival", {})
                segments_details.append({
                    "departure_code": dep.get("iataCode", "N/A"),
                    "departure_time": dep.get("at", "N/A"),
                    "arrival_code": arr.get("iataCode", "N/A"),
                    "arrival_time": arr.get("at", "N/A"),
                    "carrier": segment.get("carrierCode", "N/A"),
                    "flight_number": segment.get("number", "N/A")
                })
            itinerary_details.append({"duration": duration, "segments": segments_details})

        parsed_results.append({
            "flight_id": flight_id,
            "price": {"total": total_price, "currency": currency},
            "itineraries": itinerary_details
        })

    return json.dumps(parsed_results, indent=2)


def parse_hotel(hotel_offers):
    if isinstance(hotel_offers, str):
        return json.dumps({"error": hotel_offers})

    parsed_results = []
    for offer in hotel_offers:
        hotel = offer.get("hotel", {})
        offers_list = offer.get("offers", [])

        offers_details = []
        for room_offer in offers_list:
            offers_details.append({
                "offer_id": room_offer.get("id", "N/A"),
                "check_in": room_offer.get("checkInDate", "N/A"),
                "check_out": room_offer.get("checkOutDate", "N/A"),
                "rate_code": room_offer.get("rateCode", "N/A"),
                "room_info": room_offer.get("room", {}).get("description", {}).get("text", "N/A"),
                "price": {
                    "total": room_offer.get("price", {}).get("total", "N/A"),
                    "currency": room_offer.get("price", {}).get("currency", "N/A")
                },
                "booking_link": room_offer.get("self", "N/A")
            })

        parsed_results.append({
            "hotel_name": hotel.get("name", "N/A"),
            "hotel_id": hotel.get("hotelId", "N/A"),
            "city_code": hotel.get("cityCode", "N/A"),
            "location": {
                "latitude": hotel.get("latitude", "N/A"),
                "longitude": hotel.get("longitude", "N/A")
            },
            "offers": offers_details
        })

    return json.dumps(parsed_results, indent=2)
